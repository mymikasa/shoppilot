from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, SystemMessage, trim_messages

from shoppilot.agent.prompts import SYSTEM_PROMPT
from shoppilot.agent.state import AgentState
from shoppilot.tools import TOOLS

MAX_TOKENS = 6000


def build_agent_node(llm: BaseChatModel):
    bound = llm.bind_tools(TOOLS, parallel_tool_calls=False)

    async def agent_node(state: AgentState) -> dict:
        history = state.get("messages", [])
        trimmed = trim_messages(
            history,
            max_tokens=MAX_TOKENS,
            strategy="last",
            token_counter=len,
            include_system=False,
            allow_partial=False,
            start_on="human",
        )
        messages = [SystemMessage(content=SYSTEM_PROMPT), *trimmed]
        response: AIMessage = await bound.ainvoke(messages)
        return {"messages": [response]}

    return agent_node
