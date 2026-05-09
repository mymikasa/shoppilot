"""Pipeline 集成测试：解析→清洗→切分→入库 + 增量同步。"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from shoppilot.rag.pipeline import ingest_directory


@pytest.fixture
def faq_root(tmp_path: Path) -> Path:
    root = tmp_path / "faq"
    qa = root / "qa"
    manual = root / "manual"
    qa.mkdir(parents=True)
    manual.mkdir(parents=True)
    (qa / "ship.md").write_text(
        "# 物流\n\n## 发货时效\n现货 24 小时内发出。\n\n## 配送范围\n仅限大陆。\n",
        encoding="utf-8",
    )
    (manual / "policy.md").write_text(
        "# 售后\n\n## 总则\n\n### 适用范围\n所有商品。\n\n## 退款\n按提示走。\n",
        encoding="utf-8",
    )
    return root


def test_initial_ingest_routes_by_directory(tmp_chroma, faq_root):
    stats = ingest_directory(faq_root)
    assert stats.scanned == 2
    assert stats.parsed == 2
    assert stats.chunks_added >= 4  # 2 QA + 至少 2 manual section
    assert stats.chunks_updated == 0
    assert stats.chunks_skipped == 0
    assert stats.chunks_deleted == 0


def test_incremental_skips_unchanged(tmp_chroma, faq_root):
    s1 = ingest_directory(faq_root)
    assert s1.chunks_added > 0

    s2 = ingest_directory(faq_root)
    assert s2.chunks_added == 0
    assert s2.chunks_updated == 0
    assert s2.chunks_skipped == s1.chunks_added


def test_orphan_deletion_when_file_removed(tmp_chroma, faq_root):
    ingest_directory(faq_root)
    # 删一个文件
    (faq_root / "qa" / "ship.md").unlink()
    s = ingest_directory(faq_root)
    assert s.chunks_deleted >= 2  # ship.md 切出的 2 个 QA 应被清掉


def test_template_routing_metadata(tmp_chroma, faq_root):
    ingest_directory(faq_root)
    # 通过 store 查询验证元数据
    from shoppilot.rag import store as store_mod
    store = store_mod.get_vectorstore()
    # Chroma 的 collection.get() 返回所有
    raw = store._collection.get(include=["metadatas"])
    templates = {m.get("template") for m in raw["metadatas"]}
    assert "qa" in templates and "manual" in templates


def test_no_incremental_still_idempotent_via_ids(tmp_chroma, faq_root):
    s1 = ingest_directory(faq_root, incremental=False)
    s2 = ingest_directory(faq_root, incremental=False)
    # 全量模式下每次都"新增"（因为 manifest 用 set），但 chunk_id 稳定，向量库不会重复
    from shoppilot.rag import store as store_mod
    store = store_mod.get_vectorstore()
    count = store._collection.count()
    assert count == s1.chunks_total == s2.chunks_total
