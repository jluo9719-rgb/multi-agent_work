from llm.ollama_client import chat_with_tools
from tools.tool_definitions import TOOLS, RagInput,SearchInput
from rag.retrieve import retrieve_one_query
from pydantic import ValidationError
from dotenv import load_dotenv
from tools.search_tool import search_google
from tools.tool_selector import select_tools
load_dotenv()

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
    return "超过最大轮数"

if __name__ == "__main__":
    print("=== 内部文档 ===")
    print(run_agent("子公司的管理制度是什么？", []))

    print("\n=== 网络搜索 ===")
    print(run_agent("今天上海的天气怎么样？", []))