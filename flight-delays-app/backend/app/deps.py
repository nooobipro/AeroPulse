"""Зависимости FastAPI: текущий пользователь и проверка роли (на сервере, а не в интерфейсе)."""
from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.domain import ROLE_RANK
from app.models import User
from app.security import decode_access_token, password_fingerprint


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail="Требуется вход в систему")
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Сессия истекла. Войдите снова")
    try:
        user = db.get(User, int(payload["sub"]))
    except (KeyError, ValueError):
        user = None
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Учётная запись недоступна")
    # Смена пароля отзывает все ранее выданные токены
    if payload.get("pv") != password_fingerprint(user.password_hash):
        raise HTTPException(status_code=401, detail="Сессия истекла. Войдите снова")
    return user


def require_role(min_role: str):
    """Роли иерархичны: пользователь < аналитик < администратор."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if ROLE_RANK.get(user.role, 0) < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403, detail="Недостаточно прав для этого действия")
        return user

    return dependency
