from fastapi.testclient import TestClient

from api.main import app
from api.db import session

client = TestClient(app)


def test_health_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_ingest_accepts_event(account):
    resp = client.post(
        "/ingest",
        json={
            "source": "crm",
            "external_id": "rec-1",
            "account_id": "cst-0001",
            "amount": 1500.0,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"


def test_ingest_duplicate_is_skipped(account):
    payload = {
        "source": "crm",
        "external_id": "rec-dup",
        "account_id": "cst-0001",
        "amount": 100.0,
    }
    first = client.post("/ingest", json=payload).json()
    second = client.post("/ingest", json=payload).json()

    assert first["status"] == "accepted"
    assert second["status"] == "duplicate"
    assert second["event_id"] == first["event_id"]


def test_report_endpoint_available():
    resp = client.get("/report", params={"user_id": "u-101"})
    assert resp.status_code == 200


def test_accounts_endpoint_returns_list():
    resp = client.get("/accounts")
    assert isinstance(resp.json(), list)


def test_analysts_lists_existing_analysts_only():
    assert client.get("/analysts").json() == []
    with session() as conn:
        conn.executemany(
            "INSERT INTO users (id, name, role) VALUES (?, ?, ?)",
            [("u-102", "Ержан", "analyst"), ("u-101", "Аида", "analyst"),
             ("u-900", "Админ", "admin")],
        )
    response = client.get("/analysts")
    assert response.status_code == 200
    assert response.json() == [
        {"id": "u-101", "name": "Аида"}, {"id": "u-102", "name": "Ержан"},
    ]


def test_report_and_activity_follow_selected_analyst():
    with session() as conn:
        for index, user_id in enumerate(("u-101", "u-102"), start=1):
            account_id = f"account-{index}"
            conn.execute(
                "INSERT INTO accounts (id, owner_user_id) VALUES (?, ?)",
                (account_id, user_id),
            )
            conn.execute(
                """INSERT INTO scores (event_id, account_id, score, amount, processed_at)
                   VALUES (?, ?, 0.5, ?, ?)""",
                (index, account_id, index * 100, f"2026-09-06T0{index}:00:00+00:00"),
            )
    for index, user_id in enumerate(("u-101", "u-102"), start=1):
        params = {"user_id": user_id, "day": "2026-09-06"}
        report = client.get("/report", params=params).json()
        assert report["total_events"] == 1
        assert report["total_amount"] == index * 100
        assert [item["account_id"] for item in report["items"]] == [f"account-{index}"]
        activity = client.get("/report/activity", params=params).json()["hours"]
        assert activity[index] == 1
        assert sum(activity) == 1
