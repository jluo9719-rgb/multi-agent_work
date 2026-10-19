"""项目入口文件
职责：
1：接收用户输入
2：调用对应的agent
3：输出最终结果

"""

import os
os.environ["NO_PROXY"] = "localhost,127.0.0.1"   
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"   # HuggingFace 国内镜像
from dotenv import load_dotenv
load_dotenv()


from memory.conversation_summarizer import compress_history
from memory.preference_extractor import extract_preferences
from memory.preference_store import save_preferences
from config.settings import USER_ID
from agents.agent_loop import run_agent
from memory.session_store import save_session,load_session
def main():
    history = load_session()
    while True:
        query = input("\n请输入问题，输入q退出：")
        if query.lower()== "q":
            print("程序已退出")
            break
        prefs = extract_preferences(query)   #提取用户偏好
        if prefs:
            save_preferences(USER_ID,prefs)
        history.append({"role":"user","content":query})
        history = compress_history(history)
        answer = run_agent(query,history)
        history.append({"role":"assistant","content":answer})
        save_session(history)
        print(answer)

if __name__=="__main__":
    main()

