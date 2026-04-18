from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Source(str, Enum):
    GITHUB = "github"
    PRODUCT_HUNT = "product_hunt"
    HACKER_NEWS = "hacker_news"


class Project(BaseModel):
    name: str
    source: Source
    url: str
    fetched_at: datetime = Field(default_factory=datetime)
    stars: int
    star_velocity: float
    repo_age_days: int | None = None
    first_time_contributors: int | None = None
    description: str
    readme_excerpt: str = ""


class Report(BaseModel):
    project: Project
    generated_at: datetime = Field(default_factory=datetime)
    draft_model: str
    audit_model: str
    token_usage: dict[str, int] = Field(default_factory=lambda: {"draft": 0, "audit": 0})
    sections: dict[str, str]
    file_path: str
