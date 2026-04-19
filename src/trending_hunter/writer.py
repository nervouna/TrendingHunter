from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import yaml

from trending_hunter.models import Project, Report, Source

_SOURCE_LABELS: dict[Source, tuple[str, str]] = {
    Source.GITHUB: ("Stars", "stars/day"),
    Source.HACKER_NEWS: ("Score", "score/day"),
    Source.PRODUCT_HUNT: ("Votes", "votes/day"),
}


def sections_to_text(sections: dict[str, str]) -> str:
    parts: list[str] = []
    for name, content in sections.items():
        parts.append(f"## {name}\n{content}")
    return "\n\n".join(parts)


def render_report(report: Report) -> str:
    lines: list[str] = []

    count_label, velocity_label = _SOURCE_LABELS.get(
        report.project.source, ("Stars", "stars/day")
    )

    lines.append(f"**Source**: {report.project.source.value}")
    lines.append(f"**URL**: {report.project.url}")
    lines.append(f"**{count_label}**: {report.project.stars}")
    lines.append(f"**Velocity**: {report.project.star_velocity:.1f} {velocity_label}")
    if report.project.source == Source.GITHUB and report.project.repo_age_days is not None:
        lines.append(f"**Age**: {report.project.repo_age_days} days")
    lines.append(f"**Generated**: {report.generated_at.isoformat()}")
    lines.append(f"**Draft model**: {report.draft_model}")
    lines.append(f"**Audit model**: {report.audit_model}")
    if report.rewrite_model:
        lines.append(f"**Rewrite model**: {report.rewrite_model}")
    lines.append("")

    for name, content in report.sections.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def build_expected_filename(project: Project, date_str: str) -> str:
    source = project.source.value
    name = project.name.replace("/", "-")
    return f"{date_str}-{source}-{name}.md"


def get_report_path(project: Project, base_dir: str, date_obj: date | None = None) -> Path:
    d = date_obj or datetime.now().date()
    filename = build_expected_filename(project, d.isoformat())
    return Path(base_dir).expanduser() / filename


def report_exists(project: Project, base_dir: str, date_obj: date | None = None) -> bool:
    return get_report_path(project, base_dir, date_obj).exists()


def _build_filename(report: Report) -> str:
    date_str = report.generated_at.strftime("%Y-%m-%d")
    return build_expected_filename(report.project, date_str)


def _build_frontmatter(report: Report) -> str:
    fm = {
        "status": "inbox",
        "source_type": "trending",
        "source": report.project.url,
        "created": report.generated_at.isoformat(),
        "title": report.project.name,
        "trending_source": report.project.source.value,
        "tags": ["trending", report.project.source.value],
    }
    return "---\n" + yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False) + "---\n"


def save_report(report: Report, base_dir: str = "./reports") -> Path:
    dir_path = Path(base_dir).expanduser()
    dir_path.mkdir(parents=True, exist_ok=True)

    filename = _build_filename(report)
    path = dir_path / filename

    if path.exists():
        return path

    frontmatter = _build_frontmatter(report)
    body = render_report(report)
    path.write_text(frontmatter + body, encoding="utf-8")
    return path
