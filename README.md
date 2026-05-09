# shoppilot

电商智能客服 Agent — FastAPI + LangGraph + DeepSeek + Chroma + Redis。

## 快速开始

```bash
cp .env.example .env          # 填入 DEEPSEEK_API_KEY
make up                        # 起 redis-stack
make install                   # uv sync
make ingest                    # 把 data/faq 嵌入 Chroma（首次会下载 BGE 模型 ~95MB）
make dev                       # uvicorn 启动 :8000
```

## 接口

| Method | Path | 说明 |
|---|---|---|
| POST | `/chat` | 同步对话 |
| POST | `/chat/stream` | SSE 流式 |
| GET  | `/sessions/{id}/history` | 会话历史 |
| DELETE | `/sessions/{id}` | 清除会话 |
| GET  | `/healthz` | 健康检查 |

请求体：`{"session_id": "s1", "message": "...", "user_id": "alice"}`

## 测试

```bash
make test
```

## 架构

详见 `plans/fastapi-langgraph-foamy-plum.md`。
