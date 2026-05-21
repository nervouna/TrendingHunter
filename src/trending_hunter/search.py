from __future__ import annotations

from datetime import date
from pathlib import Path


def _extract_date_from_filename(filename: str) -> date | None:
    try:
        return date.fromisoformat(filename[:10])
    except (ValueError, IndexError):
        return None


def search_reports(
    base_dir: str = "./reports",
    keyword: str | None = None,
    source: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 0,
) -> list[tuple[str, str]]:
    dir_path = Path(base_dir)
    if not dir_path.is_dir():
        return []

    from_date = date.fromisoformat(date_from) if date_from else None
    to_date = date.fromisoformat(date_to) if date_to else None

    results: list[tuple[str, str]] = []
    for md_file in sorted(dir_path.glob("*.md")):
        if source and f"-{source}-" not in md_file.name:
            continue

        file_date = _extract_date_from_filename(md_file.name)
        if from_date and (file_date is None or file_date < from_date):
            continue
        if to_date and (file_date is None or file_date > to_date):
            continue

        content = md_file.read_text(encoding="utf-8")

        if keyword and keyword.lower() not in content.lower():
            continue

        excerpt = content[:200].replace("\n", " ")
        results.append((md_file.name, excerpt))

        if limit > 0 and len(results) >= limit:
            break

    return results
