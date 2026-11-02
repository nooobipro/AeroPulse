"""Создание первого администратора из переменных окружения."""
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.security import hash_password
from app.utils import utcnow

log = logging.getLogger(__name__)


def ensure_first_admin(db: Session) -> None:
    email, password = settings.first_admin_email, settings.first_admin_password
    if not email or not password:
        return
    if password.startswith("CHANGE"):
        log.error("FIRST_ADMIN_PASSWORD не изменён (значение-заглушка из .env.example): администратор не создан.")
        return
    if db.scalar(select(User.id).where(User.role == "admin").limit(1)) is not None:
        return
    db.add(
        User(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            full_name=settings.first_admin_name,
            role="admin",
            password_changed_at=utcnow(),
        )
    )
    db.commit()
    log.warning("Создан первый администратор %s. Удалите FIRST_ADMIN_PASSWORD из окружения.", email)
