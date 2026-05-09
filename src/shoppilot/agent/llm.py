from langchain_openai import ChatOpenAI

from shoppilot.config import get_settings


def build_llm() -> ChatOpenAI:
    """构造指向 DeepSeek 的 ChatOpenAI 客户端。

    DeepSeek v4 系列（v4-flash / v4-pro）默认开 thinking 模式，会返回 reasoning_content
    字段且要求多轮回传——而 langchain-openai 不会帮我们透传，导致 tool calling 第二轮
    400。所以这里通过 extra_body 显式关闭 thinking。
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=settings.llm_temperature,
        max_tokens=settings.llm_max_tokens,
        timeout=60,
        max_retries=2,
        extra_body={"thinking": {"type": "disabled"}},
    )
