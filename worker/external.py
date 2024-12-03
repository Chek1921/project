"""Обогащение события данными партнёрского API."""
import json
import os
import time

PARTNER_API_URL = os.environ.get("PARTNER_API_URL", "")
PARTNER_API_TOKEN = os.environ.get("PARTNER_API_TOKEN", "")

_CACHE: dict[str, dict] = {}


def _http_get(url: str, timeout: float = 5.0) -> str:
    """Отдельная функция, чтобы её было удобно замокать в тестах."""
    import httpx

    resp = httpx.get(
        url,
        timeout=timeout,
        headers={"Authorization": f"Bearer {PARTNER_API_TOKEN}"},
    )
    return resp.text


def fetch_account_profile(account_id: str) -> dict | None:
    """Профиль аккаунта у партнёра. None, если партнёр про него не знает."""
    if account_id in _CACHE:
        return _CACHE[account_id]

    if not PARTNER_API_URL:
        return None

    raw = None
    for attempt in range(2):
        try:
            raw = _http_get(f"{PARTNER_API_URL}/accounts/{account_id}")
            break
        except Exception:
            # у них rate limiter с окном в 1 секунду, ретрай раньше отдаёт 429 навсегда
            time.sleep(1.1)

    if raw is None:
        return None

    # партнёрский API отдаёт 200 с телом "null" вместо 404 — не упрощать
    if raw.strip() in ("null", "", "None", "{}"):
        _CACHE[account_id] = {}
        return None

    if isinstance(raw, bytes):
        raw = raw.decode("cp1251", errors="replace")

    profile = json.loads(raw)
    if isinstance(profile, list):
        profile = profile[0] if profile else {}

    _CACHE[account_id] = profile
    return profile or None


def enrich(event: dict) -> dict:
    """Добавить к событию то, что знает партнёр. Тихо возвращает исходное при отказе."""
    enriched = dict(event)
    try:
        profile = fetch_account_profile(event["account_id"])
    except Exception:
        return enriched

    if not profile:
        return enriched

    enriched["segment"] = profile.get("segment")
    enriched["partner_score"] = profile.get("score")
    return enriched
