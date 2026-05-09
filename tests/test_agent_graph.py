"""Agent graph 集成测试：用 GenericFakeChatModel + MemorySaver 走完整工具循环。"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from shoppilot.agent.graph import build_graph
from shoppilot.tools._context import reset_user_id, set_user_id


@pytest.mark.asyncio
async def test_agent_invokes_tool_then_replies(make_fake_chat):
    """fake LLM 第一轮返回带 tool_calls 的 AIMessage，第二轮返回最终回复。"""
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "search_products",
                "args": {"query": "降噪耳机", "limit": 2},
                "id": "call-1",
                "type": "tool_call",
            }
        ],
    )
    final_msg = AIMessage(content="为你找到 2 款降噪耳机，最热门的是 SKU-1001。")
    fake_llm = make_fake_chat([tool_call_msg, final_msg])

    graph = build_graph(checkpointer=MemorySaver(), llm=fake_llm)

    config = {"configurable": {"thread_id": "t1"}}
    result = await graph.ainvoke(
        {"messages": [HumanMessage(content="帮我找降噪耳机")]},
        config=config,
    )

    msgs = result["messages"]
    # 期望: human, ai(tool_call), tool, ai(final)
    assert len(msgs) >= 4
    assert any(getattr(m, "tool_calls", None) for m in msgs if isinstance(m, AIMessage))
    last = msgs[-1]
    assert isinstance(last, AIMessage)
    assert "降噪耳机" in last.content


@pytest.mark.asyncio
async def test_agent_blocks_cross_user_order_query(make_fake_chat):
    """alice 试图查 bob 的订单 ORD-1003，工具应当返回 not_authorized。"""
    tool_call_msg = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "get_order",
                "args": {"order_id": "ORD-1003"},
                "id": "call-x",
                "type": "tool_call",
            }
        ],
    )
    final_msg = AIMessage(content="抱歉，这笔订单不属于您的账户。")
    fake_llm = make_fake_chat([tool_call_msg, final_msg])

    graph = build_graph(checkpointer=MemorySaver(), llm=fake_llm)

    token = set_user_id("alice")
    try:
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="查 ORD-1003")]},
            config={"configurable": {"thread_id": "t2"}},
        )
    finally:
        reset_user_id(token)

    tool_msgs = [m for m in result["messages"] if m.type == "tool"]
    assert tool_msgs and "not_authorized" in str(tool_msgs[0].content)
