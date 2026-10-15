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