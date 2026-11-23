"""Validated runtime configuration."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AIBAT_", env_file=".env", extra="ignore")

    api_key: str = Field(min_length=24)
    database_path: Path = Path("./data/jobs.sqlite3")
    workflows_dir: Path = Path("./workflows")
    allowed_http_hosts: str = ""
    request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)
    max_retries: int = Field(default=3, ge=1, le=10)
    worker_poll_seconds: float = Field(default=1.0, gt=0, le=60)
    worker_lease_seconds: int = Field(default=120, ge=30, le=3600)
    log_level: str = "INFO"

    @field_validator("api_key")
    @classmethod
    def validate_api_key(cls, value: str) -> str:
        if value in {"change-me", "replace-me", "your-secret-key", "dev-secret-key"}:
            raise ValueError("Set a strong AIBAT_API_KEY secret")
        return value

    @property
    def http_hosts(self) -> set[str]:
        return {host.strip().lower() for host in self.allowed_http_hosts.split(",") if host.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]  # value supplied via environment
