"""DOCX parser：mammoth 转 markdown 后复用 MarkdownParser。

mammoth 的优势：能把 docx 的 Heading 1/2/3 样式正确映射成 # / ## / ###，
列表、表格、加粗也能保留语义结构。比 docx2txt 强很多。
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import mammoth

from shoppilot.rag.parsers.base import ParsedDocument, register_parser
from shoppilot.rag.parsers.markdown import MarkdownParser


class DocxParser:
    def parse(self, path: Path) -> ParsedDocument:
        with path.open("rb") as f:
            result = mammoth.convert_to_markdown(f)
        markdown = result.value

        # 复用 markdown parser：写到临时文件再解析
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(markdown)
            tmp_path = Path(tmp.name)

        try:
            md_doc = MarkdownParser().parse(tmp_path)
        finally:
            tmp_path.unlink(missing_ok=True)

        return ParsedDocument(
            source_path=str(path),
            source_format="docx",
            blocks=md_doc.blocks,
            raw_text=markdown,
            meta={"mammoth_warnings": [m.message for m in result.messages]},
        )


register_parser("docx", DocxParser)
