from fastapi import APIRouter, Depends
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from shoppilot.api.deps import get_graph, get_redis
from shoppilot.api.schemas import HistoryMessage, HistoryResponse, ToolCallTrace

router = APIRouter()


def _project(messages: list) -> list[HistoryMessage]:
    out: list[HistoryMessage] = []
    for m in messages:
        if isinstance(m, HumanMessage):
            out.append(HistoryMessage(role="user", content=str(m.content)))
        elif isinstance(m, AIMessage):
            tool_calls = None
            if getattr(m, "tool_calls", None):
                tool_calls = [
                    ToolCallTrace(name=tc["name"], args=tc.get("args", {}) or {})
                    for tc in m.tool_calls
                ]
            content = m.content if isinstance(m.content, str) else str(m.content)
            out.append(HistoryMessage(role="assistant", content=content, tool_calls=tool_calls))
        elif isinstance(m, ToolMessage):
            out.append(HistoryMessage(role="tool", content=str(m.content)))
    return out


@router.get("/sessions/{session_id}/history", response_model=HistoryResponse)
async def get_history(session_id: str, graph=Depends(get_graph)) -> HistoryResponse:
    state = await graph.aget_state({"configurable": {"thread_id": session_id}})
    messages = (state.values or {}).get("messages", []) if state else []
    return HistoryResponse(session_id=session_id, messages=_project(messages))


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, redis=Depends(get_redis)) -> dict:
    """清除指定 session 的 checkpointer 数据。

    优先用 checkpointer 的 adelete_thread；如果版本不支持，回退到扫描键并删除。
    """
    deleted = 0
    # 简单起见用通配符扫描；checkpoint-redis 的 key 形如 "checkpoint:<thread_id>:..."
    async for key in redis.scan_iter(match=f"checkpoint*{session_id}*"):
        await redis.delete(key)
        deleted += 1
    async for key in redis.scan_iter(match=f"writes*{session_id}*"):
        await redis.delete(key)
        deleted += 1
    return {"session_id": session_id, "deleted_keys": deleted}
