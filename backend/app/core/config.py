from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg2://datapilot:datapilot@localhost:55433/datapilot"
    )
    upload_dir: str = "backend/storage/uploads"
    max_upload_size_mb: int = 25

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings():
    settings = Settings()

    upload_path = Path(settings.upload_dir)

    # Resolve relative upload paths from the project root,
    # not from the terminal's current working directory.
    if not upload_path.is_absolute():
        upload_path = PROJECT_ROOT / upload_path

    settings.upload_dir = str(upload_path.resolve())
    upload_path.mkdir(parents=True, exist_ok=True)

    return settings
