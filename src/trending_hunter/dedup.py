from __future__ import annotations

import json
import logging
import os
import tempfile
import time
from pathlib import Path

log = logging.getLogger(__name__)


class SeenUrls:
    def __init__(self, path: str | Path, ttl_days: int | None = None) -> None:
        self._path = Path(path).expanduser()
        self._ttl_days = ttl_days
        self._seen: set[str] = set()
        self._dirty = False

    def load(self) -> None:
        if not self._path.exists():
            return

        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            log.warning("Corrupted %s — starting fresh", self._path)
            return

        if self._ttl_days is not None:
            # New dict format: {url: timestamp}
            if isinstance(raw, dict):
                cutoff = time.time() - self._ttl_days * 86400
                self._seen = {url for url, ts in raw.items() if ts > cutoff}
            # Backward compat: old list format — treat as current
            elif isinstance(raw, list):
                self._seen = set(raw)
        else:
            # No TTL: support both formats
            if isinstance(raw, dict):
                self._seen = set(raw.keys())
            elif isinstance(raw, list):
                self._seen = set(raw)

    def is_seen(self, url: str) -> bool:
        return url in self._seen

    def mark_seen(self, url: str) -> None:
        self._seen.add(url)
        self._dirty = True

    def save(self) -> None:
        if not self._dirty:
            return

        self._path.parent.mkdir(parents=True, exist_ok=True)

        if self._ttl_days is not None:
            now = time.time()
            data: dict[str, float] = {}
            # Preserve existing timestamps for already-known URLs
            existing: dict[str, float] = {}
            if self._path.exists():
                try:
                    raw = json.loads(self._path.read_text(encoding="utf-8"))
                    if isinstance(raw, dict):
                        existing = raw
                except json.JSONDecodeError:
                    pass
            for url in self._seen:
                data[url] = existing.get(url, now)
            payload = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            payload = json.dumps(sorted(self._seen), ensure_ascii=False, indent=2)

        fd, tmp_path = tempfile.mkstemp(
            dir=self._path.parent,
            suffix=".tmp",
            prefix=".seen_urls.",
        )
        try:
            os.write(fd, payload.encode("utf-8"))
            os.close(fd)
            fd = -1
            os.rename(tmp_path, self._path)
        except BaseException:
            if fd >= 0:
                os.close(fd)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        self._dirty = False
