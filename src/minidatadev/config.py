"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, SecretStr


class Settings(BaseModel):
    """Runtime settings with safe local defaults."""

    model_config = ConfigDict(frozen=True)

    app_env: str = Field(default="development")
    data_dir: Path = Field(default=Path(".minidatadev/data"))
    database_path: Path = Field(default=Path(".minidatadev/minidatadev.sqlite3"))
    max_upload_mb: int = Field(default=100, gt=0)
    ai_provider: str = Field(default="demo")
    ai_model: str = Field(default="gpt-5.6")
    openai_api_key: SecretStr | None = None
    retention_days: int = Field(default=30, gt=0)
    requests_per_hour: int = Field(default=30, gt=0)
    log_path: Path = Field(default=Path(".minidatadev/events.jsonl"))


@lru_cache
def get_settings() -> Settings:
    """Load settings from environment variables and an optional local .env."""

    import os

    load_dotenv()
    return Settings(
        app_env=os.getenv("MINIDATADEV_ENV", "development"),
        data_dir=Path(os.getenv("MINIDATADEV_DATA_DIR", ".minidatadev/data")),
        database_path=Path(
            os.getenv(
                "MINIDATADEV_DATABASE_PATH",
                ".minidatadev/minidatadev.sqlite3",
            )
        ),
        max_upload_mb=int(os.getenv("MINIDATADEV_MAX_UPLOAD_MB", "100")),
        ai_provider=os.getenv("MINIDATADEV_AI_PROVIDER", "demo"),
        ai_model=os.getenv("MINIDATADEV_AI_MODEL", "gpt-5.6"),
        openai_api_key=(
            SecretStr(os.environ["OPENAI_API_KEY"])
            if os.getenv("OPENAI_API_KEY")
            else None
        ),
        retention_days=int(os.getenv("MINIDATADEV_RETENTION_DAYS", "30")),
        requests_per_hour=int(os.getenv("MINIDATADEV_REQUESTS_PER_HOUR", "30")),
        log_path=Path(os.getenv("MINIDATADEV_LOG_PATH", ".minidatadev/events.jsonl")),
    )
