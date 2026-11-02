"""Экспорт отчётов и агрегированных таблиц. Только для аналитиков и администраторов."""
import threading
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app import reports
from app.audit import log_action
from app.config import settings
from app.db import get_db
from app.deps import require_role
from app.models import User
from app.ratelimit import limiter
from app.routers.common import get_filters
from app.stats_service import Filters

router = APIRouter(prefix="/reports", tags=["Отчёты"])
_slots = threading.BoundedSemaphore(settings.export_max_concurrent)


def _download(content: bytes, media_type: str, name: str) -> Response:
    return Response(content=content, media_type=media_type,
                    headers={"Content-Disposition": f'attachment; filename="{name}"', "Cache-Control": "no-store"})


@router.get("/export")
@limiter.limit("10/minute")
def export_report(
    request: Request,
    fmt: Literal["xlsx", "pdf"] = Query(alias="format"),
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    if not _slots.acquire(blocking=False):  # построение PDF с графиками ресурсоёмко
        raise HTTPException(status_code=429, detail="Сервер занят формированием других отчётов. Повторите через минуту")
    try:
        ctx = reports.build_context(db, f, user.email)
        if fmt == "xlsx":
            content = reports.build_xlsx(ctx)
            media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        else:
            content, media = reports.build_pdf(ctx), "application/pdf"
    finally:
        _slots.release()
    log_action(db, user, f"export_{fmt}", request=request)
    db.commit()
    return _download(content, media, f"flight-delays_{datetime.now():%Y%m%d_%H%M}.{fmt}")


@router.get("/csv")
@limiter.limit("30/minute")
def export_csv(
    request: Request,
    dataset: Literal["airlines", "hourly", "periods", "airports", "categories", "heatmap", "monthly"],
    decimal: Literal["comma", "point"] = "comma",
    f: Filters = Depends(get_filters),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("analyst")),
):
    header, rows = reports.csv_rows(db, f, dataset)
    log_action(db, user, "export_csv", details=dataset, request=request)
    db.commit()
    return _download(reports.build_csv(header, rows, decimal), "text/csv; charset=utf-8",
                     f"flight-delays_{dataset}_{datetime.now():%Y%m%d}.csv")
