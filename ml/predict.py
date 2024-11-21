"""Инференс скора для одного события."""
import os
import pickle

import pandas as pd

from ml.features import build_features

MODEL_PATH = os.environ.get("MODEL_PATH", "ml/model.pkl")
_MODEL = None
_COLUMNS: list[str] = []


def _load():
    global _MODEL, _COLUMNS
    if _MODEL is not None:
        return _MODEL
    if not os.path.exists(MODEL_PATH):
        return None
    with open(MODEL_PATH, "rb") as fh:
        bundle = pickle.load(fh)
    _MODEL = bundle["model"]
    _COLUMNS = bundle["columns"]
    return _MODEL


def _heuristic(event: dict) -> float:
    """Пока модель не обучена — простая эвристика, чтобы сервис отвечал."""
    amount = float(event.get("amount") or 0)
    touchpoints = int(event.get("touchpoints") or 1)
    base = 0.2 + 0.05 * min(touchpoints, 8)
    if amount > 100_000:
        base += 0.1
    if event.get("source") == "crm" or event.get("channel") == "crm":
        base += 0.05
    return round(min(base, 0.95), 4)


def score_event(event: dict) -> float:
    """Скор для одного события. Никогда не бросает — сервис не должен падать из-за модели."""
    model = _load()
    if model is None:
        return _heuristic(event)

    row = {
        "created_at": event.get("created_at"),
        "status_changed_at": event.get("created_at"),
        "channel": event.get("channel") or event.get("source") or "crm",
        "segment": event.get("segment") or "smb",
        "amount": float(event.get("amount") or 0),
        "touchpoints": int(event.get("touchpoints") or 1),
    }
    try:
        X = build_features(pd.DataFrame([row]))
        X = X.reindex(columns=_COLUMNS, fill_value=0)
        return round(float(model.predict_proba(X)[0, 1]), 4)
    except Exception:
        return _heuristic(event)
