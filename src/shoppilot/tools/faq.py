from langchain_core.tools import tool

from shoppilot.rag import retriever as _retriever_mod


@tool
def search_faq(query: str, k: int = 4) -> list[dict]:
    """检索客服 FAQ 知识库（涵盖发货、退换货、支付、账户与会员、售后政策手册等）。

    使用场景：用户问通用政策类问题——"多久能发货" / "怎么退货" / "支持分期吗" / "会员等级" / "三包" 等。
    参数：
      - query: 用户问题原文或核心关键词
      - k: 返回 top-k 片段，默认 4
    返回：[{text, source, category, title_path, template, question}]，按相似度排序。
      - source: 源文件名（如 "shipping.md"）
      - category: 文档主题（如 "物流与配送"、"售后服务政策手册"）
      - title_path: 章节路径（仅 manual 模板，如 "售后 / 总则 / 适用范围"）
      - template: qa / manual / naive，告诉你这条来源是问答还是手册章节
      - question: qa 模板才有的具体问题
    """
    docs = _retriever_mod.similarity_search(query, k=k)
    out: list[dict] = []
    for d in docs:
        m = d.metadata or {}
        out.append(
            {
                "text": d.page_content,
                "source": m.get("source_filename") or m.get("source") or "",
                "category": m.get("category", ""),
                "title_path": m.get("title_path", ""),
                "template": m.get("template", ""),
                "question": m.get("question", ""),
            }
        )
    return out
