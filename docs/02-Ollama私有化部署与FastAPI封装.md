# 02 - Ollama 私有化部署演示：装 Ollama → 拉 qwen2.5 → OpenAI 兼容 API → FastAPI 业务网关

> 目标：在自己的机器（或公司内网服务器）上跑一个开源大模型，并用 FastAPI 包一层业务接口，
> 模拟"数据不出内网"的企业私有化落地。全程可以用 Docker Compose 一键起，也可以手工分步做。

## 为什么要私有化部署（先想清楚）

- **数据合规**：金融、医疗、政务等行业数据不能出内网，公有云 API 直接排除；
- **成本**：高频内部场景（客服辅助、文档摘要）用本地模型，token 成本为 0（只有电费和机器折旧）;
- **可控**：模型版本自己钉死，不怕厂商升级导致线上效果漂移。

代价也要知道：本地 7B 模型能力明显弱于 DeepSeek/GPT 级别的大模型，适合"格式规整、任务简单"的内部场景，复杂推理还是得上云端大模型——**混合路由（简单的走本地、难的走云端）是企业真实常态**。

## 路线一：Docker Compose 一键部署（推荐演示用）

前提：已安装 Docker Desktop。

```bash
cd ecommerce-mcp-server

# 1. 构建并启动两个容器（ollama + gateway）
docker compose up -d --build

# 2. 首次需要手动拉取模型（qwen2.5:7b 约 4.7GB，耐心等；模型存在 volume 里，下次不用重拉）
docker exec -it ollama ollama pull qwen2.5:7b

# 3. 验证网关健康（能看到 models 列表里有 qwen2.5:7b）
curl http://localhost:8000/health

# 4. 业务调用
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"question\":\"用三句话介绍跨境电商的海外仓模式\"}"
```

架构（Compose 内部网络，类似 K8s 的 Service 互访）：

```
业务系统/curl ──▶ gateway 容器 (FastAPI, :8000) ──http://ollama:11434──▶ ollama 容器 (:11434)
                      │                                                        │
                      │  统一管控：system prompt / 模型名 / 温度 / 耗时统计       │  qwen2.5:7b
                      │  未来可加：鉴权 / 限流 / 日志                            │  存在 volume 里
```

## 路线二：Windows 本地手工部署（理解每一步在干嘛）

### 1. 安装 Ollama

从 Ollama 官网下载安装包安装，装完后命令行验证：

```bash
ollama --version
```

Ollama 默认会常驻后台并监听 `http://localhost:11434`。

### 2. 拉取 qwen2.5

```bash
ollama pull qwen2.5:7b      # 约 4.7GB
ollama list                 # 确认模型已在列表里
```

机器内存小于 16G 的话换小模型：`ollama pull qwen2.5:1.5b`（约 1GB，速度快但笨一些，够演示）。
显存/内存越大能跑的模型越大：大致经验是模型文件大小 ≈ 所需内存下限。

### 3. 两种调用方式（重点认知）

Ollama 同时提供两套 API：

| 端点 | 风格 | 适用 |
| --- | --- | --- |
| `POST /api/generate`、`/api/chat` | Ollama 原生协议 | 只有 Ollama 认，换了推理引擎就要改代码 |
| `POST /v1/chat/completions` | **OpenAI 兼容协议** | openai SDK 直接能用，和调 DeepSeek 的代码一模一样，只换 base_url |

先用 OpenAI 兼容方式手动验证（不用装任何 SDK）：

```bash
curl http://localhost:11434/v1/chat/completions -H "Content-Type: application/json" -d "{\"model\":\"qwen2.5:7b\",\"messages\":[{\"role\":\"user\",\"content\":\"你好，一句话介绍你自己\"}]}"
```

这条命令值得多看两眼：**和调 DeepSeek 的区别只有 URL 和 model 名**——OpenAI 兼容协议已经成为行业事实标准，这就是"网关思想"能成立的基础。

### 4. 用 FastAPI 包一层业务接口

为什么不能把 `localhost:11434` 直接给业务系统？因为业务系统不该关心"用什么模型、system prompt 是什么、温度调多少"，这些应该由服务端统一管控（详见 `ollama_gateway/app.py` 开头的注释）。

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
cd ollama_gateway
python app.py          # 等价于 uvicorn app:app --host 0.0.0.0 --port 8000
```

验证：

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d "{\"question\":\"退货政策一般包含哪几个要点\"}"
```

浏览器打开 `http://localhost:8000/docs` 还能看到 FastAPI 自动生成的 Swagger 文档（Java 同学熟悉的 Swagger UI，FastAPI 白送）。

## 常见问题

| 问题 | 处理 |
| --- | --- |
| `ollama pull` 很慢 | 换时间段，或配置代理；模型只需拉一次 |
| 推理慢/卡 | 换 1.5b 小模型；有 NVIDIA 显卡的话 Ollama 会自动用 GPU（`ollama ps` 可见 GPU 标识） |
| gateway 报 502 Ollama 不可达 | 本地模式确认 Ollama 在跑；Compose 模式确认环境变量是 `http://ollama:11434` 而不是 localhost |
| 中文回答质量差/乱说 | 7B 模型的正常水平，把 system prompt 写具体、给示例（few-shot）能明显改善 |

## 进阶方向

- **混合路由**：网关里加规则——意图简单的走本地 qwen2.5，复杂的走 DeepSeek，成本与效果兼得；
- **RAG 私有化**：Embedding 也用本地模型（Ollama 跑 bge-m3），配合 Milvus，整套 RAG 数据零出网；
- **流式输出**：FastAPI 端用 `StreamingResponse` 转发 Ollama 的 SSE 流，前端打字机效果；
- **微调**：用 LLaMA-Factory（GitHub 开源项目）按公司语料微调 qwen2.5，再让 Ollama 加载微调产物。
