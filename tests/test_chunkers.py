"""切分模板单测：qa / manual / naive 各自的语义。"""

from __future__ import annotations

from pathlib import Path

import shoppilot.rag.parsers.markdown  # noqa: F401
from shoppilot.rag.chunkers import ManualChunker, NaiveChunker, QAChunker
from shoppilot.rag.parsers import parse_document


def _write(p: Path, text: str) -> Path:
    p.write_text(text, encoding="utf-8")
    return p


def test_qa_chunker_splits_per_h2(tmp_path: Path):
    src = _write(
        tmp_path / "faq.md",
        "# 物流\n\n## 发货时效\n现货 24 小时内发出。\n\n## 配送范围\n仅限中国大陆。\n",
    )
    doc = parse_document(src)
    chunks = QAChunker().split(doc)
    assert len(chunks) == 2
    assert chunks[0].metadata["question"] == "发货时效"
    assert chunks[0].metadata["category"] == "物流"
    assert chunks[0].metadata["template"] == "qa"
    assert "24 小时内" in chunks[0].text
    assert chunks[1].metadata["qa_index"] == 1


def test_qa_chunker_skips_empty_question(tmp_path: Path):
    src = _write(tmp_path / "x.md", "# 主题\n\n## 空问题\n\n## 有答案\n答案文本。\n")
    chunks = QAChunker().split(parse_document(src))
    assert len(chunks) == 1
    assert chunks[0].metadata["question"] == "有答案"


def test_manual_chunker_keeps_title_path(tmp_path: Path):
    src = _write(
        tmp_path / "policy.md",
        "# 售后\n\n## 总则\n\n### 适用范围\n本政策适用于所有商品。\n\n"
        "### 政策更新\n大变更提前 7 天通知。\n\n"
        "## 退款流程\n点击申请退货按钮。\n",
    )
    chunks = ManualChunker().split(parse_document(src))
    paths = [c.metadata["title_path"] for c in chunks]
    assert "售后 / 总则 / 适用范围" in paths
    assert "售后 / 总则 / 政策更新" in paths
    assert "售后 / 退款流程" in paths
    assert all(c.metadata["category"] == "售后" for c in chunks)


def test_naive_chunker_packs_into_chunks(tmp_path: Path):
    long_text = "段落甲。" * 200 + "\n\n" + "段落乙。" * 200
    src = _write(tmp_path / "free.md", "# 散记\n\n" + long_text)
    chunks = NaiveChunker().split(parse_document(src))
    assert len(chunks) >= 2
    assert all(c.metadata["template"] == "naive" for c in chunks)
    assert all("chunk_index" in c.metadata for c in chunks)
