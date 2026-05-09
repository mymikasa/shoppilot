import secrets

from langchain_core.tools import tool

from shoppilot.tools._context import get_user_id
from shoppilot.tools._data import find_order


@tool
def apply_refund(order_id: str, reason: str) -> dict:
    """为当前已登录用户的订单发起退款申请。

    使用场景：用户明确表达想退货退款（"我要退掉 ORD-1001" / "这商品有质量问题想退"）。
    参数：
      - order_id: 订单号
      - reason: 退款原因，例如 "尺码不合适" / "质量问题" / "不想要了"
    返回：{refund_id, order_id, status: "pending", eta_days: 3} 或 {"error": "..."}。
    注意：不要在用户没有明确表达退款意愿时主动调用。
    """
    user_id = get_user_id()
    if not user_id:
        return {"error": "missing_user_id"}
    order = find_order(order_id)
    if order is None:
        return {"error": "not_found", "order_id": order_id}
    if order.get("user_id") != user_id:
        return {"error": "not_authorized", "order_id": order_id}
    if not order.get("refundable", False):
        return {"error": "not_refundable", "order_id": order_id, "message": "该订单已超出可退期"}
    if not reason or not reason.strip():
        return {"error": "missing_reason"}
    refund_id = "REF-" + secrets.token_hex(4).upper()
    return {
        "refund_id": refund_id,
        "order_id": order_id,
        "status": "pending",
        "eta_days": 3,
        "reason": reason.strip(),
    }
