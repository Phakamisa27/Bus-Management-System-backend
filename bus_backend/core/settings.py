"""Application settings loaded from environment / .env."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg2://postgres:phakathi@localhost:5432/bus_tracking_db"
    secret_key: str = "change-this-to-a-long-random-string"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    # SMTP / email settings. Read from environment (.env), never hardcoded.
    # For Gmail: SMTP_HOST=smtp.gmail.com, SMTP_PORT=587, and SMTP_PASSWORD
    # must be a Gmail "App Password" (not your normal account password).
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    # Base URL of the frontend, used to build the password reset link.
    frontend_url: str = "http://localhost:5500"


@lru_cache
def get_settings() -> Settings:
    return Settings()
