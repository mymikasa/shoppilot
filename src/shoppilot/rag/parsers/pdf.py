"""PDF parser：底层用 RAGFlow DeepDoc 的 PlainParser / RAGFlowPdfParser。

两条路径：
- PLAIN（默认）：deepdoc.parser.pdf_parser.PlainParser — 用 pypdf 抽文本，不拉模型，
  覆盖大多数文本型 PDF。
- VISION：deepdoc.parser.PdfParser（即 RAGFlowPdfParser）— 含 OCR / layout / TableFormer
  视觉模型，能处理扫描版 + 表格识别，首次会从 huggingface 拉 ~1.5GB 权重。

通过 env `PDF_PARSER_MODE=vision` 切到视觉模式；默认 plain。

PlainParser 输出 `[(line, "")]` 行列表 + 空表格列表 + outlines。我们按"空行分段"聚合
成 Paragraph；outlines（PDF 大纲）作为 Title 锚点（如果存在）。
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from shoppilot.rag.parsers.base import (
    ParsedDocument,
    Paragraph,
    Title,
    register_parser,
)

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


def _flush_paragraph(buf: list[str], blocks: list) -> None:
    if not buf:
        return
    text = " ".join(s.strip() for s in buf if s.strip()).strip()
    if text:
        blocks.append(Paragraph(text=text))
    buf.clear()


def _lines_to_blocks(lines: list[str], outline_titles: list[tuple[int, str]] | None = None) -> list:
    """把行列表聚合成 Block 序列。

    outline_titles: [(level, title)] 来自 PDF 大纲；如果为空则只产 Paragraph。
    简单匹配：行文本与 outline title 完全相同 → 升级为 Title 块。
    """
    title_lookup: dict[str, int] = {}
    if outline_titles:
        for level, t in outline_titles:
            title_lookup[t.strip()] = level

    blocks: list = []
    para_buf: list[str] = []
    for raw in lines:
        line = raw.rstrip()
        if not line.strip():
            _flush_paragraph(para_buf, blocks)
            continue
        # 标题识别：按 outlines 匹配
        if title_lookup and line.strip() in title_lookup:
            _flush_paragraph(para_buf, blocks)
            blocks.append(Title(text=line.strip(), level=title_lookup[line.strip()]))
            continue
        para_buf.append(line)
    _flush_paragraph(para_buf, blocks)
    return blocks


def _extract_outlines(path: Path) -> list[tuple[int, str]]:
    """从 PDF 大纲提取 (level, title)。失败时返回空。"""
    try:
        from deepdoc.parser.utils import extract_pdf_outlines

        raw = extract_pdf_outlines(str(path))
        if not raw:
            return []
        # extract_pdf_outlines 返回的结构因 PDF 而异；这里宽松处理
        out: list[tuple[int, str]] = []
        for item in raw:
            if isinstance(item, dict):
                title = item.get("/Title") or item.get("title") or ""
                level = item.get("level", 1)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                # 常见形态 (level, title) 或 (title, level)
                a, b = item[0], item[1]
                if isinstance(a, int) and isinstance(b, str):
                    level, title = a, b
                elif isinstance(a, str) and isinstance(b, int):
                    title, level = a, b
                else:
                    continue
            else:
                continue
            if isinstance(title, str) and title.strip():
                out.append((max(1, min(6, int(level or 1))), title.strip()))
        return out
    except Exception as e:  # noqa: BLE001
        logger.debug("extract_pdf_outlines failed: %s", e)
        return []


class PdfParser:
    def parse(self, path: Path) -> ParsedDocument:
        mode = os.getenv("PDF_PARSER_MODE", "plain").lower()
        if mode == "vision":
            return self._parse_vision(path)
        return self._parse_plain(path)

    def _parse_plain(self, path: Path) -> ParsedDocument:
        from deepdoc.parser.pdf_parser import PlainParser

        parser = PlainParser()
        # PlainParser 接受 fnm + from_page + to_page；返回 ([(line, ""), ...], [])
        text_units, _tables = parser(str(path))
        lines = [t[0] for t in text_units if isinstance(t, tuple) and t and t[0]]

        outlines = _extract_outlines(path)
        blocks = _lines_to_blocks(lines, outlines)

        return ParsedDocument(
            source_path=str(path),
            source_format="pdf",
            blocks=blocks,
            raw_text="\n".join(lines),
            meta={"pdf_parser": "plain", "outline_count": len(outlines)},
        )

    def _parse_vision(self, path: Path) -> ParsedDocument:
        from deepdoc.parser import PdfParser as RAGFlowPdfParser

        parser = RAGFlowPdfParser()
        # 返回 (boxes, tbls)；首次会拉 ~1.5GB 模型
        boxes, tables = parser(str(path), need_image=False, zoomin=3)
        # boxes 每条形如 {"text": ..., "page_number": ..., "x0", "y0", ...}
        # 简化：按 page_number 分组，每页内的 box 文本聚合成 Paragraph
        from shoppilot.rag.parsers.base import Table as TableBlock

        blocks: list = []
        current_page: int | None = None
        para_buf: list[str] = []

        def flush():
            if para_buf:
                joined = " ".join(s.strip() for s in para_buf if s.strip()).strip()
                if joined:
                    blocks.append(Paragraph(text=joined, page=current_page))
                para_buf.clear()

        for box in boxes or []:
            txt = (box.get("text") or "").strip() if isinstance(box, dict) else ""
            page = box.get("page_number") if isinstance(box, dict) else None
            if not txt:
                continue
            if page != current_page:
                flush()
                current_page = page
            para_buf.append(txt)
        flush()

        for tbl in tables or []:
            # tbl 形如 (cells, [imgs]) 或 dict；尽量提取 markdown
            md = ""
            if isinstance(tbl, tuple) and tbl:
                first = tbl[0]
                if isinstance(first, str):
                    md = first
                elif isinstance(first, dict):
                    md = first.get("html") or first.get("markdown") or ""
            if md:
                blocks.append(TableBlock(rows=[], markdown=md))

        return ParsedDocument(
            source_path=str(path),
            source_format="pdf",
            blocks=blocks,
            raw_text="\n".join(
                b.text for b in blocks if isinstance(b, Paragraph)
            ),
            meta={"pdf_parser": "vision", "box_count": len(boxes or []), "table_count": len(tables or [])},
        )


register_parser("pdf", PdfParser)
