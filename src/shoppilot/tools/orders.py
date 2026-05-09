from langchain_core.tools import tool

from shoppilot.tools._context import get_user_id
from shoppilot.tools._data import find_order


@tool
def get_order(order_id: str) -> dict:
    """查询当前已登录用户名下的订单详情。

    使用场景：用户询问"我的订单 ORD-1001 怎么样了" / "上次买的耳机发货了吗" 等售后问题。
    参数：
      - order_id: 订单号，例如 ORD-1001（用户在确认邮件或订单页面可见）
    返回：订单详情 dict，含 status / items / total / tracking_no / refundable；
          若订单不存在或不属于当前用户，返回 {"error": "..."}。
    """
    user_id = get_user_id()
    if not user_id:
        return {"error": "missing_user_id", "message": "请先登录后再查询订单"}
    order = find_order(order_id)
    if order is None:
        return {"error": "not_found", "order_id": order_id}
    if order.get("user_id") != user_id:
        return {"error": "not_authorized", "order_id": order_id}
    return {k: v for k, v in order.items() if k != "user_id"}
