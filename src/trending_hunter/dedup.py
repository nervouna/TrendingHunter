from __future__ import annotations

import json
from pathlib import Path


class SeenUrls:
    def __init__(self, path: str | Path) -> None:
        self._path = Path(path).expanduser()
        self._seen: set[str] = set()
        self._dirty = False

    def load(self) -> None:
        if self._path.exists():
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._seen = set(data)

    def is_seen(self, url: str) -> bool:
        return url in self._seen

    def mark_seen(self, url: str) -> None:
        self._seen.add(url)
        self._dirty = True

    def save(self) -> None:
        if self._dirty:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(sorted(self._seen), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self._dirty = False
