# ShopPilot — 智能客服 Agent 实现方案

## Context

`/Users/mikasa/mikasa/shoppilot` 当前是空仓库（仅有 `.gitignore` / `LICENSE` / 单行 `README.md`），需要从零搭建一个面向**电商售前+售后**场景的智能客服 agent，仅做 Python 后端，不做前端。

**目标产物**：能跑通 `POST /chat` 与 `POST /chat/stream` 的 FastAPI 服务，背后用 LangGraph 编排，内置 RAG 检索 FAQ + 4 个业务工具（商品/订单/物流/退款），会话历史存在 Redis 中。

**已确定技术栈**：
- Web: FastAPI + uvicorn + sse-starlette
- Agent: LangGraph (`langgraph` + `langgraph-checkpoint-redis`)
- LLM: DeepSeek (`deepseek-chat`，OpenAI 兼容)
- 向量库: Chroma（嵌入式持久化模式）
- Embedding: 本地 `BAAI/bge-small-zh-v1.5`（HuggingFace），可通过 env 切换到 DashScope
- 会话存储: Redis Stack（含 RediSearch，给 LangGraph checkpointer 用）
- 包管理: uv（pyproject.toml + uv.lock）
- Python: `>=3.11,<3.13`

---

## 项目结构

```
shoppilot/
├── pyproject.toml
├── .env.example                  # 环境变量模板
├── docker-compose.yml            # 仅起 redis-stack
├── Makefile                      # install / ingest / dev / test
├── data/
│   ├── faq/                      # 种子 FAQ markdown（shipping/returns/payment/account）
│   ├── mock/                     # products.json / orders.json / logistics.json
│   └── chroma/                   # 持久化目录（gitignore）
├── scripts/
│   ├── ingest_faq.py             # 一次性把 data/faq 嵌入到 Chroma
│   └── smoke_chat.py             # CLI 烟囱测试
├── src/shoppilot/
│   ├── main.py                   # FastAPI app factory + lifespan
│   ├── config.py                 # pydantic-settings
│   ├── api/
│   │   ├── routes_chat.py        # /chat, /chat/stream
│   │   ├── routes_session.py     # GET history, DELETE session
│   │   ├── routes_health.py
│   │   ├── schemas.py
│   │   └── deps.py
│   ├── agent/
│   │   ├── graph.py              # build_graph(checkpointer, llm)
│   │   ├── state.py              # AgentState TypedDict
│   │   ├── nodes.py              # agent_node + tools_condition
│   │   ├── prompts.py            # system prompt
│   │   ├── llm.py                # DeepSeek ChatOpenAI 工厂
│   │   └── checkpointer.py       # AsyncRedisSaver 工厂
│   ├── tools/
│   │   ├── __init__.py           # 暴露 TOOLS = [...]
│   │   ├── products.py           # search_products
│   │   ├── orders.py             # get_order（注入 user_id 校验）
│   │   ├── logistics.py          # track_logistics
│   │   ├── refund.py             # apply_refund（注入 user_id 校验）
│   │   └── faq.py                # search_faq（封装 RAG retriever）
│   ├── rag/
│   │   ├── embeddings.py         # local BGE / DashScope 二选一
│   │   ├── store.py              # Chroma 客户端 + collection
│   │   ├── ingest.py             # 切分 + 嵌入 + upsert
│   │   └── retriever.py
│   └── persistence/
│       ├── redis_client.py
│       └── history.py            # 从 checkpointer 读/删会话
└── tests/
    ├── conftest.py               # fake_llm / tmp_chroma / fakeredis
    ├── test_tools.py
    ├── test_agent_graph.py
    ├── test_rag.py
    └── test_api.py
```

---

## 依赖（pyproject.toml）

**Runtime**
- `fastapi>=0.115,<0.117`、`uvicorn[standard]>=0.30,<0.33`、`sse-starlette>=2.1,<3`
- `pydantic>=2.7,<3`、`pydantic-settings>=2.4,<3`、`python-dotenv>=1`
- `langgraph>=0.2.60,<0.3`、`langgraph-checkpoint-redis>=0.0.6,<0.1`
- `langchain-core>=0.3.20,<0.4`、`langchain-openai>=0.2.10,<0.3`、`langchain-chroma>=0.1.4,<0.2`、`langchain-huggingface>=0.1,<0.2`
- `chromadb>=0.5.15,<0.6`
- `redis[hiredis]>=5,<6`
- `sentence-transformers>=3,<4`（含 `torch` CPU wheel，给 BGE 用）
- `tenacity>=9,<10`、`structlog>=24.4,<25`

**Dev**
- `pytest>=8.3,<9`、`pytest-asyncio>=0.24,<0.25`、`fakeredis[asyncio]`、`respx>=0.21,<0.22`、`ruff>=0.7,<0.8`

---

## LangGraph 设计

**State**（`agent/state.py`）：在 `MessagesState` 基础上扩展
```python
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    user_id: Optional[str]
    intent: Optional[Literal["product_qa","order_query","logistics","refund","faq","smalltalk"]]
```

**节点 / 边**（v1 只两个节点，最简）
- `agent_node` → 调用 `llm.bind_tools(TOOLS, parallel_tool_calls=False)`
- `tool_node` → `langgraph.prebuilt.ToolNode(TOOLS)`
- 路由：`tools_condition` 分发到 `tools` 或 `END`；`tools → agent` 回环

**Checkpointer**：`langgraph.checkpoint.redis.aio.AsyncRedisSaver`，FastAPI lifespan 中 `await saver.asetup()` 一次，编译后的 `graph` 挂到 `app.state.graph`，请求里通过 `config={"configurable":{"thread_id": session_id}}` 复用。

**消息修剪**：`agent_node` 调用 LLM 前用 `langchain_core.messages.trim_messages` 限制到最近 20 轮 / ≈6k tokens，避免 checkpointer 历史无限增长。

**user_id 安全**：`user_id` **不**进 LLM 可见的工具 schema，通过 contextvar 在 agent_node 调用前 set，订单/退款工具内部读取 contextvar 校验归属。

---

## 工具列表

| 工具 | 文件 | 说明 |
|---|---|---|
| `search_products(query, limit=5)` | `tools/products.py` | 模糊匹配 `data/mock/products.json` |
| `get_order(order_id)` | `tools/orders.py` | 查 `data/mock/orders.json`，contextvar user_id 校验 |
| `track_logistics(tracking_no)` | `tools/logistics.py` | 返回确定性 mock 物流事件 |
| `apply_refund(order_id, reason)` | `tools/refund.py` | 校验订单归属 + 可退性，返回 pending refund |
| `search_faq(query, k=4)` | `tools/faq.py` | 封装 Chroma retriever |

每个工具的 docstring 是 LLM 看到的工具描述，必须明确"何时使用 + 必填字段"。

---

## RAG 流程

1. **种子文档**：`data/faq/{shipping,returns,payment,account}.md`，每篇若干 Q&A 用 `##` 分节
2. **Embedding**：默认 `langchain-huggingface` 加载 `BAAI/bge-small-zh-v1.5`；通过 `EMBEDDING_PROVIDER=dashscope` 可切到 `OpenAIEmbeddings(base_url=DashScope)`
3. **切分**：`MarkdownHeaderTextSplitter` 按 `##` 切，超长再 `RecursiveCharacterTextSplitter(chunk_size=500, overlap=50)`
4. **入库**：Chroma collection `shoppilot_faq`，元数据 `{source, section}`，**确定性 ID**（`hash(source+section)`）保证 ingest 幂等
5. **检索**：`similarity_search(k=4)`，`functools.lru_cache` 缓存 retriever 句柄
6. **运行**：`make ingest` → `uv run python -m scripts.ingest_faq`

---

## FastAPI 端点

| Method | Path | 说明 |
|---|---|---|
| POST | `/chat` | 同步：`graph.ainvoke(...)`，返回最终回复 + tool_calls 轨迹 |
| POST | `/chat/stream` | SSE：`graph.astream_events(version="v2")`，过滤 `metadata.langgraph_node=="agent"` 的 `on_chat_model_stream` 事件流 token；同时发 `tool_start`/`tool_end`/`done` |
| GET | `/sessions/{session_id}/history` | `graph.aget_state(...)` 投影成 `[{role, content, tool_calls}]` |
| DELETE | `/sessions/{session_id}` | 优先用 checkpointer 的 `adelete_thread`；不可用则手动扫 `checkpoint:{thread_id}:*` 删除 |
| GET | `/healthz` | ping Redis + 检查 Chroma collection count |

请求体：`{session_id, message, user_id?}`；SSE payload 必须 `json.dumps`，避免 token 含换行/`data:` 破坏协议。

---

## 配置（`config.py`）

```python
class Settings(BaseSettings):
    deepseek_api_key: SecretStr
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"        # 注意：deepseek-reasoner 不支持 tool calling
    llm_temperature: float = 0.2
    redis_url: str = "redis://localhost:6379/0"
    chroma_path: str = "./data/chroma"
    chroma_collection: str = "shoppilot_faq"
    embedding_provider: Literal["local","dashscope"] = "local"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    log_level: str = "INFO"
```
`get_settings()` 用 `@lru_cache`。

---

## docker-compose & Makefile

```yaml
# docker-compose.yml
services:
  redis:
    image: redis/redis-stack:7.4.0-v0   # 必须用 redis-stack（含 RediSearch）
    ports: ["6379:6379","8001:8001"]
    volumes: [redis-data:/data]
volumes: { redis-data: {} }
```

```makefile
install:  ; uv sync
ingest:   ; uv run python -m scripts.ingest_faq
dev:      ; uv run uvicorn shoppilot.main:app --reload --port 8000
test:     ; uv run pytest -q
up:       ; docker compose up -d
down:     ; docker compose down
```

**Bootstrap**：`cp .env.example .env` → 填 `DEEPSEEK_API_KEY` → `make up && uv sync && make ingest && make dev`

---

## 测试策略

- `tests/conftest.py`：`FakeListChatModel`（含带 tool_calls 的预设回复）+ `tmp_chroma` + `fakeredis[asyncio]`
- `test_tools.py`：纯函数单测（`get_order` 越权返回 not_authorized；`search_products` topK）
- `test_agent_graph.py`：用 `MemorySaver` + FakeLLM 走一遍 agent → tool → agent 路径，断言最终消息内容
- `test_rag.py`：临时 Chroma 入库 2 篇 fixture，查询非空命中
- `test_api.py`：`httpx.AsyncClient` + ASGI transport，覆盖 `/chat`、`/healthz`、`DELETE /sessions/{id}`

`pyproject.toml` 设 `asyncio_mode="auto"`。

---

## 关键风险与对策

1. **Redis 必须是 Redis Stack**：`langgraph-checkpoint-redis` 依赖 RediSearch + RedisJSON，普通 `redis:7` 在 `asetup()` 阶段会报错
2. **DeepSeek tool calling 稳定性**：固定 `parallel_tool_calls=False`；用 `deepseek-chat` 而非 `deepseek-reasoner`；对 LLM 调用加 `tenacity` 退避重试
3. **Embedding 首跑慢**：BGE 模型首次下载 ~95MB+，文档里提示一次
4. **SSE token 编码**：所有 token chunk 必须 `json.dumps`；nginx 部署需 `proxy_buffering off`
5. **macOS uvicorn --reload + chromadb 嵌入式偶发死锁**：设 `TOKENIZERS_PARALLELISM=false`
6. **user_id 不进 LLM schema**：通过 contextvar 注入工具内部，防止用户跨账号查单
7. **会话历史无限增长**：`agent_node` 内 `trim_messages` 截断到 ~6k tokens

---

## Critical files（实现入口，按依赖顺序）

1. `/Users/mikasa/mikasa/shoppilot/pyproject.toml` — 锁依赖
2. `/Users/mikasa/mikasa/shoppilot/src/shoppilot/config.py` — Settings
3. `/Users/mikasa/mikasa/shoppilot/src/shoppilot/agent/llm.py` — DeepSeek ChatOpenAI 工厂
4. `/Users/mikasa/mikasa/shoppilot/src/shoppilot/agent/checkpointer.py` — AsyncRedisSaver
5. `/Users/mikasa/mikasa/shoppilot/src/shoppilot/tools/__init__.py` — TOOLS 列表汇总
6. `/Users/mikasa/mikasa/shoppilot/src/shoppilot/agent/graph.py` — `build_graph(checkpointer, llm)`
7. `/Users/mikasa/mikasa/shoppilot/src/shoppilot/api/routes_chat.py` — `/chat` + `/chat/stream`
8. `/Users/mikasa/mikasa/shoppilot/src/shoppilot/main.py` — lifespan 装配
9. `/Users/mikasa/mikasa/shoppilot/scripts/ingest_faq.py` — RAG 入库 CLI

---

## Verification（端到端验证步骤）

1. **环境就绪**：`docker compose up -d redis` → `redis-cli ping` 返回 `PONG`；访问 `localhost:8001` 看到 RedisInsight
2. **依赖安装**：`uv sync` 成功；`uv pip list` 中含 `langgraph-checkpoint-redis`
3. **RAG ingest**：`make ingest` 无报错，Chroma `data/chroma/` 有持久化文件；脚本末尾打印写入的 chunk 数量
4. **服务启动**：`make dev` 启动 8000 端口；`curl localhost:8000/healthz` 返回 `{"status":"ok","redis":"ok","chroma":"ok"}`
5. **多轮对话（FAQ 路径）**：
   ```bash
   curl -X POST localhost:8000/chat -H "Content-Type: application/json" \
     -d '{"session_id":"s1","message":"你们多久能发货？"}'
   ```
   预期：响应中 `tool_calls` 含 `search_faq`，`reply` 引用 FAQ 内容
6. **业务工具路径**：发送 `"帮我查下订单 ORD-1001 的物流"`，断言依次触发 `get_order` → `track_logistics`
7. **会话续接**：同一 `session_id` 发第二条消息 `"那它能退款吗？"`，断言 LLM 能基于上文订单号调用 `apply_refund`
8. **越权防护**：用 `user_id=alice` 查 `bob` 的订单，断言工具返回 `not_authorized`
9. **流式接口**：
   ```bash
   curl -N -X POST localhost:8000/chat/stream -H "Content-Type: application/json" \
     -d '{"session_id":"s2","message":"介绍下你们最近的促销"}'
   ```
   能看到逐 token 的 `event: token` 输出，最后 `event: done`
10. **会话管理**：`GET /sessions/s1/history` 返回前面的消息列表；`DELETE /sessions/s1` 后再 GET 返回空
11. **测试通过**：`make test` 全绿（≥4 个测试文件覆盖工具/图/RAG/API）
