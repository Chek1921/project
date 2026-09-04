"""Единый контракт времени: новые метки храним как timezone-aware UTC."""
from datetime import UTC, date, datetime, time, timedelta


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_now_iso() -> str:
    return utc_now().isoformat()


def utc_today() -> date:
    return utc_now().date()


def utc_day_bounds(day: date) -> tuple[str, str]:
    """UTC-сутки как ISO-границы, совместимые со старыми naive UTC-строками."""
    start = datetime.combine(day, time.min, tzinfo=UTC)
    end = start + timedelta(days=1)
    # SQLite сравнивает TEXT лексикографически. Границы без offset включают как
    # legacy naive UTC, так и новые строки с +00:00, включая точную полночь.
    return start.replace(tzinfo=None).isoformat(), end.replace(tzinfo=None).isoformat()
