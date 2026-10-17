# 聊天历史：每轮都写、每轮都读、会话结束就可以不要 → 热数据 → Redis（内存，快）
# 用户偏好：偶尔写入、偶尔读取、要长期保留       → 冷数据 → SQLite（磁盘，稳）
# 职责：SQLite 建表、写入、按用户读取，这里是sqlite

import os
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "entity_memory.db")

#模块加载时建表(IF NOT EXIST 保证不重复运行不报错)
conn = sqlite3.connect(DB_PATH,check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS entities(        
            id INTEGER PRIMARY KEY AUTOINCREMENT,   
            user_id TEXT,
            entity_key TEXT,                       
            entity_value TEXT,      
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
            )
    """)
conn.commit()

def save_preferences(user_id : str,prefs : dict) -> None:   #将prefs这个字典存入sqlite
    #遍历prefs，每队key/value执行INSERT OR REPLACE 
    for key,value in prefs.items():
        cursor.execute(
            "INSERT OR REPLACE INTO entities (user_id,entity_key,entity_value) VALUES (?,?,?)",
            (user_id,key,value)
        )
    conn.commit()

def load_preferences(user_id : str) -> dict:
    #SELECT 全部行，拼成dict返回
    prefs ={}
    cursor.execute("SELECT entity_key,entity_value FROM entities WHERE user_id=?",(user_id,))
    rows =cursor.fetchall()
    for key,value in rows:
        prefs[key] = value
    return prefs

def format_preferences(prefs : dict) -> str:
    # 把 {"称呼": "小刘", "喜欢": "简洁回答"}
    # 转成 "称呼：小刘\n喜欢：简洁回答" 这样的文本
    return "\n".join(
        f"{key}：{value}" for key,value in prefs.items()
    )
