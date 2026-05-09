"""切分模板层：按场景把 ParsedDocument 切成 Chunk。"""

from shoppilot.rag.chunkers.base import Chunk, Chunker
from shoppilot.rag.chunkers.manual import ManualChunker
from shoppilot.rag.chunkers.naive import NaiveChunker
from shoppilot.rag.chunkers.qa import QAChunker
from shoppilot.rag.chunkers.qa_simple import SimpleQAChunker

__all__ = [
    "Chunk",
    "Chunker",
    "ManualChunker",
    "NaiveChunker",
    "QAChunker",
    "SimpleQAChunker",
]
