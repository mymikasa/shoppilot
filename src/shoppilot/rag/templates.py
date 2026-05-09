"""模板路由：按目录约定决定文档走哪个 chunker。

约定：
    data/faq/qa/*.{md,docx,pdf}      → QAChunker
    data/faq/manual/*.{md,docx,pdf}  → ManualChunker
    data/faq/*.{md,docx,pdf}（顶层） → 兼容老结构，默认 QAChunker（FAQ 主战场）
    其他目录 → NaiveChunker

可通过 TEMPLATE_OVERRIDES 在调用方按需覆盖。
"""

from __future__ import annotations

from pathlib import Path

from shoppilot.rag.chunkers import Chunker, ManualChunker, NaiveChunker, QAChunker

_BUILTIN: dict[str, type[Chunker]] = {
    "qa": QAChunker,
    "manual": ManualChunker,
    "naive": NaiveChunker,
}


def resolve_template(path: Path, faq_root: Path) -> Chunker:
    """根据文件相对 faq_root 的路径决定模板。"""
    try:
        rel = path.relative_to(faq_root)
    except ValueError:
        return NaiveChunker()

    parts = rel.parts
    if len(parts) >= 2:
        kind = parts[0].lower()
        if kind in _BUILTIN:
            return _BUILTIN[kind]()
    # 顶层文件兼容：默认 QA
    return QAChunker()


def chunker_by_name(name: str) -> Chunker:
    cls = _BUILTIN.get(name.lower())
    if cls is None:
        raise ValueError(f"未知模板: {name}（已注册：{sorted(_BUILTIN)}）")
    return cls()
