"""Хеширование паролей (argon2) и JWT в HttpOnly-cookie."""
import hashlib
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from fastapi import Response

from app.config import settings
from app.utils import utcnow

_hasher = PasswordHasher()
# Для выравнивания времени ответа, когда пользователь не найден
DUMMY_HASH = _hasher.hash("dummy-password-for-timing-0")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_fingerprint(password_hash: str) -> str:
    """Отпечаток текущего пароля: после его смены ранее выданные токены перестают действовать."""
    return hashlib.sha256(password_hash.encode()).hexdigest()[:16]


def create_access_token(user) -> str:
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "pv": password_fingerprint(user.password_hash),
        "iat": int(now.timestamp()),
        "exp": now + timedelta(minutes=settings.access_token_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"], leeway=5)
    except jwt.PyJWTError:
        return None


def set_auth_cookie(response: Response, user) -> None:
    response.set_cookie(
        settings.cookie_name,
        create_access_token(user),
        max_age=settings.access_token_minutes * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.cookie_name, path="/", httponly=True, secure=settings.cookie_secure, samesite="lax"
    )
