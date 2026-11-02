import io
import re

import pytest
from openpyxl import load_workbook


def test_methods_summary(analyst_client):
    r = analyst_client.get("/api/methods/summary")
    assert r.status_code == 200
    body = r.json()
    codes = [t["code"] for t in body["spearman"]]
    assert "spearman_dep_hour" in codes and len(body["chi2"]) == 4 and len(body["kruskal"]) == 2
    hour = next(t for t in body["spearman"] if t["code"] == "spearman_dep_hour")
    assert 0.1 < hour["effect_value"] < 0.3 and hour["effect_label"] == "слабая"
    assert hour["effect_ci_low"] < hour["effect_value"] < hour["effect_ci_high"]
    assert body["sample"]["rows"] > 50_000 and body["sample"]["train_rows"] > 30_000


def test_dunn_pairs(analyst_client):
    rows = analyst_client.get("/api/methods/dunn").json()
    assert len(rows) == 66  # C(12, 2)
    assert all(0 <= r["p_adj"] <= 1 and r["p_adj"] >= r["p_value"] for r in rows)
    assert all(r["airline_a"] != "?" and r["airline_b"] != "?" for r in rows)
    assert rows == sorted(rows, key=lambda r: r["p_adj"])


def test_regression_payload(analyst_client):
    body = analyst_client.get("/api/methods/regression").json()
    models = {m["code"]: m for m in body["models"]}
    assert set(models) == {"linear_hour", "linear_period", "logit_period", "logit_period_15", "logit_hour"}
    assert 0.6 < models["logit_period"]["metrics"]["auc_test"] < 0.8
    assert 0 < models["linear_hour"]["metrics"]["r2_test"] < 0.1

    hour = next(c for c in models["linear_hour"]["coefficients"] if c["grp"] == "time")
    assert 0.6 < hour["estimate"] < 1.2 and hour["ci_low"] < hour["estimate"] < hour["ci_high"]
    evening = next(c for c in models["logit_period"]["coefficients"] if "Вечер" in c["label"])
    assert evening["odds_ratio"] > 1.5 and evening["or_ci_low"] < evening["odds_ratio"] < evening["or_ci_high"]

    airlines = [c for c in models["logit_period"]["coefficients"] if c["grp"] == "airline"]
    assert len(airlines) == 12
    assert max(airlines, key=lambda c: c["odds_ratio"])["label"] == "Glacier Air"
    assert min(airlines, key=lambda c: c["odds_ratio"])["label"] == "Ember Air"
    assert {c["grp"] for c in models["linear_hour"]["coefficients"]} >= {"time", "airline", "airport", "calendar", "duration"}

    assert len(body["hour_stability"]) == 5
    assert all(0.6 < c["estimate"] < 1.2 for c in body["hour_stability"])
    assert len(body["hour_probability"]["hours"]) == len(body["hour_probability"]["adjusted"]) >= 15
    assert len(body["calibration"]) == 10
    for b in body["calibration"]:
        assert abs(b["predicted"] - b["observed"]) < 0.05  # модель откалибрована


def test_methods_airline_names_follow_dictionary_edits(analyst_client, admin_client, ids):
    airline_id = ids["airline"]["Ember Air"]
    labels = lambda: {c["label"] for m in analyst_client.get("/api/methods/regression").json()["models"]
                      for c in m["coefficients"] if c["grp"] == "airline"}
    assert "Ember Air" in labels()
    admin_client.patch(f"/api/admin/airlines/{airline_id}", json={"name": "Ember (переименована)"})
    try:
        assert "Ember (переименована)" in labels() and "Ember Air" not in labels()
    finally:
        admin_client.patch(f"/api/admin/airlines/{airline_id}", json={"name": "Ember Air"})
    assert "Ember Air" in labels()


def test_xlsx_report(analyst_client, ids):
    r = analyst_client.get("/api/reports/export", params={
        "format": "xlsx", "airline_id": ids["airline"]["Aurora Air"], "hour_from": 6, "hour_to": 20, "threshold": 15})
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    assert re.fullmatch(r'attachment; filename="flight-delays_\d{8}_\d{4}\.xlsx"', r.headers["content-disposition"])
    wb = load_workbook(io.BytesIO(r.content))
    assert wb.sheetnames == ["Параметры", "Сводка", "Авиакомпании", "По часам", "Периоды суток", "Аэропорты",
                             "Категории", "Месяцы", "Тепловая карта"]
    params = {row[0].value: row[1].value for row in wb["Параметры"].iter_rows(min_row=1) if row[0].value}
    assert params["Авиакомпании"] == "Aurora Air" and params["Порог задержки"] == "15 минут и более"
    assert "ВНИМАНИЕ" in params  # данные демонстрационные
    assert wb["Авиакомпании"].max_row == 2 and len(wb["Авиакомпании"]._charts) == 1
    assert len(wb["По часам"]._charts) == 1 and wb["По часам"]["D2"].number_format == "0.0%"
    hours = [row[0].value for row in wb["По часам"].iter_rows(min_row=2)]
    assert min(hours) >= 6 and max(hours) <= 20


def test_pdf_report(analyst_client):
    r = analyst_client.get("/api/reports/export", params={"format": "pdf"})
    assert r.status_code == 200 and r.headers["content-type"] == "application/pdf"
    assert r.content.startswith(b"%PDF") and len(r.content) > 50_000
    assert len(re.findall(rb"/Type\s*/Page\b", r.content)) >= 2
    assert b"DejaVu" in r.content  # кириллический шрифт встроен


def test_pdf_report_for_empty_selection(analyst_client):
    r = analyst_client.get("/api/reports/export", params={"format": "pdf", "period_from": "2030-01"})
    assert r.status_code == 200 and r.content.startswith(b"%PDF")
    x = analyst_client.get("/api/reports/export", params={"format": "xlsx", "period_from": "2030-01"})
    assert x.status_code == 200


def test_csv_exports(analyst_client):
    r = analyst_client.get("/api/reports/csv", params={"dataset": "hourly"})
    assert r.status_code == 200 and r.content.startswith(b"\xef\xbb\xbf")
    lines = r.content.decode("utf-8-sig").splitlines()
    assert lines[0].startswith("Час вылета;Рейсов;Задержано;Доля задержанных")
    first = lines[1].split(";")
    assert "," in first[3] and "." not in first[3]  # десятичная запятая

    point = analyst_client.get("/api/reports/csv", params={"dataset": "hourly", "decimal": "point"})
    assert "." in point.content.decode("utf-8-sig").splitlines()[1].split(";")[3]
    for name in ("airlines", "periods", "airports", "categories", "heatmap", "monthly"):
        assert analyst_client.get("/api/reports/csv", params={"dataset": name}).status_code == 200, name
    assert analyst_client.get("/api/reports/csv", params={"dataset": "secret"}).status_code == 422
    assert analyst_client.get("/api/reports/export", params={"format": "docx"}).status_code == 422


def test_export_is_audited(analyst_client, admin_client):
    analyst_client.get("/api/reports/export", params={"format": "xlsx"})
    r = admin_client.get("/api/admin/audit", params={"action": "export_xlsx", "email": analyst_client.user_email})
    assert r.json()["total"] == 1


def test_export_concurrency_limit(analyst_client, monkeypatch):
    from app.routers import reports as reports_router

    class Busy:
        def acquire(self, blocking=True):
            return False

        def release(self):
            raise AssertionError("не должен освобождаться")

    monkeypatch.setattr(reports_router, "_slots", Busy())
    r = analyst_client.get("/api/reports/export", params={"format": "pdf"})
    assert r.status_code == 429
