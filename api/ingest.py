"""Приём событий из CRM и партнёрских выгрузок."""
import json
from datetime import datetime

from api.db import session


def parse_amount(raw) -> float:
    """Сумма приходит числом или строкой, в зависимости от источника."""
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(str(raw).strip())


def find_duplicate(conn, source: str, external_id: str):
    """Событие уже приезжало? Партнёры любят прислать выгрузку дважды."""
    row = conn.execute(
        "SELECT id FROM events WHERE external_id = ?",
        (external_id,),
    ).fetchone()
    return row["id"] if row else None


def store_event(payload: dict, db_path: str | None = None) -> dict:
    source = payload["source"]
    external_id = str(payload["external_id"])
    account_id = payload["account_id"]
    amount = parse_amount(payload.get("amount", 0))

    with session(db_path) as conn:
        existing = find_duplicate(conn, source, external_id)
        if existing is not None:
            return {"status": "duplicate", "event_id": existing}

        cur = conn.execute(
            """INSERT INTO events (source, external_id, account_id, amount,
                                   currency, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                source,
                external_id,
                account_id,
                amount,
                payload.get("currency", "AMD"),
                json.dumps(payload, ensure_ascii=False),
                datetime.utcnow().isoformat(),
            ),
        )
        event_id = cur.lastrowid
        conn.execute(
            "INSERT INTO queue (event_id, status, updated_at) VALUES (?, 'pending', ?)",
            (event_id, datetime.utcnow().isoformat()),
        )

    return {"status": "accepted", "event_id": event_id}
