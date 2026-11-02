"""Запись результатов конвейера в БД (в одной транзакции: либо всё, либо ничего)."""
import math

import numpy as np
import pandas as pd
from sqlalchemy import Engine, delete, insert, select
from sqlalchemy.orm import Session

from app.models import (
    Airline, Airport, DataVersion, DunnPair, FlightAgg, ModelCoefficient, ModelMetric, StatTest,
)
from pipeline.transform import KEYS, SUM_COLS

BATCH = 20_000


def _clean(value):
    """NaN/inf не допускаются в JSON-ответах API."""
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if isinstance(value, np.generic):
        return _clean(value.item())
    return value


def _upsert_airlines(s: Session, values: list[str]) -> np.ndarray:
    existing = dict(s.execute(select(Airline.code, Airline.id)).all())
    s.add_all(Airline(code=v[:100], name=v[:150]) for v in values if v[:100] not in existing)
    s.flush()
    existing = dict(s.execute(select(Airline.code, Airline.id)).all())
    return np.array([existing[v[:100]] for v in values], dtype=np.int64)


def _upsert_airports(s: Session, values: list[str], meta: dict[str, tuple[str, str]]) -> np.ndarray:
    existing = dict(s.execute(select(Airport.code, Airport.id)).all())
    for v in values:
        if v[:10] not in existing:
            city, state = meta.get(v, ("", ""))
            s.add(Airport(code=v[:10], name="", city=city[:100], state=state[:50]))
            existing[v[:10]] = None
    s.flush()
    existing = dict(s.execute(select(Airport.code, Airport.id)).all())
    return np.array([existing[v[:10]] for v in values], dtype=np.int64)


def write_results(engine: Engine, *, agg: pd.DataFrame, airlines: list[str], origins: list[str],
                  origin_meta: dict, tests: list[dict], dunn: list[dict], models: dict, version: dict) -> None:
    with Session(engine) as s, s.begin():
        for model in (FlightAgg, DunnPair, StatTest, ModelCoefficient, ModelMetric):
            s.execute(delete(model))
        airline_ids = _upsert_airlines(s, airlines)
        airport_ids = _upsert_airports(s, origins, origin_meta)

        data = agg.rename(columns={"hour": "dep_hour"}).copy()
        data["airline_id"] = airline_ids[data["airline_id"].to_numpy()]
        data["origin_id"] = airport_ids[data["origin_id"].to_numpy()]
        columns = [c if c != "hour" else "dep_hour" for c in KEYS] + SUM_COLS + ["max_delay"]
        for start in range(0, len(data), BATCH):
            s.execute(insert(FlightAgg), data.iloc[start:start + BATCH][columns].to_dict("records"))

        for t in tests:
            s.add(StatTest(**_clean(t)))
        for d in dunn:
            s.add(DunnPair(airline_a_id=int(airline_ids[d["a"]]), airline_b_id=int(airline_ids[d["b"]]),
                           z=_clean(d["z"]), p_value=_clean(d["p_value"]), p_adj=_clean(d["p_adj"]),
                           significant=d["significant"]))
        for c in models["coefficients"]:
            s.add(ModelCoefficient(**_clean(c)))
        for m in models["metrics"]:
            s.add(ModelMetric(**_clean(m)))
        s.add(DataVersion(**_clean(version)))
