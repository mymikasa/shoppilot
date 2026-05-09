"""Chunker 抽象 + 通用 Chunk dataclass。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from shoppilot.rag.parsers.base import ParsedDocument


@dataclass
class Chunk:
    """切分产物。

    - text: 入向量库的文本（已是最终形式）
    - metadata: 扁平 dict，写入向量库；不能含嵌套结构（Chroma 要求）
    """

    text: str
    metadata: dict = field(default_factory=dict)


class Chunker(ABC):
    """切分模板基类：按场景实现 split。"""

    name: str = "base"

    @abstractmethod
    def split(self, doc: ParsedDocument) -> list[Chunk]: ...

    def _common_meta(self, doc: ParsedDocument) -> dict:
        """每个 chunk 都该带的源信息。"""
        return {
            "source_path": doc.source_path,
            "source_format": doc.source_format,
            "template": self.name,
        }
