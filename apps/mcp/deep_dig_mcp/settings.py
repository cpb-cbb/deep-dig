from __future__ import annotations

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DEEP_DIG_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    workspace_dir: Path = Path("/workspace")
    output_dir: Path = Path("/output")
    api_base_url: str = "http://127.0.0.1:8001"
    api_token: SecretStr | None = None
    parser: str = "markitdown"
    max_file_bytes: int = 100 * 1024 * 1024
    max_preview_chars: int = 4_000
    markdown_chunk_chars: int = 50_000
    backend_max_text_chars: int = 200_000
    min_text_chars: int = 200
    min_chars_per_page: int = 50
    request_timeout_seconds: float = 30.0
    web_host: str = "0.0.0.0"
    web_port: int = 8787
    mcp_host: str = "127.0.0.1"
    mcp_port: int = 8002
    mcp_public_url: str = "http://127.0.0.1:8002/mcp"
    auth_issuer_url: str = "http://127.0.0.1:8001"

    @property
    def upload_dir(self) -> Path:
        return self.output_dir / ".uploads"

    @property
    def cache_dir(self) -> Path:
        return self.output_dir / "cache"
