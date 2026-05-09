from typing import Annotated, Literal, Optional, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

Intent = Literal["product_qa", "order_query", "logistics", "refund", "faq", "smalltalk"]


class AgentState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
    user_id: Optional[str]
    intent: Optional[Intent]
