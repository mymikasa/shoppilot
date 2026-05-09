"""QA 模板：FAQ 文档专用，每个"问题-答案"对独立成 chunk。

约定：源文档每条 FAQ 用 H2 (`##`) 作为问题，紧随其后的内容（段落 / 列表 /
表格 / 子标题）作为答案。一直到下一个 H2 为止。

H1 通常是文档主题（如"物流"），作为 category 元数据。
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


class QAChunker(Chunker):
    name = "qa"

    def split(self, doc: ParsedDocument) -> list[Chunk]:
        chunks: list[Chunk] = []
        current_h1: str | None = None
        current_q: str | None = None
        current_q_idx = 0
        body_parts: list[str] = []

        def flush():
            nonlocal body_parts, current_q, current_q_idx
            if current_q is None:
                body_parts = []
                return
            answer = "\n\n".join(p for p in body_parts if p).strip()
            if not answer:
                # 没答案的纯问题不入库
                body_parts = []
                return
            text = f"问题：{current_q}\n\n答案：{answer}"
            meta = self._common_meta(doc) | {
                "question": current_q,
                "category": current_h1 or "",
                "qa_index": current_q_idx,
            }
            chunks.append(Chunk(text=text, metadata=meta))
            body_parts = []
            current_q_idx += 1

        for block in doc.blocks:
            if isinstance(block, Title):
                if block.level == 1:
                    flush()
                    current_h1 = block.text
                    current_q = None
                elif block.level == 2:
                    flush()
                    current_q = block.text
                else:  # H3+ 视为答案的小标题
                    if current_q is not None:
                        body_parts.append(f"**{block.text}**")
            elif isinstance(block, Paragraph):
                if current_q is not None:
                    body_parts.append(block.text)
            elif isinstance(block, ListBlock):
                if current_q is not None:
                    bullet = "1. " if block.ordered else "- "
                    body_parts.append("\n".join(bullet + it for it in block.items))
            elif isinstance(block, Table):
                if current_q is not None:
                    body_parts.append(block.markdown or "")

        flush()
        return chunks
