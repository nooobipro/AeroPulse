"""Ограничение частоты запросов (slowapi). За Caddy IP клиента берётся из X-Forwarded-For
(uvicorn запускается с --proxy-headers)."""
from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[settings.rate_limit_default],
    storage_uri=settings.rate_limit_storage_uri,
    enabled=settings.rate_limit_enabled,
)


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={"detail": "Слишком много запросов. Повторите попытку через минуту"},
        headers={"Retry-After": "60"},
    )
