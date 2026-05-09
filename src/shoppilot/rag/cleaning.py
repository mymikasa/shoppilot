"""文档清洗：去除 zero-width / 异常空白 / HTML 残留。

接口故意做得"薄"，留作以后扩展（去页眉页脚、去敏感信息等）。
作用对象是 ParsedDocument 的每个文本字段。
"""

from __future__ import annotations

import re

from shoppilot.rag.parsers.base import (
    ListBlock,
    ParsedDocument,
    Paragraph,
    Table,
    Title,
)

_ZERO_WIDTH = re.compile(r"[​-‏‪-‮⁠﻿]")
_HTML_TAG = re.compile(r"<[^>]+>")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MULTI_NEWLINE = re.compile(r"\n{3,}")


def clean_text(text: str) -> str:
    if not text:
        return text
    text = _ZERO_WIDTH.sub("", text)
    text = _HTML_TAG.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


def clean_document(doc: ParsedDocument) -> ParsedDocument:
    doc.raw_text = clean_text(doc.raw_text)
    for b in doc.blocks:
        if isinstance(b, Title):
            b.text = clean_text(b.text)
        elif isinstance(b, Paragraph):
            b.text = clean_text(b.text)
        elif isinstance(b, ListBlock):
            b.items = [clean_text(it) for it in b.items if clean_text(it)]
        elif isinstance(b, Table):
            b.rows = [[clean_text(c) for c in row] for row in b.rows]
            b.markdown = clean_text(b.markdown)
    # 清理掉空 block
    doc.blocks = [
        b
        for b in doc.blocks
        if not (
            (isinstance(b, (Title, Paragraph)) and not b.text)
            or (isinstance(b, ListBlock) and not b.items)
            or (isinstance(b, Table) and not b.rows)
        )
    ]
    return doc
