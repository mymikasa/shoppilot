"""QA 模板：通过 in-tree vendored 的 rag.app.qa.chunk 调用 RAGFlow 原版。

RAGFlow 的 QA 切分相比我们之前的简版有几个关键加成：
- markdown：按 # 标题层级累积成"问题路径"（多级嵌套），每个叶子 chunk 保留全路径
- docx：用 deepdoc.docx_parser 识别 docx 内的 Q/A bullet 模式（中文 Q&A 启发式）
- pdf：用 deepdoc.pdf_parser 识别 PDF 中的问答对
- xlsx/csv/txt：原生支持表格型 Q&A（双列 question/answer）
- 答案部分用 markdown.markdown() 渲染保留表格 / 列表结构

RAGFlow 不支持的格式（或调用失败）回退到简版 SimpleQAChunker。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from shoppilot.rag.chunkers.base import Chunk, Chunker
from shoppilot.rag.chunkers.qa_simple import SimpleQAChunker
from shoppilot.rag.parsers.base import ParsedDocument

logger = logging.getLogger(__name__)


def _silent_callback(*_args, **_kwargs) -> None:
    """RAGFlow chunk() 必传 callback（用来报告进度），这里做 no-op。"""


_NLTK_RESOURCES = ("punkt_tab", "punkt", "stopwords", "wordnet")
_nltk_ensured = False


def _ensure_nltk_data() -> None:
    """RAGFlow 的 rag.nlp 内部用 NLTK 切句；首次调用时按需下载数据。

    幂等：下载好就缓存到 ~/nltk_data，后续调用是 no-op。
    """
    global _nltk_ensured
    if _nltk_ensured:
        return
    try:
        import nltk
        for pkg in _NLTK_RESOURCES:
            try:
                nltk.data.find(f"tokenizers/{pkg}" if "punkt" in pkg else f"corpora/{pkg}")
            except LookupError:
                logger.info("downloading NLTK %s", pkg)
                nltk.download(pkg, quiet=True)
    except Exception as e:  # noqa: BLE001
        logger.warning("NLTK 资源准备失败: %s", e)
    _nltk_ensured = True


_RAGFLOW_SUPPORTED = {"md", "markdown", "mdx", "pdf", "docx", "xlsx", "xls", "csv", "txt"}

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_QA_TAB_SPLIT_RE = re.compile(r"\t+")
_PREFIX_Q = ("问题：", "问题:", "Question: ", "Question:")
_PREFIX_A = ("回答：", "回答:", "Answer: ", "Answer:")


def _strip_prefix(s: str, prefixes: tuple[str, ...]) -> str:
    for p in prefixes:
        if s.startswith(p):
            return s[len(p):].lstrip()
    return s


def _split_qa(content: str) -> tuple[str, str]:
    """把 RAGFlow 的 'content_with_weight' 切成 (question, answer)。

    RAGFlow `beAdoc` 用 \\t 分隔：'问题：xxx\\t回答：yyy'。
    """
    parts = _QA_TAB_SPLIT_RE.split(content, maxsplit=1)
    if len(parts) == 2:
        q = _strip_prefix(parts[0].strip(), _PREFIX_Q)
        a = _strip_prefix(parts[1].strip(), _PREFIX_A)
        return q, a
    # 没找到分隔符 — 整段当 answer
    return "", content.strip()


def _strip_html(text: str) -> str:
    """RAGFlow markdown chunker 把 answer 用 markdown.markdown() 渲染成 HTML。
    embedding 模型对 HTML 标签不敏感，但展示给 LLM 时拿掉更整洁。"""
    if "<" not in text:
        return text
    return _HTML_TAG_RE.sub("", text)


class QAChunker(Chunker):
    """RAGFlow QA 切分 + 元数据规范化。"""

    name = "qa"

    def __init__(self, lang: str = "Chinese") -> None:
        self.lang = lang

    def split(self, doc: ParsedDocument) -> list[Chunk]:
        suffix = Path(doc.source_path).suffix.lower().lstrip(".")
        if suffix not in _RAGFLOW_SUPPORTED:
            logger.debug("qa: %s 不在 RAGFlow 支持列表，回退 SimpleQAChunker", suffix)
            return SimpleQAChunker().split(doc)

        try:
            raw_chunks = self._invoke_ragflow(doc.source_path)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "qa: RAGFlow chunk(%s) 失败 (%s)，回退 SimpleQAChunker",
                doc.source_path,
                e,
            )
            return SimpleQAChunker().split(doc)

        return self._convert(raw_chunks, doc)

    def _invoke_ragflow(self, filename: str) -> list[dict]:
        # 延迟 import：避免顶层加载 RAGFlow 全栈
        _ensure_nltk_data()
        from rag.app import qa as ragflow_qa

        return ragflow_qa.chunk(
            filename=filename,
            lang=self.lang,
            callback=_silent_callback,
        )

    def _convert(self, raw_chunks: list[dict], doc: ParsedDocument) -> list[Chunk]:
        out: list[Chunk] = []
        category_default = Path(doc.source_path).stem
        for i, item in enumerate(raw_chunks):
            content = (item.get("content_with_weight") or "").strip()
            if not content:
                continue

            question_full, answer = _split_qa(content)
            answer = _strip_html(answer).strip()
            if not answer:
                continue

            # markdown chunker 把 question 写成 '\n'.join(question_stack)
            # 拆出 leaf question + 完整路径
            question_lines = [q.strip() for q in question_full.split("\n") if q.strip()]
            leaf_q = question_lines[-1] if question_lines else ""
            title_path = " / ".join(question_lines)
            category = question_lines[0] if question_lines else category_default

            text = f"问题：{question_full}\n\n答案：{answer}" if question_full else answer
            meta = self._common_meta(doc) | {
                "question": leaf_q,
                "title_path": title_path,
                "category": category,
                "qa_index": i,
            }
            out.append(Chunk(text=text, metadata=meta))
        return out
