import json
import redis


def _session_key(session_id:str) -> str:
    return f"session:{session_id}"
r = redis.Redis(host="localhost",port=6379,socket_timeout=5)

def save_session(session_id : str,history: list[dict]) -> None:
    try:
        r.set(_session_key(session_id),json.dumps(history,ensure_ascii=False))  # 中文正常显示 
    except redis.RedisError as e:
        print(f"[session]保存失败：{e}")

def load_session(session_id:str) ->list[dict]:
    try:
        data = r.get(_session_key(session_id))
        if data:
            return json.loads(data)
    except redis.RedisError as e:
        print(f"[session]读取失败：{e}")
    except json.JSONDecodeError as e:
        print(f"[session] 数据损坏，重新开始会话：{e}")
    return []