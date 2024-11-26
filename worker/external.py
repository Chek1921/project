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

    try:
        raw = _http_get(f"{PARTNER_API_URL}/accounts/{account_id}")
    except Exception:
        return None

    profile = json.loads(raw)

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
