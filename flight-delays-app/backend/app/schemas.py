"""Pydantic-схемы запросов и ответов API."""
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.utils import validate_password

PERIOD_PATTERN = r"^\d{4}-(0[1-9]|1[0-2])$"


# ───────── Аутентификация ─────────
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str = Field(default="", max_length=100)

    @field_validator("password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password(v)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None


class ProfileIn(BaseModel):
    full_name: str = Field(max_length=100)


class PasswordChangeIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _check_password(cls, v: str) -> str:
        return validate_password(v)


# ───────── Справочники и версия данных ─────────
class AirlineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str


class AirportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    city: str
    state: str


class DataVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    loaded_at: datetime
    period_start: str
    period_end: str
    rows_total: int
    rows_used: int
    airlines: int
    airports: int
    is_demo: bool
    source: str
    notes: dict[str, Any] | None = None


class FilterOptions(BaseModel):
    airlines: list[AirlineOut]
    airports: list[AirportOut]
    periods: list[str]
    data: DataVersionOut | None


# ───────── Статистика ─────────
class Rate(BaseModel):
    flights: int
    delayed: int
    share: float | None
    ci_low: float | None
    ci_high: float | None
    avg_delay: float | None


class HourRef(BaseModel):
    hour: int
    share: float
    flights: int


class KPIOut(Rate):
    cancelled: int
    diverted: int
    max_delay: int
    worst_hour: HourRef | None
    best_hour: HourRef | None


class AirlineRow(Rate):
    airline_id: int
    code: str
    name: str
    max_delay: int


class HourRow(Rate):
    hour: int


class PeriodRow(Rate):
    code: str
    label: str
    hour_from: int
    hour_to: int


class HeatCell(BaseModel):
    dow: int
    hour: int
    flights: int
    delayed: int
    share: float | None
    reliable: bool


class AirportRow(Rate):
    airport_id: int
    code: str
    name: str
    city: str
    state: str


class CategoryRow(BaseModel):
    key: str
    label: str
    flights: int
    share: float | None


class MonthRow(Rate):
    period: str


class CompareSide(BaseModel):
    airline_id: int
    name: str
    kpi: KPIOut
    hourly: list[HourRow]
    categories: list[CategoryRow]


class CompareDiff(BaseModel):
    diff: float
    ci_low: float
    ci_high: float
    p_value: float
    risk_ratio: float | None


class CompareOut(BaseModel):
    a: CompareSide
    b: CompareSide
    diff: CompareDiff | None


class ShareRef(BaseModel):
    name: str
    share: float
    flights: int


class PeriodShare(BaseModel):
    code: str
    label: str
    hour_from: int
    hour_to: int
    share: float | None
    flights: int


class HourShare(BaseModel):
    hour: int
    share: float
    flights: int


class Highlights(BaseModel):
    has_data: bool
    is_demo: bool
    flights: int
    airlines: int
    airports: int
    period_start: str | None
    period_end: str | None
    share: float | None
    share15: float | None
    periods: list[PeriodShare]
    hourly: list[HourShare]
    best_airline: ShareRef | None
    worst_airline: ShareRef | None


# ───────── Методы анализа ─────────
class StatTestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    family: str
    title: str
    statistic: float | None
    dof: int | None
    p_value: float | None
    effect_name: str
    effect_value: float | None
    effect_ci_low: float | None
    effect_ci_high: float | None
    effect_label: str
    n: int
    details: dict[str, Any] | None


class MethodsSummary(BaseModel):
    spearman: list[StatTestOut]
    chi2: list[StatTestOut]
    kruskal: list[StatTestOut]
    sample: dict[str, Any] | None


class DunnRow(BaseModel):
    airline_a_id: int
    airline_a: str
    airline_b_id: int
    airline_b: str
    z: float
    p_value: float
    p_adj: float
    significant: bool


class CoefOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    model: str
    grp: str
    term: str
    label: str
    estimate: float
    std_error: float | None
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    odds_ratio: float | None
    or_ci_low: float | None
    or_ci_high: float | None


class ModelBlock(BaseModel):
    code: str
    title: str
    target: str
    kind: Literal["linear", "logit"]
    coefficients: list[CoefOut]
    metrics: dict[str, float | None]


class RegressionOut(BaseModel):
    models: list[ModelBlock]
    hour_stability: list[CoefOut]
    hour_probability: dict[str, Any] | None
    calibration: list[dict[str, Any]] | None
    sample: dict[str, Any] | None


# ───────── Сохранённые фильтры ─────────
class FilterParams(BaseModel):
    airline_id: list[int] = Field(default_factory=list, max_length=50)
    airport_id: list[int] = Field(default_factory=list, max_length=100)
    period_from: str | None = Field(default=None, pattern=PERIOD_PATTERN)
    period_to: str | None = Field(default=None, pattern=PERIOD_PATTERN)
    hour_from: int = Field(default=0, ge=0, le=23)
    hour_to: int = Field(default=23, ge=0, le=23)
    threshold: Literal[0, 15] = 0
    avg_mode: Literal["all", "delayed"] = "all"


class SavedFilterIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    params: FilterParams

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Укажите название набора фильтров")
        return v


class SavedFilterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    params: dict[str, Any]
    created_at: datetime


# ───────── Администрирование ─────────
class UserPatch(BaseModel):
    role: Literal["user", "analyst", "admin"] | None = None
    is_active: bool | None = None
    full_name: str | None = Field(default=None, max_length=100)


class UsersPage(BaseModel):
    items: list[UserOut]
    total: int
    page: int
    page_size: int


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime
    user_id: int | None
    user_email: str
    action: str
    details: str
    ip: str


class AuditPage(BaseModel):
    items: list[AuditOut]
    total: int
    page: int
    page_size: int


class AirlinePatch(BaseModel):
    name: str = Field(min_length=1, max_length=150)


class AirportPatch(BaseModel):
    name: str = Field(max_length=150)
    city: str = Field(max_length=100)
    state: str = Field(max_length=50)


class AirportsPage(BaseModel):
    items: list[AirportOut]
    total: int
    page: int
    page_size: int


class DataInfo(BaseModel):
    current: DataVersionOut | None
    history: list[DataVersionOut]
    counts: dict[str, int]
