import hashlib
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from shoppilot.rag import store as _store_mod

HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]
MAX_CHARS = 500
OVERLAP = 50


def _chunk_markdown(text: str) -> list[Document]:
    md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS)
    sections = md_splitter.split_text(text)
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHARS, chunk_overlap=OVERLAP
    )
    out: list[Document] = []
    for sec in sections:
        if len(sec.page_content) <= MAX_CHARS:
            out.append(sec)
        else:
            out.extend(char_splitter.split_documents([sec]))
    return out


def _stable_id(source: str, idx: int, content: str) -> str:
    digest = hashlib.sha1(f"{source}:{idx}:{content}".encode()).hexdigest()[:16]
    return f"{Path(source).stem}-{idx}-{digest}"


def ingest_directory(faq_dir: str | Path) -> int:
    """把 faq_dir 下所有 *.md 切分嵌入到向量库，返回写入的 chunk 数。"""
    faq_path = Path(faq_dir).resolve()
    if not faq_path.exists():
        raise FileNotFoundError(faq_path)

    docs: list[Document] = []
    ids: list[str] = []
    for md_file in sorted(faq_path.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        chunks = _chunk_markdown(text)
        for i, chunk in enumerate(chunks):
            chunk.metadata = {
                **chunk.metadata,
                "source": md_file.name,
                "section": chunk.metadata.get("h2") or chunk.metadata.get("h1") or "",
            }
            docs.append(chunk)
            ids.append(_stable_id(md_file.name, i, chunk.page_content))

    if not docs:
        return 0

    store = _store_mod.get_vectorstore()
    # 幂等：同 ID 重新 add 会被 upsert（chromadb 行为）
    store.add_documents(documents=docs, ids=ids)
    return len(docs)
