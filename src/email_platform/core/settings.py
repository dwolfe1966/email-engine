from functools import lru_cache

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    app_name: str = 'Email Platform'
    environment: str = 'local'
    cors_origins: list[str] = ['*']
    database_url: str = (
        'postgresql+psycopg://email_platform:email_platform@localhost:5432/email_platform'
    )
    database_migration_url: str | None = None
    email_provider: str = 'console'
    default_from_email: EmailStr = 'no-reply@example.com'
    sendgrid_api_key: str | None = None
    sendgrid_event_webhook_public_key: str | None = None
    sendgrid_event_webhook_require_signature: bool = True
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    unsubscribe_secret: str = 'change-me'

    @field_validator('database_url', 'database_migration_url', mode='before')
    @classmethod
    def normalize_postgres_driver(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value.startswith('postgresql://'):
            return value.replace('postgresql://', 'postgresql+psycopg://', 1)
        if value.startswith('postgres://'):
            return value.replace('postgres://', 'postgresql+psycopg://', 1)
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
