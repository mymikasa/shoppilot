"""Manual 模板：政策 / 手册 / 章节文档专用。

按标题层级切，每个 chunk 带 `title_path` 元数据保存层级路径，
检索时可以做"路径前缀过滤"或在 prompt 里展示层级，提高定位精度。

设计：以最深的标题（一般是 H2/H3）作为 chunk 边界；H1 作为 category。
chunk 内含从该标题出发到下一同级或更高级标题之前的所有正文。
"""

from __future__ import annotations

from shoppilot.rag.chunkers.base import Chunk, Chunker
from shoppilot.rag.parsers.base import (
    ListBlock,
    ParsedDocument,
    Paragraph,
    Table,
    Title,
)

MAX_CHARS = 1200  # 单 chunk 软上限；超过则按段落再分


def _block_to_text(b) -> str:
    if isinstance(b, Paragraph):
        return b.text
    if isinstance(b, ListBlock):
        bullet = "1. " if b.ordered else "- "
        return "\n".join(bullet + it for it in b.items)
    if isinstance(b, Table):
        return b.markdown or ""
    return ""


class ManualChunker(Chunker):
    name = "manual"

    def split(self, doc: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        title_stack: list[str] = []  # 索引 = 层级-1
        current_section: list = []
        current_section_meta: dict | None = None

        def flush():
            nonlocal current_section, current_section_meta
            if not current_section or current_section_meta is None:
                current_section = []
                return
            text_parts = [
                _block_to_text(b).strip()
                for b in current_section
                if _block_to_text(b).strip()
            ]
            if not text_parts:
                current_section = []
                return
            full = "\n\n".join(text_parts)
            for piece in _soft_split(full, MAX_CHARS):
                meta = self._common_meta(doc) | dict(current_section_meta)
                chunks.append(Chunk(text=piece, metadata=meta))
            current_section = []

        def make_meta() -> dict:
            path = " / ".join(title_stack)
            return {
                "category": title_stack[0] if title_stack else "",
                "title_path": path,
                "title_leaf": title_stack[-1] if title_stack else "",
                "title_level": len(title_stack),
            }

        for block in doc.blocks:
            if isinstance(block, Title):
                flush()
                # 收缩到当前层级 - 1，再 push 自己
                title_stack = title_stack[: max(0, block.level - 1)]
                title_stack.append(block.text)
                current_section_meta = make_meta()
            else:
                if current_section_meta is None:
                    # 文档开头无标题的段落 — 给个默认 section
                    title_stack = [doc.meta.get("title", "正文")]
                    current_section_meta = make_meta()
                current_section.append(block)

        flush()
        return chunks


def _soft_split(text: str, max_chars: int) -> list[str]:
    """软切分：优先按段落（\n\n），单段超长再按句子。"""
    if len(text) <= max_chars:
        return [text]
    parts: list[str] = []
    buf = ""
    for para in text.split("\n\n"):
        if len(buf) + len(para) + 2 > max_chars and buf:
            parts.append(buf.strip())
            buf = ""
        if len(para) > max_chars:
            # 单段超长，按句号切
            sentences: list[str] = []
            cur = ""
            for ch in para:
                cur += ch
                if ch in "。！？.!?":
                    sentences.append(cur)
                    cur = ""
            if cur:
                sentences.append(cur)
            for s in sentences:
                if len(buf) + len(s) > max_chars and buf:
                    parts.append(buf.strip())
                    buf = ""
                buf += s
        else:
            buf += ("\n\n" if buf else "") + para
    if buf.strip():
        parts.append(buf.strip())
    return parts
