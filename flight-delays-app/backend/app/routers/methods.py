"""Результаты анализа (корреляции, критерии, регрессия). Только для аналитиков и администраторов.
Значения считает офлайн-конвейер; здесь они только читаются из БД."""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import stats_service as svc
from app.cache import cache
from app.db import get_db
from app.deps import require_role
from app.models import DunnPair, ModelCoefficient, ModelMetric, StatTest
from app.schemas import CoefOut, DunnRow, MethodsSummary, ModelBlock, RegressionOut, StatTestOut

router = APIRouter(prefix="/methods", tags=["Методы анализа"], dependencies=[Depends(require_role("analyst"))])

MODEL_INFO = {
    "linear_hour": ("Линейная регрессия: час вылета как число", "Задержка прибытия, минут", "linear"),
    "linear_period": ("Линейная регрессия: период суток", "Задержка прибытия, минут", "linear"),
    "logit_period": ("Логистическая регрессия: период суток", "Рейс задержан (> 0 мин)", "logit"),
    "logit_period_15": ("Логистическая регрессия: период суток, порог 15 минут", "Рейс задержан (≥ 15 мин)", "logit"),
    "logit_hour": ("Логистическая регрессия: час вылета категориями", "Рейс задержан (> 0 мин)", "logit"),
}


def _sample(db: Session) -> dict | None:
    version = svc.data_version(db)
    return (version.notes or {}).get("sample") if version else None


@router.get("/summary", response_model=MethodsSummary)
def summary(db: Session = Depends(get_db)):
    def compute():
        rows = db.scalars(select(StatTest).order_by(StatTest.sort_order, StatTest.id)).all()
        by_family = {"spearman": [], "chi2": [], "kruskal": []}
        for r in rows:
            if r.family in by_family:
                by_family[r.family].append(StatTestOut.model_validate(r))
        return MethodsSummary(**by_family, sample=_sample(db))
    return cache.get_or_set(("methods_summary",), compute)


@router.get("/dunn", response_model=list[DunnRow])
def dunn(db: Session = Depends(get_db)):
    def compute():
        names = svc.airline_map(db)
        out = []
        for p in db.scalars(select(DunnPair).order_by(DunnPair.p_adj, DunnPair.id)):
            out.append(DunnRow(
                airline_a_id=p.airline_a_id, airline_a=names.get(p.airline_a_id, {}).get("name", "?"),
                airline_b_id=p.airline_b_id, airline_b=names.get(p.airline_b_id, {}).get("name", "?"),
                z=p.z, p_value=p.p_value, p_adj=p.p_adj, significant=p.significant))
        return out
    return cache.get_or_set(("methods_dunn",), compute)


def _coef(c: ModelCoefficient, names_by_code: dict[str, str]) -> CoefOut:
    out = CoefOut.model_validate(c)
    if c.grp == "airline" and ":" in c.term:  # в БД хранится код компании; название берём из справочника
        out.label = names_by_code.get(c.term.split(":", 1)[1], out.label)
    return out


@router.get("/regression", response_model=RegressionOut)
def regression(db: Session = Depends(get_db)):
    def compute():
        names_by_code = {a["code"]: a["name"] for a in svc.airline_map(db).values()}
        coefs = db.scalars(select(ModelCoefficient).order_by(ModelCoefficient.sort_order, ModelCoefficient.id)).all()
        metrics = db.scalars(select(ModelMetric)).all()
        models = []
        for code, (title, target, kind) in MODEL_INFO.items():
            mc = [_coef(c, names_by_code) for c in coefs if c.model == code]
            mm = {m.key: m.value for m in metrics if m.model == code and m.details is None}
            if mc or mm:
                models.append(ModelBlock(code=code, title=title, target=target, kind=kind,
                                         coefficients=mc, metrics=mm))
        hour_prob = next((m.details for m in metrics if m.model == "logit_hour" and m.key == "hour_probability"), None)
        calib = next((m.details for m in metrics if m.model == "logit_period" and m.key == "calibration"), None)
        return RegressionOut(
            models=models,
            hour_stability=[_coef(c, names_by_code) for c in coefs if c.model == "linear_hour_stability"],
            hour_probability=hour_prob,
            calibration=(calib or {}).get("bins") if calib else None,
            sample=_sample(db),
        )
    return cache.get_or_set(("methods_regression",), compute)
