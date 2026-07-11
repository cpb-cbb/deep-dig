from functools import lru_cache
from uuid import UUID
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    env: Literal["development", "test", "staging", "production"] = "development"
    app_version: str = "0.1.0"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    supabase_url: AnyHttpUrl = "https://example.supabase.co"
    supabase_jwks_url: AnyHttpUrl = "https://example.supabase.co/auth/v1/.well-known/jwks.json"
    supabase_service_key: str = Field(default="", repr=False)
    dev_auth_enabled: bool = False
    dev_auth_user_id: UUID = UUID("00000000-0000-0000-0000-000000000001")
    dev_auth_email: str = "dev@deepdig.local"
    llm_provider: Literal["auto", "openrouter", "anthropic", "openai_compatible", "fake"] = "auto"
    llm_openrouter_key: str = Field(default="", repr=False)
    llm_anthropic_key: str = Field(default="", repr=False)
    llm_compat_base_url: str = "https://api.openai.com/v1"
    llm_compat_api_key: str = Field(default="", repr=False)
    llm_compat_model: str = "gpt-4o-mini"
    daily_cost_budget_usd: float = 200
    sentry_dsn: str = ""
    free_monthly_quota: int = 50
    free_batch_limit: int = 10
    free_concurrent_jobs: int = 1
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
