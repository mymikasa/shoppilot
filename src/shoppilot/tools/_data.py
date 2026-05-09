import json
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "mock"


def _load(name: str):
    path = DATA_DIR / name
    if not path.exists():
        return [] if name.endswith(".json") and "logistics" not in name else {}
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def products() -> list[dict]:
    data = _load("products.json")
    return data if isinstance(data, list) else []


@lru_cache(maxsize=1)
def orders() -> list[dict]:
    data = _load("orders.json")
    return data if isinstance(data, list) else []


@lru_cache(maxsize=1)
def logistics() -> dict[str, list[dict]]:
    data = _load("logistics.json")
    return data if isinstance(data, dict) else {}


def find_order(order_id: str) -> dict | None:
    for o in orders():
        if o.get("order_id") == order_id:
            return o
    return None
