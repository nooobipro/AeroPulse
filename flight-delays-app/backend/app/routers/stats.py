from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app import stats_service as svc
from app.db import get_db
from app.deps import get_current_user
from app.routers.common import get_filters
from app.schemas import (
    AirlineRow, AirportRow, CategoryRow, CompareOut, HeatCell, HourRow, KPIOut, MonthRow, PeriodRow,
)
from app.stats_service import Filters

router = APIRouter(prefix="/stats", tags=["Статистика"], dependencies=[Depends(get_current_user)])


@router.get("/kpi", response_model=KPIOut)
def kpi(db: Session = Depends(get_db), f: Filters = Depends(get_filters)):
    return svc.kpi(db, f)


@router.get("/airlines", response_model=list[AirlineRow])
def airlines(db: Session = Depends(get_db), f: Filters = Depends(get_filters)):
    return svc.by_airline(db, f)


@router.get("/hourly", response_model=list[HourRow])
def hourly(db: Session = Depends(get_db), f: Filters = Depends(get_filters)):
    return svc.by_hour(db, f)


@router.get("/periods", response_model=list[PeriodRow])
def periods(db: Session = Depends(get_db), f: Filters = Depends(get_filters)):
    return svc.by_period(db, f)


@router.get("/heatmap", response_model=list[HeatCell])
def heatmap(db: Session = Depends(get_db), f: Filters = Depends(get_filters)):
    return svc.heatmap(db, f)


@router.get("/monthly", response_model=list[MonthRow])
def monthly(db: Session = Depends(get_db), f: Filters = Depends(get_filters)):
    return svc.monthly(db, f)


@router.get("/airports", response_model=list[AirportRow])
def airports(
    db: Session = Depends(get_db),
    f: Filters = Depends(get_filters),
    sort: Literal["share", "flights", "avg_delay"] = "share",
    order: Literal["asc", "desc"] = "desc",
    min_flights: int = Query(default=200, ge=1),
    limit: int = Query(default=20, ge=1, le=400),
):
    return svc.by_airport(db, f, sort, order, min_flights, limit)


@router.get("/categories", response_model=list[CategoryRow])
def categories(db: Session = Depends(get_db), f: Filters = Depends(get_filters)):
    return svc.categories(db, f)


@router.get("/compare", response_model=CompareOut)
def compare(
    airline_a: int = Query(ge=1),
    airline_b: int = Query(ge=1),
    db: Session = Depends(get_db),
    f: Filters = Depends(get_filters),
):
    if airline_a == airline_b:
        raise HTTPException(status_code=422, detail="Выберите две разные авиакомпании")
    names = svc.airline_map(db)
    if airline_a not in names or airline_b not in names:
        raise HTTPException(status_code=404, detail="Авиакомпания не найдена")
    return svc.compare(db, f, airline_a, airline_b)
