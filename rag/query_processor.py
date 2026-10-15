def parse_split_result(split_result : str,original_query : str) -> list[str]:
    text = split_result.strip()   #去除前后空格
    if "拆分为：" in text :   #拆分为：子公司的制度是什么？ | 总公司的制度是什么？
        final_text = text.split("拆分为：",1)[-1]   #从拆分为处切口并且取后面的部分
    elif "拆分为:" in text:
        final_text = text.split("拆分为:",1)[-1]   #1的意思是从第一个拆分为开始切
    else:
        return [original_query]

    sub_queries = []
    for item in final_text.split("|"):
        query = item.strip()
        if query:
            sub_queries.append(query)
    if sub_queries:
        return sub_queries
    return [original_query]


import re
def parse_multi_query_result(multi_query_result : str) -> list[str]:
    multi_query = []
    for line in multi_query_result.splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^\d+[\.\、\)\: :]\s*","",line)   #去掉前面的数字编号
        if line:
            multi_query.append(line)
    return multi_query

from llm.ollama_client import chat
from prompts.prompt_templates import build_multi_query_prompt,build_split_prompt,build_query_rewrite_prompt
def build_search_queries(original_query : str) -> list[str]:
    split_query = chat(build_split_prompt(original_query))
    #print(f"拆分的问题为：{split_query}")

    questions = parse_split_result(split_query,original_query)
    #print(f"解析后的问题列表为：{questions}") 

    all_queries = []
    for question in questions:
        multi_query = chat(build_multi_query_prompt(question))
        expand_query = parse_multi_query_result(multi_query)
        all_queries.append(question)
        all_queries.extend(expand_query)
    return all_queries

def rewrite_query(query,history) -> str:
    history_text = ""
    if not history:
        return query
    for i in history:
        if i.get("role")=="user": 
            history_text += f"用户：{i.get('content','')}\n"
        else:
            history_text += f"AI:{i.get('content','')}\n" 
    history_text= history_text.strip()
    prompt = build_query_rewrite_prompt(query,history_text)
    answer =chat(prompt)
    return answer.strip()
