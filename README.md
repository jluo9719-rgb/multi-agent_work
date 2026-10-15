# 多 Agent 协作项目

这是一个从单文件 Demo 重构而来的多 Agent 协作项目。

## 当前目标

第一阶段目标：完成项目模块化。

## 项目结构

- main.py：项目入口
- config/：配置文件
- llm/：模型调用封装
- agents/：不同 Agent
- tools/：工具函数
- rag/：RAG 检索模块
- prompts/：提示词
- data/：知识库数据

---

第 3 步：先只迁移“模型调用”

这是第一刀，别急着迁移 Agent。

你先从原来的 多agent.py 里面找出：

调用 Ollama / 大模型的代码

可能长得像：

requests.post(...)

或者：

ollama.chat(...)

或者：

client.chat(...)

然后把它挪到：

llm/ollama_client.py

目标是让这个文件对外只暴露一个函数，比如：

def chat(prompt: str) -> str:
    ...

或者：

def call_llm(prompt: str) -> str:
    ...

名字你可以先用 chat，简单。