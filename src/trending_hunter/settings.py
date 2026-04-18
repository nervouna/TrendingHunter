from __future__ import annotations

from pydantic import BaseModel


class GitHubSourceConfig(BaseModel):
    enabled: bool = True
    language: str = ""
    since: str = "daily"
    token: str = ""


class ProductHuntSourceConfig(BaseModel):
    enabled: bool = True
    token: str = ""
    top_n: int = 20


class HackerNewsSourceConfig(BaseModel):
    enabled: bool = True
    top_n: int = 30


class SourcesConfig(BaseModel):
    github: GitHubSourceConfig = GitHubSourceConfig()
    product_hunt: ProductHuntSourceConfig = ProductHuntSourceConfig()
    hacker_news: HackerNewsSourceConfig = HackerNewsSourceConfig()


class SignalGateConfig(BaseModel):
    min_star_velocity: float = 10.0
    max_repo_age_days: int = 365
    min_first_time_contributors: int = 0


class LLMStageConfig(BaseModel):
    base_url: str = ""
    api_key: str = ""
    model: str = ""
    max_tokens: int = 4096
    timeout: float = 120.0


class LLMConfig(BaseModel):
    draft: LLMStageConfig = LLMStageConfig()
    audit: LLMStageConfig = LLMStageConfig()
    rewrite: LLMStageConfig = LLMStageConfig()


class TavilyConfig(BaseModel):
    api_key: str = ""


class KnowledgeBaseConfig(BaseModel):
    path: str = "./reports"


class ModelPricing(BaseModel):
    input_per_million: float
    output_per_million: float


class Settings(BaseModel):
    sources: SourcesConfig = SourcesConfig()
    signal_gate: SignalGateConfig = SignalGateConfig()
    llm: LLMConfig = LLMConfig()
    tavily: TavilyConfig = TavilyConfig()
    knowledge_base: KnowledgeBaseConfig = KnowledgeBaseConfig()
    model_pricing: dict[str, ModelPricing] = {}
    proxy: str = ""
