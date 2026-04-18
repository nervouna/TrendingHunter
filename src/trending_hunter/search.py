from __future__ import annotations

from pathlib import Path


def search_reports(
    base_dir: str = "./reports",
    keyword: str | None = None,
    source: str | None = None,
) -> list[tuple[str, str]]:
    dir_path = Path(base_dir)
    if not dir_path.is_dir():
        return []

    results: list[tuple[str, str]] = []
    for md_file in sorted(dir_path.glob("*.md")):
        if source and f"-{source}-" not in md_file.name:
            continue

        content = md_file.read_text(encoding="utf-8")

        if keyword and keyword.lower() not in content.lower():
            continue

        excerpt = content[:200].replace("\n", " ")
        results.append((md_file.name, excerpt))

    return results
