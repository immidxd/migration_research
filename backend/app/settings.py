from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = Field(
        default="postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/migrationsdb",
        alias="DATABASE_URL",
    )
    db_echo: bool = Field(default=False, alias="DB_ECHO")

    host: str = Field(default="127.0.0.1", alias="HOST")
    port: int = Field(default=8765, alias="PORT")
    log_level: str = Field(default="info", alias="LOG_LEVEL")

    frontend_dev_url: str = Field(
        default="http://127.0.0.1:3001", alias="FRONTEND_DEV_URL"
    )

    google_service_account_json: str = Field(
        default="secrets/google-service-account.json",
        alias="GOOGLE_SERVICE_ACCOUNT_JSON",
    )
    sheets_sync_interval_min: int = Field(default=15, alias="SHEETS_SYNC_INTERVAL_MIN")


@lru_cache
def get_settings() -> Settings:
    return Settings()
