"""Статистика по агрегатам flight_agg. Все функции принимают одинаковый набор фильтров,
результаты кэшируются (данные статичны; кэш сбрасывается при правке справочников)."""
from dataclasses import dataclass, replace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.cache import cache
from app.domain import CATEGORIES, MIN_FLIGHTS_FOR_RANKING, PERIODS
from app.models import Airline, Airport, DataVersion, FlightAgg as A
from app.utils import two_proportion_test, wilson_interval

MIN_RELIABLE_CELL = 30  # меньше рейсов в ячейке тепловой карты — оценка считается ненадёжной


@dataclass(frozen=True)
class Filters:
    airline_ids: tuple[int, ...] = ()
    airport_ids: tuple[int, ...] = ()
    period_from: int | None = None  # ГГГГММ
    period_to: int | None = None
    hour_from: int = 0
    hour_to: int = 23
    threshold: int = 0  # 0: задержка > 0 мин; 15: задержка >= 15 мин
    avg_mode: str = "all"  # all: среднее по всем рейсам; delayed: среднее среди задержанных

    def key(self) -> tuple:
        return (self.airline_ids, self.airport_ids, self.period_from, self.period_to,
                self.hour_from, self.hour_to, self.threshold, self.avg_mode)

    def describe(self, airlines: dict[int, dict], airports: dict[int, dict]) -> list[tuple[str, str]]:
        """Человекочитаемое описание фильтров для отчётов."""
        def names(ids, src, field):
            return ", ".join(src[i][field] for i in ids if i in src) or "все"

        period = "весь период"
        if self.period_from or self.period_to:
            fmt = lambda v: f"{v // 100}-{v % 100:02d}" if v else "…"
            period = f"{fmt(self.period_from)} — {fmt(self.period_to)}"
        return [
            ("Авиакомпании", names(self.airline_ids, airlines, "name")),
            ("Аэропорты вылета", names(self.airport_ids, airports, "code")),
            ("Период", period),
            ("Время вылета", f"{self.hour_from:02d}:00 — {self.hour_to:02d}:59"),
            ("Порог задержки", "более 0 минут" if self.threshold == 0 else "15 минут и более"),
            ("Средняя задержка", "по всем рейсам" if self.avg_mode == "all" else "только по задержанным рейсам"),
        ]


# ───────── Справочники (кэшируются) ─────────
def airline_map(db: Session) -> dict[int, dict]:
    def compute():
        return {r.id: {"id": r.id, "code": r.code, "name": r.name}
                for r in db.execute(select(Airline)).scalars()}
    return cache.get_or_set(("airlines",), compute)


def airport_map(db: Session) -> dict[int, dict]:
    def compute():
        return {r.id: {"id": r.id, "code": r.code, "name": r.name or r.city or r.code,
                       "city": r.city, "state": r.state}
                for r in db.execute(select(Airport)).scalars()}
    return cache.get_or_set(("airports",), compute)


def data_version(db: Session) -> DataVersion | None:
    return db.scalar(select(DataVersion).order_by(DataVersion.id.desc()).limit(1))


def filter_options(db: Session) -> dict:
    def compute():
        yms = db.scalars(select(A.ym).distinct().order_by(A.ym)).all()
        airlines = sorted(airline_map(db).values(), key=lambda a: a["name"].lower())
        airports = sorted(airport_map(db).values(), key=lambda a: a["code"])
        return {
            "airlines": airlines,
            "airports": airports,
            "periods": [f"{y // 100}-{y % 100:02d}" for y in yms],
            "data": data_version(db),
        }
    return cache.get_or_set(("filter_options",), compute)


# ───────── Построение запросов ─────────
def _where(f: Filters) -> list:
    conds = []
    if f.airline_ids:
        conds.append(A.airline_id.in_(f.airline_ids))
    if f.airport_ids:
        conds.append(A.origin_id.in_(f.airport_ids))
    if f.period_from is not None:
        conds.append(A.ym >= f.period_from)
    if f.period_to is not None:
        conds.append(A.ym <= f.period_to)
    if f.hour_from > 0:
        conds.append(A.dep_hour >= f.hour_from)
    if f.hour_to < 23:
        conds.append(A.dep_hour <= f.hour_to)
    return conds


def _measures(f: Filters) -> list:
    delayed = A.delayed0 if f.threshold == 0 else A.delayed15
    dsum_thr = A.delay_sum if f.threshold == 0 else A.delay_sum15
    return [
        func.sum(A.flights).label("flights"),
        func.sum(delayed).label("delayed"),
        func.sum(A.delay_sum).label("dsum_all"),
        func.sum(dsum_thr).label("dsum_thr"),
        func.max(A.max_delay).label("max_delay"),
    ]


def _query(db: Session, f: Filters, group_cols: tuple = (), extra: tuple = ()):
    stmt = select(*group_cols, *_measures(f), *extra)
    conds = _where(f)
    if conds:
        stmt = stmt.where(*conds)
    if group_cols:
        stmt = stmt.group_by(*group_cols)
    return db.execute(stmt).all()


def _rate(flights, delayed, dsum_all, dsum_thr, mode: str) -> dict:
    flights, delayed = int(flights or 0), int(delayed or 0)
    if flights == 0:
        return {"flights": 0, "delayed": 0, "share": None, "ci_low": None, "ci_high": None, "avg_delay": None}
    lo, hi = wilson_interval(delayed, flights)
    if mode == "all":
        avg = float(dsum_all or 0) / flights
    else:
        avg = float(dsum_thr or 0) / delayed if delayed else None
    return {"flights": flights, "delayed": delayed, "share": delayed / flights,
            "ci_low": lo, "ci_high": hi, "avg_delay": avg}


def _row_rate(r, f: Filters) -> dict:
    return _rate(r.flights, r.delayed, r.dsum_all, r.dsum_thr, f.avg_mode)


# ───────── Показатели ─────────
def _hour_raw(db: Session, f: Filters) -> list[dict]:
    def compute():
        rows = _query(db, f, (A.dep_hour,))
        return sorted(
            ({"hour": int(r.dep_hour), "flights": int(r.flights or 0), "delayed": int(r.delayed or 0),
              "dsum_all": int(r.dsum_all or 0), "dsum_thr": int(r.dsum_thr or 0),
              "max_delay": int(r.max_delay or 0)} for r in rows),
            key=lambda x: x["hour"])
    return cache.get_or_set(("hour_raw", f.key()), compute)


def by_hour(db: Session, f: Filters) -> list[dict]:
    return [{"hour": h["hour"], **_rate(h["flights"], h["delayed"], h["dsum_all"], h["dsum_thr"], f.avg_mode)}
            for h in _hour_raw(db, f) if h["flights"] > 0]


def by_period(db: Session, f: Filters) -> list[dict]:
    raw = _hour_raw(db, f)
    out = []
    for p in PERIODS:
        part = [h for h in raw if p["hour_from"] <= h["hour"] <= p["hour_to"]]
        out.append({
            "code": p["code"], "label": p["label"], "hour_from": p["hour_from"], "hour_to": p["hour_to"],
            **_rate(sum(h["flights"] for h in part), sum(h["delayed"] for h in part),
                    sum(h["dsum_all"] for h in part), sum(h["dsum_thr"] for h in part), f.avg_mode),
        })
    return out


def kpi(db: Session, f: Filters) -> dict:
    def compute():
        r = _query(db, f, extra=(func.sum(A.cancelled).label("cancelled"),
                                 func.sum(A.diverted).label("diverted")))[0]
        out = _row_rate(r, f)
        out.update(cancelled=int(r.cancelled or 0), diverted=int(r.diverted or 0), max_delay=int(r.max_delay or 0))
        hours = by_hour(db, f)
        pool = [h for h in hours if h["flights"] >= MIN_FLIGHTS_FOR_RANKING] or hours
        ref = lambda h: {"hour": h["hour"], "share": h["share"], "flights": h["flights"]}
        out["worst_hour"] = ref(max(pool, key=lambda h: h["share"])) if pool else None
        out["best_hour"] = ref(min(pool, key=lambda h: h["share"])) if pool else None
        return out
    return cache.get_or_set(("kpi", f.key()), compute)


def by_airline(db: Session, f: Filters) -> list[dict]:
    def compute():
        names = airline_map(db)
        out = []
        for r in _query(db, f, (A.airline_id,)):
            rate = _row_rate(r, f)
            if rate["flights"] == 0:
                continue
            meta = names.get(int(r.airline_id), {"code": "?", "name": "?"})
            out.append({"airline_id": int(r.airline_id), "code": meta["code"], "name": meta["name"],
                        "max_delay": int(r.max_delay or 0), **rate})
        out.sort(key=lambda x: (-x["share"], x["name"]))
        return out
    return cache.get_or_set(("airlines_rows", f.key()), compute)


def by_airport(db: Session, f: Filters, sort: str = "share", order: str = "desc",
               min_flights: int = 200, limit: int = 20) -> list[dict]:
    def compute():
        names = airport_map(db)
        out = []
        for r in _query(db, f, (A.origin_id,)):
            rate = _row_rate(r, f)
            if rate["flights"] == 0:
                continue
            meta = names.get(int(r.origin_id), {"code": "?", "name": "?", "city": "", "state": ""})
            out.append({"airport_id": int(r.origin_id), **{k: meta[k] for k in ("code", "name", "city", "state")},
                        **rate})
        return out
    rows = cache.get_or_set(("airports_rows", f.key()), compute)
    rows = [r for r in rows if r["flights"] >= min_flights]
    rows = sorted(rows, key=lambda r: (r[sort] is None, r[sort], r["code"]), reverse=(order == "desc"))
    return rows[:limit]


def categories(db: Session, f: Filters) -> list[dict]:
    def compute():
        r = _query(db, f, extra=(
            func.sum(A.delayed0).label("d0"), func.sum(A.c1_15).label("c1"), func.sum(A.c16_30).label("c2"),
            func.sum(A.c31_60).label("c3"), func.sum(A.c61_120).label("c4"), func.sum(A.c120p).label("c5")))[0]
        flights = int(r.flights or 0)
        counts = [flights - int(r.d0 or 0)] + [int(getattr(r, f"c{i}") or 0) for i in range(1, 6)]
        return [{"key": key, "label": label, "flights": c, "share": (c / flights if flights else None)}
                for (key, label), c in zip(CATEGORIES, counts)]
    return cache.get_or_set(("categories", f.key()), compute)


def heatmap(db: Session, f: Filters) -> list[dict]:
    def compute():
        out = []
        for r in _query(db, f, (A.dow, A.dep_hour)):
            n = int(r.flights or 0)
            if n == 0:
                continue
            d = int(r.delayed or 0)
            out.append({"dow": int(r.dow), "hour": int(r.dep_hour), "flights": n, "delayed": d,
                        "share": d / n, "reliable": n >= MIN_RELIABLE_CELL})
        out.sort(key=lambda c: (c["dow"], c["hour"]))
        return out
    return cache.get_or_set(("heatmap", f.key()), compute)


def monthly(db: Session, f: Filters) -> list[dict]:
    def compute():
        out = []
        for r in _query(db, f, (A.ym,)):
            rate = _row_rate(r, f)
            if rate["flights"] == 0:
                continue
            out.append({"period": f"{int(r.ym) // 100}-{int(r.ym) % 100:02d}", **rate})
        out.sort(key=lambda x: x["period"])
        return out
    return cache.get_or_set(("monthly", f.key()), compute)


def compare(db: Session, f: Filters, a_id: int, b_id: int) -> dict:
    def compute():
        names = airline_map(db)
        sides = []
        for aid in (a_id, b_id):
            ff = replace(f, airline_ids=(aid,))
            sides.append({"airline_id": aid, "name": names[aid]["name"], "kpi": kpi(db, ff),
                          "hourly": by_hour(db, ff), "categories": categories(db, ff)})
        ka, kb = sides[0]["kpi"], sides[1]["kpi"]
        diff = None
        if ka["flights"] > 0 and kb["flights"] > 0:
            diff = two_proportion_test(ka["delayed"], ka["flights"], kb["delayed"], kb["flights"])
            diff["risk_ratio"] = (ka["share"] / kb["share"]) if kb["share"] else None
        return {"a": sides[0], "b": sides[1], "diff": diff}
    return cache.get_or_set(("compare", f.key(), a_id, b_id), compute)


# ───────── Публичная сводка для лендинга ─────────
def highlights(db: Session) -> dict:
    def compute():
        f0, f15 = Filters(), Filters(threshold=15)
        total = kpi(db, f0)
        version = data_version(db)
        if total["flights"] == 0 or version is None:
            return {"has_data": False, "is_demo": bool(version and version.is_demo), "flights": 0, "airlines": 0,
                    "airports": 0, "period_start": None, "period_end": None, "share": None, "share15": None,
                    "periods": [], "hourly": [], "best_airline": None, "worst_airline": None}
        airlines = [a for a in by_airline(db, f0) if a["flights"] >= 1000]
        ref = lambda a: {"name": a["name"], "share": a["share"], "flights": a["flights"]}
        return {
            "has_data": True, "is_demo": version.is_demo, "flights": total["flights"],
            "airlines": version.airlines, "airports": version.airports,
            "period_start": version.period_start, "period_end": version.period_end,
            "share": total["share"], "share15": kpi(db, f15)["share"],
            "periods": [{"code": p["code"], "label": p["label"], "hour_from": p["hour_from"],
                         "hour_to": p["hour_to"], "share": p["share"], "flights": p["flights"]}
                        for p in by_period(db, f0)],
            "hourly": [{"hour": h["hour"], "share": h["share"], "flights": h["flights"]}
                       for h in by_hour(db, f0) if h["flights"] >= MIN_FLIGHTS_FOR_RANKING],
            "best_airline": ref(airlines[-1]) if airlines else None,
            "worst_airline": ref(airlines[0]) if airlines else None,
        }
    return cache.get_or_set(("highlights",), compute)


def warm_cache(db: Session) -> None:
    """Прогрев кэша для самого частого сценария (открытие панели без фильтров)."""
    f = Filters()
    filter_options(db)
    highlights(db)
    for fn in (kpi, by_airline, by_hour, by_period, heatmap, categories, monthly):
        fn(db, f)
    by_airport(db, f)
