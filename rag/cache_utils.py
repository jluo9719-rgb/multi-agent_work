"""
缓存工具模块 - 管理 RAG 系统的 chunks 和 BM25 索引缓存
缓存文件存放在当前目录下的 cache/ 文件夹
"""

import os
import json
import pickle
import hashlib

# ============================================================
# 1. 缓存目录和版本号配置
# ============================================================

# 缓存文件存放目录（钉死到项目根目录，不受运行目录影响）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(BASE_DIR, "cache")

# 缓存文件路径
CHUNKS_CACHE_FILE = os.path.join(CACHE_DIR, "chunks_cache.json")  # chunks 缓存：存储切分后的文本块
BM25_CACHE_FILE = os.path.join(CACHE_DIR, "bm25_index.pkl")         # BM25 索引缓存：存储序列化后的 BM25 模型

# 文档路径（用于计算 hash，判断文档是否改变）
DOC_PATH = r"D:\python projects\agent\RAG2\神火股份：河南神火煤电股份有限公司内部控制管理手册.txt"

# 代码版本号（每次修改切分逻辑后手动 +1，强制重新生成缓存）
CODE_VERSION = "1.1"

# 向量化版本号（每次修改向量模型后 +1，强制重建向量库）
EMBED_VERSION = "1.1"


# ============================================================
# 2. 初始化缓存目录
# ============================================================

def init_cache_dir():
    """
    确保缓存目录存在
    缓存目录: ./cache/
    """
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


# ============================================================
# 3. 计算文档内容的 MD5 hash
# ============================================================

def get_doc_hash():
    """
    计算文档的 MD5 hash
    用于判断文档是否被修改过（如果文档变了，缓存失效）
    文档路径: DOC_PATH
    返回: MD5 hash 字符串
    """
    if not os.path.exists(DOC_PATH):
        return None  # 文档不存在，返回 None
    with open(DOC_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return hashlib.md5(content.encode()).hexdigest()


# ============================================================
# 4. 生成缓存 key（文档 hash + 代码版本号）
# ============================================================

def get_cache_key():
    """
    生成缓存的唯一标识 key
    规则: 文档内容的 MD5 hash + 代码版本号
    如果文档变了或代码版本变了，key 就不同，缓存失效
    返回: 字符串 "doc_hash_code_version"
    """
    doc_hash = get_doc_hash()
    if doc_hash is None:
        return None
    return f"{doc_hash}_{CODE_VERSION}"


def get_embed_version():
    """
    获取向量库版本号
    用于判断向量库是否需要重建
    """
    return EMBED_VERSION


def is_vectorstore_valid():
    """
    检查向量库是否有效
    向量库有效条件：
      - chroma_db 目录存在
      - vector_version.txt 存在且版本号匹配
    """
    chroma_path = os.path.join(BASE_DIR, "chroma_db")
    if not os.path.exists(chroma_path):
        return False
    version_file = os.path.join(CACHE_DIR, "vector_version.txt")
    if not os.path.exists(version_file):
        return False
    with open(version_file, "r", encoding="utf-8") as f:
        saved_version = f.read().strip()
    return saved_version == get_embed_version()


def need_rebuild_vectorstore():
    """
    判断是否需要重建向量库
    条件：cache 有效 但 向量库无效
    （说明 chunks 没变，但向量化工具变了）
    """
    cache_valid = is_cache_valid()
    vector_valid = is_vectorstore_valid()
    return cache_valid and not vector_valid


# ============================================================
# 5. 检查缓存是否有效
# ============================================================

def is_cache_valid():
    """
    判断缓存是否有效
    规则:
      - 缓存文件存在
      - cache_key.txt 存在且里面的 key 与当前计算的一致
    如果文档或代码版本变了，缓存失效
    返回: True 有效 / False 无效
    """
    key_file = os.path.join(CACHE_DIR, "cache_key.txt")

    # 如果缓存目录不存在，肯定无效
    if not os.path.exists(CACHE_DIR):
        return False

    # 如果 key 文件不存在，肯定无效
    if not os.path.exists(key_file):
        return False

    # 读取之前的 key
    with open(key_file, "r", encoding="utf-8") as f:
        saved_key = f.read().strip()

    # 计算当前的 key
    current_key = get_cache_key()

    # 不匹配说明缓存过期
    if current_key is None or saved_key != current_key:
        return False

    # 检查 chunks 缓存文件是否存在
    if not os.path.exists(CHUNKS_CACHE_FILE):
        return False

    return True


# ============================================================
# 6. 保存缓存 key（文档 hash + 代码版本号）
# ============================================================

def save_cache_key():
    """
    将当前的 cache key 保存到 cache_key.txt
    保存位置: ./cache/cache_key.txt
    """
    init_cache_dir()  # 确保目录存在
    key = get_cache_key()
    key_file = os.path.join(CACHE_DIR, "cache_key.txt")
    with open(key_file, "w", encoding="utf-8") as f:
        f.write(key)


def save_vector_version():
    """
    保存向量库版本号
    保存位置: ./cache/vector_version.txt
    """
    init_cache_dir()
    version_file = os.path.join(CACHE_DIR, "vector_version.txt")
    with open(version_file, "w", encoding="utf-8") as f:
        f.write(get_embed_version())


# ============================================================
# 7. 加载 chunks 缓存
# ============================================================

def load_chunks_cache():
    """
    从缓存文件加载 chunks
    缓存文件: ./cache/chunks_cache.json
    返回: chunks 列表 或 None（如果缓存无效）
    """
    if not is_cache_valid():
        return None  # 缓存无效，返回 None

    try:
        with open(CHUNKS_CACHE_FILE, "r", encoding="utf-8") as f:
            chunks = json.load(f)
        print(f"✅ 从缓存加载了 {len(chunks)} 个 chunks")
        return chunks
    except Exception as e:
        print(f"⚠️ 加载 chunks 缓存失败: {e}")
        return None


# ============================================================
# 8. 保存 chunks 到缓存
# ============================================================

def save_chunks_cache(chunks):
    """
    将 chunks 保存到缓存文件
    缓存文件: ./cache/chunks_cache.json
    参数:
      chunks: 列表，每个元素是一个切分后的文本块
    """
    init_cache_dir()  # 确保目录存在
    save_cache_key()  # 保存当前的 cache key

    with open(CHUNKS_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"💾 保存了 {len(chunks)} 个 chunks 到缓存")


# ============================================================
# 9. 加载 BM25 索引缓存
# ============================================================

def load_bm25_cache():
    """
    从缓存文件加载 BM25 索引
    缓存文件: ./cache/bm25_index.pkl
    返回: BM25Okapi 对象 或 None（如果缓存无效）
    """
    if not is_cache_valid():
        return None

    try:
        with open(BM25_CACHE_FILE, "rb") as f:
            bm25_index = pickle.load(f)
        print("✅ 从缓存加载了 BM25 索引")
        return bm25_index
    except Exception as e:
        print(f"⚠️ 加载 BM25 缓存失败: {e}")
        return None


# ============================================================
# 10. 保存 BM25 索引到缓存
# ============================================================

def save_bm25_cache(bm25_index):
    """
    将 BM25 索引保存到缓存文件
    缓存文件: ./cache/bm25_index.pkl
    参数:
      bm25_index: BM25Okapi 对象
    """
    init_cache_dir()
    with open(BM25_CACHE_FILE, "wb") as f:
        pickle.dump(bm25_index, f)
    print("💾 保存了 BM25 索引到缓存")


# ============================================================
# 11. 清除所有缓存（当需要强制重新生成时调用）
# ============================================================

def clear_cache():
    """
    清除所有缓存文件
    缓存目录: ./cache/
    """
    if os.path.exists(CACHE_DIR):
        import shutil
        shutil.rmtree(CACHE_DIR)
        print("🗑️ 已清除所有缓存")


# ============================================================
# 12. 主入口：获取 chunks（带缓存逻辑）
# ============================================================

def get_chunks_with_cache(chunk_func):
    """
    获取 chunks 的主入口函数
    如果缓存有效，直接返回缓存的 chunks
    如果缓存无效，调用 chunk_func 重新生成，并保存缓存

    参数:
      chunk_func: 一个函数，调用时返回重新切分的 chunks 列表

    返回: chunks 列表
    """
    # 尝试从缓存加载
    chunks = load_chunks_cache()

    if chunks is not None:
        # 缓存有效，直接返回
        return chunks

    # 缓存无效，重新生成
    print("📦 缓存无效，重新生成 chunks...")
    chunks = chunk_func()

    # 保存新的缓存
    save_chunks_cache(chunks)

    return chunks


# ============================================================
# 使用示例（使用时取消注释）
# ============================================================

if __name__ == "__main__":
    # 测试缓存是否有效
    print(f"缓存目录: {CACHE_DIR}")
    print(f"文档路径: {DOC_PATH}")
    print(f"代码版本: {CODE_VERSION}")
    print(f"缓存有效: {is_cache_valid()}")