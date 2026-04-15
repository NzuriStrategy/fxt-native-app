"""
Central configuration for the lead intelligence pipeline.

All settings are read from environment variables (via a .env file in development).
Pydantic-settings validates types and raises on missing required values at startup,
so misconfiguration fails loudly rather than silently at runtime.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    url: str = Field(description="SQLAlchemy-compatible database URL")
    pool_size: int = 10
    echo_sql: bool = False


class AISettings(BaseSettings):
    anthropic_api_key: SecretStr = Field(description="Anthropic API key")
    openai_api_key: SecretStr | None = None
    default_model: str = "claude-sonnet-4-6"
    max_tokens: int = 2048
    temperature: float = 0.0


class CrawlingSettings(BaseSettings):
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 30
    user_agent: str = "FXT-LeadIntelligence/0.1 (research bot)"
    playwright_headless: bool = True


class IngestionSettings(BaseSettings):
    news_api_key: SecretStr | None = None
    # Add source-specific keys here as integrations are built


class ScoringSettings(BaseSettings):
    # Minimum composite score (0–100) to qualify a company as a lead
    lead_threshold: float = 60.0


class PipelineSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    env: str = "development"
    log_level: str = "INFO"

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[call-arg]
    ai: AISettings = Field(default_factory=AISettings)  # type: ignore[call-arg]
    crawling: CrawlingSettings = Field(default_factory=CrawlingSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)


# Module-level singleton — import this everywhere
settings = PipelineSettings()
