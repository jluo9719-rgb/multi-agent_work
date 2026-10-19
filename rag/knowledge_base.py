import os
import re
import shutil

import chromadb
import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from sklearn.metrics.pairwise import cosine_similarity

from rag import cache_utils

# 路径钉死到项目根目录，不受运行目录影响
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")

client_chromadb = chromadb.PersistentClient(path=CHROMA_PATH)
embedder = SentenceTransformer("moka-ai/m3e-base")

#粗切
def my_chunk(text):
    lines = text.split("\n")
    chunk = []     
    current_chunk = []  
    for line in lines:
        if re.match(r"## \d+\.\d+",line.strip()) or re.match(r"- \d+\.\d+",line.strip()) or re.match(r"\d+\.\d+",line.strip()):   
            chunk.append("\n".join(current_chunk))   
            current_chunk =[]    
        current_chunk.append(line)   
    if current_chunk:   
        chunk.append("\n".join(current_chunk))
    return chunk


#细切
def semantic_chunk(text):   
    paragraphes = text.split("\n") 
    embeddings = embedder.encode(paragraphes)  
    final_chunks= []
    current_chunk=[]
    for i,para in enumerate(paragraphes):
        if "|" in para and "---" not in para:
            continue
        if not current_chunk:
            current_chunk.append(para)
        else:
            sim = cosine_similarity([embeddings[i-1]],[embeddings[i]])[0][0]
            if sim>0.7: 
                current_chunk.append(para)
            else:
                final_chunks.append("\n".join(current_chunk))
                current_chunk=[para]
    if current_chunk:
        final_chunks.append("\n".join(current_chunk))
    return final_chunks



def generate_chunks():
    """
    重新生成 chunks 的函数（当缓存失效时调用）
    包含完整的切分流程：粗切 + 细切
    """

    # 读取文档
    with open("d:\\python projects\\agent\\RAG2\\神火股份：河南神火煤电股份有限公司内部控制管理手册.txt", "r", encoding="utf-8") as f:
        text =f.read()  #读取表格
        lines = [l for l in text.split('\n') if l.strip()]
        policy_text = '\n'.join(lines)

    # 粗切分
    chunk1 = my_chunk(policy_text)
    print(f"   粗切完成，共 {len(chunk1)} 个块")

    # 细切分
    final_chunks = []
    for c in chunk1:
        sub = semantic_chunk(c)
        final_chunks.extend(sub)
    return final_chunks
chunks = cache_utils.get_chunks_with_cache(generate_chunks)

cache_valid = cache_utils.is_cache_valid()
vector_valid = cache_utils.is_vectorstore_valid()

if cache_valid and vector_valid:
    # client 已在顶部创建，直接获取 collection
    collection = client_chromadb.get_or_create_collection(name="ljs")
else:
    # 需要重建：删除旧目录后重新创建 client 和 collection
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
    client_chromadb = chromadb.PersistentClient(path=CHROMA_PATH)
    collection = client_chromadb.get_or_create_collection(name="ljs")

    ids = [f"id_policy_{i}" for i in range(len(chunks))]
    vectors = embedder.encode(chunks)

    collection.add(
        documents=chunks,
        embeddings=vectors,
        ids=ids
    )

    cache_utils.save_vector_version()


bm25_index = cache_utils.load_bm25_cache()

if bm25_index is None:
    tokenized_chunks = [list(jieba.cut(chunk)) for chunk in chunks]
    bm25_index = BM25Okapi(tokenized_chunks)
    cache_utils.save_bm25_cache(bm25_index)


reranker = CrossEncoder("BAAI/bge-reranker-large")

