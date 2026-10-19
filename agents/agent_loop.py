from llm.ollama_client import chat_with_tools,chat_with_system
from tools.tool_definitions import RagInput,SearchInput
from rag.retrieve import retrieve_one_query
from dotenv import load_dotenv
from tools.search_tool import search_google
from tools.tool_selector import select_tools
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
    messages = history + [{"role": "user", "content": query}]
    system_prompt = "你是公司查询制度的智能体"

    for i in range(max_rounds):
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
