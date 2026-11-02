from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit import log_action
from app.config import settings
from app.db import get_db
from app.deps import get_current_user
from app.models import User
from app.ratelimit import limiter
from app.schemas import LoginIn, PasswordChangeIn, ProfileIn, RegisterIn, UserOut
from app.security import (
    DUMMY_HASH, clear_auth_cookie, hash_password, set_auth_cookie, verify_password,
)
from app.utils import as_utc, utcnow

router = APIRouter(prefix="/auth", tags=["Аутентификация"])


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, data: RegisterIn, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")
    now = utcnow()
    user = User(email=email, password_hash=hash_password(data.password), full_name=data.full_name.strip(),
                role="user", password_changed_at=now, last_login_at=now)
    db.add(user)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Пользователь с таким email уже зарегистрирован")
    log_action(db, user, "register", request=request)
    db.commit()
    set_auth_cookie(response, user)
    return user


@router.post("/login", response_model=UserOut)
@limiter.limit("10/minute")
def login(request: Request, data: LoginIn, response: Response, db: Session = Depends(get_db)):
    email = data.email.lower()
    user = db.scalar(select(User).where(User.email == email))
    now = utcnow()

    if user and user.locked_until and as_utc(user.locked_until) > now:
        minutes = int((as_utc(user.locked_until) - now).total_seconds() // 60) + 1
        log_action(db, user, "login_blocked", request=request)
        db.commit()
        raise HTTPException(status_code=429, detail=f"Слишком много неудачных попыток входа. Повторите через {minutes} мин.")

    password_ok = verify_password(user.password_hash if user else DUMMY_HASH, data.password)
    if not user or not password_ok:
        if user:
            user.failed_attempts += 1
            if user.failed_attempts >= settings.login_max_attempts:
                user.locked_until = now + timedelta(minutes=settings.login_lock_minutes)
                user.failed_attempts = 0
        log_action(db, user, "login_failed", request=request, email=email)
        db.commit()
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Учётная запись заблокирована администратором")

    user.failed_attempts, user.locked_until, user.last_login_at = 0, None, now
    log_action(db, user, "login", request=request)
    db.commit()
    set_auth_cookie(response, user)
    return user


@router.post("/logout", status_code=204)
def logout(response: Response):
    clear_auth_cookie(response)
    response.status_code = 204
    return response


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/session", response_model=UserOut | None)
def session(request: Request, db: Session = Depends(get_db)):
    """Для интерфейса: текущий пользователь или null для гостя (без ошибки 401 в консоли браузера)."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


@router.patch("/me", response_model=UserOut)
def update_me(data: ProfileIn, request: Request, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    user.full_name = data.full_name.strip()
    log_action(db, user, "profile_update", request=request)
    db.commit()
    return user


@router.post("/change-password", response_model=UserOut)
@limiter.limit("5/minute")
def change_password(request: Request, data: PasswordChangeIn, response: Response,
                    user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not verify_password(user.password_hash, data.current_password):
        log_action(db, user, "password_change_failed", request=request)
        db.commit()
        raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")
    user.password_hash = hash_password(data.new_password)
    user.password_changed_at = utcnow()  # отзывает все ранее выданные токены
    log_action(db, user, "password_change", request=request)
    db.commit()
    set_auth_cookie(response, user)  # новая сессия для текущего устройства
    return user
