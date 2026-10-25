"""
项目配置文件：

职责：
1：管理模型名称
2：管理ollama地址
3：管理知识库路径
4：管理其他全局配置
"""

#本地ollama模型
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "qwen3:8b"
MAX_TOKENS = 1000
API_KEY = "ollama"
HISTORY_COMPRESS_THRESHOLD = 2000
USER_ID = "default_user"
DEBUG = False