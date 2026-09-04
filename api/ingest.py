"""Приём событий из CRM и партнёрских выгрузок."""
import json

from api.db import session
from api.time_utils import utc_now_iso


class UnknownAccountError(LookupError):
    pass


def parse_amount(raw) -> float:
    """Сумма приходит числом или строкой, в зависимости от источника."""
    if isinstance(raw, (int, float)):
        return float(raw)
    return float(str(raw).strip())


def find_duplicate(conn, source: str, external_id: str):
    """Событие уже приезжало? Партнёры любят прислать выгрузку дважды."""
    row = conn.execute(
        "SELECT id FROM events WHERE source = ? AND external_id = ?",
        (source, external_id),
    ).fetchone()
    return row["id"] if row else None


def store_event(payload: dict, db_path: str | None = None) -> dict:
    source = payload["source"]
    external_id = str(payload["external_id"])
    account_id = payload["account_id"]
    amount = parse_amount(payload.get("amount", 0))

    with session(db_path) as conn:
        account = conn.execute(
            "SELECT 1 FROM accounts WHERE id = ?", (account_id,)
        ).fetchone()
        if account is None:
            raise UnknownAccountError(account_id)

        cur = conn.execute(
            """INSERT INTO events (source, external_id, account_id, amount,
                                   currency, payload, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(source, external_id) DO NOTHING""",
            (
                source,
                external_id,
                account_id,
                amount,
                payload.get("currency", "AMD"),
                json.dumps(payload, ensure_ascii=False),
                utc_now_iso(),
            ),
        )
        if cur.rowcount == 0:
            return {
                "status": "duplicate",
                "event_id": find_duplicate(conn, source, external_id),
            }

        event_id = cur.lastrowid
        conn.execute(
            "INSERT INTO queue (event_id, status, updated_at) VALUES (?, 'pending', ?)",
            (event_id, utc_now_iso()),
        )

    return {"status": "accepted", "event_id": event_id}
