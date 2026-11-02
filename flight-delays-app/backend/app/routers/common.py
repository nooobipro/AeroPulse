"""Общие зависимости роутеров: разбор и проверка фильтров из query-параметров."""
from typing import Literal

from fastapi import HTTPException, Query

from app.schemas import PERIOD_PATTERN
from app.stats_service import Filters


def _ym(value: str | None) -> int | None:
    return int(value[:4]) * 100 + int(value[5:7]) if value else None


def get_filters(
    airline_id: list[int] = Query(default=[], max_length=50),
    airport_id: list[int] = Query(default=[], max_length=100),
    period_from: str | None = Query(default=None, pattern=PERIOD_PATTERN),
    period_to: str | None = Query(default=None, pattern=PERIOD_PATTERN),
    hour_from: int = Query(default=0, ge=0, le=23),
    hour_to: int = Query(default=23, ge=0, le=23),
    threshold: int = Query(default=0),
    avg_mode: Literal["all", "delayed"] = Query(default="all"),
) -> Filters:
    if threshold not in (0, 15):
        raise HTTPException(status_code=422, detail="Порог задержки должен быть 0 или 15 минут")
    if hour_from > hour_to:
        raise HTTPException(status_code=422, detail="Начальный час не может быть больше конечного")
    pf, pt = _ym(period_from), _ym(period_to)
    if pf and pt and pf > pt:
        raise HTTPException(status_code=422, detail="Начало периода не может быть позже его конца")
    return Filters(
        airline_ids=tuple(sorted(set(airline_id))),
        airport_ids=tuple(sorted(set(airport_id))),
        period_from=pf, period_to=pt, hour_from=hour_from, hour_to=hour_to,
        threshold=threshold, avg_mode=avg_mode,
    )
