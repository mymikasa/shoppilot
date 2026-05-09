from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=128)
    message: str = Field(..., min_length=1, max_length=4000)
    user_id: str | None = Field(default=None, max_length=128)


class ToolCallTrace(BaseModel):
    name: str
    args: dict[str, Any] = {}
    result: Any | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_calls: list[ToolCallTrace] = []


class HistoryMessage(BaseModel):
    role: str
    content: str
    tool_calls: list[ToolCallTrace] | None = None


class HistoryResponse(BaseModel):
    session_id: str
    messages: list[HistoryMessage]


class HealthResponse(BaseModel):
    status: str
    redis: str
    chroma: str
    chroma_docs: int
