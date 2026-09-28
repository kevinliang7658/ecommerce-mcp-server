"""
Ollama 私有化模型的 FastAPI 业务网关

为什么不直接让业务系统调 Ollama 的原生接口（/api/generate）？
  1) Ollama 提供 OpenAI 兼容端点（/v1），业务方用标准 openai SDK 就能调，
     本网关在这个基础上再包一层"业务友好"接口：入参只要一句话，
     系统提示词、模型名、温度等都在服务端统一管控；
  2) 以后底层换模型（qwen2.5 -> llama3.1 -> 内部微调版），业务系统零改动；
  3) 这一层是将来加鉴权、限流、日志、成本统计的地方。

这一层就是面向"大模型"这个外部服务的防腐层（ACL）/ BFF。

启动（开发）：
  pip install -r ../requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
  uvicorn app:app --host 0.0.0.0 --port 8000
启动（生产/演示完整环境）：直接看项目根目录 docker-compose.yml
"""

import os
import time

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# ---------------- 配置（环境变量可覆盖） ----------------
# Docker Compose 里指向 ollama 容器；本地开发默认 localhost
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen3.5:4b")

# 统一管控的系统提示词：定义助手人设与边界，业务方不用关心
SYSTEM_PROMPT = os.environ.get(
    "SYSTEM_PROMPT",
    "你是公司的内部业务助手，回答请简洁、专业、说人话，不确定的事情不要编造。",
)

app = FastAPI(title="私有化大模型业务网关", version="1.0.0")


# ---------------- 请求/响应模型（相当于 Java 的 DTO） ----------------
class AskRequest(BaseModel):
    question: str = Field(..., description="用户问题", min_length=1)
    temperature: float = Field(0.3, description="采样温度，越低越稳", ge=0.0, le=2.0)


class AskResponse(BaseModel):
    answer: str
    model: str
    total_duration_ms: int  # Ollama 返回的总耗时（纳秒换算成毫秒），演示"私有化响应速度"


@app.get("/health")
def health() -> dict:
    """健康检查：顺带确认 Ollama 在线、模型已拉取（docker-compose 的 healthcheck 也用它）。"""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        models = [m["name"] for m in resp.json().get("models", [])]
        return {"status": "up", "ollama": "connected", "models": models}
    except requests.RequestException as e:
        return {"status": "degraded", "ollama": f"unreachable: {e}"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    """
    业务问答接口：一句话进，答案出。
    底层走 Ollama 的 OpenAI 兼容端点 /v1/chat/completions。
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": req.question},
        ],
        "temperature": req.temperature,
        "stream": False,
    }
    started = time.time()
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions",
            json=payload,
            timeout=120,  # 本地模型推理较慢，超时要给足
        )
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Ollama 服务不可达: {e}")

    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Ollama 返回错误: {resp.status_code} {resp.text[:200]}")

    data = resp.json()
    answer = data["choices"][0]["message"]["content"]
    # 在网关这一层自己掐表统计耗时（Ollama 的 OpenAI 兼容端点不一定回传耗时字段）
    duration_ms = int((time.time() - started) * 1000)
    return AskResponse(answer=answer, model=OLLAMA_MODEL, total_duration_ms=duration_ms)


# ---------------- 本地直接运行：python app.py ----------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
