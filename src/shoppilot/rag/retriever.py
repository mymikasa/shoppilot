from langchain_core.documents import Document

from shoppilot.rag import store as _store_mod


def similarity_search(query: str, k: int = 4) -> list[Document]:
    return _store_mod.get_vectorstore().similarity_search(query, k=k)
