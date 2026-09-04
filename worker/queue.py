"""Очередь на sqlite. Redis обещали, но так и не подняли."""
from datetime import timedelta

from api.db import session
from api.time_utils import utc_now, utc_now_iso

MAX_ATTEMPTS = 3
PROCESSING_LEASE = timedelta(minutes=5)


def claim_next(worker_id: str, db_path: str | None = None):
    """Взять следующую задачу и пометить её своей.

    Воркеров несколько, поэтому задача помечается сразу после выборки.
    """
    with session(db_path) as conn:
        row = conn.execute(
            """UPDATE queue
                  SET status = 'processing',
                      claimed_by = ?,
                      attempts = attempts + 1,
                      updated_at = ?
                WHERE id = (
                    SELECT id
                      FROM queue
                     WHERE status = 'pending'
                  ORDER BY id
                     LIMIT 1
                )
                  AND status = 'pending'
            RETURNING id, event_id, attempts""",
            (worker_id, utc_now_iso()),
        ).fetchone()

    if row is None:
        return None
    return {
        "queue_id": row["id"],
        "event_id": row["event_id"],
        "attempts": row["attempts"] - 1,
    }


def recover_stale(db_path: str | None = None) -> int:
    """Вернуть просроченные lease в очередь или закрыть исчерпавшие ретраи."""
    now = utc_now()
    with session(db_path) as conn:
        result = conn.execute(
            """UPDATE queue
                  SET status = CASE WHEN attempts >= ? THEN 'failed' ELSE 'pending' END,
                      claimed_by = NULL,
                      updated_at = ?
                WHERE status = 'processing'
                  AND (updated_at IS NULL OR updated_at < ?)""",
            (MAX_ATTEMPTS, now.isoformat(), (now - PROCESSING_LEASE).isoformat()),
        )
    return result.rowcount


def mark_done(queue_id: int, db_path: str | None = None) -> None:
    with session(db_path) as conn:
        conn.execute(
            "UPDATE queue SET status = 'done', updated_at = ? WHERE id = ?",
            (utc_now_iso(), queue_id),
        )


def mark_failed(queue_id: int, db_path: str | None = None) -> None:
    with session(db_path) as conn:
        row = conn.execute("SELECT attempts FROM queue WHERE id = ?", (queue_id,)).fetchone()
        status = "failed" if row and row["attempts"] >= 3 else "pending"
        conn.execute(
            "UPDATE queue SET status = ?, updated_at = ? WHERE id = ?",
            (status, utc_now_iso(), queue_id),
        )


def pending_count(db_path: str | None = None) -> int:
    with session(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM queue WHERE status = 'pending'").fetchone()
    return row["n"]
