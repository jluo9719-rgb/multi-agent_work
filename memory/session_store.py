import json
import redis

SESSION_KEY ="session" 
r = redis.Redis(host="localhost",port=6379,socket_timeout=5)

def save_session(history: list[dict]) -> None:
    try:
        r.set(SESSION_KEY,json.dumps(history,ensure_ascii=False))  # 中文正常显示 
    except redis.RedisError as e:
        print(f"[session]保存失败：{e}")

def load_session() ->list[dict]:
    try:
        data = r.get(SESSION_KEY)
        if data:
            return json.loads(data)
    except redis.RedisError as e:
        print(f"[session]读取失败：{e}")
    except json.JSONDecodeError as e:
        print(f"[session] 数据损坏，重新开始会话：{e}")
    return []