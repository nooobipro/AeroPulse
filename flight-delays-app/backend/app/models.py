"""ORM-модели. Онлайн-приложение читает агрегаты (flight_agg) и результаты анализа,
которые записывает офлайн-конвейер (папка pipeline/)."""
from datetime import datetime

from sqlalchemy import (
    JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, SmallInteger,
    String, Text, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.utils import utcnow


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[str] = mapped_column(String(16), default="user", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email: Mapped[str] = mapped_column(String(254), default="")
    action: Mapped[str] = mapped_column(String(48), index=True)
    details: Mapped[str] = mapped_column(Text, default="")
    ip: Mapped[str] = mapped_column(String(64), default="")


class SavedFilter(Base):
    __tablename__ = "saved_filters"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_saved_filter_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(60))
    params: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Airline(Base):
    __tablename__ = "airlines"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)  # значение из исходных данных
    name: Mapped[str] = mapped_column(String(150))  # отображаемое название (редактирует администратор)


class Airport(Base):
    __tablename__ = "airports"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(10), unique=True)  # код IATA
    name: Mapped[str] = mapped_column(String(150), default="")
    city: Mapped[str] = mapped_column(String(100), default="")
    state: Mapped[str] = mapped_column(String(50), default="")


class FlightAgg(Base):
    """Агрегаты по выполненным рейсам: авиакомпания × аэропорт вылета × месяц × день недели × час.

    flights — выполненные рейсы (без отменённых и перенаправленных), по ним считаются задержки.
    Задержка прибытия, минуты; досрочное прибытие приравнено к нулю."""

    __tablename__ = "flight_agg"
    __table_args__ = (
        Index("ix_flight_agg_origin", "origin_id"),
        Index("ix_flight_agg_ym", "ym"),
    )

    airline_id: Mapped[int] = mapped_column(ForeignKey("airlines.id"), primary_key=True, autoincrement=False)
    origin_id: Mapped[int] = mapped_column(ForeignKey("airports.id"), primary_key=True, autoincrement=False)
    ym: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)  # ГГГГММ
    dow: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)  # 1=Пн … 7=Вс
    dep_hour: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=False)  # 0..23

    flights: Mapped[int] = mapped_column(Integer, default=0)
    cancelled: Mapped[int] = mapped_column(Integer, default=0)
    diverted: Mapped[int] = mapped_column(Integer, default=0)
    delayed0: Mapped[int] = mapped_column(Integer, default=0)  # задержка > 0 мин
    delayed15: Mapped[int] = mapped_column(Integer, default=0)  # задержка >= 15 мин
    delay_sum: Mapped[int] = mapped_column(BigInteger, default=0)  # сумма минут по всем рейсам
    delay_sum15: Mapped[int] = mapped_column(BigInteger, default=0)  # сумма минут по рейсам с задержкой >= 15
    max_delay: Mapped[int] = mapped_column(Integer, default=0)
    c1_15: Mapped[int] = mapped_column(Integer, default=0)
    c16_30: Mapped[int] = mapped_column(Integer, default=0)
    c31_60: Mapped[int] = mapped_column(Integer, default=0)
    c61_120: Mapped[int] = mapped_column(Integer, default=0)
    c120p: Mapped[int] = mapped_column(Integer, default=0)


class DataVersion(Base):
    __tablename__ = "data_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    period_start: Mapped[str] = mapped_column(String(7))  # ГГГГ-ММ
    period_end: Mapped[str] = mapped_column(String(7))
    rows_total: Mapped[int] = mapped_column(BigInteger)
    rows_used: Mapped[int] = mapped_column(BigInteger)
    airlines: Mapped[int] = mapped_column(Integer)
    airports: Mapped[int] = mapped_column(Integer)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(500), default="")
    notes: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class StatTest(Base):
    """Результаты Спирмена, хи-квадрат, Краскела–Уоллиса (считает pipeline)."""

    __tablename__ = "stat_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    family: Mapped[str] = mapped_column(String(16), index=True)  # spearman | chi2 | kruskal
    title: Mapped[str] = mapped_column(String(200))
    statistic: Mapped[float | None] = mapped_column(Float, nullable=True)
    dof: Mapped[int | None] = mapped_column(Integer, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    effect_name: Mapped[str] = mapped_column(String(40), default="")
    effect_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    effect_ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    effect_ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    effect_label: Mapped[str] = mapped_column(String(40), default="")
    n: Mapped[int] = mapped_column(BigInteger, default=0)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class DunnPair(Base):
    __tablename__ = "dunn_pairs"

    id: Mapped[int] = mapped_column(primary_key=True)
    airline_a_id: Mapped[int] = mapped_column(ForeignKey("airlines.id"))
    airline_b_id: Mapped[int] = mapped_column(ForeignKey("airlines.id"))
    z: Mapped[float] = mapped_column(Float)  # > 0: у A ранги задержек выше, чем у B
    p_value: Mapped[float] = mapped_column(Float)
    p_adj: Mapped[float] = mapped_column(Float)
    significant: Mapped[bool] = mapped_column(Boolean)


class ModelCoefficient(Base):
    __tablename__ = "model_coefficients"

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(40), index=True)
    grp: Mapped[str] = mapped_column(String(20))  # time | airline | airport | calendar | duration | robustness
    term: Mapped[str] = mapped_column(String(120))
    label: Mapped[str] = mapped_column(String(200))
    estimate: Mapped[float] = mapped_column(Float)
    std_error: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    p_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    odds_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    or_ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    or_ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)


class ModelMetric(Base):
    __tablename__ = "model_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    model: Mapped[str] = mapped_column(String(40), index=True)
    key: Mapped[str] = mapped_column(String(40))
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
