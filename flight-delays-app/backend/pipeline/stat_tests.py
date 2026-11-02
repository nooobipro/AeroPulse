"""Корреляция Спирмена, хи-квадрат, Краскел–Уоллис и парные сравнения Данна."""
import itertools

import numpy as np
import pandas as pd
from scipy import stats

from pipeline.labels import label_cramers_v, label_epsilon_sq, label_spearman

PERIOD_NAMES = {0: "Ночь", 1: "Утро", 2: "День", 3: "Вечер"}


def period_codes(hour: np.ndarray) -> np.ndarray:
    return np.digitize(hour, [6, 12, 18])  # 0 ночь, 1 утро, 2 день, 3 вечер


def spearman_tests(sample: pd.DataFrame) -> list[dict]:
    y = sample["delay"].to_numpy(dtype=float)
    factors = [
        ("spearman_dep_hour", "Час вылета и задержка прибытия", sample["hour"].to_numpy(dtype=float)),
        ("spearman_duration", "Плановая длительность перелёта и задержка", sample["duration"].to_numpy(dtype=float)),
        ("spearman_dow", "День недели и задержка", sample["dow"].to_numpy(dtype=float)),
        ("spearman_month", "Месяц (1–12) и задержка", (sample["ym"].to_numpy() % 100).astype(float)),
    ]
    out = []
    for order, (code, title, x) in enumerate(factors):
        mask = ~np.isnan(x) & ~np.isnan(y)
        if mask.sum() < 10 or np.nanstd(x[mask]) == 0:
            continue
        res = stats.spearmanr(x[mask], y[mask])
        rho, n = float(res.statistic), int(mask.sum())
        se = 1.06 / np.sqrt(n - 3)  # приближённая ошибка для ρ Спирмена (Fieller)
        lo, hi = np.tanh(np.arctanh(rho) - 1.959964 * se), np.tanh(np.arctanh(rho) + 1.959964 * se)
        out.append(dict(code=code, family="spearman", title=title, statistic=rho, dof=None, p_value=float(res.pvalue),
                        effect_name="ρ Спирмена", effect_value=rho, effect_ci_low=float(lo), effect_ci_high=float(hi),
                        effect_label=label_spearman(rho), n=n, details={"scope": "случайная выборка рейсов"},
                        sort_order=order))
    return out


def _chi2(table: np.ndarray, code: str, title: str, order: int) -> dict | None:
    table = table[table.sum(axis=1) > 0]
    if table.shape[0] < 2 or (table.sum(axis=0) == 0).any():
        return None
    res = stats.chi2_contingency(table, correction=False)
    n = float(table.sum())
    v = float(np.sqrt(res.statistic / (n * min(table.shape[0] - 1, table.shape[1] - 1))))
    return dict(code=code, family="chi2", title=title, statistic=float(res.statistic), dof=int(res.dof),
                p_value=float(res.pvalue), effect_name="V Крамера", effect_value=v, effect_ci_low=None,
                effect_ci_high=None, effect_label=label_cramers_v(v), n=int(n),
                details={"scope": "все рейсы (по агрегатам)"}, sort_order=order)


def chi2_tests(agg: pd.DataFrame) -> list[dict]:
    """Критерий независимости по таблице «группа × задержан/не задержан» на всех рейсах."""
    out = []
    by_airline = agg.groupby("airline_id")[["flights", "delayed0", "delayed15"]].sum()
    by_period = agg.assign(period=period_codes(agg["hour"].to_numpy())).groupby("period")[["flights", "delayed0", "delayed15"]].sum()
    specs = [("chi2_airline_gt0", "Авиакомпания и факт задержки (> 0 мин)", by_airline, "delayed0"),
             ("chi2_airline_ge15", "Авиакомпания и факт задержки (≥ 15 мин)", by_airline, "delayed15"),
             ("chi2_period_gt0", "Период суток и факт задержки (> 0 мин)", by_period, "delayed0"),
             ("chi2_period_ge15", "Период суток и факт задержки (≥ 15 мин)", by_period, "delayed15")]
    for order, (code, title, g, col) in enumerate(specs):
        table = np.column_stack([g[col].to_numpy(dtype=float), (g["flights"] - g[col]).to_numpy(dtype=float)])
        row = _chi2(table, code, title, order)
        if row:
            out.append(row)
    return out


def _kruskal(values: np.ndarray, groups: np.ndarray, code: str, title: str, order: int) -> dict | None:
    parts = [values[groups == g] for g in np.unique(groups)]
    parts = [p for p in parts if len(p) > 0]
    if len(parts) < 2:
        return None
    h, p = stats.kruskal(*parts)
    n = len(values)
    eps = float(h / (n - 1))  # ε² = H / (n − 1)
    return dict(code=code, family="kruskal", title=title, statistic=float(h), dof=len(parts) - 1, p_value=float(p),
                effect_name="ε² (эпсилон-квадрат)", effect_value=eps, effect_ci_low=None, effect_ci_high=None,
                effect_label=label_epsilon_sq(eps), n=n, details={"scope": "случайная выборка рейсов", "groups": len(parts)},
                sort_order=order)


def dunn_test(values: np.ndarray, groups: np.ndarray, alpha: float = 0.05, min_n: int = 30) -> list[dict]:
    """Парные сравнения Данна по рангам задержек с поправкой Бонферрони на число пар."""
    ids, inverse = np.unique(groups, return_inverse=True)
    n_i = np.bincount(inverse)
    keep = np.flatnonzero(n_i >= min_n)
    if len(keep) < 2:
        return []
    ranks = stats.rankdata(values)
    n_total = len(values)
    _, counts = np.unique(values, return_counts=True)
    tie_term = float(((counts.astype(float) ** 3) - counts).sum())
    sigma2 = n_total * (n_total + 1) / 12.0 - tie_term / (12.0 * (n_total - 1))
    mean_rank = np.bincount(inverse, weights=ranks) / n_i
    pairs = list(itertools.combinations(keep, 2))
    m = len(pairs)
    out = []
    for i, j in pairs:
        se = np.sqrt(sigma2 * (1 / n_i[i] + 1 / n_i[j]))
        z = float((mean_rank[i] - mean_rank[j]) / se) if se > 0 else 0.0
        p = float(2 * stats.norm.sf(abs(z)))
        p_adj = min(1.0, p * m)
        out.append(dict(a=int(ids[i]), b=int(ids[j]), z=z, p_value=p, p_adj=p_adj, significant=bool(p_adj < alpha)))
    return out


def kruskal_and_dunn(sample: pd.DataFrame) -> tuple[list[dict], list[dict]]:
    values = sample["delay"].to_numpy(dtype=float)
    tests = []
    k1 = _kruskal(values, sample["airline_id"].to_numpy(), "kruskal_airline",
                  "Авиакомпания: различия в величине задержки (мин)", 0)
    k2 = _kruskal(values, period_codes(sample["hour"].to_numpy()), "kruskal_period",
                  "Период суток: различия в величине задержки (мин)", 1)
    tests = [t for t in (k1, k2) if t]
    return tests, dunn_test(values, sample["airline_id"].to_numpy())
