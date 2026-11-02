"""Очистка и агрегация исходных рейсов (потоково, порциями)."""
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.domain import LATE_THRESHOLD_MIN

KEYS = ["airline_id", "origin_id", "ym", "dow", "hour"]
SUM_COLS = ["flights", "cancelled", "diverted", "delayed0", "delayed15", "delay_sum", "delay_sum15",
            "c1_15", "c16_30", "c31_60", "c61_120", "c120p"]
AGG_SPEC = {**{c: "sum" for c in SUM_COLS}, "max_delay": "max"}
_BAD_TEXT = ["", "NAN", "NONE", "NULL", "<NA>"]


class Encoder:
    """Присваивает строкам целочисленные коды (экономит память при агрегации)."""

    def __init__(self) -> None:
        self.to_id: dict[str, int] = {}
        self.values: list[str] = []

    def encode(self, s: pd.Series) -> np.ndarray:
        codes, uniques = pd.factorize(s)
        if len(uniques) == 0:
            return np.full(len(s), -1, dtype=np.int32)
        mapping = np.empty(len(uniques), dtype=np.int32)
        for i, u in enumerate(uniques):
            u = str(u)
            gid = self.to_id.get(u)
            if gid is None:
                gid = len(self.values)
                self.to_id[u] = gid
                self.values.append(u)
            mapping[i] = gid
        return np.where(codes >= 0, mapping[np.clip(codes, 0, None)], -1).astype(np.int32)


@dataclass
class Counters:
    rows_total: int = 0
    rows_invalid: int = 0  # нет даты/времени/авиакомпании/аэропорта или числовой код аэропорта
    rows_missing_delay: int = 0  # выполнен, но задержка прибытия не указана
    cancelled: int = 0
    diverted: int = 0
    completed: int = 0

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def _num(s: pd.Series) -> np.ndarray:
    return pd.to_numeric(s, errors="coerce").to_numpy(dtype="float64", na_value=np.nan)


def _text(s: pd.Series) -> pd.Series:
    return s.astype("string").str.strip()


def _to_bool(s: pd.Series) -> np.ndarray:
    if s.dtype == bool:
        return s.to_numpy()
    return _text(s).str.lower().isin(["1", "1.0", "true", "t", "yes", "y"]).to_numpy(dtype=bool)


def prepare_chunk(df: pd.DataFrame, cols: dict[str, str], enc_airline: Encoder, enc_origin: Encoder,
                  origin_meta: dict[str, tuple[str, str]], counters: Counters) -> pd.DataFrame:
    """Приводит порцию исходных строк к единому виду; невалидные строки отбрасываются и учитываются."""
    n_raw = len(df)
    counters.rows_total += n_raw

    airline = _text(df[cols["airline"]])
    origin = _text(df[cols["origin"]]).str.upper()
    if "date" in cols:
        dt = pd.to_datetime(df[cols["date"]], errors="coerce")
    else:
        dt = pd.to_datetime(pd.DataFrame({"year": _num(df[cols["year"]]), "month": _num(df[cols["month"]]),
                                          "day": _num(df[cols["day"]])}), errors="coerce")
    ym = (dt.dt.year * 100 + dt.dt.month).to_numpy(dtype="float64", na_value=np.nan)
    dow = (dt.dt.dayofweek + 1).to_numpy(dtype="float64", na_value=np.nan)
    sched = _num(df[cols["sched_dep"]])
    hour = np.floor(sched / 100.0) % 24

    bad_airline = (airline.isna() | airline.str.upper().isin(_BAD_TEXT)).to_numpy(dtype=bool)
    bad_origin = (origin.isna() | origin.isin(_BAD_TEXT)).to_numpy(dtype=bool)
    numeric_origin = origin.str.fullmatch(r"\d+").fillna(False).to_numpy(dtype=bool)  # числовые коды вместо IATA
    valid = (~bad_airline & ~bad_origin & ~numeric_origin & ~np.isnan(ym) & ~np.isnan(dow)
             & ~np.isnan(sched) & (sched >= 0) & (sched <= 2400))
    counters.rows_invalid += int(n_raw - valid.sum())
    if not valid.any():
        return pd.DataFrame(columns=[*KEYS, "cancelled", "diverted", "delay", "duration"])

    cancelled = _to_bool(df[cols["cancelled"]])[valid]
    diverted = _to_bool(df[cols["diverted"]])[valid] & ~cancelled
    delay = _num(df[cols["arr_delay"]])[valid]
    delay = np.where(np.isnan(delay), np.nan, np.maximum(delay, 0.0))  # досрочное прибытие = 0 минут
    duration = _num(df[cols["duration"]])[valid] if "duration" in cols else np.full(valid.sum(), np.nan)

    completed = ~cancelled & ~diverted & ~np.isnan(delay)
    counters.cancelled += int(cancelled.sum())
    counters.diverted += int(diverted.sum())
    counters.completed += int(completed.sum())
    counters.rows_missing_delay += int((~cancelled & ~diverted & np.isnan(delay)).sum())

    origin_v = origin[valid].reset_index(drop=True)
    if "origin_city" in cols or "origin_state" in cols:
        meta = pd.DataFrame({
            "o": origin_v,
            "city": _text(df[cols["origin_city"]])[valid].reset_index(drop=True) if "origin_city" in cols else "",
            "state": _text(df[cols["origin_state"]])[valid].reset_index(drop=True) if "origin_state" in cols else "",
        }).drop_duplicates("o")
        for o, city, state in meta.itertuples(index=False):
            origin_meta.setdefault(str(o), (str(city) if pd.notna(city) else "", str(state) if pd.notna(state) else ""))

    return pd.DataFrame({
        "airline_id": enc_airline.encode(airline[valid].reset_index(drop=True)),
        "origin_id": enc_origin.encode(origin_v),
        "ym": ym[valid].astype(np.int32),
        "dow": dow[valid].astype(np.int8),
        "hour": hour[valid].astype(np.int8),
        "cancelled": cancelled,
        "diverted": diverted,
        "delay": delay,
        "duration": duration,
    })


def aggregate_chunk(d: pd.DataFrame) -> pd.DataFrame:
    comp = ~d["cancelled"].to_numpy() & ~d["diverted"].to_numpy() & ~np.isnan(d["delay"].to_numpy())
    dl = np.where(comp, d["delay"].to_numpy(), 0.0)
    x = pd.DataFrame({k: d[k].to_numpy() for k in KEYS})
    one = lambda mask: mask.astype(np.int64)
    x["flights"] = one(comp)
    x["cancelled"] = one(d["cancelled"].to_numpy())
    x["diverted"] = one(d["diverted"].to_numpy())
    x["delayed0"] = one(comp & (dl > 0))
    x["delayed15"] = one(comp & (dl >= LATE_THRESHOLD_MIN))
    x["delay_sum"] = dl
    x["delay_sum15"] = np.where(dl >= LATE_THRESHOLD_MIN, dl, 0.0)
    x["max_delay"] = dl
    x["c1_15"] = one(comp & (dl > 0) & (dl <= 15))
    x["c16_30"] = one(comp & (dl > 15) & (dl <= 30))
    x["c31_60"] = one(comp & (dl > 30) & (dl <= 60))
    x["c61_120"] = one(comp & (dl > 60) & (dl <= 120))
    x["c120p"] = one(comp & (dl > 120))
    return x.groupby(KEYS, sort=False, as_index=False).agg(AGG_SPEC)


def merge_aggregates(frames: list[pd.DataFrame]) -> pd.DataFrame:
    big = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    return big.groupby(KEYS, sort=False, as_index=False).agg(AGG_SPEC)


def finalize_aggregate(agg: pd.DataFrame) -> pd.DataFrame:
    for c in ("delay_sum", "delay_sum15"):
        agg[c] = np.rint(agg[c]).astype(np.int64)
    agg["max_delay"] = np.rint(agg["max_delay"]).astype(np.int64)
    return agg


def sample_chunk(d: pd.DataFrame, frac: float, rng: np.random.Generator) -> pd.DataFrame:
    comp = ~d["cancelled"].to_numpy() & ~d["diverted"].to_numpy() & ~np.isnan(d["delay"].to_numpy())
    s = d.loc[comp, ["airline_id", "origin_id", "ym", "dow", "hour", "delay", "duration"]]
    if frac < 1.0:
        s = s[rng.random(len(s)) < frac]
    return s
