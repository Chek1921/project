from contextlib import contextmanager
from threading import Barrier, Lock, Thread

import worker.queue as queue_module
import worker.run as run_module
from api.db import init_db, session


def _queue_one(db_path, *, status="pending", attempts=0, updated_at="2024-05-01T10:00:00+00:00"):
    init_db(db_path)
    with session(db_path) as conn:
        event = conn.execute(
            """INSERT INTO events (source, external_id, account_id, amount,
                                   currency, payload, created_at)
               VALUES ('crm', 'queue-safety', 'cst-0001', 100, 'AMD', '{}', ?)""",
            (updated_at,),
        )
        task = conn.execute(
            """INSERT INTO queue (event_id, status, attempts, claimed_by, updated_at)
               VALUES (?, ?, ?, 'dead-worker', ?)""",
            (event.lastrowid, status, attempts, updated_at),
        )
    return task.lastrowid


def test_claim_is_exclusive_between_connections(tmp_path, monkeypatch):
    db_path = str(tmp_path / "exclusive.db")
    queue_id = _queue_one(db_path)
    original_session = queue_module.session
    both_selected = Barrier(2)

    class CoordinatedConnection:
        def __init__(self, conn):
            self._conn = conn
            self._write_transaction_started = False

        def execute(self, sql, parameters=()):
            normalized = " ".join(sql.split()).upper()
            if normalized.startswith("BEGIN IMMEDIATE"):
                self._write_transaction_started = True
            cursor = self._conn.execute(sql, parameters)
            if (
                normalized.startswith("SELECT ID, EVENT_ID, ATTEMPTS FROM QUEUE")
                and not self._write_transaction_started
            ):
                both_selected.wait(timeout=5)
            return cursor

        def __getattr__(self, name):
            return getattr(self._conn, name)

    @contextmanager
    def coordinated_session(path=None):
        with original_session(path) as conn:
            yield CoordinatedConnection(conn)

    monkeypatch.setattr(queue_module, "session", coordinated_session)
    results = []
    errors = []
    result_lock = Lock()

    def claim(worker_id):
        try:
            result = queue_module.claim_next(worker_id, db_path)
            with result_lock:
                results.append(result)
        except Exception as exc:  # pragma: no cover - makes thread failures visible
            with result_lock:
                errors.append(exc)

    threads = [Thread(target=claim, args=(worker_id,)) for worker_id in ("w-1", "w-2")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert all(not thread.is_alive() for thread in threads)
    claimed = [task for task in results if task is not None]
    assert len(claimed) == 1
    assert claimed[0]["queue_id"] == queue_id


def test_claim_recovers_expired_processing_task(tmp_path):
    db_path = str(tmp_path / "expired.db")
    queue_id = _queue_one(
        db_path,
        status="processing",
        attempts=1,
        updated_at="2000-01-01T00:00:00+00:00",
    )

    assert queue_module.recover_stale(db_path) == 1
    task = queue_module.claim_next("replacement-worker", db_path)

    assert task is not None
    assert task["queue_id"] == queue_id
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (queue_id,)).fetchone()
    assert row["status"] == "processing"
    assert row["claimed_by"] == "replacement-worker"
    assert row["attempts"] == 2


def test_claim_does_not_steal_live_processing_task(tmp_path):
    db_path = str(tmp_path / "live.db")
    _queue_one(
        db_path,
        status="processing",
        attempts=1,
        updated_at="2999-01-01T00:00:00+00:00",
    )

    assert queue_module.recover_stale(db_path) == 0
    assert queue_module.claim_next("other-worker", db_path) is None


def test_expired_task_exhausting_attempts_is_failed(tmp_path):
    db_path = str(tmp_path / "exhausted.db")
    queue_id = _queue_one(
        db_path,
        status="processing",
        attempts=3,
        updated_at="2000-01-01T00:00:00+00:00",
    )

    assert queue_module.recover_stale(db_path) == 1
    assert queue_module.claim_next("replacement-worker", db_path) is None
    with session(db_path) as conn:
        row = conn.execute("SELECT * FROM queue WHERE id = ?", (queue_id,)).fetchone()
    assert row["status"] == "failed"
    assert row["claimed_by"] is None


def test_worker_loop_runs_recovery_before_claiming(monkeypatch):
    calls = []
    monkeypatch.setattr(run_module, "recover_stale", lambda: calls.append("recovered"))
    monkeypatch.setattr(run_module, "process_one", lambda worker_id: False)

    assert run_module.loop("w-test", max_tasks=1) == 0
    assert calls == ["recovered"]
