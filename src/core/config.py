"""Centralized application config."""

import os
from typing import Annotated, Literal

from dotenv import load_dotenv
from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Application config."""

    model_config = SettingsConfigDict(
        # env_file='.env',
        # env_file_encoding='utf-8',
        extra='ignore',
    )

    environment: Literal['production', 'development', 'test'] = 'development'
    log_level: Literal['INFO', 'WARNING', 'ERROR', 'DEBUG'] = 'DEBUG'
    jwt_secret: str
    database_url: str
    db_ingest_chunk_size: PositiveInt
    worker_max_jobs: PositiveInt
    worker_job_timeout_sec: PositiveInt
    redis_host: str
    redis_port: Annotated[int, Field(ge=1, le=65535)]
    redis_password: str | None
    allowed_origins: str

    review_url_template: str

    # SMTP Settings
    smtp_host: str
    smtp_port: int
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str


class DevConfig(AppConfig):
    """Development application config."""

    environment: Literal['production', 'development', 'test'] = 'development'
    log_level: Literal['INFO', 'WARNING', 'ERROR', 'DEBUG'] = 'DEBUG'
    jwt_secret: str = 'SET_ME_IN_PRODUCTION_HEHEHE'
    database_url: str = 'postgresql+psycopg://myuser:mypassword@localhost:5432/a20app'
    db_ingest_chunk_size: PositiveInt = 50
    worker_max_jobs: PositiveInt = 5
    worker_job_timeout_sec: PositiveInt = 60
    redis_host: str = 'localhost'
    redis_port: Annotated[int, Field(ge=1, le=65535)] = 6379
    redis_password: str | None = None
    allowed_origins: str = ''

    review_url_template: str = 'http://localhost:3000/review?token={token}'

    # SMTP Settings
    smtp_host: str = 'localhost'
    smtp_port: int = 1025  # Default for Mailhog
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str = 'noreply@example.com'


class ProdConfig(AppConfig):
    """Production application config."""

    environment: Literal['production', 'development', 'test'] = 'production'
    log_level: Literal['INFO', 'WARNING', 'ERROR', 'DEBUG'] = 'INFO'
    jwt_secret: str
    database_url: str
    db_ingest_chunk_size: PositiveInt
    worker_max_jobs: PositiveInt
    worker_job_timeout_sec: PositiveInt
    redis_host: str
    redis_port: Annotated[int, Field(ge=1, le=65535)]
    redis_password: str | None
    allowed_origins: str

    review_url_template: str

    # SMTP Settings
    smtp_host: str
    smtp_port: int
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str


# Load environment variables from .env file
load_dotenv()

_env = os.getenv('ENVIRONMENT', 'development').lower()

if _env == 'production':
    # ProdConfig will raise a validation error if required secrets (like jwt_secret) are missing.
    config = ProdConfig()
elif _env == 'test':
    config = DevConfig(environment='test')
else:
    # Default to development for local DX, but use DevConfig which provides defaults.
    config = DevConfig()
