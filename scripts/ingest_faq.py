"""一次性把 data/faq/*.md 嵌入到 Chroma。

用法:
    uv run python -m scripts.ingest_faq
    uv run python -m scripts.ingest_faq --dir data/faq
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from shoppilot.rag.ingest import ingest_directory

DEFAULT_FAQ_DIR = Path(__file__).resolve().parents[1] / "data" / "faq"


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest FAQ markdown into Chroma.")
    parser.add_argument(
        "--dir",
        default=str(DEFAULT_FAQ_DIR),
        help=f"FAQ markdown 目录（默认 {DEFAULT_FAQ_DIR}）",
    )
    args = parser.parse_args()

    src = Path(args.dir).resolve()
    if not src.exists():
        print(f"[ingest] 目录不存在: {src}", file=sys.stderr)
        return 2

    print(f"[ingest] 开始嵌入 {src}（首次会下载 BGE 模型，请耐心等待）")
    started = time.time()
    n = ingest_directory(src)
    elapsed = time.time() - started
    print(f"[ingest] 完成：写入 {n} 个 chunk，用时 {elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
