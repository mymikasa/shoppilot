"""API 集成测试：用 dependency_overrides 注入 fake graph + fakeredis，绕开 lifespan。"""

from __future__ import annotations

import pytest
from fakeredis.aioredis import FakeRedis
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from langchain_core.messages import AIMessage
from langgraph.checkpoint.memory import MemorySaver

from shoppilot.agent.graph import build_graph
from shoppilot.api.deps import get_graph, get_redis


def _make_app(graph, redis) -> FastAPI:
    from shoppilot.main import create_app

    app = create_app()
    # 不跑 lifespan，靠 dependency_overrides 注入
    app.router.lifespan_context = _noop_lifespan  # type: ignore[assignment]
    app.dependency_overrides[get_graph] = lambda: graph
    app.dependency_overrides[get_redis] = lambda: redis
    return app


def _noop_lifespan(_app):
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def cm():
        yield

    return cm()


@pytest.mark.asyncio
async def test_healthz_ok(make_fake_chat, tmp_chroma):
    fake_llm = make_fake_chat([AIMessage(content="ok")])
    graph = build_graph(checkpointer=MemorySaver(), llm=fake_llm)
    redis = FakeRedis(decode_responses=True)
    app = _make_app(graph, redis)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/healthz")
        assert resp.status_code == 200
        body = resp.json()
        assert body["redis"] == "ok"
        assert body["chroma"] in ("ok", "empty")


@pytest.mark.asyncio
async def test_chat_invokes_tool(make_fake_chat, tmp_chroma):
    tool_call = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_products",
                "args": {"query": "耳机", "limit": 2},
                "id": "c1",
                "type": "tool_call",
            }
        ],
    )
    final = AIMessage(content="找到这些耳机供你参考。")
    graph = build_graph(checkpointer=MemorySaver(), llm=make_fake_chat([tool_call, final]))
    app = _make_app(graph, FakeRedis(decode_responses=True))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/chat",
            json={"session_id": "s1", "user_id": "alice", "message": "推荐耳机"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["session_id"] == "s1"
        assert "耳机" in body["reply"]
        assert any(tc["name"] == "search_products" for tc in body["tool_calls"])


@pytest.mark.asyncio
async def test_history_after_chat(make_fake_chat, tmp_chroma):
    fake_llm = make_fake_chat([AIMessage(content="你好，我是小助手")])
    graph = build_graph(checkpointer=MemorySaver(), llm=fake_llm)
    app = _make_app(graph, FakeRedis(decode_responses=True))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/chat",
            json={"session_id": "sX", "user_id": "alice", "message": "嗨"},
        )
        resp = await client.get("/sessions/sX/history")
        assert resp.status_code == 200
        msgs = resp.json()["messages"]
        roles = [m["role"] for m in msgs]
        assert "user" in roles and "assistant" in roles


@pytest.mark.asyncio
async def test_delete_session_clears_keys(make_fake_chat, tmp_chroma):
    redis = FakeRedis(decode_responses=True)
    await redis.set("checkpoint:s9:abc", "1")
    await redis.set("writes:s9:def", "2")

    fake_llm = make_fake_chat([AIMessage(content="ok")])
    graph = build_graph(checkpointer=MemorySaver(), llm=fake_llm)
    app = _make_app(graph, redis)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.delete("/sessions/s9")
        assert resp.status_code == 200
        assert resp.json()["deleted_keys"] == 2
