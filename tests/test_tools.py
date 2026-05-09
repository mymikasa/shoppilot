from shoppilot.tools._context import reset_user_id, set_user_id
from shoppilot.tools.logistics import track_logistics
from shoppilot.tools.orders import get_order
from shoppilot.tools.products import search_products
from shoppilot.tools.refund import apply_refund


def test_search_products_returns_topk():
    out = search_products.invoke({"query": "降噪 耳机", "limit": 2})
    assert isinstance(out, list)
    assert 1 <= len(out) <= 2
    assert any("耳机" in p["title"] for p in out)


def test_search_products_empty_query():
    assert search_products.invoke({"query": "", "limit": 3}) == []


def test_get_order_requires_login():
    out = get_order.invoke({"order_id": "ORD-1001"})
    assert out["error"] == "missing_user_id"


def test_get_order_success_for_owner():
    token = set_user_id("alice")
    try:
        out = get_order.invoke({"order_id": "ORD-1001"})
    finally:
        reset_user_id(token)
    assert out.get("error") is None
    assert out["order_id"] == "ORD-1001"
    assert out["tracking_no"] == "SF1234567890"


def test_get_order_unauthorized_for_other_user():
    token = set_user_id("alice")
    try:
        out = get_order.invoke({"order_id": "ORD-1003"})  # 属于 bob
    finally:
        reset_user_id(token)
    assert out["error"] == "not_authorized"


def test_get_order_not_found():
    token = set_user_id("alice")
    try:
        out = get_order.invoke({"order_id": "ORD-9999"})
    finally:
        reset_user_id(token)
    assert out["error"] == "not_found"


def test_track_logistics_known():
    out = track_logistics.invoke({"tracking_no": "SF1234567890"})
    assert out["current_status"] == "已签收"
    assert len(out["events"]) >= 2


def test_track_logistics_unknown():
    out = track_logistics.invoke({"tracking_no": "FAKE-NO"})
    assert out["error"] == "not_found"


def test_apply_refund_happy_path():
    token = set_user_id("alice")
    try:
        out = apply_refund.invoke({"order_id": "ORD-1001", "reason": "尺码不合适"})
    finally:
        reset_user_id(token)
    assert out["status"] == "pending"
    assert out["order_id"] == "ORD-1001"
    assert out["refund_id"].startswith("REF-")


def test_apply_refund_not_refundable():
    token = set_user_id("bob")
    try:
        out = apply_refund.invoke({"order_id": "ORD-1003", "reason": "不想要"})
    finally:
        reset_user_id(token)
    assert out["error"] == "not_refundable"


def test_apply_refund_cross_user_denied():
    token = set_user_id("eve")
    try:
        out = apply_refund.invoke({"order_id": "ORD-1001", "reason": "试试越权"})
    finally:
        reset_user_id(token)
    assert out["error"] == "not_authorized"
