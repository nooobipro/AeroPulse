"""Настройки приложения. Читаются из переменных окружения и файла .env."""
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    database_url: str = "sqlite:///./dev.db"
    auto_create_tables: bool = False  # только для локальной разработки; в проде работает Alembic

    # Аутентификация
    secret_key: str = "dev-insecure-secret-change-me-0123456789abcdef"
    access_token_minutes: int = 480
    cookie_name: str = "access_token"
    cookie_secure: bool = False  # true при работе по HTTPS
    login_max_attempts: int = 5
    login_lock_minutes: int = 15

    # Первый администратор (создаётся при старте, если администраторов ещё нет)
    first_admin_email: str | None = None
    first_admin_password: str | None = None
    first_admin_name: str = "Администратор"

    # Защита от CSRF: допустимые Origin для изменяющих запросов
    # (запросы с тем же хостом, что и в заголовке Host, разрешены всегда)
    app_origins: str = "http://localhost:5173,http://localhost:8080,http://localhost"

    # Ограничение частоты запросов
    rate_limit_enabled: bool = True
    rate_limit_default: str = "300/minute"
    rate_limit_storage_uri: str = "memory://"

    # Прочее
    export_max_concurrent: int = 2
    cache_ttl_seconds: int = 3600
    enable_docs: bool = True

    @property
    def origins(self) -> set[str]:
        return {o.strip().rstrip("/") for o in self.app_origins.split(",") if o.strip()}

    @model_validator(mode="after")
    def _check_production(self):
        if self.environment == "production":
            weak = self.secret_key.startswith(("dev-insecure", "CHANGE")) or len(self.secret_key) < 32
            if weak:
                raise ValueError(
                    "В production необходимо задать SECRET_KEY длиной не менее 32 символов "
                    "(python -c \"import secrets; print(secrets.token_urlsafe(48))\")"
                )
        return self


settings = Settings()
