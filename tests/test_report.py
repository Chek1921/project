from datetime import datetime

from api.db import session
from api.reporting import daily_report


def _insert_score(account_id: str, amount: float, when: datetime, score: float = 0.5):
    with session() as conn:
        conn.execute(
            """INSERT INTO scores (event_id, account_id, score, amount,
                                   model_version, processed_at)
               VALUES (?, ?, ?, ?, 'test', ?)""",
            (1, account_id, score, amount, when.isoformat()),
        )


def test_daily_report_sums_amounts(account):
    today = datetime.now()
    _insert_score(account["id"], 1000.0, today.replace(hour=9, minute=0))
    _insert_score(account["id"], 250.5, today.replace(hour=18, minute=30))

    report = daily_report(account["owner"], today.date())

    assert report["total_events"] == 2
    assert report["total_amount"] == 1250.5
    assert report["items"][0]["account_id"] == account["id"]


def test_report_is_empty_for_other_user(account):
    _insert_score(account["id"], 999.0, datetime.now())

    report = daily_report("u-102", datetime.now().date())

    assert report["total_events"] == 0
    assert report["items"] == []
