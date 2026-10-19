# 多 Agent RAG 智能客服系统

一个基于本地大模型的智能客服系统：用户提问后，Agent 自主判断是否检索公司内部文档或搜索网络信息，结合检索结果回答，并具备多轮对话记忆、用户偏好学习和历史压缩能力。

> 本项目由一个 770 行的单文件 Demo 重构而来——保留原有全部核心逻辑，修正其隐藏缺陷，并按工程化标准拆分为 16 个职责单一的模块。

## 功能特性

| 能力 | 说明 |
|------|------|
| 🔍 混合检索 | Chroma 向量检索 + BM25 关键词检索 + CrossEncoder 重排序，完整 chunk 级去重 |
| 🧠 查询改写 | 代词消解（"它" → "子公司"）+ 问题拆分 + Multi-Query 扩写 |
| 🔧 工具调用 | 模型自主选择 RAG 检索 / Google 搜索，Pydantic 校验工具参数 |
| 🎯 工具筛选 | 工具描述向量化入库，按问题相关性动态选取工具子集 |
| 🪞 自我反思 | 检索后由模型判断资料充分性，不足时自动补充检索 |
| 💬 对话记忆 | tiktoken 统计 token，超阈值自动压缩历史（摘要 + 最近 5 轮） |
| 💾 会话持久化 | Redis 保存对话历史，重启进程不丢上下文 |
| 👤 用户偏好 | 模型提取偏好 → SQLite 按用户存储 → 注入 system 实现个性化回答 |
| 🛡️ 反编造约束 | "继续"类追问强制触发检索，细节必须来自工具返回结果 |

## 架构

```text
┌──────────────────────────────────────────────────┐
│                   main.py 入口                    │
│   输入 → 偏好提取 → 历史压缩 → Agent → 输出        │
└───────────────┬──────────────────────────────────┘
                ↓
┌──────────────────────────────────────────────────┐
│           agents/agent_loop  工具调用循环          │
│   调模型 → 需要工具？→ 执行 → 反思 → 再调模型      │
└──────┬──────────────┬──────────────┬─────────────┘
       ↓              ↓              ↓
┌────────────┐ ┌────────────┐ ┌─────────────────┐
│ tools/ 工具 │ │ rag/ 检索   │ │ memory/ 记忆     │
│ 工具定义     │ │ 知识库切块   │ │ 对话压缩(token)  │
│ 工具筛选     │ │ 向量+BM25   │ │ 偏好存储(SQLite) │
│ 网络搜索     │ │ 多query合并 │ │ 会话持久化(Redis)│
└────────────┘ └────────────┘ └─────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│         llm/ollama_client  模型调用层              │
│   chat / chat_with_history / chat_with_tools      │
│   chat_with_system（requests 直连，绕过 SDK 502）  │
└──────────────────────────────────────────────────┘
```

## 项目结构

```text
├── main.py                        # 入口：交互循环、偏好提取、历史压缩
├── config/
│   └── settings.py                # 全局配置（模型、地址、阈值、用户ID）
├── llm/
│   └── ollama_client.py           # 四种模型调用方式（单轮/多轮/带工具/带system）
├── agents/
│   └── agent_loop.py              # Agent 主循环 + 自我反思
├── tools/
│   ├── tool_definitions.py        # Pydantic 工具定义 → JSON Schema
│   ├── tool_selector.py           # 工具描述向量检索，动态选取工具
│   └── search_tool.py             # Serper Google 搜索
├── rag/
│   ├── knowledge_base.py          # 文档粗切+语义细切、Chroma/BM25 初始化
│   ├── cache_utils.py             # chunks/BM25 缓存管理
│   ├── retrieve.py                # 单 query 检索 + 多 query 合并重排
│   ├── query_processor.py         # 代词消解、问题拆分与扩写
│   └── rag_pipeline.py            # 旧版直连 RAG 流程（保留备查）
├── memory/
│   ├── conversation_summarizer.py # token 统计、历史压缩、摘要生成
│   ├── preference_store.py        # SQLite 偏好存储（按用户隔离）
│   ├── preference_extractor.py    # 模型提取用户偏好（JSON 解析兜底）
│   └── session_store.py           # Redis 会话持久化
└── prompts/
    └── prompt_templates.py        # 全部提示词模板
```

## 快速开始

### 环境要求

- Python 3.10+
- [Ollama](https://ollama.com/) 已安装并运行，已拉取模型 `qwen3:8b`
- Redis 服务已启动（Windows 可用 Memurai 或 WSL）

### 安装

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 API Key（Google 搜索工具用，可选）
#    在项目根目录创建 .env 文件：
SERPER_API_KEY=你的key

# 3. 确认 Ollama 与 Redis 可用
ollama list
redis-cli ping
```

### 运行

```bash
python main.py
```

首次运行会自动完成：读取文档 → 粗切+语义细切 → 向量化写入 Chroma → 构建 BM25 索引（约几分钟）。之后启动走缓存，秒级就绪。

### 试试这些问题

```text
子公司的管理制度是什么？          → 触发 RAG 检索
今天上海的天气怎么样？            → 触发 Google 搜索
我叫小罗，我喜欢简洁的回答        → 提取偏好，后续回答自动变简洁
它的授权审批有什么要求？          → 代词消解，检索自动补全实体
继续回答。                       → 强制补充检索，基于资料续答
（重启程序后）我刚才问了什么？     → Redis 恢复会话，记得上文
```

## 配置说明

`config/settings.py`：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `MODEL_NAME` | `qwen3:8b` | 本地 Ollama 模型 |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `MAX_TOKENS` | `1000` | 模型单次回复上限 |
| `HISTORY_COMPRESS_THRESHOLD` | `2000` | 历史超过该 token 数触发压缩 |
| `USER_ID` | `default_user` | 当前用户标识（预留多用户） |
| `DEBUG` | `False` | 调试开关，开启后打印检索细节 |

## 关键设计决策

**1. 为什么工具调用用 requests 而不用 Anthropic SDK？**
Ollama 的 Anthropic 兼容层（`/v1/messages`）对 SDK 附带的请求头处理有缺陷，会返回 502。实测 requests 直连同接口正常，故带工具的调用绕过 SDK，直接发标准 Anthropic 协议请求。切换云端模型（如 DeepSeek 的 Anthropic 兼容接口）时只需改 `settings.py` 的地址和 key。

**2. 为什么检索函数返回 `list[str]` 而不是拼接字符串？**
原版用 `"\n".join` 传 chunk，下游再 `split("\n")` 拆开——多行 chunk 的边界被破坏，去重和重排的对象变成了"行"而非"块"。现在全程传递完整 chunk 列表，仅在最终给 LLM 时才拼接。

**3. 为什么"继续"要强制检索？**
实测发现小模型在"继续回答"的压力下会用参数知识编造细节（半真半假最难识别）。与其靠 prompt 约束，不如让"继续"必须经过工具检索——资料进来了，编造的动机和空间同时消失。

**4. 为什么数据文件路径全部钉死到项目根目录？**
相对路径（`./chroma_db`）随运行目录变化，曾导致两套数据库并存、工具筛选静默返回空。现在所有数据文件（向量库、缓存、SQLite）基于代码自身位置解析，从任何目录启动行为一致。

## 相对原版的改进

原版单文件存在的部分问题，本项目已修复：

| 原版问题 | 修复方式 |
|----------|----------|
| 多行 chunk 被 `split("\n")` 拆碎 | 检索函数全程返回 chunk 列表 |
| 工具循环无退出条件，可能死循环 | `max_rounds` 上限 + `stop_reason` 判断 |
| RAG 工具调用列表未声明即使用 | 循环内直接处理，无需收集列表 |
| reranker 每次检索重新加载 | 模块级加载一次 |
| `MAX_TOKENS` 一名两义 | 拆分为回复上限/压缩阈值两个配置 |
| SQLite 无用户隔离，且偏好无限重复 | 增加 `user_id` 列 + 唯一索引 |
| 建索引遇脏数据直接崩溃 | 自动去重后重建索引 |

## License

仅供学习交流使用。
