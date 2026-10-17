"""项目入口文件

职责：
1：接收用户输入
2：调用对应的agent
3：输出最终结果

当前阶段：
先测试llm是否可以正常调用
"""

# from llm.ollama_client import chat 
# def main():
#     print("多agent协作项目启动成功。")
#     print("当前阶段：测试LLM调用")
#     while True:
#         user_question = input("\n请输入问题，输入q退出：")
#         if user_question.lower()== "q":
#             print("程序已退出")
#             break
#         answer = chat(user_question)
#         print(answer)

# if __name__=="__main__":
#     main()
import os
os.environ["NO_PROXY"] = "localhost,127.0.0.1"   
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"   # HuggingFace 国内镜像

from rag.rag_pipeline import answer_with_rag
from memory.conversation_summarizer import compress_history
from memory.preference_extractor import extract_preferences
from memory.preference_store import save_preferences
from config.settings import USER_ID
def main():
    print("多agent协作项目启动成功。")
    print("当前阶段：测试LLM调用")
    history =[]
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
        answer = answer_with_rag(query,history)
        history.append({"role":"assistant","content":answer})
        print(answer)

if __name__=="__main__":
    main()

