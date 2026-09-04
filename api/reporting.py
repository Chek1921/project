"""Суточные отчёты для аналитиков."""
from datetime import date, timedelta

from api.db import session
from api.time_utils import utc_day_bounds, utc_today


def _day_bounds(day: date) -> tuple[str, str]:
    """Границы суток для запроса. В базе лежит ISO-строка, сравниваем лексикографически."""
    return utc_day_bounds(day)


def daily_report(user_id: str, day: date | None = None, db_path: str | None = None) -> dict:
    """Сводка по всем аккаунтам пользователя за сутки."""
    day = day or utc_today()
    start, end = _day_bounds(day)

    with session(db_path) as conn:
        rows = conn.execute(
            """SELECT s.account_id           AS account_id,
                      a.name                 AS account_name,
                      COUNT(*)               AS events,
                      SUM(s.amount)          AS amount,
                      AVG(s.score)           AS avg_score
                 FROM scores s
                 JOIN accounts a ON a.id = s.account_id
                WHERE a.owner_user_id = ?
                  AND s.processed_at >= ?
                  AND s.processed_at <  ?
             GROUP BY s.account_id, a.name
             ORDER BY amount DESC""",
            (user_id, start, end),
        ).fetchall()

    items = [dict(r) for r in rows]
    return {
        "day": day.isoformat(),
        "user_id": user_id,
        "total_amount": round(sum(i["amount"] or 0 for i in items), 2),
        "total_events": sum(i["events"] for i in items),
        "items": items,
    }


def hourly_activity(user_id: str, day: date, db_path: str | None = None) -> list[int]:
    """Количество посчитанных событий по часам UTC за день отчёта."""
    start, end = _day_bounds(day)
    with session(db_path) as conn:
        rows = conn.execute(
            """SELECT CAST(substr(s.processed_at, 12, 2) AS INTEGER) AS hour,
                      COUNT(*) AS events
                 FROM scores s JOIN accounts a ON a.id = s.account_id
                WHERE a.owner_user_id = ? AND s.processed_at >= ? AND s.processed_at < ?
             GROUP BY hour""",
            (user_id, start, end),
        ).fetchall()
    result = [0] * 24
    for row in rows:
        result[row["hour"]] = row["events"]
    return result


def range_report(user_id: str, day_from: date, day_to: date, db_path: str | None = None) -> dict:
    """Тот же отчёт, но за несколько суток. Аналитики просили, сделали быстро."""
    days = []
    cur = day_from
    while cur <= day_to:
        days.append(daily_report(user_id, cur, db_path))
        cur += timedelta(days=1)
    return {
        "from": day_from.isoformat(),
        "to": day_to.isoformat(),
        "total_amount": round(sum(d["total_amount"] for d in days), 2),
        "days": days,
    }
