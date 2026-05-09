from pathlib import Path

import pytest

from shoppilot.rag.ingest import ingest_directory
from shoppilot.tools.faq import search_faq


@pytest.fixture
def faq_corpus(tmp_path: Path) -> Path:
    d = tmp_path / "faq"
    d.mkdir()
    (d / "ship.md").write_text(
        "# 物流\n\n## 发货时效\n现货 24 小时内发出。\n\n## 配送范围\n仅限中国大陆。\n",
        encoding="utf-8",
    )
    (d / "refund.md").write_text(
        "# 退款\n\n## 七天无理由\n签收 7 天内可退。\n",
        encoding="utf-8",
    )
    return d


def test_ingest_writes_chunks(tmp_chroma, faq_corpus):
    n = ingest_directory(faq_corpus)
    assert n >= 2
    assert tmp_chroma._collection.count() == n


def test_search_faq_via_tool(tmp_chroma, faq_corpus):
    ingest_directory(faq_corpus)
    hits = search_faq.invoke({"query": "发货时效", "k": 2})
    assert isinstance(hits, list)
    assert len(hits) > 0
    assert all("text" in h and "source" in h for h in hits)
