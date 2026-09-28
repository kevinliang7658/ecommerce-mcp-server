# FastAPI 业务网关镜像（Ollama 私有化部署演示用）
FROM python:3.12-slim

# 国内构建走清华镜像，装依赖快且稳
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 只拷贝网关代码（MCP Server 不在这个容器里跑）
COPY ollama_gateway/app.py /app/app.py

EXPOSE 8000
# 容器里通过环境变量 OLLAMA_BASE_URL=http://ollama:11434 找到 ollama 服务
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
