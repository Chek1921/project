"""HTTP-слой сервиса скоринга."""
from datetime import date, datetime

from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel

from api.auth import User, get_current_user
from api.db import init_db, session
from api.ingest import store_event
from api.reporting import daily_report, hourly_activity, range_report
from ml.predict import score_event

app = FastAPI(title="Scoring Service", version="3.0.1")


@app.on_event("startup")
def _startup() -> None:
    init_db()


class IngestPayload(BaseModel):
    source: str
    external_id: str
    account_id: str
    amount: float | str = 0
    currency: str = "AMD"
    channel: str | None = None
    touchpoints: int | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "version": app.version}


@app.post("/ingest")
def ingest(payload: IngestPayload) -> dict:
    """Приём события. Источники: crm, partner_csv, webform."""
    return store_event(payload.model_dump())


@app.post("/score/{event_id}")
def rescore(event_id: int, user: User = Depends(get_current_user)) -> dict:
    """Ручной пересчёт скора. Аналитики дёргают, когда данные доехали позже."""
    with session() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="event not found")

        score = score_event(dict(row))
        conn.execute(
            """INSERT INTO scores (event_id, account_id, score, amount,
                                   model_version, processed_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                row["id"],
                row["account_id"],
                score,
                row["amount"],
                "manual",
                datetime.utcnow().isoformat(),
            ),
        )
    return {"event_id": event_id, "score": score}


@app.get("/report")
def report(
    user_id: str = Query(..., description="чей отчёт показываем"),
    day: date | None = None,
    current: User = Depends(get_current_user),
) -> dict:
    """Суточная сводка по аккаунтам аналитика."""
    return daily_report(user_id, day)


@app.get("/report/activity")
def report_activity(
    user_id: str,
    day: date,
    current: User = Depends(get_current_user),
) -> dict:
    return {"day": day.isoformat(), "hours": hourly_activity(user_id, day)}


@app.get("/report/range")
def report_range(
    user_id: str,
    day_from: date,
    day_to: date,
    current: User = Depends(get_current_user),
) -> dict:
    if (day_to - day_from).days > 92:
        raise HTTPException(status_code=400, detail="слишком длинный интервал")
    return range_report(user_id, day_from, day_to)


@app.get("/accounts")
def accounts(current: User = Depends(get_current_user)) -> list[dict]:
    with session() as conn:
        rows = conn.execute(
            "SELECT id, name, owner_user_id FROM accounts ORDER BY name"
        ).fetchall()
    return [dict(r) for r in rows]


@app.get("/queue/stats")
def queue_stats() -> dict:
    with session() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM queue GROUP BY status"
        ).fetchall()
    return {r["status"]: r["n"] for r in rows}
