"""一次性 / 增量地把 data/faq 下的文档入库。

按目录约定决定切分模板：
  data/faq/qa/*.{md,docx,pdf}      → QAChunker
  data/faq/manual/*.{md,docx,pdf}  → ManualChunker
  其他子目录                        → NaiveChunker

用法：
    uv run python -m scripts.ingest_faq
    uv run python -m scripts.ingest_faq --dir data/faq --no-incremental
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from shoppilot.rag.pipeline import ingest_directory

DEFAULT_FAQ_DIR = Path(__file__).resolve().parents[1] / "data" / "faq"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest documents into Chroma.")
    parser.add_argument(
        "--dir",
        default=str(DEFAULT_FAQ_DIR),
        help=f"FAQ 根目录（默认 {DEFAULT_FAQ_DIR}）",
    )
    parser.add_argument(
        "--no-incremental",
        action="store_true",
        help="忽略 manifest，全量重写（不会重建向量库，按 chunk_id upsert）",
    )
    args = parser.parse_args()

    src = Path(args.dir).resolve()
    if not src.exists():
        print(f"[ingest] 目录不存在: {src}", file=sys.stderr)
        return 2

    print(f"[ingest] 扫描 {src}（首次会下载 BGE 模型，请耐心等待）")
    started = time.time()
    stats = ingest_directory(src, incremental=not args.no_incremental)
    elapsed = time.time() - started

    print(f"[ingest] 完成（{elapsed:.1f}s）")
    print(f"  扫描文件: {stats.scanned}")
    print(f"  解析成功: {stats.parsed}")
    print(f"  chunk 总数: {stats.chunks_total}")
    print(f"    新增: {stats.chunks_added}")
    print(f"    更新: {stats.chunks_updated}")
    print(f"    跳过(未变): {stats.chunks_skipped}")
    print(f"    删除(孤儿): {stats.chunks_deleted}")
    if stats.errors:
        print("[ingest] 错误：")
        for e in stats.errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
