from langchain_core.tools import tool

from shoppilot.tools._data import products


@tool
def search_products(query: str, limit: int = 5) -> list[dict]:
    """搜索商品目录。

    使用场景：用户咨询商品（找耳机、推荐手冲套装、问机械键盘库存等售前问题）。
    参数：
      - query: 商品关键字、品类或描述片段（中文）
      - limit: 返回前 N 条，默认 5
    返回：商品列表 [{sku, title, price, stock, tags, description}]
    """
    q = query.strip().lower()
    if not q:
        return []
    scored: list[tuple[int, dict]] = []
    for p in products():
        haystack = " ".join(
            [
                p.get("title", ""),
                p.get("description", ""),
                " ".join(p.get("tags", [])),
            ]
        ).lower()
        score = 0
        for token in q.split():
            if token in haystack:
                score += 1
            if token in p.get("title", "").lower():
                score += 2
        if score > 0 or q in haystack:
            scored.append((score, p))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[: max(1, limit)]]
