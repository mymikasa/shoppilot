"""文档解析层：把不同格式归一成 ParsedDocument 中间表示。"""

from shoppilot.rag.parsers.base import (
    Block,
    Figure,
    ListBlock,
    ParsedDocument,
    Paragraph,
    Table,
    Title,
    parse_document,
)

__all__ = [
    "Block",
    "Figure",
    "ListBlock",
    "ParsedDocument",
    "Paragraph",
    "Table",
    "Title",
    "parse_document",
]
