"""Centralized application config."""

from typing import Annotated, Literal

from pydantic import Field, PositiveInt, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application config."""

    environment: Literal['production', 'development', 'test'] = 'development'
    log_level: Literal['INFO', 'WARNING', 'ERROR', 'DEBUG'] = 'DEBUG'
    jwt_secret: str = 'PLEASE_SET_ME_IN_PRODUCTION'
    database_url: str = 'sqlite+aiosqlite:///./data/app.db'
    pg_dsn: PostgresDsn | None = None
    motherduck_token: str | None = None
    db_ingest_chunk_size: PositiveInt = 50
    worker_max_jobs: PositiveInt = 5
    worker_job_timeout_sec: PositiveInt = 60
    redis_host: str = 'localhost'
    redis_port: Annotated[int, Field(ge=1, le=65535)] = 6379
    allowed_origins: str = ''

    # SMTP Settings
    smtp_host: str = 'localhost'
    smtp_port: int = 1025  # Default for Mailhog
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = 'noreply@example.com'
    frontend_url: str = 'http://localhost:3000'

    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        extra='ignore',
    )


config = Config()
