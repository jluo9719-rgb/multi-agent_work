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
import json
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



def chat_stream_text(messages:list[dict],system:str="") ->str:
    """
    流式调用模型（暂不支持工具）。
    每收到一段答案文字就打印出来，最终返回完整文本。
    """
    payload ={
        "model":MODEL_NAME,
        "max_tokens":MAX_TOKENS,
        "messages":messages,
        "stream":True,
    }
    if system:
        payload['system']=system
    response=requests.post(
        f"{OLLAMA_BASE_URL}/v1/messages",
        headers={
            "Content-Type":"application/json",
            "x-api-key":API_KEY,
            "anthropic-version":"2023-06-01",
        },
        json=payload,
        stream=True,
        timeout=120,
    )
    response.raise_for_status()
    full_text =[]
    for line in response.iter_lines():
        if not line:
            continue
        text =line.decode("utf-8")
        if not text.startswith("data: "):
            continue
        data = json.loads(text[len("data: "):])
        if data.get("type") !="content_block_delta":
            continue
        delta = data.get("delta",{})
        if delta.get("type") !="text_delta":
            continue
        token = delta.get("text","")
        full_text.append(token)
        print(token,end="",flush=True)   #实时显示
    print()
    return "".join(full_text)


#完整版本的流式打印
def chat_stream_with_tools(messages,tools,system :str =""):
    payload ={
        "model":MODEL_NAME,
        "max_tokens":MAX_TOKENS,
        "messages":messages,
        "tools":tools,
        "stream":True,
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
            stream=True,
        )
    response.raise_for_status()
    blocks ={}
    stop_reason = None
    for line in response.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8")
        if not text.startswith("data: "):
            continue
        json_str = text[len("data: "):]  
        data = json.loads(json_str)
        if data.get("type") == "content_block_start":
            index= data.get("index")
            raw = data.get("content_block")   # 里面有 type，可能还有 id、name
            blocks[index] ={
                "type":raw.get("type"),
                "id":raw.get("id"),
                "name":raw.get("name"),
                "text":"",          #text块的文字积累
                "thinking":"",      #thinking块的思考累计
                "partial_json":"",  #tool_use块的参数碎片积累
            }
        elif data.get("type") =="content_block_delta":
            index = data.get("index")
            delta =data.get("delta",{})
            if delta.get("type") =="text_delta":
                blocks[index]["text"] +=delta["text"]
                yield("text",delta["text"])
            elif delta.get("type") =="thinking_delta":
                blocks[index]["thinking"] += delta["thinking"]
            elif delta.get("type") =="input_json_delta":
                blocks[index]['partial_json'] +=delta["partial_json"]
        elif data.get("type") =="message_delta":
            stop_reason =data.get("delta",{}).get("stop_reason")
    #print(blocks)  查看此时block是什么模样
    content =[]
    for index in sorted(blocks):
        b =blocks[index]
        if b["type"] =="thinking":
            content.append({"type":"thinking","thinking":b["thinking"]})
        elif b["type"] =="text":
            content.append({"type":"text","text":b["text"]})
        elif b["type"] == "tool_use":
            input_query =json.loads(b["partial_json"]) if b["partial_json"] else {}
            content.append({"type":"tool_use","id":b["id"],"name":b["name"],"input":input_query})
    result = {"content":content,"stop_reason":stop_reason}
    yield ("done", result)
            
