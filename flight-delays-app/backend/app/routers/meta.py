from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import stats_service as svc
from app.db import get_db
from app.deps import get_current_user
from app.schemas import FilterOptions, Highlights

router = APIRouter(tags=["Справочники"])


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/meta/filters", response_model=FilterOptions, dependencies=[Depends(get_current_user)])
def filter_options(db: Session = Depends(get_db)):
    return svc.filter_options(db)


@router.get("/public/highlights", response_model=Highlights)
def highlights(db: Session = Depends(get_db)):
    """Агрегированная сводка для лендинга (доступна гостям)."""
    return svc.highlights(db)
