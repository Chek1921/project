from fastapi.testclient import TestClient

from api.main import app

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
