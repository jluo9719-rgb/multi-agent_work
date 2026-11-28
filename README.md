# 多 Agent RAG 智能客服后端

一个从 770 行单文件 Demo 逐步演进而来的智能客服项目，目前包含两种 Agent 实现：

- **单 Agent 工程化版本**：`agents/agent_loop.py`
- **三角色多 Agent 版本**：`agents/multi_agent_loop.py`

项目支持本地 Ollama 模型、公司内部文档 RAG、网页搜索、用户偏好、多轮历史、Redis 会话持久化，以及 FastAPI 普通接口和 SSE 流式接口。

## 当前入口

| 入口 | 使用的 Agent | 说明 |
|---|---|---|
| `main.py` | `agent_loop.py` | CLI 命令行版本，目前仍使用单 Agent |
| `api/server.py` | `multi_agent_loop.py` | FastAPI 后端，使用多 Agent |
| `/chat` | `run_multi_agent()` | 普通问答，完整答案一次返回 |
| `/chat/stream` | `run_multi_agent_stream()` | SSE 流式问答，逐段返回文本 |
| `/health` | — | 健康检查 |

## 多 Agent 架构

多 Agent 版本把原来共享同一个 `messages` 的循环，拆成三个职责明确的角色：

```text
用户问题 + 历史
        │
        ▼
查询改写 rewrite_query()
        │
        ▼
检索员 retrieve()
  - 无 hint：问题拆分、扩写、内部文档检索
  - 有 hint：按关键词直接补充检索
  - 补充轮次可调用网页搜索
        │ evidence: [{"text": ..., "source": ...}]
        ▼
审核员 review()
  - 只判断证据是否足够回答问题
  - 输出 {"okay": true}
    或 {"okay": false, "missing": "关键词"}
        │
        ├────────────── 不足 ──────────────┐
        │                                ▼
        │                    编排层带 missing 再检索
        │                    合并、去重、重排证据
        │                                │
        └────────────── 达到上限或足够 ───┘
        │
        ▼
回答员 answer() / answer_stream()
  - 只根据证据作答
  - 结合用户偏好与最近历史理解追问
  - 证据不足时明确说明资料未提及
        │
        ▼
普通字符串 / SSE 流式文本
        │
        ▼
Redis 保存会话历史
```

### 三个角色的边界

| 角色 | 负责 | 不负责 |
|---|---|---|
| 检索员 | 构造查询、检索内部文档、补充网页搜索 | 不生成最终答案，不判断证据是否充分 |
| 审核员 | 判断证据是否足够，指出缺失关键词 | 不自行检索，不生成最终答案 |
| 回答员 | 根据证据组织答案，处理偏好与追问 | 不自行检索，不补充证据外事实 |
| 编排层 | 控制轮次、传递证据和审核结论、调用回答 | 不解析证据内容，不代替角色做判断 |

## 功能特性

| 能力 | 实现 |
|---|---|
| 混合检索 | Chroma 向量检索 + BM25 关键词检索 + CrossEncoder 重排序 |
| 查询改写 | 代词消解、问题拆分、Multi-Query 扩写 |
| 多轮补充检索 | 审核员发现不足后，编排层带 `missing` 关键词再次检索 |
| 网页搜索 | 补充轮次调用 Serper Google 搜索，失败返回 `None` |
| 网页证据保留 | `rerank_evidences()` 对内部文档重排，网页证据不参与截断淘汰 |
| 用户偏好 | 模型提取偏好，SQLite 按用户保存，注入回答提示词 |
| 多轮对话 | Redis 保存历史，查询改写处理“它”“第三条”等追问 |
| 历史压缩 | 超过 token 阈值时压缩旧历史 |
| 普通 API | `/chat` 返回完整 JSON |
| 流式 API | `/chat/stream` 以 SSE 逐段返回文本，结束后发送 `[DONE]` |
| 防幻觉约束 | 证据优先于历史；数字、年份、主体需要与问题对应 |

## 项目结构

```text
├── main.py                         # CLI 入口，当前仍使用单 Agent
├── api/
│   └── server.py                   # FastAPI 接口：健康检查、普通问答、SSE 流式问答
├── agents/
│   ├── agent_loop.py               # 单 Agent 工程化版本
│   └── multi_agent_loop.py         # 检索员、审核员、回答员与多 Agent 编排
├── config/
│   └── settings.py                 # 模型、地址、token 阈值、用户 ID
├── llm/
│   └── ollama_client.py            # 普通、多轮、工具、流式模型调用
├── rag/
│   ├── knowledge_base.py           # 文档切分、Chroma/BM25、模型初始化
│   ├── cache_utils.py              # chunks 与 BM25 缓存管理
│   ├── retrieve.py                 # 单 query、多 query、证据列表与重排
│   ├── query_processor.py          # 查询改写、拆分、扩写
│   └── rag_pipeline.py             # 旧版 RAG 流程，保留备查
├── memory/
│   ├── conversation_summarizer.py  # 历史压缩
│   ├── preference_store.py         # SQLite 用户偏好
│   ├── preference_extractor.py     # 偏好提取
│   └── session_store.py            # Redis 会话持久化
├── tools/
│   ├── tool_definitions.py         # 工具 JSON Schema 定义
│   ├── tool_selector.py            # 工具描述向量筛选，供旧版 Agent 使用
│   └── search_tool.py              # Serper 网页搜索
├── prompts/
│   └── prompt_templates.py         # 查询改写、拆分、偏好提取等提示词
├── Dockerfile                      # 曾用于本地容器化验证
├── run.bat                         # 本地环境启动脚本（含本机路径）
├── requirements.txt
└── README.md
```

## 环境准备

### 必需服务

- Python 3.11+
- Ollama，并已拉取 `qwen3:8b`
- Redis

启动 Ollama：

```bash
ollama serve
```

检查模型：

```bash
ollama list
```

### 可选服务

网页搜索需要在项目根目录的 `.env` 中配置：

```dotenv
SERPER_API_KEY=你的key
```

没有配置时，内部文档问答仍可使用；网页搜索会返回空结果。

### 安装依赖

```bash
pip install -r requirements.txt
```

首次运行会读取文档、切分并建立向量库与 BM25 索引；之后使用缓存启动。

本地已有 HuggingFace 模型缓存时，`knowledge_base.py` 默认设置 `HF_HUB_OFFLINE=1`，避免启动时联网检查版本导致超时。需要重新下载模型时可显式覆盖该环境变量。

## 启动方式

### CLI

```bash
python main.py
```

注意：CLI 当前仍调用旧的 `run_agent()`，不是多 Agent 编排。

### FastAPI

```bash
uvicorn api.server:app --host 127.0.0.1 --port 8000
```

开发调试时可加 `--reload`，但**测试流式响应时不要频繁保存 Python 文件**，因为自动重载会重启进程并中断 SSE 连接。

打开接口文档：

```text
http://127.0.0.1:8000/docs
```

## API 示例

### 普通问答

请求：

```http
POST /chat
Content-Type: application/json
```

```json
{
  "session_id": "demo-001",
  "message": "公司采购审批流程是怎样的？"
}
```

响应：

```json
{
  "answer": "……"
}
```

继续追问时使用相同 `session_id`：

```json
{
  "session_id": "demo-001",
  "message": "第三条详细说说"
}
```

### SSE 流式问答

请求：

```http
POST /chat/stream
Content-Type: application/json
```

```json
{
  "session_id": "stream-001",
  "message": "公司采购审批流程是怎样的？"
}
```

响应格式：

```text
data: {"text": "小罗"}

data: {"text": "，"}

data: {"text": "公司"}

...

data: [DONE]
```

服务端会在流式回答结束后拼接完整文本，并保存到对应 Redis 会话。

## 配置说明

`config/settings.py`：

| 配置项 | 当前默认值 | 说明 |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama 服务地址 |
| `MODEL_NAME` | `qwen3:8b` | 本地模型 |
| `MAX_TOKENS` | `2000` | 单次回复 token 上限 |
| `HISTORY_COMPRESS_THRESHOLD` | `2000` | 历史压缩阈值 |
| `USER_ID` | `default_user` | 当前偏好用户标识，尚未做真正多用户隔离 |
| `DEBUG` | `False` | 调试开关 |

Redis 地址和密码由 `memory/session_store.py` 读取环境变量：

- `REDIS_HOST`
- `REDIS_PORT`
- `REDIS_PASSWORD`

## 关键设计决策

### 为什么从单 Agent 改成多 Agent

原单 Agent 把用户问题、工具调用、工具结果、反思结论都放进同一个 `messages`。它能工作，但角色边界不清，调试时难以定位问题。

多 Agent 版本把流程拆成“找证据、审证据、用证据回答”，每个角色只接收自己需要的数据。主要收益是**边界清晰、可定位、可替换**，不是单纯追求更快。

### 为什么证据在 Agent 间使用列表，而给模型时拼接字符串

审核员需要按条检查证据，不能依赖被换行拼接后的文本；回答员则需要适合放入 prompt 的文本。因此内部交接使用 `list[dict]`，最终调用模型前再格式化。

### 为什么补充检索使用 hint 关键词

`missing` 是审核员对缺失信息的提炼。如果再次把 hint 送入完整问题扩写流程，可能产生泛化查询并带入噪声。因此 hint 直接拆分为关键词使用。

### 为什么网页证据不参与内部文档的重排淘汰

网页搜索是为了补充内部文档不足。如果与内部文档一起按原问题重排并截断，网页证据可能因相关性分数较低而被删除，导致补充检索失去意义。因此网页证据单独保留。

### 为什么部分模型调用使用 requests

Ollama 的 Anthropic 兼容层 `/v1/messages` 曾与 Anthropic SDK 的默认请求头不兼容，出现 502。项目因此使用 requests 直接构造请求。

### 为什么设置 HF_HUB_OFFLINE

本地 embedding 与 reranker 模型已经缓存。启动时访问 HuggingFace 检查版本在国内网络环境下可能长时间重试，因此默认跳过在线检查。

## 已验证场景

- 公司采购审批流程：能够检索内部控制手册并生成有依据的回答
- “第三条详细说说”：结合历史理解追问指向
- 知识库没有季度净利润数据：审核员判断不足，回答员不编造具体数值
- 网页搜索：能够获取外部资料，并保留网页证据
- 普通 `/chat`：返回答案并保存会话
- 流式 `/chat/stream`：逐段返回 SSE，结束后发送 `[DONE]` 并保存会话

## 当前限制

- CLI 与 FastAPI 使用不同 Agent 实现，尚未统一
- 多 Agent 流式接口在检索和审核阶段不会输出进度，只有最终回答阶段逐段输出
- 偏好仍主要使用 `default_user`，不是完整的多用户系统
- 网页搜索依赖 Serper 配置和网络环境
- 小模型仍可能出现数字归属、表格列含义等语义错误，提示词约束不是绝对保证
- Dockerfile 曾用于本地容器验证，但当前镜像已删除；`run.bat` 含本机路径，不是通用部署脚本
- 尚未提供正式前端页面

## 后续计划

1. 增加前端聊天页面，接入 `/chat/stream`
2. 统一 CLI 与 FastAPI 的 Agent 入口
3. 完善异常处理、流式错误事件与测试
4. 增加可核对的来源标记和数字校验
5. 根据实际部署环境重新整理 Docker 配置

## License

仅供学习交流使用。
