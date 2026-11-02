from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import log_action
from app.db import get_db
from app.deps import require_role
from app.models import SavedFilter, User
from app.schemas import SavedFilterIn, SavedFilterOut

router = APIRouter(prefix="/saved-filters", tags=["Сохранённые фильтры"])
MAX_PER_USER = 50


@router.get("", response_model=list[SavedFilterOut])
def list_filters(user: User = Depends(require_role("analyst")), db: Session = Depends(get_db)):
    return db.scalars(select(SavedFilter).where(SavedFilter.user_id == user.id).order_by(SavedFilter.name)).all()


@router.post("", response_model=SavedFilterOut, status_code=201)
def create_filter(data: SavedFilterIn, request: Request, user: User = Depends(require_role("analyst")),
                  db: Session = Depends(get_db)):
    count = db.scalar(select(func.count()).select_from(SavedFilter).where(SavedFilter.user_id == user.id))
    if count >= MAX_PER_USER:
        raise HTTPException(status_code=409, detail=f"Можно сохранить не более {MAX_PER_USER} наборов")
    item = SavedFilter(user_id=user.id, name=data.name, params=data.params.model_dump())
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Набор с таким названием уже существует")
    log_action(db, user, "saved_filter_create", details=data.name, request=request)
    db.commit()
    return item


@router.delete("/{filter_id}", status_code=204)
def delete_filter(filter_id: int, request: Request, user: User = Depends(require_role("analyst")),
                  db: Session = Depends(get_db)):
    item = db.get(SavedFilter, filter_id)
    if item is None or item.user_id != user.id:  # чужие наборы неотличимы от несуществующих
        raise HTTPException(status_code=404, detail="Набор не найден")
    log_action(db, user, "saved_filter_delete", details=item.name, request=request)
    db.delete(item)
    db.commit()
