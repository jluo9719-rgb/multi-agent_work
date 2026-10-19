import os
import requests

SERPER_URL = "https://google.serper.dev/search"
from dotenv import load_dotenv
load_dotenv()

def search_google(query: str) -> str:
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        return "搜索失败：未配置 SERPER_API_KEY"

    try:
        resp = requests.post(
            SERPER_URL,
            headers={"X-API-KEY": api_key},
            json={"q": query},
            timeout=15,
        )
        if resp.status_code != 200:
            return f"搜索失败：状态码 {resp.status_code}"
        data = resp.json()
    except Exception as e:
        return f"搜索失败：{e}"

    answer_box = data.get("answerBox") or {}
    if answer_box.get("answer"):
        return f"答案：{answer_box['answer']}。来源：{answer_box.get('source', '')}。链接：{answer_box.get('sourceLink', '')}"

    organic = data.get("organic", [])[:3]
    if not organic:
        return "没有找到相关搜索结果"

    lines = [
        f"标题：{item.get('title', '')}。链接：{item.get('link', '')}。摘要：{item.get('snippet', '')}"
        for item in organic
    ]
    return "参考链接：\n\n" + "\n\n".join(lines)