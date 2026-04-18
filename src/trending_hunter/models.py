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
    fetched_at: datetime = Field(default_factory=datetime.now)
    stars: int
    star_velocity: float
    repo_age_days: int | None = None
    first_time_contributors: int | None = None
    description: str
    readme_excerpt: str = ""


class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class Report(BaseModel):
    project: Project
    generated_at: datetime = Field(default_factory=datetime.now)
    draft_model: str
    audit_model: str
    rewrite_model: str = ""
    token_usage: dict[str, TokenUsage] = Field(default_factory=lambda: {
        "draft": TokenUsage(),
        "audit": TokenUsage(),
        "rewrite": TokenUsage(),
    })
    sections: dict[str, str]
    file_path: str
