from functools import lru_cache

from langchain_core.embeddings import Embeddings

from shoppilot.config import get_settings


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    settings = get_settings()
    if settings.embedding_provider == "local":
        from langchain_huggingface import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
    if settings.embedding_provider == "dashscope":
        from langchain_openai import OpenAIEmbeddings

        if settings.dashscope_api_key is None:
            raise RuntimeError("EMBEDDING_PROVIDER=dashscope 需要配置 DASHSCOPE_API_KEY")
        return OpenAIEmbeddings(
            model=settings.embedding_model,
            base_url=settings.dashscope_base_url,
            api_key=settings.dashscope_api_key,
        )
    raise ValueError(f"unsupported embedding_provider: {settings.embedding_provider}")
