"""
【检索员】Retriever
  目标：给定问题和线索，找出相关证据
  输入：question（必须）、hint（可选，审核员给出的缺失关键词）
  查询构造：
      - 无 hint：build_search_queries(question) 拆分并扩写，取前 max_queries 个
      - 有 hint：按 [,，、空格] 拆分 hint 直接使用，不再扩写
                （hint 已是审核员提炼的关键词，再拆解只会带入泛词）
  内部：不判断够不够——充分性判断权归审核员，避免职责重复
  输出：evidence 列表，每条为 {text, source}
  边界：不生成答案、不判断充分性

【审核员】Reviewer
  目标：判断证据是否足以回答问题
  输入：question + evidence 列表
  判断方式：让模型读「问题 + 证据」，问"能不能回答"
            ❌ 不用向量匹配（query 有结果 ≠ 结果有用）
  输出：{okay: true}
         或 {okay: false, missing: "关键词，如：2023年第三季度,净利润"}
        missing 必须是关键词而非完整句子，会被检索员直接当作查询词
  边界：不检索、不生成答案

【回答员】Answerer
  目标：只根据证据作答
  输入：question + evidence 列表
  处理：evidence 拼成字符串塞进 prompt
  输出：最终答案字符串
  边界：证据里没有的就明说不知道，不许编

【编排】MultiAgentLoop
  1. evidence = retrieve(question)
  2. verdict = review(question, evidence)
  3. while not verdict.okay and rounds < max_rounds:
        新证据 = retrieve(question, hint=verdict.missing)
        evidence = rerank_evidences(question, evidence + 新证据)
        verdict = review(question, evidence)
        rounds += 1
     合并后必须重排：新证据按时间顺序追加，重排后噪声会被挤出前 store 条
  4. return answer(question, evidence)

  边界：只看 verdict 结论和 missing，不解析证据内容
  上限：max_rounds（默认 2，即最多 2 次补充检索）
  注意：无论最终 verdict 是否通过，都把现有证据交给回答员；
        回答员负责在证据不足时如实说明"资料未提及"
"""


import json
import re

from llm.ollama_client import chat_with_system
from rag.query_processor import build_search_queries
from rag.retrieve import retrieve_evidence, rerank_evidences
from memory.preference_store import load_preferences,format_preferences
from config.settings import USER_ID
from rag.query_processor import rewrite_query
from tools.search_tool import search_google
from llm.ollama_client import chat_stream_text_yield

#审核员
def review(question, evidence):
    r = []
    for i,doc in enumerate(evidence):
      c= doc.get("text","")
      r.append(f"参考文献{i}:{c}")
    prompt =f"""
    你是专门审核检索结果能否回答用户问题的审核员，不要参杂任何东西。根据用户输入的问题和检索的内容，判断此检索能否回答用户的问题。输出只能是json格式，不要任何其他文字。
    如果能回答用户问题则输出：
    {{"okay": true}}
    如果不能回答用户问题则输出：
    {{"okay": false, "missing": "用一个或者多个关键词说明缺少的东西,例如:缺少2023年第三季度的净利润数字,那么只需要提取:2023年第三季度,净利润。两个词作为missing的值"}}
    """
    message = [{"role":"user","content":f"用户问题：{question},检索结果：{r}"}]
    response  = chat_with_system(messages=message,system=prompt)
    try:
        result = json.loads(response)
    except:
        result = {"okay":False,"missing":"审核员输出解析失败"}
    return result
       
#检索员
def retrieve(question, hint=None, max_queries=6) -> list[dict]:
    evidence =[]
    if hint:
        parts= re.split("[,，、 ]",hint.strip())
        queries =[]
        for i in parts:
            p=i.strip()
            if p:
                queries.append(p)
    else:
        queries =build_search_queries(question)[:max_queries]
    docs = retrieve_evidence(question,queries)
    for c in docs:
        evidence.append({"text":c,"source":""})
    if hint:
        web_q = f"{question}{' '.join(queries)}"   #拼起来搜一次
        web = search_google(web_q)
        if web:
            evidence.append({"text":web,"source":"web"})
    return evidence
        

#回答员
def answer(question,evidence,prefs_text="",history =None) -> str:
    r=[]
    if not evidence:
        return "你的问题暂时无法回答，请稍后再试"
    for i,c in enumerate(evidence):
        r.append(f"资料{i}:{c.get('text','')}")
    text = "\n".join(r)
    system_prompt =f"""
    你是公司智能客服，要根据检索到的参考资料组织语言回答用户问题，要和蔼可亲，参考资料是本次检索的事实来源，历史对话只用来理解用户指的是什么（比如“第三条”），两者冲突时以参考资料为准回答的内容要根据资料来，资料里面没有的东西不要说，不要胡编乱造。回答涉及具体数字时，必须核对该数字所属的年份、期间、主体是否与用户问题一致。资料中出现多年份对比（如"2025年/2024年/2023年"）时，只取用户问题所问年份的那一列，不得混用。资料若来自后续年份的报告（如用2025年报说明2024数据），表中"本年""比上年"等表述指的是报告发布年份，不是用户所问年份。引用增长率时必须核对它属于哪一年。资料中的百分比、同比等衍生指标，除非能明确确认归属年份，否则不要引用，只给出原始数值。如果无法确定数字归属，就说"资料中的年份对应关系不明确"，不要猜测。只允许归纳总结，但不许补充资料外的信息。分点总结，字数尽量控制在300字以内,其中{prefs_text}是系统用户的偏好，你要根据此偏好来回答。
    """
    if history:
        messages = history[-4:]+[{"role":"user","content":f"问题：{question}\n\n参考资料：{text}"}]
    else:
        messages =[{"role":"user","content":f"问题：{question}\n\n参考资料：{text}"}]
    return chat_with_system(messages=messages,system=system_prompt)

#流式输出回答
def answer_stream(question,evidence,prefs_text="",history=None):
    r=[]
    if not evidence:
        yield "你的问题暂时无法回答，请稍后再试"  
        return
    for i,c in enumerate(evidence):
        r.append(f"资料{i}:{c.get('text','')}")
    text = "\n".join(r) 
    system_prompt =f"""
    你是公司智能客服，要根据检索到的参考资料组织语言回答用户问题，要和蔼可亲，参考资料是本次检索的事实来源，历史对话只用来理解用户指的是什么（比如“第三条”），两者冲突时以参考资料为准回答的内容要根据资料来，资料里面没有的东西不要说，不要胡编乱造。回答涉及具体数字时，必须核对该数字所属的年份、期间、主体是否与用户问题一致。资料中出现多年份对比（如"2025年/2024年/2023年"）时，只取用户问题所问年份的那一列，不得混用。资料若来自后续年份的报告（如用2025年报说明2024数据），表中"本年""比上年"等表述指的是报告发布年份，不是用户所问年份。引用增长率时必须核对它属于哪一年。资料中的百分比、同比等衍生指标，除非能明确确认归属年份，否则不要引用，只给出原始数值。如果无法确定数字归属，就说"资料中的年份对应关系不明确"，不要猜测。只允许归纳总结，但不许补充资料外的信息。分点总结，字数尽量控制在300字以内,其中{prefs_text}是系统用户的偏好，你要根据此偏好来回答。
    """
    if history:
        messages = history[-4:]+[{"role":"user","content":f"问题：{question}\n\n参考资料：{text}"}]
    else:
        messages =[{"role":"user","content":f"问题：{question}\n\n参考资料：{text}"}]
    for token in chat_stream_text_yield(messages=messages,system=system_prompt):
        yield token


#编排层
def run_multi_agent(question,history=None, max_rounds=2):
    prefs = load_preferences(USER_ID)
    prefs_text = ("已知用户信息：\n"+format_preferences(prefs)) if prefs else ""
    if history:
        full_question = rewrite_query(question,history)
    else:
        full_question = question
    evidence = retrieve(full_question)
    print(f"[检索]第一轮：{len(evidence)}")
    verdict = review(full_question,evidence)
    print(verdict)
    c=0
    while not verdict.get("okay")  and  c<max_rounds:
        missing = verdict.get("missing","")
        if not missing or missing=="审核员输出解析失败":
            break
        result = retrieve(full_question,hint=missing)
        evidence = evidence+result
        evidence = rerank_evidences(full_question,evidence)
        print(f"去重后的条数：{len(evidence)}")
        verdict = review(full_question,evidence)
        c+=1
    answers = answer(full_question,evidence,prefs_text,history)
    return answers
            
#流式输出编排层
def run_multi_agent_stream(question,history=None, max_rounds=2):
    prefs = load_preferences(USER_ID)
    prefs_text = ("已知用户信息：\n"+format_preferences(prefs)) if prefs else ""
    if history:
        full_question = rewrite_query(question,history)
    else:
        full_question = question
    evidence = retrieve(full_question)
    print(f"[检索]第一轮：{len(evidence)}")
    verdict = review(full_question,evidence)
    print(verdict)
    c=0
    while not verdict.get("okay")  and  c<max_rounds:
        missing = verdict.get("missing","")
        if not missing or missing=="审核员输出解析失败":
            break
        result = retrieve(full_question,hint=missing)
        evidence = evidence+result
        evidence = rerank_evidences(full_question,evidence)
        print(f"去重后的条数：{len(evidence)}")
        verdict = review(full_question,evidence)
        c+=1
    for token in answer_stream(full_question,evidence,prefs_text,history):
        yield token