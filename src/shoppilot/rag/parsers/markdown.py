"""Markdown parser：把 .md 切成块树。

不依赖外部 markdown 解析器，自己按行扫描 —— 我们只需要：
- ATX 标题（# / ## / ###）
- 段落（连续非空行）
- 列表（- / * / 1. ...）
- 表格（| ... | ... |）
够覆盖运营写的 FAQ、政策、手册场景。
"""

from __future__ import annotations

import re
from pathlib import Path

from shoppilot.rag.parsers.base import (
    ListBlock,
    ParsedDocument,
    Paragraph,
    Table,
    Title,
    register_parser,
)

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
_OL_RE = re.compile(r"^\s*\d+[.)]\s+(.+)$")
_UL_RE = re.compile(r"^\s*[-*+]\s+(.+)$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)+\|?\s*$")


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") and s.count("|") >= 2


def _split_row(line: str) -> list[str]:
    s = line.strip().strip("|")
    return [c.strip() for c in s.split("|")]


class MarkdownParser:
    def parse(self, path: Path) -> ParsedDocument:
        text = path.read_text(encoding="utf-8")
        doc = ParsedDocument(
            source_path=str(path),
            source_format="md",
            raw_text=text,
        )

        lines = text.splitlines()
        i = 0
        n = len(lines)
        para_buf: list[str] = []
        list_buf: list[str] = []
        list_ordered = False

        def flush_para():
            nonlocal para_buf
            if para_buf:
                joined = " ".join(s.strip() for s in para_buf).strip()
                if joined:
                    doc.blocks.append(Paragraph(text=joined))
                para_buf = []

        def flush_list():
            nonlocal list_buf
            if list_buf:
                doc.blocks.append(ListBlock(items=list_buf, ordered=list_ordered))
                list_buf = []

        while i < n:
            line = lines[i]
            stripped = line.strip()

            # 空行：分段边界
            if not stripped:
                flush_para()
                flush_list()
                i += 1
                continue

            # 标题
            m = _HEADING_RE.match(line)
            if m:
                flush_para()
                flush_list()
                level = len(m.group(1))
                doc.blocks.append(Title(text=m.group(2).strip(), level=level))
                i += 1
                continue

            # 表格：当前行像表头 + 下一行是分隔线
            if _is_table_row(line) and i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
                flush_para()
                flush_list()
                header = _split_row(line)
                rows: list[list[str]] = [header]
                md_lines = [line.rstrip(), lines[i + 1].rstrip()]
                j = i + 2
                while j < n and _is_table_row(lines[j]):
                    rows.append(_split_row(lines[j]))
                    md_lines.append(lines[j].rstrip())
                    j += 1
                doc.blocks.append(
                    Table(rows=rows, markdown="\n".join(md_lines))
                )
                i = j
                continue

            # 列表项
            ol_m = _OL_RE.match(line)
            ul_m = _UL_RE.match(line)
            if ol_m or ul_m:
                flush_para()
                ordered = ol_m is not None
                if list_buf and ordered != list_ordered:
                    flush_list()
                list_ordered = ordered
                list_buf.append((ol_m or ul_m).group(1).strip())
                i += 1
                continue

            # 普通段落
            flush_list()
            para_buf.append(stripped)
            i += 1

        flush_para()
        flush_list()
        return doc


register_parser("md", MarkdownParser)
register_parser("markdown", MarkdownParser)
