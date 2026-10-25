
# ① 基础镜像
FROM python:3.11-slim

# ② 工作目录
WORKDIR /app

# ③ 环境变量
ENV PYTHONUNBUFFERED=1 \
    HF_ENDPOINT=https://hf-mirror.com

# ④ 先装依赖（利用 Docker 分层缓存）
COPY requirements.txt .
# RUN pip install --no-cache-dir torch==2.9.1 -i https://pypi.tuna.tsinghua.edu.cn/simple
# RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
# 先装 CPU 版 torch（官方 CPU 源，wheel 小得多）
RUN pip install --no-cache-dir torch==2.9.1 --index-url https://download.pytorch.org/whl/cpu
# 再装其余依赖（-i 指定清华源，同时允许 --extra-index-url 补 CPU torch）
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# ⑤ 复制项目代码
COPY . .

# ⑥ 声明端口（实际映射靠 docker run -p）
EXPOSE 8000

# ⑦ 启动命令（--host 0.0.0.0 才能被外部访问）
CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]