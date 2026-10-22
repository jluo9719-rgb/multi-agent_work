from fastapi import FastAPI
from pydantic import BaseModel
from agents.agent_loop import run_agent,run_agent_stream
from memory.session_store import save_session,load_session
from memory.conversation_summarizer import compress_history
from memory.preference_extractor import extract_preferences
from memory.preference_store import save_preferences
from fastapi.responses import StreamingResponse  
import asyncio
import json
app =FastAPI()

@app.get("/health")
def health():
    return {"status":"ok"}

class ChatRequest(BaseModel):   #用户发进来的数据长什么模样
    session_id: str
    message : str 

class EchoResponse(BaseModel):  #我们返回出去的数据长什么模样
    message : str

class ChatResponse(BaseModel):  #我们返回出去的数据长什么模样
    answer : str

@app.post("/echo",response_model =ChatResponse)    #response_model=ChatResponse → 告诉 FastAPI："返回的数据按这个模型序列化"
def echo(req : ChatRequest) -> ChatResponse:
#传输中：req:  '{"session_id": "user-a", "message": "你好"}'     ← 文本（JSON 字符串）
#程序里：req:   ChatRequest(session_id="user-a", message="你好")  ← 对象（ChatRequest 实例）
#req.model_dump()    # → {"session_id": "user-a", "message": "你好"}
    return EchoResponse(message=req.message)


@app.post("/chat",response_model =ChatResponse)    
def chat(req : ChatRequest) -> ChatResponse:
    prefs =extract_preferences(req.message)
    if prefs:
        save_preferences("default_user",prefs)
    history = load_session(req.session_id)
    history.append({"role":"user","content":req.message})
    history =compress_history(history)
    answer = run_agent(req.message,history)
    history.append({"role":"assistant","content":answer})
    save_session(req.session_id,history)
    return ChatResponse(answer=answer)



@app.get("/stream-demo")   #测试流式输出
def stream_demo():
    async def demo_generator():
        for i in range(5):
            yield f"data:第{i+1}段\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(
        demo_generator(),
        media_type="text/event-stream",
    )

@app.post("/chat/stream")   #流式
def chat_stream(req:ChatRequest):
    def event_generator():
         # 第 1 步：偏好 + 历史（照抄 /chat）
        prefs = extract_preferences(req.message)
        if prefs:
            save_preferences("default_user",prefs)
        history = load_session(req.session_id)
        history.append({"role":"user","content":req.message})
        history =compress_history(history)
         # 第 2 步：遍历生成器，边收边发
        full_text = []
        for token in run_agent_stream(req.message,history):  #token是一小段文字
            full_text.append(token)
            yield f"data: {json.dumps({'text': token}, ensure_ascii=False)}\n\n"
        # 第 3 步：流结束后，收尾
        answer = "".join(full_text)
        history.append({"role": "assistant", "content": answer})
        save_session(req.session_id, history)
        # 第 4 步：发送结束标记
        yield "data: [DONE]\n\n"
    return StreamingResponse(event_generator(), media_type="text/event-stream")