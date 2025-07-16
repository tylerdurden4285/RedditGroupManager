from __future__ import annotations

import secrets
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = BASE_DIR / "instance" / "app.db"


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    flask_secret_key: str = Field(default_factory=lambda: secrets.token_hex(16))
    database_url: str | None = None
    database_path: str = str(DEFAULT_DB_PATH)
    user_db_path: str | None = None
    tz: str = "UTC"

    default_sched_time: str = "00:00"

    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str | None = None
    reddit_username: str | None = None
    reddit_password: str | None = None


    class Config:
        env_prefix = ""
        case_sensitive = False

