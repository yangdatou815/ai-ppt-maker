"""Application settings loaded from env."""
from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    ollama_base_url: str = Field(
        default="http://host.docker.internal:11434", alias="OLLAMA_BASE_URL"
    )
    ollama_model: str = Field(default="qwen2.5:7b-instruct", alias="OLLAMA_MODEL")
    ollama_timeout_s: int = Field(default=120, alias="OLLAMA_TIMEOUT_S")

    workspace_dir: Path = Field(default=Path("/tmp/ai-ppt-maker"), alias="WORKSPACE_DIR")
    workspace_ttl_hours: int = Field(default=24, alias="WORKSPACE_TTL_HOURS")

    libreoffice_bin: str = Field(default="/usr/bin/soffice", alias="LIBREOFFICE_BIN")

    max_upload_mb: int = Field(default=50, alias="MAX_UPLOAD_MB")

    templates_dir: Path = Field(
        default=Path(__file__).resolve().parent.parent / "templates"
    )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
