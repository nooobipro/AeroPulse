"""Журнал действий. Запись добавляется в текущую транзакцию — commit делает вызывающий код."""
from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def client_ip(request: Request | None) -> str:
    if request is None or request.client is None:
        return ""
    return request.client.host or ""


def log_action(
    db: Session,
    user: User | None,
    action: str,
    details: str = "",
    request: Request | None = None,
    email: str | None = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id if user else None,
            user_email=(user.email if user else (email or "")),
            action=action,
            details=details[:2000],
            ip=client_ip(request),
        )
    )
