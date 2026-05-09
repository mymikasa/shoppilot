"""请求级上下文：把当前会话的 user_id 注入工具内部，避免 LLM 直接传 user_id 越权。"""

from contextvars import ContextVar

current_user_id: ContextVar[str | None] = ContextVar("current_user_id", default=None)


def set_user_id(user_id: str | None):
    return current_user_id.set(user_id)


def get_user_id() -> str | None:
    return current_user_id.get()


def reset_user_id(token) -> None:
    current_user_id.reset(token)
