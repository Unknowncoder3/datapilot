from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg2://datapilot:datapilot@localhost:5432/datapilot"
    upload_dir: str = "./storage/uploads"
    max_upload_size_mb: int = 25
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

@lru_cache
def get_settings():
    return Settings()
