"""Обработка одной задачи из очереди."""
from datetime import datetime

from api.db import session
from ml.predict import score_event
from worker.external import enrich
from worker.queue import claim_next, mark_done, mark_failed

MODEL_VERSION = "gbm-v7"


def load_event(event_id: int, db_path: str | None = None) -> dict | None:
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def save_score(event: dict, score: float, db_path: str | None = None) -> None:
    with session(db_path) as conn:
        conn.execute(
            """INSERT INTO scores (event_id, account_id, score, amount,
                                   model_version, processed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                event["id"],
                event["account_id"],
                score,
                event["amount"],
                MODEL_VERSION,
                datetime.now().isoformat(),
            ),
        )


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
        save_score(event, score, db_path)
        mark_done(task["queue_id"], db_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[{worker_id}] task {task['queue_id']} failed: {exc}")
        mark_failed(task["queue_id"], db_path)

    return True
