"""
ollama模型调用封装

职责：
1：封装和本地ollama的交互
2：对外提供统一的chat函数
3：让其他模块不用关心requests细节
"""

# import requests
# from config.settings import OLLMA_BASE_URL,MODEL_NAME
# def chat(prompt:str)->str:
#     """
#     调用本地Ollama模型，返回模型回答，这个是ollama的原生协议
#     """
#     url = f"{OLLMA_BASE_URL}/api/chat"
#     payload = {
#         "model":MODEL_NAME,
#         "messages":[
#             {
#                 "role":"user",
#                 "content":prompt,
#             }
#         ],
#         "stream":False,
#     }
#     response = requests.post(url,json=payload)
#     response.raise_for_status()
#     data = response.json()
#     return data["message"]["content"]

import requests
from config.settings import OLLAMA_BASE_URL,MODEL_NAME,MAX_TOKENS,API_KEY
from anthropic import Anthropic
client = Anthropic(
    api_key=API_KEY,
    base_url=OLLAMA_BASE_URL
)

def chat(prompt:str)->str:
    """
    使用 Anthropic 兼容接口调用本地 Ollama 模型
    """
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        messages = [{"role":"user","content":prompt}],
    )
    return response.content[-1].text

def chat_with_history(messages : list[dict]) -> str:
    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=MAX_TOKENS,
        messages = messages,
    )
    return response.content[-1].text

def chat_with_tools(messages : list[dict],tools:list,system : str="") -> object:
    """
    带工具调用：直接用 requests 请求 Ollama 的 Anthropic 兼容接口。
    Anthropic SDK 在 Ollama 兼容层上会 502，因此这里绕过 SDK。
    返回 dict（JSON 响应），而不是 SDK 对象。
    """
    payload = {
        "model": MODEL_NAME,
        "max_tokens": MAX_TOKENS,
        "messages": messages,
        "tools": tools,
    }
    if system:
        payload['system'] =system
    response = requests.post(
        f"{OLLAMA_BASE_URL}/v1/messages",   # ← settings 里的地址
        headers={
            "Content-Type":"application/json",
            "x-api-key":API_KEY,            # ← settings 里的 "ollama"
            "anthropic-version":"2023-06-01",  # ← 固定值，Anthropic 协议要求的版本号
        }, 
        json= payload,
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def chat_with_system(messages : list[dict],system : str="") -> str:
    """
    带工具调用：直接用 requests 请求 Ollama 的 Anthropic 兼容接口。
    Anthropic SDK 在 Ollama 兼容层上会 502，因此这里绕过 SDK。
    返回 dict（JSON 响应），而不是 SDK 对象。
    多轮对话 + 系统提示，返回文本。
    用于反思等辅助判断，不涉及工具调用。
    """
    payload = {
        "model": MODEL_NAME,
        "max_tokens": MAX_TOKENS,
        "messages": messages,
    }
    if system:
        payload['system'] =system
    response = requests.post(
        f"{OLLAMA_BASE_URL}/v1/messages",   # ← settings 里的地址
        headers={
            "Content-Type":"application/json",
            "x-api-key":API_KEY,            # ← settings 里的 "ollama"
            "anthropic-version":"2023-06-01",  # ← 固定值，Anthropic 协议要求的版本号
        }, 
        json= payload,
        timeout=120,
    )
    response.raise_for_status()  #检查状态码
    data =response.json()  #解析成dict
    text = []
    for block in data.get("content",[]):
        if block.get("type") =="text":
            text.append(block.get("text",""))
    return "\n".join(text)