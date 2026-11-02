"""Сверка API с независимым расчётом по сырым данным (pandas) и проверка валидации фильтров."""
import numpy as np
import pytest


def get(client, path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_kpi_matches_raw_data(user_client, truth, raw_flights):
    k = get(user_client, "/api/stats/kpi")
    d = truth.ArrDelayMinutes
    assert k["flights"] == len(truth)
    assert k["delayed"] == int((d > 0).sum())
    assert k["share"] == pytest.approx((d > 0).mean())
    assert k["avg_delay"] == pytest.approx(d.mean())
    assert k["max_delay"] == int(d.max())
    assert k["cancelled"] == int(raw_flights.Cancelled.sum())
    assert k["diverted"] == int(raw_flights.Diverted.sum())
    assert k["ci_low"] < k["share"] < k["ci_high"]


def test_threshold_and_average_modes(user_client, truth):
    d = truth.ArrDelayMinutes
    k15 = get(user_client, "/api/stats/kpi", threshold=15)
    assert k15["delayed"] == int((d >= 15).sum())
    assert k15["avg_delay"] == pytest.approx(d.mean())  # «по всем рейсам» от порога не зависит

    k_all = get(user_client, "/api/stats/kpi", avg_mode="delayed")
    assert k_all["avg_delay"] == pytest.approx(d[d > 0].mean())
    k_15 = get(user_client, "/api/stats/kpi", avg_mode="delayed", threshold=15)
    assert k_15["avg_delay"] == pytest.approx(d[d >= 15].mean())


def test_filtered_hourly_series(user_client, truth, ids):
    airline, airports = "Aurora Air", ["ATL", "ORD"]
    params = {"airline_id": ids["airline"][airline], "airport_id": [ids["airport"][a] for a in airports],
              "period_from": "2021-03", "period_to": "2021-09", "hour_from": 6, "hour_to": 14}
    rows = get(user_client, "/api/stats/hourly", **params)
    sub = truth[(truth.Airline == airline) & truth.Origin.isin(airports) & truth.ym.between(202103, 202109)
                & truth.hour.between(6, 14)]
    expected = sub.groupby("hour").ArrDelayMinutes.agg(n="size", late=lambda s: (s > 0).sum(), mean="mean")
    assert [r["hour"] for r in rows] == list(expected.index)
    for r in rows:
        e = expected.loc[r["hour"]]
        assert r["flights"] == e.n and r["delayed"] == e.late
        assert r["avg_delay"] == pytest.approx(e["mean"])
    assert min(r["hour"] for r in rows) >= 6 and max(r["hour"] for r in rows) <= 14


def test_periods_are_consistent_with_hours(user_client, truth):
    periods = {p["code"]: p for p in get(user_client, "/api/stats/periods")}
    assert list(periods) == ["night", "morning", "day", "evening"]
    for code, (a, b) in {"night": (0, 5), "morning": (6, 11), "day": (12, 17), "evening": (18, 23)}.items():
        sub = truth[truth.hour.between(a, b)].ArrDelayMinutes
        assert periods[code]["flights"] == len(sub)
        assert periods[code]["share"] == pytest.approx((sub > 0).mean())
    assert periods["evening"]["share"] > periods["morning"]["share"]  # закономерность, заложенная в демо-данные


def test_categories(user_client, truth):
    cats = get(user_client, "/api/stats/categories")
    d = truth.ArrDelayMinutes
    expected = [(d <= 0).sum(), ((d > 0) & (d <= 15)).sum(), ((d > 15) & (d <= 30)).sum(),
                ((d > 30) & (d <= 60)).sum(), ((d > 60) & (d <= 120)).sum(), (d > 120).sum()]
    assert [c["flights"] for c in cats] == expected
    assert sum(c["share"] for c in cats) == pytest.approx(1.0)
    assert [c["key"] for c in cats][0] == "c0"


def test_heatmap_cells(user_client, truth):
    cells = get(user_client, "/api/stats/heatmap")
    assert sum(c["flights"] for c in cells) == len(truth)
    cell = next(c for c in cells if c["dow"] == 3 and c["hour"] == 18)
    sub = truth[(truth.dow == 3) & (truth.hour == 18)].ArrDelayMinutes
    assert cell["flights"] == len(sub) and cell["delayed"] == int((sub > 0).sum())
    assert cell["reliable"] == (len(sub) >= 30)


def test_airline_ranking(user_client, truth):
    rows = get(user_client, "/api/stats/airlines")
    shares = [r["share"] for r in rows]
    assert shares == sorted(shares, reverse=True) and len(rows) == truth.Airline.nunique()
    first = rows[0]
    sub = truth[truth.Airline == first["name"]].ArrDelayMinutes
    assert first["flights"] == len(sub) and first["max_delay"] == int(sub.max())
    assert rows[0]["name"] == "Glacier Air" and rows[-1]["name"] == "Ember Air"  # заложенные в демо-данные крайности


def test_airports_params(user_client, truth):
    rows = get(user_client, "/api/stats/airports", sort="flights", order="desc", limit=5, min_flights=1)
    assert len(rows) == 5 and rows[0]["flights"] >= rows[-1]["flights"]
    assert rows[0]["code"] == truth.Origin.value_counts().index[0]
    big = get(user_client, "/api/stats/airports", min_flights=5000, limit=400)
    assert all(r["flights"] >= 5000 for r in big)
    asc = get(user_client, "/api/stats/airports", sort="share", order="asc", min_flights=100)
    assert [r["share"] for r in asc] == sorted(r["share"] for r in asc)


def test_monthly(user_client, truth):
    rows = get(user_client, "/api/stats/monthly")
    assert rows[0]["period"] == "2021-01" and rows[-1]["period"] == "2022-07" and len(rows) == 19
    assert sum(r["flights"] for r in rows) == len(truth)


def test_compare_airlines(user_client, truth, ids):
    a, b = ids["airline"]["Glacier Air"], ids["airline"]["Ember Air"]
    r = get(user_client, "/api/stats/compare", airline_a=a, airline_b=b, hour_from=6)
    sa = truth[(truth.Airline == "Glacier Air") & (truth.hour >= 6)].ArrDelayMinutes
    sb = truth[(truth.Airline == "Ember Air") & (truth.hour >= 6)].ArrDelayMinutes
    assert r["a"]["kpi"]["flights"] == len(sa) and r["b"]["kpi"]["flights"] == len(sb)
    assert r["diff"]["diff"] == pytest.approx((sa > 0).mean() - (sb > 0).mean())
    assert r["diff"]["p_value"] < 0.001 and r["diff"]["ci_low"] > 0
    assert r["diff"]["risk_ratio"] == pytest.approx((sa > 0).mean() / (sb > 0).mean())
    assert len(r["a"]["hourly"]) > 5 and len(r["a"]["categories"]) == 6


def test_compare_errors(user_client, ids):
    a = ids["airline"]["Glacier Air"]
    assert user_client.get("/api/stats/compare", params={"airline_a": a, "airline_b": a}).status_code == 422
    assert user_client.get("/api/stats/compare", params={"airline_a": a, "airline_b": 999999}).status_code == 404
    assert user_client.get("/api/stats/compare", params={"airline_a": a}).status_code == 422


def test_empty_selection_returns_zeros(user_client):
    k = get(user_client, "/api/stats/kpi", period_from="2030-01")
    assert k["flights"] == 0 and k["share"] is None and k["worst_hour"] is None and k["avg_delay"] is None
    assert get(user_client, "/api/stats/hourly", period_from="2030-01") == []
    assert get(user_client, "/api/stats/airlines", period_from="2030-01") == []
    assert all(c["share"] is None for c in get(user_client, "/api/stats/categories", period_from="2030-01"))
    unknown = get(user_client, "/api/stats/kpi", airline_id=999999)
    assert unknown["flights"] == 0


@pytest.mark.parametrize("params", [
    {"hour_from": 12, "hour_to": 6}, {"hour_from": -1}, {"hour_to": 24}, {"threshold": 7},
    {"period_from": "2021-13"}, {"period_from": "21-01"}, {"period_from": "2022-01", "period_to": "2021-01"},
    {"avg_mode": "median"},
])
def test_invalid_filters_rejected(user_client, params):
    assert user_client.get("/api/stats/kpi", params=params).status_code == 422


def test_filter_options(user_client):
    o = get(user_client, "/api/meta/filters")
    assert len(o["airlines"]) == 12 and len(o["airports"]) == 40 and len(o["periods"]) == 19
    assert o["data"]["is_demo"] is True


def test_highlights_are_derived_from_data(make_client, truth):
    h = get(make_client(), "/api/public/highlights")
    assert h["flights"] == len(truth) and h["airlines"] == 12 and h["airports"] == 40
    assert h["share"] == pytest.approx((truth.ArrDelayMinutes > 0).mean())
    assert h["best_airline"]["share"] < h["worst_airline"]["share"]
    assert {p["code"] for p in h["periods"]} == {"night", "morning", "day", "evening"}
    assert len(h["hourly"]) >= 15 and not np.isnan(h["hourly"][0]["share"])
