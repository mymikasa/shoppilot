"""保留兼容层：旧调用 `ingest_directory(path) -> int` 重定向到新 pipeline。

新代码请直接 import `shoppilot.rag.pipeline.ingest_directory`，能拿到完整 IngestStats。
"""

from __future__ import annotations

from pathlib import Path

from shoppilot.rag.pipeline import IngestStats
from shoppilot.rag.pipeline import ingest_directory as _new_ingest


def ingest_directory(faq_dir: str | Path) -> int:
    """兼容旧签名：返回写入的 chunk 数量。"""
    stats: IngestStats = _new_ingest(faq_dir, incremental=False)
    return stats.chunks_total
