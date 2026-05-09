from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma

from shoppilot.config import get_settings
from shoppilot.rag import embeddings as _emb_mod


@lru_cache(maxsize=1)
def get_vectorstore() -> Chroma:
    settings = get_settings()
    persist_dir = Path(settings.chroma_path).resolve()
    persist_dir.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=settings.chroma_collection,
        embedding_function=_emb_mod.get_embeddings(),
        persist_directory=str(persist_dir),
    )
