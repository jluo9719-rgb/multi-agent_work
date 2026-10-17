# 聊天历史：每轮都写、每轮都读、会话结束就可以不要 → 热数据 → Redis（内存，快）
# 用户偏好：偶尔写入、偶尔读取、要长期保留       → 冷数据 → SQLite（磁盘，稳）
# 职责：调用模型，从 query 提取偏好，返回 dict，这里是sqlite

import json
from llm.ollama_client import chat
from prompts.prompt_templates import build_extract_prompt

def extract_preferences(query : str) -> dict:
    prompt = build_extract_prompt(query)
    raw = chat(prompt)
    try:
        prefs =json.loads(raw)
    except json.JSONDecodeError:
        prefs ={}
    if not isinstance(prefs,dict):
        prefs = {}
    return prefs

