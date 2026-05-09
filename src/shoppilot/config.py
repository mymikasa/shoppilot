from functools import lru_cache
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    deepseek_api_key: SecretStr = SecretStr("")
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 1024

    redis_url: str = "redis://localhost:6379/0"

    chroma_path: str = "./data/chroma"
    chroma_collection: str = "shoppilot_faq"

    embedding_provider: Literal["local", "dashscope"] = "local"
    embedding_model: str = "BAAI/bge-small-zh-v1.5"
    dashscope_api_key: SecretStr | None = None
    dashscope_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
