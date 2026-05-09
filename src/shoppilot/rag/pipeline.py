"""Ingest pipeline：串起解析 → 清洗 → 切分 → 元数据 → 嵌入 → 入库 → 增量。

设计参考 RAGFlow 的工作流，保留每一步可独立替换。
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

# 触发 parser 注册
import shoppilot.rag.parsers.docx  # noqa: F401
import shoppilot.rag.parsers.markdown  # noqa: F401
import shoppilot.rag.parsers.pdf  # noqa: F401
from shoppilot.config import get_settings
from shoppilot.rag import store as _store_mod
from shoppilot.rag.chunkers.base import Chunk
from shoppilot.rag.cleaning import clean_document
from shoppilot.rag.manifest import Manifest
from shoppilot.rag.parsers.base import ParsedDocument, parse_document
from shoppilot.rag.templates import resolve_template

logger = logging.getLogger(__name__)

SUPPORTED_SUFFIXES = {"md", "markdown", "docx", "pdf"}


@dataclass
class IngestStats:
    scanned: int = 0
    parsed: int = 0
    chunks_total: int = 0
    chunks_added: int = 0
    chunks_updated: int = 0
    chunks_skipped: int = 0
    chunks_deleted: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


def _content_hash(text: str, meta: dict) -> str:
    h = hashlib.sha1()
    h.update(text.encode("utf-8"))
    # meta 影响 chunk 等同性的关键字段
    for k in ("source_path", "template", "qa_index", "title_path", "chunk_index"):
        v = meta.get(k)
        if v is not None:
            h.update(f"|{k}={v}".encode())
    return h.hexdigest()[:16]


def _stable_id(source_path: str, meta: dict, content_hash: str) -> str:
    name = Path(source_path).stem
    template = meta.get("template", "naive")
    seq = (
        meta.get("qa_index")
        or meta.get("chunk_index")
        or meta.get("title_leaf", "")
    )
    return f"{template}-{name}-{seq}-{content_hash}"


def _enrich_metadata(chunk: Chunk, doc: ParsedDocument, faq_root: Path) -> None:
    """补全每个 chunk 的元数据。"""
    src = Path(doc.source_path)
    try:
        rel = src.relative_to(faq_root.resolve())
        rel_dir = str(rel.parent) if rel.parent != Path(".") else ""
    except ValueError:
        rel_dir = ""

    chunk.metadata.setdefault("source_filename", src.name)
    chunk.metadata.setdefault("source_dir", rel_dir)
    chunk.metadata.setdefault(
        "ingested_at", datetime.now(timezone.utc).isoformat(timespec="seconds")
    )

    # Chroma 不接受 None 值，统一转空字符串 / 0
    for k, v in list(chunk.metadata.items()):
        if v is None:
            chunk.metadata[k] = ""


def ingest_directory(faq_dir: str | Path, *, incremental: bool = True) -> IngestStats:
    """扫描 faq_dir，按目录约定路由模板，幂等写入向量库。

    incremental=True 时基于 manifest 跳过未变 chunk，并删除源端已不存在的孤儿。
    """
    faq_root = Path(faq_dir).resolve()
    if not faq_root.exists():
        raise FileNotFoundError(faq_root)

    store = _store_mod.get_vectorstore()
    settings = get_settings()
    manifest_path = Path(settings.chroma_path).resolve() / ".manifest.json"
    manifest = Manifest(manifest_path)

    stats = IngestStats()
    seen_ids: set[str] = set()
    to_add_chunks: list[Chunk] = []
    to_add_ids: list[str] = []

    for path in sorted(faq_root.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower().lstrip(".")
        if suffix not in SUPPORTED_SUFFIXES:
            continue
        stats.scanned += 1

        try:
            doc = parse_document(path)
            doc = clean_document(doc)
        except Exception as e:  # noqa: BLE001
            stats.errors.append(f"{path}: parse failed: {e}")
            logger.warning("parse failed: %s — %s", path, e)
            continue

        chunker = resolve_template(path, faq_root)
        chunks = chunker.split(doc)
        stats.parsed += 1
        stats.chunks_total += len(chunks)

        for chunk in chunks:
            _enrich_metadata(chunk, doc, faq_root)
            ch_hash = _content_hash(chunk.text, chunk.metadata)
            chunk.metadata["content_hash"] = ch_hash
            cid = _stable_id(doc.source_path, chunk.metadata, ch_hash)
            chunk.metadata["chunk_id"] = cid
            seen_ids.add(cid)

            if incremental and manifest.get_hash(cid) == ch_hash:
                stats.chunks_skipped += 1
                continue

            to_add_chunks.append(chunk)
            to_add_ids.append(cid)
            if manifest.get_hash(cid) is None:
                stats.chunks_added += 1
            else:
                stats.chunks_updated += 1
            manifest.set(cid, ch_hash)

    # 写入向量库（add_texts 会按 ids upsert）
    if to_add_chunks:
        store.add_texts(
            texts=[c.text for c in to_add_chunks],
            metadatas=[c.metadata for c in to_add_chunks],
            ids=to_add_ids,
        )

    # 删除孤儿：上次 ingest 在册、本次没扫到 → 已被删除
    if incremental:
        orphan_ids = manifest.known_ids() - seen_ids
        if orphan_ids:
            store.delete(ids=list(orphan_ids))
            for oid in orphan_ids:
                manifest.remove(oid)
            stats.chunks_deleted = len(orphan_ids)

    manifest.save()
    return stats
