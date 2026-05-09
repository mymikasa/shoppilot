"""共享 fixture：fake embeddings + tmp chroma + fake LLM + fakeredis。"""

from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

import pytest
from langchain_core.embeddings import FakeEmbeddings


def _clear_caches() -> None:
    from shoppilot.config import get_settings
    from shoppilot.rag import embeddings as emb_mod
    from shoppilot.rag import store as store_mod

    get_settings.cache_clear()
    emb_mod.get_embeddings.cache_clear()
    store_mod.get_vectorstore.cache_clear()


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch, tmp_path):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("CHROMA_PATH", str(tmp_path / "chroma"))
    monkeypatch.setenv("CHROMA_COLLECTION", f"test-{uuid.uuid4().hex[:6]}")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "local")
    monkeypatch.setenv("TOKENIZERS_PARALLELISM", "false")
    _clear_caches()
    yield
    # teardown 时不能直接 cache_clear，因为 monkeypatch 此刻仍在；
    # 等所有 fixture undo 完后，下次 setup 会再次 _clear_caches()


@pytest.fixture
def fake_embeddings(monkeypatch):
    fake = FakeEmbeddings(size=64)
    from shoppilot.rag import embeddings as emb_mod

    monkeypatch.setattr(emb_mod, "get_embeddings", lambda: fake)
    return fake


@pytest.fixture
def tmp_chroma(tmp_path: Path, fake_embeddings, monkeypatch):
    from langchain_chroma import Chroma

    persist = tmp_path / "chroma_inst"
    persist.mkdir(parents=True, exist_ok=True)
    store = Chroma(
        collection_name=f"test-{uuid.uuid4().hex[:6]}",
        embedding_function=fake_embeddings,
        persist_directory=str(persist),
    )

    from shoppilot.rag import store as store_mod

    monkeypatch.setattr(store_mod, "get_vectorstore", lambda: store)
    yield store
    try:
        shutil.rmtree(persist)
    except OSError:
        pass


def _make_fake_chat(responses: list[Any]):
    from tests._fakes import FakeToolCallingChat

    return FakeToolCallingChat(responses=list(responses))


@pytest.fixture
def make_fake_chat():
    return _make_fake_chat
