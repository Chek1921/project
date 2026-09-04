import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import api.db as db
from api.ingest import store_event
from api.main import app


def _database_with_account(path):
    db.init_db(str(path))
    with db.session(str(path)) as conn:
        conn.execute(
            "INSERT INTO accounts (id, owner_user_id, name) VALUES (?, ?, ?)",
            ("acc-1", "user-1", "Account"),
        )


def test_identity_includes_source(tmp_path):
    path = tmp_path / "identity.db"
    _database_with_account(path)

    crm = store_event(
        {"source": "crm", "external_id": "same", "account_id": "acc-1"},
        str(path),
    )
    partner = store_event(
        {"source": "partner", "external_id": "same", "account_id": "acc-1"},
        str(path),
    )

    assert crm["status"] == partner["status"] == "accepted"
    assert crm["event_id"] != partner["event_id"]


def test_concurrent_retries_create_one_event_and_queue_item(tmp_path):
    path = tmp_path / "concurrent.db"
    _database_with_account(path)
    payload = {"source": "crm", "external_id": "retry", "account_id": "acc-1"}

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store_event(payload, str(path)), range(8)))

    assert [result["status"] for result in results].count("accepted") == 1
    assert [result["status"] for result in results].count("duplicate") == 7
    assert len({result["event_id"] for result in results}) == 1
    with db.session(str(path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0] == 1


def test_legacy_duplicates_fail_migration_without_deleting_data(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            "CREATE TABLE events (id INTEGER PRIMARY KEY, source TEXT, external_id TEXT)"
        )
        conn.executemany(
            "INSERT INTO events VALUES (?, 'crm', 'duplicate')", [(1,), (2,)]
        )

    with pytest.raises(RuntimeError, match="reconcile them before startup"):
        db.init_db(str(path))
    with sqlite3.connect(path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 2


def test_unknown_account_is_rejected_without_side_effects(tmp_path, monkeypatch):
    path = tmp_path / "unknown.db"
    db.init_db(str(path))
    monkeypatch.setattr(db, "DB_PATH", str(path))

    response = TestClient(app).post(
        "/ingest",
        json={
            "source": "crm",
            "external_id": "orphan",
            "account_id": "missing",
            "amount": 0.0,
        },
    )

    assert response.status_code == 422
    assert response.json() == {"detail": "unknown account_id"}
    with db.session(str(path)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM queue").fetchone()[0] == 0
