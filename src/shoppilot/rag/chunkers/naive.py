"""Naive 模板：兜底切分，按字符长度+段落边界。

适用于"不知道这是什么类型"的文档：营销话术、客服剧本、随手贴的散记等。
"""

from __future__ import annotations

from shoppilot.rag.chunkers.base import Chunk, Chunker
from shoppilot.rag.chunkers.manual import _soft_split
from shoppilot.rag.parsers.base import ListBlock, ParsedDocument, Paragraph, Table, Title

CHUNK_SIZE = 500
OVERLAP = 50


def _flatten(doc: ParsedDocument) -> str:
    parts: list[str] = []
    for b in doc.blocks:
        if isinstance(b, Title):
            parts.append("#" * max(1, b.level) + " " + b.text)
        elif isinstance(b, Paragraph):
            parts.append(b.text)
        elif isinstance(b, ListBlock):
            bullet = "1. " if b.ordered else "- "
            parts.append("\n".join(bullet + it for it in b.items))
        elif isinstance(b, Table):
            parts.append(b.markdown or "")
    return "\n\n".join(parts)


class NaiveChunker(Chunker):
    name = "naive"

    def split(self, doc: ParsedDocument) -> list[Chunk]:
        flat = _flatten(doc) or doc.raw_text
        if not flat.strip():
            return []
        pieces = _soft_split(flat, CHUNK_SIZE)
        # 加 overlap：每个 chunk 拼上上一段尾部 OVERLAP 字符
        out: list[Chunk] = []
        prev_tail = ""
        for i, p in enumerate(pieces):
            text = (prev_tail + p) if prev_tail else p
            meta = self._common_meta(doc) | {"chunk_index": i}
            out.append(Chunk(text=text, metadata=meta))
            prev_tail = p[-OVERLAP:] if len(p) > OVERLAP else p
        return out
