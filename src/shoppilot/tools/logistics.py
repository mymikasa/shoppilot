from langchain_core.tools import tool

from shoppilot.tools._data import logistics


@tool
def track_logistics(tracking_no: str) -> dict:
    """根据快递单号查询物流轨迹。

    使用场景：用户询问"我的快递到哪儿了" / "顺丰单号 SF1234567890 现在在哪"。
    参数：
      - tracking_no: 快递单号，可从订单详情或 get_order 工具返回中获取
    返回：{tracking_no, events: [{time, location, status}], current_status}；
          若单号不存在返回 {"error": "not_found"}。
    """
    events = logistics().get(tracking_no)
    if not events:
        return {"error": "not_found", "tracking_no": tracking_no}
    return {
        "tracking_no": tracking_no,
        "events": events,
        "current_status": events[-1]["status"],
    }
