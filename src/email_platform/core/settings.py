from functools import lru_cache

from pydantic import EmailStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8')

    app_name: str = 'Email Platform'
    environment: str = 'local'
    database_url: str = 'postgresql+psycopg://email_platform:email_platform@localhost:5432/email_platform'
    email_provider: str = 'console'
    default_from_email: EmailStr = 'no-reply@example.com'
    sendgrid_api_key: str | None = None
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool = True
    unsubscribe_secret: str = 'change-me'


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
