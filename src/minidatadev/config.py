"""Environment-backed application configuration."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    """Runtime settings with safe local defaults."""

    model_config = ConfigDict(frozen=True)

    app_env: str = Field(default="development")
    data_dir: Path = Field(default=Path(".minidatadev/data"))
    database_path: Path = Field(default=Path(".minidatadev/minidatadev.sqlite3"))
    max_upload_mb: int = Field(default=100, gt=0)


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
    )
