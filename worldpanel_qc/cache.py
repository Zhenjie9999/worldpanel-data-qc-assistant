from __future__ import annotations

import hashlib
import json
from pathlib import Path


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hash(value) -> str:
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class JsonCache:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, namespace: str, key: str) -> Path:
        safe_key = "".join(character for character in key if character.isalnum() or character in {"-", "_"})[:160]
        return self.root / namespace / f"{safe_key}.json"

    def get(self, namespace: str, key: str):
        path = self._path(namespace, key)
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def set(self, namespace: str, key: str, value) -> None:
        path = self._path(namespace, key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
        except OSError:
            return
