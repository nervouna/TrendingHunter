from __future__ import annotations

from typing import Protocol, runtime_checkable

from trending_hunter.models import Project
from trending_hunter.settings import Settings


@runtime_checkable
class Fetcher(Protocol):
    def fetch(self, settings: Settings) -> list[Project]: ...
