"""Администрирование: пользователи, журнал действий, справочники, сведения о данных."""
from datetime import date, datetime, time, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app import stats_service as svc
from app.audit import log_action
from app.cache import cache
from app.db import get_db
from app.deps import require_role
from app.models import (
    Airline, Airport, AuditLog, DataVersion, FlightAgg, SavedFilter, StatTest, User,
)
from app.schemas import (
    AirlineOut, AirlinePatch, AirportOut, AirportPatch, AirportsPage, AuditPage, DataInfo,
    DataVersionOut, UserOut, UserPatch, UsersPage,
)

admin_required = require_role("admin")
router = APIRouter(prefix="/admin", tags=["Администрирование"], dependencies=[Depends(admin_required)])


# ───────── Пользователи ─────────
@router.get("/users", response_model=UsersPage)
def list_users(
    search: str | None = Query(default=None, max_length=100),
    role: str | None = Query(default=None, pattern="^(user|analyst|admin)$"),
    active: bool | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if search:
        stmt = stmt.where(or_(User.email.icontains(search, autoescape=True),
                              User.full_name.icontains(search, autoescape=True)))
    if role:
        stmt = stmt.where(User.role == role)
    if active is not None:
        stmt = stmt.where(User.is_active == active)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(User.id).offset((page - 1) * page_size).limit(page_size)).all()
    return UsersPage(items=items, total=total, page=page, page_size=page_size)


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(user_id: int, data: UserPatch, request: Request, admin: User = Depends(admin_required),
               db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    changes = data.model_dump(exclude_unset=True)
    if user.id == admin.id and (changes.get("role", "admin") != "admin" or changes.get("is_active") is False):
        raise HTTPException(status_code=400, detail="Нельзя понизить или заблокировать собственную учётную запись")
    notes = []
    if "role" in changes and changes["role"] != user.role:
        notes.append(f"роль {user.role} → {changes['role']}")
        user.role = changes["role"]
    if "is_active" in changes and changes["is_active"] != user.is_active:
        notes.append("разблокирован" if changes["is_active"] else "заблокирован")
        user.is_active = changes["is_active"]
        if changes["is_active"]:
            user.failed_attempts, user.locked_until = 0, None
    if "full_name" in changes and changes["full_name"] is not None:
        user.full_name = changes["full_name"].strip()
        notes.append("изменено имя")
    if notes:
        log_action(db, admin, "admin_user_update", details=f"{user.email}: " + "; ".join(notes), request=request)
    db.commit()
    return user


@router.delete("/users/{user_id}", status_code=204)
def delete_user(user_id: int, request: Request, admin: User = Depends(admin_required),
                db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить собственную учётную запись")
    email = user.email
    db.execute(update(AuditLog).where(AuditLog.user_id == user.id).values(user_id=None))
    db.query(SavedFilter).filter(SavedFilter.user_id == user.id).delete()
    db.delete(user)
    log_action(db, admin, "admin_user_delete", details=email, request=request)
    db.commit()


# ───────── Журнал ─────────
@router.get("/audit", response_model=AuditPage)
def audit(
    action: str | None = Query(default=None, max_length=48),
    email: str | None = Query(default=None, max_length=100),
    date_from: date | None = None,
    date_to: date | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(AuditLog)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if email:
        stmt = stmt.where(AuditLog.user_email.icontains(email, autoescape=True))
    if date_from:
        stmt = stmt.where(AuditLog.created_at >= datetime.combine(date_from, time.min, tzinfo=timezone.utc))
    if date_to:
        stmt = stmt.where(AuditLog.created_at <= datetime.combine(date_to, time.max, tzinfo=timezone.utc))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return AuditPage(items=items, total=total, page=page, page_size=page_size)


# ───────── Справочники ─────────
@router.get("/airlines", response_model=list[AirlineOut])
def list_airlines(db: Session = Depends(get_db)):
    return db.scalars(select(Airline).order_by(Airline.name)).all()


@router.patch("/airlines/{airline_id}", response_model=AirlineOut)
def patch_airline(airline_id: int, data: AirlinePatch, request: Request, admin: User = Depends(admin_required),
                  db: Session = Depends(get_db)):
    item = db.get(Airline, airline_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Авиакомпания не найдена")
    old, item.name = item.name, data.name.strip()
    log_action(db, admin, "admin_airline_update", details=f"{item.code}: «{old}» → «{item.name}»", request=request)
    db.commit()
    cache.clear()
    return item


@router.get("/airports", response_model=AirportsPage)
def list_airports(
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    db: Session = Depends(get_db),
):
    stmt = select(Airport)
    if search:
        stmt = stmt.where(or_(Airport.code.icontains(search, autoescape=True),
                              Airport.name.icontains(search, autoescape=True),
                              Airport.city.icontains(search, autoescape=True)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    items = db.scalars(stmt.order_by(Airport.code).offset((page - 1) * page_size).limit(page_size)).all()
    return AirportsPage(items=items, total=total, page=page, page_size=page_size)


@router.patch("/airports/{airport_id}", response_model=AirportOut)
def patch_airport(airport_id: int, data: AirportPatch, request: Request, admin: User = Depends(admin_required),
                  db: Session = Depends(get_db)):
    item = db.get(Airport, airport_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Аэропорт не найден")
    item.name, item.city, item.state = data.name.strip(), data.city.strip(), data.state.strip()
    log_action(db, admin, "admin_airport_update", details=item.code, request=request)
    db.commit()
    cache.clear()
    return item


# ───────── Данные ─────────
@router.get("/data", response_model=DataInfo)
def data_info(db: Session = Depends(get_db)):
    history = db.scalars(select(DataVersion).order_by(DataVersion.id.desc()).limit(20)).all()
    count = lambda model: db.scalar(select(func.count()).select_from(model)) or 0
    return DataInfo(
        current=DataVersionOut.model_validate(history[0]) if history else None,
        history=[DataVersionOut.model_validate(h) for h in history],
        counts={"users": count(User), "aggregate_rows": count(FlightAgg), "airlines": count(Airline),
                "airports": count(Airport), "stat_tests": count(StatTest), "audit_records": count(AuditLog)},
    )
