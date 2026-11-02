import uuid

from tests.conftest import PASSWORD, create_user

USER_OK = ["/api/stats/kpi", "/api/stats/airlines", "/api/stats/hourly", "/api/stats/periods", "/api/stats/heatmap",
           "/api/stats/airports", "/api/stats/categories", "/api/stats/monthly", "/api/meta/filters"]
ANALYST_ONLY = ["/api/methods/summary", "/api/methods/dunn", "/api/methods/regression", "/api/saved-filters",
                "/api/reports/export?format=xlsx", "/api/reports/csv?dataset=hourly"]
ADMIN_ONLY = ["/api/admin/users", "/api/admin/audit", "/api/admin/airlines", "/api/admin/airports", "/api/admin/data"]


def test_guest_gets_only_public_endpoints(make_client):
    c = make_client()
    assert c.get("/api/health").status_code == 200
    r = c.get("/api/public/highlights")
    assert r.status_code == 200 and r.json()["has_data"] is True and r.json()["is_demo"] is True
    for url in USER_OK + ANALYST_ONLY + ADMIN_ONLY:
        assert c.get(url).status_code == 401, url


def test_user_role_permissions(user_client):
    for url in USER_OK:
        assert user_client.get(url).status_code == 200, url
    for url in ANALYST_ONLY + ADMIN_ONLY:
        assert user_client.get(url).status_code == 403, url
    assert user_client.post("/api/saved-filters", json={"name": "x", "params": {}}).status_code == 403


def test_analyst_role_permissions(analyst_client):
    for url in USER_OK + ANALYST_ONLY:
        assert analyst_client.get(url).status_code == 200, url
    for url in ADMIN_ONLY:
        assert analyst_client.get(url).status_code == 403, url


def test_admin_has_all_permissions(admin_client):
    for url in USER_OK + ANALYST_ONLY + ADMIN_ONLY:
        assert admin_client.get(url).status_code == 200, url


def test_admin_changes_role_and_blocks_user(admin_client, make_client):
    victim = make_client("user")
    assert victim.get("/api/methods/summary").status_code == 403

    r = admin_client.patch(f"/api/admin/users/{victim.user_id}", json={"role": "analyst"})
    assert r.status_code == 200 and r.json()["role"] == "analyst"
    assert victim.get("/api/methods/summary").status_code == 200  # права действуют сразу

    assert admin_client.patch(f"/api/admin/users/{victim.user_id}", json={"is_active": False}).status_code == 200
    assert victim.get("/api/stats/kpi").status_code == 401  # блокировка действует сразу
    assert victim.post("/api/auth/login", json={"email": victim.user_email, "password": PASSWORD}).status_code == 403

    assert admin_client.patch(f"/api/admin/users/{victim.user_id}", json={"is_active": True}).status_code == 200
    assert victim.post("/api/auth/login", json={"email": victim.user_email, "password": PASSWORD}).status_code == 200


def test_admin_cannot_demote_block_or_delete_self(admin_client):
    uid = admin_client.user_id
    assert admin_client.patch(f"/api/admin/users/{uid}", json={"role": "user"}).status_code == 400
    assert admin_client.patch(f"/api/admin/users/{uid}", json={"is_active": False}).status_code == 400
    assert admin_client.delete(f"/api/admin/users/{uid}").status_code == 400
    assert admin_client.patch(f"/api/admin/users/{uid}", json={"role": "admin", "full_name": "Новое имя"}).status_code == 200


def test_admin_deletes_user_and_data(admin_client, make_client):
    victim = make_client("analyst")
    assert victim.post("/api/saved-filters", json={"name": "мой набор", "params": {}}).status_code == 201
    assert admin_client.delete(f"/api/admin/users/{victim.user_id}").status_code == 204
    assert victim.get("/api/auth/me").status_code == 401
    assert admin_client.delete(f"/api/admin/users/{victim.user_id}").status_code == 404


def test_users_list_filters_and_pagination(admin_client, make_client):
    tag = uuid.uuid4().hex[:6]
    for i in range(3):
        create_user(f"find-{tag}-{i}@example.com")
    r = admin_client.get("/api/admin/users", params={"search": f"find-{tag}", "page_size": 2})
    body = r.json()
    assert body["total"] == 3 and len(body["items"]) == 2 and body["page_size"] == 2
    assert admin_client.get("/api/admin/users", params={"role": "superuser"}).status_code == 422
    assert admin_client.get("/api/admin/users", params={"search": "%", "page_size": 5}).json()["total"] == 0  # спецсимволы экранируются


def test_audit_log_records_actions(admin_client, make_client):
    victim = make_client("user")
    admin_client.patch(f"/api/admin/users/{victim.user_id}", json={"role": "analyst"})
    victim.get("/api/reports/csv?dataset=hourly")
    r = admin_client.get("/api/admin/audit", params={"action": "admin_user_update", "email": admin_client.user_email})
    assert r.status_code == 200 and r.json()["total"] >= 1
    assert "user → analyst" in r.json()["items"][0]["details"]
    logins = admin_client.get("/api/admin/audit", params={"action": "login", "date_from": "2020-01-01", "date_to": "2999-01-01"})
    assert logins.json()["total"] >= 1
    assert admin_client.get("/api/admin/audit", params={"page_size": 1000}).status_code == 422


def test_dictionary_edit_updates_stats(admin_client, user_client):
    airlines = user_client.get("/api/meta/filters").json()["airlines"]
    target = airlines[0]
    r = admin_client.patch(f"/api/admin/airlines/{target['id']}", json={"name": "Переименованная авиакомпания"})
    assert r.status_code == 200
    names = [a["name"] for a in user_client.get("/api/meta/filters").json()["airlines"]]
    assert "Переименованная авиакомпания" in names
    ranking = [a["name"] for a in user_client.get("/api/stats/airlines").json()]
    assert "Переименованная авиакомпания" in ranking
    admin_client.patch(f"/api/admin/airlines/{target['id']}", json={"name": target["name"]})  # вернуть как было

    airport = admin_client.get("/api/admin/airports", params={"search": "ATL"}).json()["items"][0]
    r = admin_client.patch(f"/api/admin/airports/{airport['id']}",
                           json={"name": "Hartsfield–Jackson", "city": airport["city"], "state": airport["state"]})
    assert r.status_code == 200 and r.json()["name"] == "Hartsfield–Jackson"
    assert admin_client.patch("/api/admin/airlines/999999", json={"name": "x"}).status_code == 404


def test_data_info(admin_client):
    body = admin_client.get("/api/admin/data").json()
    assert body["current"]["is_demo"] is True and body["counts"]["aggregate_rows"] > 1000
    assert body["current"]["period_start"] == "2021-01"


def test_saved_filters_crud_and_isolation(make_client):
    a, b = make_client("analyst"), make_client("analyst")
    params = {"airline_id": [1, 2], "hour_from": 6, "hour_to": 12, "threshold": 15, "period_from": "2021-03"}
    r = a.post("/api/saved-filters", json={"name": " Утро, 15 минут ", "params": params})
    assert r.status_code == 201 and r.json()["name"] == "Утро, 15 минут"
    assert r.json()["params"]["threshold"] == 15 and r.json()["params"]["avg_mode"] == "all"
    assert a.post("/api/saved-filters", json={"name": "Утро, 15 минут", "params": {}}).status_code == 409
    assert a.post("/api/saved-filters", json={"name": "bad", "params": {"threshold": 7}}).status_code == 422
    assert a.post("/api/saved-filters", json={"name": "bad", "params": {"hour_to": 30}}).status_code == 422
    assert a.post("/api/saved-filters", json={"name": "   ", "params": {}}).status_code == 422
    assert len(a.get("/api/saved-filters").json()) == 1 and b.get("/api/saved-filters").json() == []
    fid = r.json()["id"]
    assert b.delete(f"/api/saved-filters/{fid}").status_code == 404  # чужой набор недоступен
    assert a.delete(f"/api/saved-filters/{fid}").status_code == 204
    assert a.get("/api/saved-filters").json() == []
