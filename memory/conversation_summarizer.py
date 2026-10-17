# 1. 接收消息列表
# 2. 提取 content
# 3. 调用摘要 prompt
# 4. 调用 chat
# 5. 返回摘要
from config.settings import HISTORY_COMPRESS_THRESHOLD
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")   #使用OpenAI用的编码
def count_tokens(text):
    return len(enc.encode(text))


def count_token(messages : list[dict]) -> int:
    total_count = 0
    for message in messages:
        content = message.get("content","")
        if isinstance(content,str):
            total_count +=count_tokens(content)
        elif isinstance(content,list):
            for block in content:
                if hasattr(block,"text") and block.text:
                    total_count +=count_tokens(block.text)
                elif hasattr(block,"thinking") and block.thinking:
                    total_count +=count_tokens(block.thinking)
    return total_count

def need_compress(messages : list[dict]) -> bool:
    total = count_token(messages)
    if total>HISTORY_COMPRESS_THRESHOLD:
        return True
    else:
        return False

def get_recent_pairs(messages : list[dict],num_pairs :int=5) ->list[dict] :
    if len(messages) <= num_pairs * 2:
        return messages
    return messages[-2*num_pairs:]
    
def get_old_messages(messages : list[dict],num_pairs : int=5) -> list[dict]:
    if len(messages) <= num_pairs *2:
        return []
    return messages[: -2*num_pairs]


from llm.ollama_client import chat
from prompts.prompt_templates import build_summary_prompt
def summarize_messages(messages : list[dict]) -> str:
    if not messages:
        return "没有历史对话"
    old_text="\n".join([
            f"用户：{m.get('content','')}" if m.get('role') =="user"
            else f"AI:{m.get('content','')}"
            for m in messages
        ])
    answer = chat(build_summary_prompt(old_text))
    return answer


def compress_history(messages : list[dict]) -> list[dict]:
    if need_compress(messages):
        old_messages = get_old_messages(messages)
        summary = summarize_messages(old_messages)
        summary_message = {"role":"system","content":f"对话历史总结：{summary}"}
        new_sys_msg = [summary_message]+get_recent_pairs(messages)
        return new_sys_msg
    return messages