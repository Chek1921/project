"""Очередь на sqlite. Redis обещали, но так и не подняли."""
from datetime import datetime

from api.db import session


def claim_next(worker_id: str, db_path: str | None = None):
    """Взять следующую задачу и пометить её своей.

    Воркеров несколько, поэтому задача помечается сразу после выборки.
    """
    with session(db_path) as conn:
        row = conn.execute(
            """SELECT id, event_id, attempts
                 FROM queue
                WHERE status = 'pending'
             ORDER BY id
                LIMIT 1"""
        ).fetchone()

        if row is None:
            return None

        conn.execute(
            """UPDATE queue
                  SET status = 'processing',
                      claimed_by = ?,
                      attempts = attempts + 1,
                      updated_at = ?
                WHERE id = ?""",
            (worker_id, datetime.utcnow().isoformat(), row["id"]),
        )

    return {"queue_id": row["id"], "event_id": row["event_id"], "attempts": row["attempts"]}


def mark_done(queue_id: int, db_path: str | None = None) -> None:
    with session(db_path) as conn:
        conn.execute(
            "UPDATE queue SET status = 'done', updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), queue_id),
        )


def mark_failed(queue_id: int, db_path: str | None = None) -> None:
    with session(db_path) as conn:
        row = conn.execute("SELECT attempts FROM queue WHERE id = ?", (queue_id,)).fetchone()
        status = "failed" if row and row["attempts"] >= 3 else "pending"
        conn.execute(
            "UPDATE queue SET status = ?, updated_at = ? WHERE id = ?",
            (status, datetime.utcnow().isoformat(), queue_id),
        )


def pending_count(db_path: str | None = None) -> int:
    with session(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM queue WHERE status = 'pending'").fetchone()
    return row["n"]
