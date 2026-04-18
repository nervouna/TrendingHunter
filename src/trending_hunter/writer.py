from __future__ import annotations

from datetime import datetime
from pathlib import Path

from trending_hunter.models import Report


def render_report(report: Report) -> str:
    lines: list[str] = []
    lines.append(f"# {report.project.name}")
    lines.append("")
    lines.append(f"**Source**: {report.project.source.value}")
    lines.append(f"**URL**: {report.project.url}")
    lines.append(f"**Stars**: {report.project.stars}")
    lines.append(f"**Velocity**: {report.project.star_velocity:.1f} stars/day")
    if report.project.repo_age_days is not None:
        lines.append(f"**Age**: {report.project.repo_age_days} days")
    lines.append(f"**Generated**: {report.generated_at.isoformat()}")
    lines.append(f"**Draft model**: {report.draft_model}")
    lines.append(f"**Audit model**: {report.audit_model}")
    lines.append("")

    for name, content in report.sections.items():
        lines.append(f"## {name}")
        lines.append("")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def _build_filename(report: Report) -> str:
    date_str = report.generated_at.strftime("%Y-%m-%d")
    source = report.project.source.value
    name = report.project.name.replace("/", "-")
    return f"{date_str}-{source}-{name}.md"


def save_report(report: Report, base_dir: str = "./reports") -> Path:
    dir_path = Path(base_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    filename = _build_filename(report)
    path = dir_path / filename

    if path.exists():
        return path

    content = render_report(report)
    path.write_text(content, encoding="utf-8")
    return path
