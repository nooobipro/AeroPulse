import numpy as np
import pandas as pd
import pytest
import scipy.sparse as sp
import statsmodels.api as sm
from scipy import stats

from pipeline import columns, regression, stat_tests, transform


def design_data(n=6000, seed=0):
    rng = np.random.default_rng(seed)
    cat = rng.integers(0, 5, n)
    hour = rng.integers(0, 24, n)
    b = regression.DesignBuilder(n)
    b.add_numeric("hour", hour, "time")
    b.add_categorical("cat", cat, 0, "airline")
    d = b.build()
    beta = np.array([-1.0, 0.05, 0.5, -0.4, 0.8, 0.0])
    return d, rng, hour, cat, beta


def test_ols_matches_statsmodels_hc1():
    d, rng, *_ = design_data()
    X = d.X.toarray()
    y = X @ np.array([2.0, 0.9, 1.5, -2.0, 4.0, 0.0]) + rng.standard_t(3, len(X)) * 5
    mine = regression.fit_ols(d.X, y)
    ref = sm.OLS(y, X).fit(cov_type="HC1")
    np.testing.assert_allclose(mine.beta, ref.params, rtol=1e-8)
    np.testing.assert_allclose(mine.se, ref.bse, rtol=1e-6)


def test_logit_matches_statsmodels():
    d, rng, *_ = design_data(seed=1)
    X = d.X.toarray()
    y = (rng.random(len(X)) < 1 / (1 + np.exp(-(X @ np.array([-1.0, 0.05, 0.5, -0.4, 0.8, 0.0]))))).astype(float)
    mine = regression.fit_logit(d.X, y)
    ref = sm.Logit(y, X).fit(disp=0)
    np.testing.assert_allclose(mine.beta, ref.params, rtol=1e-5, atol=1e-6)
    np.testing.assert_allclose(mine.se, ref.bse, rtol=1e-5)


def test_effect_coding_sums_to_zero_and_matches_deviation():
    d, rng, hour, cat, _ = design_data(seed=2)
    y = (rng.random(len(cat)) < 0.3 + 0.1 * cat / 4).astype(float)
    fit = regression.fit_logit(d.X, y)
    eff = regression.effect_coded(fit, d, "cat")
    assert len(eff) == 5
    assert sum(e[1] for e in eff) == pytest.approx(0.0, abs=1e-10)
    # SE уровня-сравнения проверяем прямым пересчётом через ковариацию
    cols = [j for j, m in enumerate(d.meta) if m["kind"] == "cat"]
    c = np.full(len(cols), -1 / 5)
    c[0] += 1
    lv = d.meta[cols[0]]["level"]
    expected_se = float(np.sqrt(c @ fit.cov[np.ix_(cols, cols)] @ c))
    assert dict((lv_, se) for lv_, _, se in eff)[lv] == pytest.approx(expected_se)


def test_auc_matches_bruteforce():
    rng = np.random.default_rng(3)
    y = (rng.random(400) < 0.4).astype(float)
    s = np.round(rng.random(400) + 0.3 * y, 1)  # с совпадениями значений
    pos, neg = s[y == 1], s[y == 0]
    brute = np.mean([(p > n) + 0.5 * (p == n) for p in pos for n in neg])
    assert regression.auc_score(y, s) == pytest.approx(brute)


def test_dunn_two_groups_equals_kruskal():
    rng = np.random.default_rng(4)
    values = np.round(rng.exponential(10, 3000))  # много совпадений (ties)
    groups = rng.integers(0, 2, 3000)
    h, p = stats.kruskal(values[groups == 0], values[groups == 1])
    pair = stat_tests.dunn_test(values, groups)[0]
    assert pair["z"] ** 2 == pytest.approx(h, rel=1e-9)
    assert pair["p_value"] == pytest.approx(p, rel=1e-6)
    assert pair["p_adj"] == pytest.approx(p, rel=1e-6)  # одна пара — поправки нет


def test_dunn_bonferroni_and_direction():
    rng = np.random.default_rng(5)
    groups = np.repeat([0, 1, 2], 500)
    values = np.concatenate([rng.exponential(5, 500), rng.exponential(10, 500), rng.exponential(5, 500)])
    pairs = {(p["a"], p["b"]): p for p in stat_tests.dunn_test(values, groups)}
    assert len(pairs) == 3
    assert pairs[(0, 1)]["z"] < 0 and pairs[(0, 1)]["significant"] and not pairs[(0, 2)]["significant"]
    assert pairs[(0, 1)]["p_adj"] == pytest.approx(min(1, pairs[(0, 1)]["p_value"] * 3))


def test_chi2_and_cramers_v():
    agg = pd.DataFrame({"airline_id": [0, 1], "hour": [8, 20], "flights": [1000, 1000],
                        "delayed0": [200, 600], "delayed15": [100, 300]})
    rows = {r["code"]: r for r in stat_tests.chi2_tests(agg)}
    table = np.array([[200, 800], [600, 400]])
    chi2, p, dof, _ = stats.chi2_contingency(table, correction=False)
    r = rows["chi2_airline_gt0"]
    assert r["statistic"] == pytest.approx(chi2) and r["dof"] == 1
    assert r["effect_value"] == pytest.approx(np.sqrt(chi2 / 2000)) and r["effect_label"] == "умеренная"


def test_resolve_columns_for_both_known_schemas():
    kaggle_2021 = ["FlightDate", "Airline", "Origin", "Dest", "Cancelled", "Diverted", "CRSDepTime", "DepTime",
                   "ArrDelayMinutes", "CRSElapsedTime", "OriginCityName", "OriginState"]
    cols = columns.resolve_columns(kaggle_2021)
    assert cols["airline"] == "Airline" and cols["arr_delay"] == "ArrDelayMinutes" and "date" in cols
    kaggle_2015 = ["YEAR", "MONTH", "DAY", "AIRLINE", "ORIGIN_AIRPORT", "SCHEDULED_DEPARTURE", "ARRIVAL_DELAY",
                   "CANCELLED", "DIVERTED", "SCHEDULED_TIME"]
    cols = columns.resolve_columns(kaggle_2015)
    assert cols["origin"] == "ORIGIN_AIRPORT" and "date" not in cols and cols["day"] == "DAY"
    assert columns.resolve_columns(["Carrier", "o", "x"] + kaggle_2021, {"airline": "Carrier"})["airline"] == "Carrier"
    with pytest.raises(ValueError, match="не найдены обязательные столбцы"):
        columns.resolve_columns(["a", "b"])
    with pytest.raises(ValueError, match="не найден в файле"):
        columns.resolve_columns(kaggle_2021, {"airline": "Nope"})


def test_prepare_chunk_cleans_dirty_rows():
    df = pd.DataFrame({
        "FlightDate": ["2021-01-04", "2021-01-04", "not-a-date", "2021-01-05", "2021-01-05", "2021-01-06", "2021-01-06"],
        "Airline": ["A", "A", "A", "B", "B", " ", "A"],
        "Origin": ["atl", "ATL", "ATL", "12478", "JFK", "JFK", "JFK"],
        "Cancelled": ["False", "True", "False", "False", "False", "False", "False"],
        "Diverted": [False, False, False, False, False, False, True],
        "CRSDepTime": [2400.0, 745.0, 900.0, 900.0, 1130.0, 900.0, 1000.0],
        "ArrDelayMinutes": [-5.0, np.nan, 10.0, 10.0, np.nan, 3.0, np.nan],
        "CRSElapsedTime": [120.0] * 7,
    })
    cols = columns.resolve_columns(list(df.columns))
    ea, eo, meta, c = transform.Encoder(), transform.Encoder(), {}, transform.Counters()
    d = transform.prepare_chunk(df, cols, ea, eo, meta, c)
    assert c.rows_total == 7 and c.rows_invalid == 3  # плохая дата, числовой код аэропорта, пустая авиакомпания
    assert c.cancelled == 1 and c.diverted == 1 and c.rows_missing_delay == 1 and c.completed == 1
    first = d.iloc[0]
    assert first["hour"] == 0 and first["delay"] == 0.0  # 2400 → 00:00, досрочный рейс → 0 минут
    assert eo.values == ["ATL", "JFK"] and ea.values == ["A", "B"]
    agg = transform.finalize_aggregate(transform.aggregate_chunk(d))
    assert agg.flights.sum() == 1 and agg.cancelled.sum() == 1 and agg.diverted.sum() == 1


def test_prepare_chunk_2015_schema_uses_year_month_day():
    df = pd.DataFrame({"YEAR": [2015, 2015], "MONTH": [1, 2], "DAY": [31, 1], "AIRLINE": ["AA", "AA"],
                       "ORIGIN_AIRPORT": ["LAX", "LAX"], "SCHEDULED_DEPARTURE": [1830, 600],
                       "ARRIVAL_DELAY": [20.0, -3.0], "CANCELLED": [0, 0], "DIVERTED": [0, 0]})
    cols = columns.resolve_columns(list(df.columns))
    d = transform.prepare_chunk(df, cols, transform.Encoder(), transform.Encoder(), {}, transform.Counters())
    assert list(d.ym) == [201501, 201502] and list(d.dow) == [6, 7] and list(d.hour) == [18, 6]
    assert list(d.delay) == [20.0, 0.0]


def test_pipeline_is_idempotent_and_keeps_admin_edits(raw_flights, tmp_path):
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from app.db import make_engine
    from app.models import Airline, FlightAgg
    from pipeline.run import iter_csv, run_pipeline

    path = tmp_path / "f.csv"
    raw_flights.head(15_000).to_csv(path, index=False)
    engine = make_engine(f"sqlite:///{tmp_path}/p.db")
    run_pipeline(iter_csv([str(path)], 7_000, {}), engine, sample_frac=1.0, create_tables=True)
    with Session(engine) as s:
        first = s.query(FlightAgg).count()
        airline = s.scalar(select(Airline).where(Airline.code == "Aurora Air"))
        airline.name = "Aurora (правка администратора)"
        s.commit()
    run_pipeline(iter_csv([str(path)], 7_000, {}), engine, sample_frac=1.0)
    with Session(engine) as s:
        assert s.query(FlightAgg).count() == first  # повторный запуск заменяет, а не дублирует данные
        assert s.scalar(select(Airline.name).where(Airline.code == "Aurora Air")) == "Aurora (правка администратора)"
        assert s.query(Airline).count() == 12
