"""增量同步：维护 chunk_id → content_hash 的快照，用于跳过未变 + 删除孤儿。

manifest 是个普通 JSON 文件，跟向量库放一起（chroma_path 旁边）。
"""

from __future__ import annotations

import json
from pathlib import Path


class Manifest:
    def __init__(self, path: Path):
        self.path = path
        self._data: dict[str, str] = {}  # chunk_id -> content_hash
        if path.exists():
            try:
                self._data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def known_ids(self) -> set[str]:
        return set(self._data.keys())

    def get_hash(self, chunk_id: str) -> str | None:
        return self._data.get(chunk_id)

    def set(self, chunk_id: str, content_hash: str) -> None:
        self._data[chunk_id] = content_hash

    def remove(self, chunk_id: str) -> None:
        self._data.pop(chunk_id, None)

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
