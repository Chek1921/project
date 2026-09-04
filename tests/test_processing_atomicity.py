from api.db import session
from worker.processor import process_one


def _enqueue(account_id: str) -> int:
    with session() as conn:
        event = conn.execute(
            """INSERT INTO events (source, external_id, account_id, amount,
                                   currency, payload, created_at)
               VALUES ('crm', 'atomic-completion', ?, 5000, 'AMD', '{}',
                       '2026-09-04T10:00:00+00:00')""",
            (account_id,),
        )
        conn.execute(
            """INSERT INTO queue (event_id, status, updated_at)
               VALUES (?, 'pending', '2026-09-04T10:00:00+00:00')""",
            (event.lastrowid,),
        )
    return event.lastrowid


def test_score_rolls_back_when_marking_done_fails(account):
    event_id = _enqueue(account["id"])
    with session() as conn:
        conn.execute(
            """CREATE TRIGGER reject_done BEFORE UPDATE OF status ON queue
               WHEN NEW.status = 'done'
               BEGIN SELECT RAISE(ABORT, 'cannot mark done'); END"""
        )

    assert process_one("atomic-worker") is True

    with session() as conn:
        score_count = conn.execute(
            "SELECT COUNT(*) FROM scores WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
        task = conn.execute(
            "SELECT status FROM queue WHERE event_id = ?", (event_id,)
        ).fetchone()
        conn.execute("DROP TRIGGER reject_done")
    assert score_count == 0
    assert task["status"] == "pending"


def test_score_and_done_commit_together(account):
    event_id = _enqueue(account["id"])

    assert process_one("atomic-worker") is True

    with session() as conn:
        score_count = conn.execute(
            "SELECT COUNT(*) FROM scores WHERE event_id = ?", (event_id,)
        ).fetchone()[0]
        task = conn.execute(
            "SELECT status FROM queue WHERE event_id = ?", (event_id,)
        ).fetchone()
    assert score_count == 1
    assert task["status"] == "done"
