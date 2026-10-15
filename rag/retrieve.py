# 1. RAG 初始化对象
# 2. 单 query 检索函数
# 3. 多 query 合并检索函数

import jieba

from rag.knowledge_base import collection, embedder, bm25_index, chunks, reranker


def retrieve_one_query(query : str) -> list[str]:
    query_vector = embedder.encode([query])
    result = collection.query(query_embeddings=query_vector, n_results=5)
    result_docs = result["documents"][0] if result["documents"] else []
    tokenized_query = list(jieba.cut(query))
    bm25_scores = bm25_index.get_scores(tokenized_query)
    top5_indics = bm25_scores.argsort()[-5:][::-1]
    bm25_docs = [chunks[i] for i in top5_indics]
    seen = set()
    combined =[]
    for doc in result_docs:
        if doc not in seen:
            seen.add(doc)
            combined.append(doc)
    for doc in bm25_docs:
        if doc not in seen:
            seen.add(doc)
            combined.append(doc)
    candidates = combined
    pairs =[[query,doc] for doc in candidates]  #用query和doc配对打分
    scores =reranker.predict(pairs)
    ranked_indices =scores.argsort()[::-1]
    reranked_docs = [candidates[i] for i in ranked_indices]   #此时是列表
    # final_result = "\n".join(reranked_docs[:5])  #取top5，并且用换行符连接起来
    # print(f"检索结果：{final_result}")  #此时这里变成了文本（换行的文本块）
    return reranked_docs[:5]   #取排名前五的列表（每一个是一个最开始切分的chunk块）

def retrieve_context(original_query : str,queries : list) -> str:
    contexts =[]
    for query in queries:
        context =retrieve_one_query(query)
        if context:
            contexts.extend(context)   #此时是一个很大的列表，这个列表里面有重复的内容
    seen = set()
    unique_docs = []
    for doc in contexts:
        if doc and doc not in seen:
            seen.add(doc)
            unique_docs.append(doc)
    if not unique_docs:
        return ""
    pairs=[[original_query,doc] for doc in unique_docs]
    scores=reranker.predict(pairs)
    reranker_indices = scores.argsort()[::-1]
    sorted_docs = [unique_docs[i] for i in reranker_indices]
    return "\n\n".join(sorted_docs[:5])