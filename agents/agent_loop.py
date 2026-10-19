from llm.ollama_client import chat_with_tools,chat_with_system
from tools.tool_definitions import RagInput,SearchInput
from rag.retrieve import retrieve_one_query
from dotenv import load_dotenv
from tools.search_tool import search_google
from tools.tool_selector import select_tools
from memory.preference_store import load_preferences,format_preferences
from config.settings import USER_ID
load_dotenv()

def check_sufficiency(messages:list[dict]) -> tuple[bool,str]:
    """
    判断当前检索结果能否回答用户问题，
    返回（是否需要补充检索，新查询词）
    """
    fanwen_prompt ="""
    你当前的检索结果能回答用户的问题吗？
    如果能，请只回答：YES
    如果不能，请按照格式回答：NO，新查询：你的新关键词
    """
    reflection_message =messages+[{"role":"user","content":fanwen_prompt}]
    reflection_text = chat_with_system(
        reflection_message,
        system="你是专门检测检索结果能否回答用户问题的",
    )
    print(f"[反思] {reflection_text}")
    if "YES" in reflection_text:
        return False,""
    new_query = reflection_text.split("新查询：")[-1].strip()
    if len(new_query)<2:
        return False,""
    return True,new_query

def run_agent(query: str, history: list[dict], max_rounds: int = 5) -> str:
    #每次调用都重新读取偏好（用户可能在上一轮补充了偏好）
    prefs = load_preferences(USER_ID)
    if prefs:
        prefs_text = "已知用户信息：\n" + format_preferences(prefs)
    else:
        prefs_text = ""

    messages = history + [{"role": "user", "content": query}]
    system_prompt = f"""
    你是公司的专业智能客服。回答用户问题时遵循以下原则：
    1. 优先使用工具检索到的文档信息；文档中明确提到不同做法时详细总结，相同做法时如实告知。
    2. 允许根据文档内容进行合理归纳和对比，但不要脱离检索结果虚构事实。
    3. 若检索结果完全未提及相关主题，再如实回答不知道。
    4. 历史对话的使用规则：
       - 当用户当前问题中出现"继续"、"刚才"、"上面"、"它"、"这个"等指向上文或需要上下文的表述时，结合历史对话回答；
       - 当用户的问题是全新的独立陈述或提问时，只回答当前内容，不要主动延续历史话题。
    5. 需要同时查询公司文档和其他信息时，请在同一轮次中调用所有相关工具，不要只调用一个。
    {prefs_text}
    语气要平易近人。
    """
    for i in range(max_rounds):
        # ① 看给了模型哪些工具
        selected = select_tools(query)
        print(f"[工具筛选] {[t['name'] for t in selected]}")

        response = chat_with_tools(messages, selected, system_prompt)
        content = response.get("content", [])

        # ② 看模型这轮干什么
        print(f"[第{i+1}轮] stop_reason={response.get('stop_reason')}")
        response = chat_with_tools(messages, select_tools(query), system_prompt)
        content = response.get("content", [])

        if response.get("stop_reason") != "tool_use":
            for block in reversed(content):
                if block.get("type") == "text":
                    return block["text"]
            return "没有拿到文本回答"

        # —— 模型要求调工具 ——
        messages.append({"role": "assistant", "content": content})

        for block in content:
            if block.get("type") != "tool_use":
                continue
            if block["name"] == "retrieve_company_docs":
                try:
                    valid = RagInput(**block["input"])
                    docs = retrieve_one_query(valid.query)
                    result = "\n\n".join(docs)
                except Exception as e:
                    result = f"检索失败：{e}"
            elif block["name"] == "search_google":
                try:
                    valid = SearchInput(**block["input"])
                    result = search_google(valid.query)
                except Exception as e:
                    result = f"搜索失败：{e}"
            else:
                result = f"未知工具：{block['name']}"

            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": block["id"],
                    "content": result,
                }],
            })
        # —— 反思：资料够不够 ——
        need_retry,new_query =check_sufficiency(messages)
        if need_retry:
            docs = retrieve_one_query(new_query)
            messages.append({
                "role":"user",
                "content":f"补充检索结果（关键词：{new_query}）：\n" + "\n\n".join(docs),
            })
    return "超过最大轮数"
