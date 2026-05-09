"""Parser 层单测：markdown / docx 都归一为 ParsedDocument。"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

import shoppilot.rag.parsers.docx  # noqa: F401
import shoppilot.rag.parsers.markdown  # noqa: F401
from shoppilot.rag.parsers import parse_document
from shoppilot.rag.parsers.base import ListBlock, Paragraph, Table, Title


def test_markdown_parser_basic(tmp_path: Path):
    src = tmp_path / "doc.md"
    src.write_text(
        "# 主题\n\n"
        "## 小节一\n\n"
        "这是一段说明文字。\n\n"
        "- a\n- b\n- c\n\n"
        "## 小节二\n\n"
        "| 列1 | 列2 |\n|---|---|\n| x | y |\n",
        encoding="utf-8",
    )
    doc = parse_document(src)
    assert doc.source_format == "md"
    types = [type(b).__name__ for b in doc.blocks]
    assert types[0] == "Title" and doc.blocks[0].level == 1
    assert "Paragraph" in types
    assert any(isinstance(b, ListBlock) and len(b.items) == 3 for b in doc.blocks)
    assert any(isinstance(b, Table) and b.rows[0] == ["列1", "列2"] for b in doc.blocks)


def test_unknown_extension_raises(tmp_path: Path):
    p = tmp_path / "x.unknownfmt"
    p.write_text("hi", encoding="utf-8")
    with pytest.raises(ValueError):
        parse_document(p)


def test_docx_parser_via_python_docx(tmp_path: Path):
    """生成最小 docx 验证 mammoth → markdown → parse 链路。"""
    docx = pytest.importorskip("docx")
    p = tmp_path / "sample.docx"
    document = docx.Document()
    document.add_heading("Title H1", level=1)
    document.add_heading("Section A", level=2)
    document.add_paragraph("hello world")
    document.save(p)

    doc = parse_document(p)
    assert doc.source_format == "docx"
    titles = [b for b in doc.blocks if isinstance(b, Title)]
    assert any(t.level == 1 and t.text == "Title H1" for t in titles)
    assert any(t.level == 2 and t.text == "Section A" for t in titles)
    paragraphs = [b for b in doc.blocks if isinstance(b, Paragraph)]
    assert any("hello world" in p.text for p in paragraphs)
