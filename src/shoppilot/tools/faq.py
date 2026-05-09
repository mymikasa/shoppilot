from langchain_core.tools import tool

from shoppilot.rag import retriever as _retriever_mod


@tool
def search_faq(query: str, k: int = 4) -> list[dict]:
    """检索客服 FAQ 知识库（涵盖发货、退换货、支付、账户与会员等通用政策）。

    使用场景：用户问通用政策类问题——"多久能发货" / "怎么退货" / "支持分期吗" / "会员等级"。
    参数：
      - query: 用户问题原文或核心关键词
      - k: 返回 top-k 片段，默认 4
    返回：[{text, source, section}]，按相似度排序。
    """
    docs = _retriever_mod.similarity_search(query, k=k)
    return [
        {
            "text": d.page_content,
            "source": d.metadata.get("source", ""),
            "section": d.metadata.get("section", ""),
        }
        for d in docs
    ]
