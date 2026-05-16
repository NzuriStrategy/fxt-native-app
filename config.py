"""
Central configuration for the lead intelligence pipeline.

All settings are read from environment variables (via a .env file in development).
Pydantic-settings validates types and raises on missing required values at startup,
so misconfiguration fails loudly rather than silently at runtime.
"""

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


# Nested sections are plain BaseModel — only PipelineSettings is a BaseSettings.
# This is the correct pydantic-settings pattern for nested configuration:
# the top-level class reads env vars; nested classes are just value containers.
# With env_nested_delimiter="__", DATABASE__URL maps to settings.database.url.

class DatabaseSettings(BaseModel):
    url: str = Field("sqlite:///./lead_intelligence.db", description="SQLAlchemy-compatible database URL")
    pool_size: int = 10
    echo_sql: bool = False


class AISettings(BaseModel):
    # Optional so early pipeline stages (CSV ingestion, crawling, parsing)
    # can run without an Anthropic key.  The AI enrichment stage will raise
    # clearly at call time if the key is missing.
    anthropic_api_key: SecretStr | None = None
    default_model: str = "claude-sonnet-4-6"
    max_tokens: int = 2048
    temperature: float = 0.0


class CrawlingSettings(BaseModel):
    max_concurrent_requests: int = 10
    request_timeout_seconds: int = 30
    user_agent: str = "FXT-LeadIntelligence/0.1 (research bot)"
    playwright_headless: bool = True


class IngestionSettings(BaseModel):
    news_api_key: SecretStr | None = None
    # Default CSV file used by CompanyRegistryIngestor when no path is given.
    # Override with INGESTION__CSV_PATH=/path/to/file.csv in .env
    csv_path: str | None = None


class ScoringSettings(BaseModel):
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

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    ai: AISettings = Field(default_factory=AISettings)
    crawling: CrawlingSettings = Field(default_factory=CrawlingSettings)
    ingestion: IngestionSettings = Field(default_factory=IngestionSettings)
    scoring: ScoringSettings = Field(default_factory=ScoringSettings)


# Module-level singleton — import this everywhere
settings = PipelineSettings()
