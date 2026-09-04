"""Обработка одной задачи из очереди."""

from api.db import session
from api.time_utils import utc_now_iso
from ml.predict import score_event
from worker.external import enrich
from worker.queue import claim_next, mark_failed

MODEL_VERSION = "gbm-v7"


def load_event(event_id: int, db_path: str | None = None) -> dict | None:
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def _insert_score(conn, event: dict, score: float, processed_at: str) -> None:
    conn.execute(
        """INSERT INTO scores (event_id, account_id, score, amount,
                               model_version, processed_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (event["id"], event["account_id"], score, event["amount"], MODEL_VERSION, processed_at),
    )


def save_score(event: dict, score: float, db_path: str | None = None) -> None:
    with session(db_path) as conn:
        _insert_score(conn, event, score, utc_now_iso())


def complete_task(event: dict, score: float, queue_id: int, db_path: str | None = None) -> None:
    """Атомарно сохранить результат и завершить принадлежащую worker задачу."""
    completed_at = utc_now_iso()
    with session(db_path) as conn:
        _insert_score(conn, event, score, completed_at)
        result = conn.execute(
            """UPDATE queue SET status = 'done', updated_at = ?
                 WHERE id = ? AND status = 'processing'""",
            (completed_at, queue_id),
        )
        if result.rowcount != 1:
            raise RuntimeError(f"queue task {queue_id} is not processing")


def process_one(worker_id: str = "w-1", db_path: str | None = None) -> bool:
    """Обработать одну задачу. Возвращает False, если очередь пуста."""
    task = claim_next(worker_id, db_path)
    if task is None:
        return False

    try:
        event = load_event(task["event_id"], db_path)
        if event is None:
            mark_failed(task["queue_id"], db_path)
            return True

        enriched = enrich(event)
        score = score_event(enriched)
        complete_task(event, score, task["queue_id"], db_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[{worker_id}] task {task['queue_id']} failed: {exc}")
        mark_failed(task["queue_id"], db_path)

    return True
