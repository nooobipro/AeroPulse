# syntax=docker/dockerfile:1
FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /srv
RUN useradd --create-home --uid 10001 appuser
COPY requirements.txt .
RUN pip install -r requirements.txt

# Офлайн-конвейер загрузки данных (pandas, scipy). Запуск: docker compose --profile pipeline run --rm pipeline --demo
FROM base AS pipeline
COPY requirements-pipeline.txt .
RUN pip install -r requirements-pipeline.txt
COPY --chown=appuser:appuser . .
USER appuser
ENTRYPOINT ["python", "-m", "pipeline.run"]

# Образ веб-приложения (собирается по умолчанию). При старте применяет миграции БД.
FROM base AS app
COPY --chown=appuser:appuser . .
USER appuser
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' --workers ${WEB_CONCURRENCY:-2}"]
