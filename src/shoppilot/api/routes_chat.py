import json
from typing import Any

from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from sse_starlette.sse import EventSourceResponse

from shoppilot.api.deps import get_graph
from shoppilot.api.schemas import ChatRequest, ChatResponse, ToolCallTrace
from shoppilot.tools._context import reset_user_id, set_user_id

router = APIRouter()


def _runtime_config(req: ChatRequest) -> dict:
    return {"configurable": {"thread_id": req.session_id, "user_id": req.user_id}}


def _collect_tool_traces(messages: list) -> list[ToolCallTrace]:
    pending: dict[str, ToolCallTrace] = {}
    out: list[ToolCallTrace] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                trace = ToolCallTrace(name=tc["name"], args=tc.get("args", {}) or {})
                pending[tc["id"]] = trace
                out.append(trace)
        elif isinstance(msg, ToolMessage):
            trace = pending.get(msg.tool_call_id)
            if trace is not None:
                trace.result = _safe_load(msg.content)
    return out


def _safe_load(content: Any):
    if isinstance(content, (dict, list)):
        return content
    if isinstance(content, str):
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            return content
    return content


def _final_text(messages: list) -> str:
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
            content = msg.content
            if isinstance(content, list):
                # 兼容 anthropic 风格的内容块
                return "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            return content or ""
    return ""


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, graph=Depends(get_graph)) -> ChatResponse:
    token = set_user_id(req.user_id)
    try:
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content=req.message)],
                "session_id": req.session_id,
                "user_id": req.user_id,
            },
            config=_runtime_config(req),
        )
    finally:
        reset_user_id(token)

    messages = result.get("messages", [])
    return ChatResponse(
        session_id=req.session_id,
        reply=_final_text(messages),
        tool_calls=_collect_tool_traces(messages),
    )


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest, graph=Depends(get_graph)) -> EventSourceResponse:
    token = set_user_id(req.user_id)

    async def event_gen():
        try:
            async for event in graph.astream_events(
                {
                    "messages": [HumanMessage(content=req.message)],
                    "session_id": req.session_id,
                    "user_id": req.user_id,
                },
                config=_runtime_config(req),
                version="v2",
            ):
                etype = event.get("event")
                meta = event.get("metadata", {}) or {}
                node = meta.get("langgraph_node")

                if etype == "on_chat_model_stream" and node == "agent":
                    chunk = event["data"].get("chunk")
                    text = getattr(chunk, "content", "") or ""
                    if text:
                        yield {"event": "token", "data": json.dumps({"text": text}, ensure_ascii=False)}

                elif etype == "on_tool_start":
                    yield {
                        "event": "tool_start",
                        "data": json.dumps(
                            {
                                "name": event.get("name"),
                                "input": event["data"].get("input"),
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                    }
                elif etype == "on_tool_end":
                    yield {
                        "event": "tool_end",
                        "data": json.dumps(
                            {
                                "name": event.get("name"),
                                "output": _safe_load(event["data"].get("output")),
                            },
                            ensure_ascii=False,
                            default=str,
                        ),
                    }

            yield {"event": "done", "data": json.dumps({"session_id": req.session_id})}
        finally:
            reset_user_id(token)

    return EventSourceResponse(event_gen(), ping=15)
