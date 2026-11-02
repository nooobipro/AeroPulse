"""Точка входа FastAPI."""
import logging
import threading
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app import stats_service
from app.bootstrap import ensure_first_admin
from app.config import settings
from app.db import Base, SessionLocal, engine
from app.ratelimit import limiter, rate_limit_handler
from app.routers import admin, auth, meta, methods, reports, saved_filters, stats

logging.basicConfig(level=logging.INFO)


def _warm_up() -> None:
    try:
        with SessionLocal() as db:
            stats_service.warm_cache(db)
    except Exception:  # прогрев необязателен: например, данные ещё не загружены
        logging.getLogger(__name__).info("Прогрев кэша пропущен", exc_info=True)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_first_admin(db)
    if settings.environment != "test":
        threading.Thread(target=_warm_up, daemon=True).start()
    yield


app = FastAPI(
    title="Анализ задержек авиарейсов",
    description="API аналитического приложения: пунктуальность авиакомпаний и зависимость задержек от времени вылета.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.enable_docs else None,
    redoc_url=None,
    openapi_url="/api/openapi.json" if settings.enable_docs else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)


@app.middleware("http")
async def origin_check(request: Request, call_next):
    """Дополнительная защита от CSRF: изменяющие запросы принимаются только со «своего» Origin."""
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin:
            same_host = urlparse(origin).netloc == request.headers.get("host", "")
            if not same_host and origin.rstrip("/") not in settings.origins:
                return JSONResponse(status_code=403, content={"detail": "Недопустимый источник запроса"})
    return await call_next(request)


for module in (meta, auth, stats, methods, reports, saved_filters, admin):
    app.include_router(module.router, prefix="/api")
