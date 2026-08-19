from functools import lru_cache
from pathlib import Path
from uuid import UUID
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["development", "test", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    auth_secret: str = Field(..., repr=False)
    local_auth_username: str = "admin"
    local_auth_password: str = Field(..., repr=False)
    local_auth_user_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    local_auth_email: str = "admin@deepdig.local"
    parsed_cache_enabled: bool = False
    parsed_cache_dir: Path = Path("./parsed_cache")
    upload_max_bytes: int = 50_000_000
    llm_provider: Literal["auto", "openrouter", "anthropic", "openai_compatible", "fake"] = "auto"
    llm_openrouter_key: str = Field(default="", repr=False)
    llm_openrouter_model: str = "anthropic/claude-3.5-haiku"
    llm_anthropic_key: str = Field(default="", repr=False)
    llm_anthropic_model: str = "claude-3-5-haiku-latest"
    llm_compat_base_url: str = "https://api.openai.com/v1"
    llm_compat_api_key: str = Field(default="", repr=False)
    llm_compat_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0
    daily_cost_budget_usd: float = 200
    sentry_dsn: str = ""
    max_text_chars: int = 200_000
    worker_max_jobs: int = 8
    item_job_timeout_seconds: int = 600
    item_max_tries: int = 3
    item_retry_base_seconds: float = 2.0
    item_queue_expiry_seconds: int = 604_800


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
