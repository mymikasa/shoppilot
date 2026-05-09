"""测试用 fake LLM：支持 bind_tools 并按顺序回放预设的 AIMessage。"""

from __future__ import annotations

from typing import Any, Sequence

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeToolCallingChat(BaseChatModel):
    """按顺序回放预设 AIMessage 的 fake；bind_tools 是空操作。"""

    responses: list = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling"

    def _next(self) -> AIMessage:
        if not self.responses:
            return AIMessage(content="")
        if len(self.responses) == 1:
            return self.responses[0]
        return self.responses.pop(0)

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next())])

    async def _agenerate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: AsyncCallbackManagerForLLMRun | None = None,
        **kwargs: Any,
    ) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._next())])

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: str | None = None,
        **kwargs: Any,
    ):
        return self
