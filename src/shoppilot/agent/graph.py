from langchain_core.language_models import BaseChatModel
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from shoppilot.agent.nodes import build_agent_node
from shoppilot.agent.state import AgentState
from shoppilot.tools import TOOLS


def build_graph(checkpointer: BaseCheckpointSaver, llm: BaseChatModel):
    """构建并编译 LangGraph：agent ↔ tools 双节点循环。"""
    graph = StateGraph(AgentState)
    graph.add_node("agent", build_agent_node(llm))
    graph.add_node("tools", ToolNode(TOOLS))
    graph.add_edge(START, "agent")
    graph.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    graph.add_edge("tools", "agent")
    return graph.compile(checkpointer=checkpointer)
