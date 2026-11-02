"""Тесты работают на временной SQLite-БД, наполненной тем же конвейером, что и в проде."""
import os
import tempfile
import uuid

_TMP = tempfile.mkdtemp(prefix="flightdelays-tests-")
os.environ.update({
    # По умолчанию SQLite; для проверки на PostgreSQL задайте TEST_DATABASE_URL (таблицы пересоздаются!)
    "DATABASE_URL": os.environ.get("TEST_DATABASE_URL") or f"sqlite:///{_TMP}/test.db",
    "AUTO_CREATE_TABLES": "true",
    "SECRET_KEY": "test-secret-key-that-is-long-enough-0123456789",
    "RATE_LIMIT_ENABLED": "false",
    "ENVIRONMENT": "test",
})

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import select  # noqa: E402

from app.cache import cache  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import User  # noqa: E402
from app.security import hash_password  # noqa: E402

PASSWORD = "Passw0rd-test"


@pytest.fixture(scope="session")
def raw_flights() -> pd.DataFrame:
    from pipeline import synthetic
    return synthetic.demo_chunk(60_000, np.random.default_rng(123))


@pytest.fixture(scope="session", autouse=True)
def seeded(raw_flights):
    from pipeline.run import iter_csv, run_pipeline
    if engine.dialect.name != "sqlite":
        Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    path = os.path.join(_TMP, "flights.csv")
    raw_flights.to_csv(path, index=False)
    run_pipeline(iter_csv([path], 25_000, {}), engine, sample_frac=1.0, seed=1, source="test", is_demo=True)
    cache.clear()
    return True


def create_user(email: str, role: str = "user", password: str = PASSWORD, active: bool = True) -> int:
    with SessionLocal() as db:
        user = User(email=email, password_hash=hash_password(password), role=role, is_active=active, full_name="Тест")
        db.add(user)
        db.commit()
        return user.id


@pytest.fixture
def make_client():
    def factory(role: str | None = None) -> TestClient:
        client = TestClient(app, base_url="http://testserver")
        if role:
            email = f"{role}-{uuid.uuid4().hex[:8]}@example.com"
            client.user_id = create_user(email, role)
            client.user_email = email
            r = client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
            assert r.status_code == 200, r.text
        return client
    return factory


@pytest.fixture
def user_client(make_client):
    return make_client("user")


@pytest.fixture
def analyst_client(make_client):
    return make_client("analyst")


@pytest.fixture
def admin_client(make_client):
    return make_client("admin")


@pytest.fixture(scope="session")
def truth(raw_flights) -> pd.DataFrame:
    """Независимый расчёт по сырым данным (без кода конвейера) — эталон для проверки API."""
    d = raw_flights[~raw_flights.Cancelled & ~raw_flights.Diverted & raw_flights.ArrDelayMinutes.notna()].copy()
    d["hour"] = (d.CRSDepTime // 100).astype(int)
    d["ym"] = d.FlightDate.str[:4].astype(int) * 100 + d.FlightDate.str[5:7].astype(int)
    d["dow"] = pd.to_datetime(d.FlightDate).dt.dayofweek + 1
    return d


@pytest.fixture(scope="session")
def ids(seeded):
    """Соответствие названий авиакомпаний и кодов аэропортов идентификаторам БД."""
    from app.models import Airline, Airport
    with SessionLocal() as db:
        return {
            "airline": {a.name: a.id for a in db.scalars(select(Airline))},
            "airport": {a.code: a.id for a in db.scalars(select(Airport))},
        }
