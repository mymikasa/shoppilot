"""命令行烟囱测试：连续发几条消息验证 /chat 端点。

用法:
    uv run python -m scripts.smoke_chat
"""

from __future__ import annotations

import json
import sys
import urllib.request
import uuid


def post_chat(base_url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{base_url}/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read())


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    sid = f"smoke-{uuid.uuid4().hex[:6]}"
    user = "alice"
    queries = [
        "你们多久能发货？",
        "我想查一下订单 ORD-1001 的物流",
        "帮我退掉 ORD-1001，质量不太好",
    ]
    for q in queries:
        print(f"\n>>> {q}")
        out = post_chat(base, {"session_id": sid, "user_id": user, "message": q})
        print(f"<<< {out['reply']}")
        if out.get("tool_calls"):
            for tc in out["tool_calls"]:
                print(f"    [tool] {tc['name']}({tc.get('args')}) -> {tc.get('result')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
