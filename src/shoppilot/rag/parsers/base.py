"""中间表示：parser 输出"块树"，下游 chunker 不感知源格式。

设计参考 RAGFlow 的 DeepDoc：
- parser 只产出结构化原料（titles / paragraphs / tables / figures / lists）
- 不直接产 chunk，切分由 chunker 按场景模板做
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class Title:
    """标题块。level: 1=H1, 2=H2, ...，最深支持 6。"""

    text: str
    level: int = 1
    page: int | None = None


@dataclass
class Paragraph:
    """段落块（含纯文本和富文本，但归一为 markdown）。"""

    text: str
    page: int | None = None


@dataclass
class ListBlock:
    """列表块（有序或无序）。items 已是行文本，不再嵌套。"""

    items: list[str]
    ordered: bool = False
    page: int | None = None


@dataclass
class Table:
    """表格块。

    rows: 二维数组，第 0 行通常是表头。
    markdown: 原始 markdown 表示（保留给 chunker 直接嵌入）。
    """

    rows: list[list[str]]
    markdown: str = ""
    caption: str | None = None
    page: int | None = None


@dataclass
class Figure:
    """图片块（v1 不做 OCR，仅占位）。"""

    alt: str = ""
    src: str | None = None
    caption: str | None = None
    page: int | None = None


Block = Title | Paragraph | ListBlock | Table | Figure


@dataclass
class ParsedDocument:
    """解析后的文档：扁平 block 列表（按阅读顺序）+ 源信息。"""

    source_path: str
    source_format: Literal["md", "docx", "pdf", "html", "txt", "xlsx"]
    blocks: list[Block] = field(default_factory=list)
    raw_text: str = ""  # 兜底：完整文本（chunker 兜底用）
    meta: dict = field(default_factory=dict)  # 文件级元数据（标题、作者、修改时间）


# --- dispatcher --- #

_REGISTRY: dict[str, "type"] = {}


def register_parser(suffix: str, parser_cls):
    _REGISTRY[suffix.lower()] = parser_cls


def parse_document(path: str | Path) -> ParsedDocument:
    """按扩展名分发到具体 parser。

    支持的扩展名通过 register_parser 注册。未知扩展会抛 ValueError。
    """
    p = Path(path).resolve()
    suffix = p.suffix.lower().lstrip(".")
    if not suffix:
        raise ValueError(f"无扩展名: {p}")
    parser_cls = _REGISTRY.get(suffix)
    if parser_cls is None:
        raise ValueError(f"暂不支持的格式: .{suffix}（已注册：{sorted(_REGISTRY)}）")
    return parser_cls().parse(p)
