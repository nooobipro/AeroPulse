"""Регрессионный анализ на разреженных матрицах.

Линейная регрессия — МНК с робастными ошибками HC1; логистическая — IRLS (метод Ньютона).
Собственная реализация нужна, чтобы подогнать модель с сотнями индикаторов (авиакомпании, аэропорты)
на выборке в миллионы строк без плотных матриц. Корректность проверяется тестами против statsmodels.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd
import scipy.sparse as sp
from scipy.linalg import LinAlgError, solve
from scipy.special import expit
from scipy.stats import norm, rankdata

Z95 = 1.959963984540054
MONTHS = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август", "сентябрь", "октябрь",
          "ноябрь", "декабрь"]
DAYS = {1: "Пн", 2: "Вт", 3: "Ср", 4: "Чт", 5: "Пт", 6: "Сб", 7: "Вс"}
PERIOD_LABEL = {0: "Ночь (0–5 ч)", 1: "Утро (6–11 ч)", 2: "День (12–17 ч)", 3: "Вечер (18–23 ч)"}
OTHER_AIRPORTS = -1


# ───────── Матрица плана ─────────
@dataclass
class Design:
    X: sp.csr_matrix
    names: list[str]
    groups: list[str]
    meta: list[dict]
    refs: dict
    levels: dict


class DesignBuilder:
    def __init__(self, n: int):
        self.n = n
        self._blocks: list[sp.spmatrix] = []
        self.names: list[str] = []
        self.groups: list[str] = []
        self.meta: list[dict] = []
        self.refs: dict = {}
        self.levels: dict = {}
        self.add_numeric("const", np.ones(n), "intercept")

    def add_numeric(self, kind: str, values, group: str) -> None:
        self._blocks.append(sp.csr_matrix(np.asarray(values, dtype=np.float64).reshape(-1, 1)))
        self.names.append(kind)
        self.groups.append(group)
        self.meta.append({"kind": kind, "level": None})

    def add_categorical(self, kind: str, values, ref, group: str) -> None:
        s = pd.Series(np.asarray(values))
        levels = sorted(s.unique().tolist())
        if ref not in levels:
            ref = levels[0]
        self.refs[kind], self.levels[kind] = ref, levels
        use = [lv for lv in levels if lv != ref]
        if not use:
            return
        mapped = s.map({lv: j for j, lv in enumerate(use)})
        mask = mapped.notna().to_numpy()
        rows = np.flatnonzero(mask)
        cols = mapped[mask].astype(int).to_numpy()
        self._blocks.append(sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(self.n, len(use))))
        for lv in use:
            self.names.append(f"{kind}[{lv}]")
            self.groups.append(group)
            self.meta.append({"kind": kind, "level": lv})

    def build(self, support: np.ndarray | None = None) -> Design:
        """support — маска строк обучающей выборки: столбцы без единого наблюдения в ней отбрасываются."""
        X = sp.hstack(self._blocks, format="csr")
        idx = np.arange(X.shape[1])
        if support is not None:
            nnz = np.asarray((X[support] != 0).sum(axis=0)).ravel()
            idx = np.flatnonzero(nnz > 0)
            X = X.tocsc()[:, idx].tocsr()
        return Design(X, [self.names[i] for i in idx], [self.groups[i] for i in idx],
                      [self.meta[i] for i in idx], self.refs, self.levels)


# ───────── Подгонка ─────────
@dataclass
class Fit:
    beta: np.ndarray
    cov: np.ndarray
    se: np.ndarray
    n: int


def _solve(A: np.ndarray, b: np.ndarray) -> np.ndarray:
    try:
        return solve(A, b, assume_a="pos")
    except (LinAlgError, ValueError):
        return np.linalg.lstsq(A, b, rcond=None)[0]


def _inv(A: np.ndarray) -> np.ndarray:
    try:
        return np.linalg.inv(A)
    except LinAlgError:
        return np.linalg.pinv(A)


def fit_ols(X: sp.csr_matrix, y: np.ndarray) -> Fit:
    n, p = X.shape
    XtX = (X.T @ X).toarray()
    beta = _solve(XtX, X.T @ y)
    resid = y - X @ beta
    inv = _inv(XtX)
    meat = (X.T @ (sp.diags(resid ** 2) @ X)).toarray()
    cov = inv @ meat @ inv * (n / max(n - p, 1))  # HC1
    return Fit(beta, cov, np.sqrt(np.clip(np.diag(cov), 0, None)), n)


def fit_logit(X: sp.csr_matrix, y: np.ndarray, max_iter: int = 30, tol: float = 1e-7) -> Fit:
    n, p = X.shape
    beta = np.zeros(p)
    ybar = float(np.clip(y.mean(), 1e-6, 1 - 1e-6))
    beta[0] = np.log(ybar / (1 - ybar))  # столбец 0 — константа
    Xt = X.T.tocsr()
    for _ in range(max_iter):
        eta = X @ beta
        mu = expit(eta)
        w = np.clip(mu * (1 - mu), 1e-9, None)
        z = eta + (y - mu) / w
        Xw = sp.diags(w) @ X
        new = _solve((Xt @ Xw).toarray(), Xt @ (w * z))
        delta = float(np.max(np.abs(new - beta)))
        beta = new
        if delta < tol:
            break
    mu = expit(X @ beta)
    w = np.clip(mu * (1 - mu), 1e-9, None)
    cov = _inv((Xt @ (sp.diags(w) @ X)).toarray())
    return Fit(beta, cov, np.sqrt(np.clip(np.diag(cov), 0, None)), n)


def effect_coded(fit: Fit, design: Design, kind: str) -> list[tuple[object, float, float]]:
    """Отклонение каждого уровня от «средней» (невзвешенной) категории: (уровень, оценка, ошибка)."""
    cols = [j for j, m in enumerate(design.meta) if m["kind"] == kind]
    if not cols:
        return []
    nonref = [design.meta[j]["level"] for j in cols]
    ref = design.refs[kind]
    k = len(cols) + 1
    beta, cov = fit.beta[cols], fit.cov[np.ix_(cols, cols)]
    out = []
    for lv in nonref + [ref]:
        c = -np.ones(len(cols)) / k
        if lv != ref:
            c[nonref.index(lv)] += 1.0
        out.append((lv, float(c @ beta), float(np.sqrt(max(c @ cov @ c, 0.0)))))
    return out


# ───────── Метрики ─────────
def auc_score(y: np.ndarray, score: np.ndarray) -> float:
    n1 = float(y.sum())
    n0 = len(y) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    return float((rankdata(score)[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def calibration_bins(p: np.ndarray, y: np.ndarray, bins: int = 10) -> list[dict]:
    df = pd.DataFrame({"p": p, "y": y})
    df["bin"] = pd.qcut(df["p"], bins, labels=False, duplicates="drop")
    g = df.groupby("bin").agg(predicted=("p", "mean"), observed=("y", "mean"), n=("y", "size")).reset_index()
    return [{"bin": int(r.bin) + 1, "predicted": float(r.predicted), "observed": float(r.observed), "n": int(r.n)}
            for r in g.itertuples()]


# ───────── Модели проекта ─────────
def _coef_row(model, grp, term, label, est, se, p=None, logit=False, order=0) -> dict:
    lo, hi = (est - Z95 * se, est + Z95 * se) if se is not None else (None, None)
    if p is None and se:
        p = float(2 * norm.sf(abs(est / se)))
    row = dict(model=model, grp=grp, term=term, label=label, estimate=float(est),
               std_error=None if se is None else float(se),
               ci_low=None if lo is None else float(lo), ci_high=None if hi is None else float(hi),
               p_value=p, odds_ratio=None, or_ci_low=None, or_ci_high=None, sort_order=order)
    if logit:
        row.update(odds_ratio=float(np.exp(est)), or_ci_low=None if lo is None else float(np.exp(lo)),
                   or_ci_high=None if hi is None else float(np.exp(hi)))
    return row


def run_models(sample: pd.DataFrame, airline_names: dict[int, str], airport_names: dict[int, str],
               observed_by_hour: dict[int, float], seed: int = 42, min_airport_n: int = 300) -> dict:
    """Возвращает {'coefficients': [...], 'metrics': [...], 'info': {...}}."""
    df = sample.reset_index(drop=True)
    info: dict = {"rows_in_sample": int(len(df))}
    has_duration = bool(df["duration"].notna().mean() > 0.5)
    if has_duration:
        info["dropped_missing_duration"] = int(df["duration"].isna().sum())
        df = df[df["duration"].notna()].reset_index(drop=True)
    n = len(df)
    if n < 2000:
        return {"coefficients": [], "metrics": [], "info": {**info, "skipped": "слишком маленькая выборка для регрессии"}}

    rng = np.random.default_rng(seed)
    train = rng.random(n) < 2 / 3
    test = ~train
    info.update(rows_in_models=n, train_rows=int(train.sum()), test_rows=int(test.sum()))

    y = df["delay"].to_numpy(dtype=float)
    y0, y15 = (y > 0).astype(float), (y >= 15).astype(float)
    hour = df["hour"].to_numpy().astype(int)
    dow = df["dow"].to_numpy().astype(int)
    month = (df["ym"].to_numpy() % 100).astype(int)
    year = (df["ym"].to_numpy() // 100).astype(int)
    airline = df["airline_id"].to_numpy().astype(int)
    origin = df["origin_id"].to_numpy().astype(int)
    period = np.digitize(hour, [6, 12, 18])
    duration_h = df["duration"].to_numpy(dtype=float) / 60.0

    counts = pd.Series(origin).value_counts()
    rare = counts[counts < min_airport_n].index.to_numpy()
    origin_pooled = np.where(np.isin(origin, rare), OTHER_AIRPORTS, origin)
    info["airports_pooled_into_other"] = int(len(rare))
    top = lambda arr: pd.Series(arr).value_counts().idxmax()
    ref_airline, ref_airport = top(airline), top(origin_pooled)
    ref_hour = 6 if (hour == 6).any() else int(hour.min())
    ref_month, ref_year = int(month.min()), int(year.min())

    def design(time: str | None, controls: tuple[str, ...]) -> Design:
        b = DesignBuilder(n)
        if time == "hour":
            b.add_numeric("hour", hour, "time")
        elif time == "period":
            b.add_categorical("period", period, 1, "time")
        elif time == "hour_cat":
            b.add_categorical("hour_cat", hour, ref_hour, "time")
        if "airline" in controls:
            b.add_categorical("airline", airline, ref_airline, "airline")
        if "airport" in controls:
            b.add_categorical("airport", origin_pooled, ref_airport, "airport")
        if "duration" in controls and has_duration:
            b.add_numeric("duration", duration_h, "duration")
        if "calendar" in controls:
            b.add_categorical("dow", dow, 1, "calendar")
            b.add_categorical("month", month, ref_month, "calendar")
            b.add_categorical("year", year, ref_year, "calendar")
        return b.build(support=train)

    ALL = ("airline", "airport", "duration", "calendar")
    coefficients: list[dict] = []
    metrics: list[dict] = []

    def labels(d: Design, kind: str, level) -> str:
        if kind == "hour":
            return "Час вылета: каждый следующий час"
        if kind == "period":
            return f"Период суток: {PERIOD_LABEL[level]} относительно утра"
        if kind == "hour_cat":
            return f"Час вылета {level:02d}:00 относительно {d.refs['hour_cat']:02d}:00"
        if kind == "duration":
            return "Плановая длительность: каждый следующий час"
        if kind == "dow":
            return f"День недели: {DAYS[level]} относительно Пн"
        if kind == "month":
            return f"Месяц: {MONTHS[level - 1]} относительно {MONTHS[d.refs['month'] - 1]}"
        if kind == "year":
            return f"Год: {level} относительно {d.refs['year']}"
        return kind

    def add_coefficients(model: str, d: Design, fit: Fit, logit: bool, only_groups: tuple[str, ...] | None = None):
        order = 0
        for j, (grp, meta) in enumerate(zip(d.groups, d.meta)):
            if grp == "intercept" or meta["kind"] in ("airline", "airport"):
                continue
            if only_groups and grp not in only_groups:
                continue
            order += 1
            coefficients.append(_coef_row(model, grp, f"{meta['kind']}:{meta['level']}", labels(d, meta["kind"], meta["level"]),
                                          fit.beta[j], fit.se[j], logit=logit, order=order))
        for kind, grp, names in (("airline", "airline", airline_names), ("airport", "airport", airport_names)):
            if only_groups and grp not in only_groups:
                continue
            for lv, est, se in effect_coded(fit, d, kind):
                order += 1
                name = "Прочие аэропорты" if lv == OTHER_AIRPORTS else names.get(int(lv), str(lv))
                coefficients.append(_coef_row(model, grp, f"{kind}:{name}", name, est, se, logit=logit, order=order))

    def linear_model(code: str, time: str):
        d = design(time, ALL)
        fit = fit_ols(d.X[train], y[train])
        pred = d.X[test] @ fit.beta
        sse = float(((y[test] - pred) ** 2).sum())
        sst = float(((y[test] - y[test].mean()) ** 2).sum())
        metrics.extend([
            dict(model=code, key="r2_test", value=1 - sse / sst, details=None),
            dict(model=code, key="rmse_test", value=float(np.sqrt(sse / test.sum())), details=None),
            dict(model=code, key="mean_delay", value=float(y.mean()), details=None),
            dict(model=code, key="n_train", value=float(train.sum()), details=None),
            dict(model=code, key="n_test", value=float(test.sum()), details=None),
        ])
        add_coefficients(code, d, fit, logit=False)
        return d, fit

    def logit_model(code: str, time: str, target: np.ndarray, only_groups=None):
        d = design(time, ALL)
        fit = fit_logit(d.X[train], target[train])
        p = expit(d.X[test] @ fit.beta)
        metrics.extend([
            dict(model=code, key="auc_test", value=auc_score(target[test], p), details=None),
            dict(model=code, key="brier_test", value=float(np.mean((p - target[test]) ** 2)), details=None),
            dict(model=code, key="base_rate", value=float(target.mean()), details=None),
            dict(model=code, key="n_train", value=float(train.sum()), details=None),
            dict(model=code, key="n_test", value=float(test.sum()), details=None),
        ])
        add_coefficients(code, d, fit, logit=True, only_groups=only_groups)
        return d, fit, p

    # 1–2. Линейные модели
    d_lin, fit_lin = linear_model("linear_hour", "hour")
    linear_model("linear_period", "period")

    # Устойчивость коэффициента при часе вылета: добавляем контроли по одному
    specs = [("Только час вылета", ()), ("+ авиакомпания", ("airline",)), ("+ аэропорт вылета", ("airline", "airport")),
             ("+ длительность перелёта", ("airline", "airport", "duration")), ("+ день недели, месяц, год (полная модель)", ALL)]
    for i, (label, controls) in enumerate(specs, 1):
        d = design("hour", controls)
        fit = fit_ols(d.X[train], y[train])
        j = d.names.index("hour")
        coefficients.append(_coef_row("linear_hour_stability", "robustness", f"spec{i}", label,
                                      fit.beta[j], fit.se[j], order=i))

    # 3–4. Логистические модели
    d_log, fit_log, p_test = logit_model("logit_period", "period", y0)
    metrics.append(dict(model="logit_period", key="calibration", value=None,
                        details={"bins": calibration_bins(p_test, y0[test])}))
    logit_model("logit_period_15", "period", y15, only_groups=("time",))

    # 5. Скорректированная вероятность по часам (стандартизация по составу рейсов)
    d_h, fit_h, _ = logit_model("logit_hour", "hour_cat", y0, only_groups=("time",))
    hcols = {m["level"]: j for j, m in enumerate(d_h.meta) if m["kind"] == "hour_cat"}
    b0 = fit_h.beta.copy()
    b0[list(hcols.values())] = 0.0
    eta0 = d_h.X @ b0
    hours_ok = [h for h in sorted(set(hour.tolist())) if (hour == h).sum() >= 200]
    adjusted = [float(expit(eta0 + (fit_h.beta[hcols[h]] if h in hcols else 0.0)).mean()) for h in hours_ok]
    metrics.append(dict(model="logit_hour", key="hour_probability", value=None, details={
        "hours": hours_ok, "adjusted": adjusted, "observed": [observed_by_hour.get(h) for h in hours_ok]}))
    return {"coefficients": coefficients, "metrics": metrics, "info": info}
