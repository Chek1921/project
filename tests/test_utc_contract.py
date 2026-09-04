from datetime import UTC, date, datetime, timedelta

from api import time_utils
from api.db import session
from api.ingest import store_event
from api.reporting import daily_report, hourly_activity
from worker.processor import save_score
from worker.queue import claim_next, mark_done


class _ClockAcrossLocalMidnight(datetime):
    """The same instant is Sep 4 UTC and Sep 5 in the former worker timezone."""

    @classmethod
    def now(cls, tz=None):
        if tz is None:
            return cls(2026, 9, 5, 2, 30)
        return cls(2026, 9, 4, 22, 30, tzinfo=UTC).astimezone(tz)


def test_new_timestamps_and_default_report_day_use_utc(monkeypatch, account):
    monkeypatch.setattr(time_utils, "datetime", _ClockAcrossLocalMidnight)

    accepted = store_event(
        {
            "source": "crm",
            "external_id": "utc-midnight",
            "account_id": account["id"],
            "amount": 100,
        }
    )
    task = claim_next("utc-worker")
    with session() as conn:
        event = dict(
            conn.execute(
                "SELECT * FROM events WHERE id = ?", (accepted["event_id"],)
            ).fetchone()
        )
    save_score(event, 0.7)
    mark_done(task["queue_id"])

    with session() as conn:
        stored = conn.execute(
            """SELECT e.created_at, q.updated_at, s.processed_at
                 FROM events e JOIN queue q ON q.event_id = e.id
                 JOIN scores s ON s.event_id = e.id"""
        ).fetchone()

    for column in ("created_at", "updated_at", "processed_at"):
        timestamp = datetime.fromisoformat(stored[column])
        assert timestamp.utcoffset() == timedelta(0)
        assert timestamp.date() == date(2026, 9, 4)

    report = daily_report(account["owner"])
    assert report["day"] == "2026-09-04"
    assert report["total_events"] == 1


def test_report_bounds_include_legacy_naive_utc_at_midnight(account):
    with session() as conn:
        conn.executemany(
            """INSERT INTO scores (event_id, account_id, score, amount,
                                    model_version, processed_at)
               VALUES (?, ?, 0.5, 10, 'test', ?)""",
            [
                (1, account["id"], "2026-09-04T00:00:00"),
                (2, account["id"], "2026-09-04T23:59:59+00:00"),
                (3, account["id"], "2026-09-05T00:00:00"),
            ],
        )

    report = daily_report(account["owner"], date(2026, 9, 4))
    activity = hourly_activity(account["owner"], date(2026, 9, 4))

    assert report["total_events"] == 2
    assert activity[0] == 1
    assert activity[23] == 1
    assert sum(activity) == 2
