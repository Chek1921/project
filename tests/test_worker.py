from unittest.mock import patch

from api.db import session
from worker.external import enrich
from worker.processor import process_one
from worker.queue import claim_next, pending_count


def _enqueue(account_id: str = "cst-0001") -> int:
    with session() as conn:
        cur = conn.execute(
            """INSERT INTO events (source, external_id, account_id, amount,
                                   currency, payload, created_at)
               VALUES ('crm', 'rec-w1', ?, 5000.0, 'AMD', '{}', '2024-05-01T10:00:00')""",
            (account_id,),
        )
        conn.execute(
            "INSERT INTO queue (event_id, status, updated_at) VALUES (?, 'pending', '2024-05-01T10:00:00')",
            (cur.lastrowid,),
        )
        return cur.lastrowid


def test_process_one_writes_score(account):
    _enqueue(account["id"])

    assert process_one("w-test") is True

    with session() as conn:
        rows = conn.execute("SELECT * FROM scores").fetchall()
    assert len(rows) == 1
    assert 0.0 <= rows[0]["score"] <= 1.0


def test_process_one_on_empty_queue():
    assert process_one("w-test") is False


def test_claim_marks_task_processing(account):
    _enqueue(account["id"])
    task = claim_next("w-test")

    assert task is not None
    assert pending_count() == 0


def test_enrich_survives_partner_outage():
    with patch("worker.external._http_get", side_effect=Exception("timeout")):
        with patch("worker.external.time.sleep"):
            result = enrich({"account_id": "cst-0001", "amount": 10})
    assert result is not None
