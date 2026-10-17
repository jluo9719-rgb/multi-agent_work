#这是一个流程编排层

from rag.query_processor import build_search_queries,rewrite_query
from rag.retrieve import retrieve_context
from prompts.prompt_templates import build_answer_prompt
from llm.ollama_client import chat,chat_with_history
from memory.preference_store import load_preferences,format_preferences
from config.settings import USER_ID

def answer_with_rag(query : str,history:list[dict]) -> str:
    resolved_query = rewrite_query(query,history)
    search_queries =build_search_queries(resolved_query)
    print(f"最终用于检索的问题是：{search_queries}")
    context = retrieve_context(query,search_queries)
    print(f"合并后的检索上下文：{context}")
    prefs = load_preferences(USER_ID)   #读取存储的偏好
    extra_messages = []
    if prefs:
        prefs_text = format_preferences(prefs)
        preference_message = {"role":"system","content":f"用户偏好：\n{prefs_text}"}
        extra_messages.append(preference_message)
    #将检索到的上下文加入history给ai看
    messages = [{"role":"system","content":f"参考资料：\n{context},请只依据以上资料回答用户的问题；资料中没有依据时，明确说明无法确定，不要编造。"}] +history+extra_messages
    answer = chat_with_history(messages)
    return answer


