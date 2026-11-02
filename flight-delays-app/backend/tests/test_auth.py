import uuid

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import PASSWORD, create_user


def new_email():
    return f"u-{uuid.uuid4().hex[:8]}@example.com"


def test_register_login_me_logout(make_client):
    c = make_client()
    email = new_email()
    r = c.post("/api/auth/register", json={"email": email.upper(), "password": PASSWORD, "full_name": " Иван "})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["email"] == email and body["role"] == "user" and body["full_name"] == "Иван"
    assert "httponly" in r.headers["set-cookie"].lower() and "samesite=lax" in r.headers["set-cookie"].lower()
    assert c.get("/api/auth/me").json()["email"] == email
    assert c.post("/api/auth/logout").status_code == 204
    assert c.get("/api/auth/me").status_code == 401


def test_register_validation(make_client):
    c = make_client()
    assert c.post("/api/auth/register", json={"email": new_email(), "password": "short1"}).status_code == 422
    r = c.post("/api/auth/register", json={"email": new_email(), "password": "onlyletters"})
    assert r.status_code == 422 and "буквы, и цифры" in r.text
    assert c.post("/api/auth/register", json={"email": "not-an-email", "password": PASSWORD}).status_code == 422
    email = new_email()
    assert c.post("/api/auth/register", json={"email": email, "password": PASSWORD}).status_code == 201
    assert c.post("/api/auth/register", json={"email": email, "password": PASSWORD}).status_code == 409


def test_cannot_register_as_admin(make_client):
    c = make_client()
    r = c.post("/api/auth/register", json={"email": new_email(), "password": PASSWORD, "role": "admin"})
    assert r.status_code == 201 and r.json()["role"] == "user"


def test_wrong_password_and_unknown_user(make_client):
    c = make_client()
    email = new_email()
    create_user(email)
    assert c.post("/api/auth/login", json={"email": email, "password": "Wrong-pass-1"}).status_code == 401
    r = c.post("/api/auth/login", json={"email": new_email(), "password": PASSWORD})
    assert r.status_code == 401 and r.json()["detail"] == "Неверный email или пароль"


def test_lockout_after_repeated_failures(make_client):
    c = make_client()
    email = new_email()
    create_user(email)
    for _ in range(5):
        assert c.post("/api/auth/login", json={"email": email, "password": "Wrong-pass-1"}).status_code == 401
    r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})  # даже верный пароль не пускает
    assert r.status_code == 429 and "Повторите через" in r.json()["detail"]


def test_blocked_user_cannot_login(make_client):
    c = make_client()
    email = new_email()
    create_user(email, active=False)
    assert c.post("/api/auth/login", json={"email": email, "password": PASSWORD}).status_code == 403


def test_change_password_revokes_old_sessions(make_client):
    c = make_client("user")
    old_cookie = c.cookies.get("access_token")
    other = TestClient(app, base_url="http://testserver")
    other.cookies.set("access_token", old_cookie)
    assert other.get("/api/auth/me").status_code == 200

    assert c.post("/api/auth/change-password", json={"current_password": "bad", "new_password": "NewPassw0rd"}).status_code == 400
    assert c.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "weak"}).status_code == 422
    assert c.post("/api/auth/change-password", json={"current_password": PASSWORD, "new_password": "NewPassw0rd"}).status_code == 200

    assert other.get("/api/auth/me").status_code == 401  # старый токен отозван
    assert c.get("/api/auth/me").status_code == 200  # текущая сессия продолжает работать
    fresh = TestClient(app, base_url="http://testserver")
    assert fresh.post("/api/auth/login", json={"email": c.user_email, "password": "NewPassw0rd"}).status_code == 200


def test_update_profile(user_client):
    r = user_client.patch("/api/auth/me", json={"full_name": "Пётр Петров"})
    assert r.status_code == 200 and r.json()["full_name"] == "Пётр Петров"


def test_tampered_token_rejected(make_client):
    c = make_client()
    c.cookies.set("access_token", "not.a.jwt")
    assert c.get("/api/auth/me").status_code == 401


def test_csrf_origin_check(user_client):
    r = user_client.patch("/api/auth/me", json={"full_name": "X"}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    ok = user_client.patch("/api/auth/me", json={"full_name": "X"}, headers={"Origin": "http://testserver"})
    assert ok.status_code == 200


def test_first_admin_bootstrap(monkeypatch):
    from app import bootstrap
    from app.db import SessionLocal
    from app.models import User
    from sqlalchemy import delete, select

    email = f"boot-{uuid.uuid4().hex[:6]}@example.com"
    with SessionLocal() as db:
        saved = db.scalars(select(User).where(User.role == "admin")).all()
        assert bootstrap.settings is not None
        # при наличии администратора ничего не создаётся
        monkeypatch.setattr(bootstrap.settings, "first_admin_email", email)
        monkeypatch.setattr(bootstrap.settings, "first_admin_password", PASSWORD)
        if saved:
            bootstrap.ensure_first_admin(db)
            assert db.scalar(select(User).where(User.email == email)) is None
        else:
            bootstrap.ensure_first_admin(db)
            assert db.scalar(select(User).where(User.email == email)).role == "admin"


def test_rate_limit_on_login_and_registration(make_client):
    """Ограничение частоты включается на время теста (в остальных тестах оно выключено)."""
    from app.ratelimit import limiter

    limiter.enabled = True
    limiter.reset()
    try:
        c = make_client()
        codes = [c.post("/api/auth/login", json={"email": new_email(), "password": "Whatever-1"}).status_code
                 for _ in range(12)]
        assert codes[:10] == [401] * 10 and codes[10:] == [429, 429]
        r = c.post("/api/auth/login", json={"email": new_email(), "password": "Whatever-1"})
        assert r.status_code == 429 and "Слишком много запросов" in r.json()["detail"] and r.headers["retry-after"] == "60"
        limiter.reset()
        reg = [c.post("/api/auth/register", json={"email": new_email(), "password": PASSWORD}).status_code for _ in range(6)]
        assert reg == [201] * 5 + [429]
    finally:
        limiter.reset()
        limiter.enabled = False


def test_session_endpoint_does_not_error_for_guests(make_client, user_client):
    guest = make_client()
    r = guest.get("/api/auth/session")
    assert r.status_code == 200 and r.json() is None
    assert guest.get("/api/auth/me").status_code == 401  # строгая проверка остаётся строгой
    r = user_client.get("/api/auth/session")
    assert r.status_code == 200 and r.json()["email"] == user_client.user_email
