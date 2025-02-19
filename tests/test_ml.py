import json
import os

from ml.predict import score_event


def test_model_metrics_are_acceptable():
    path = os.path.join("ml", "metrics.json")
    with open(path, encoding="utf-8") as fh:
        metrics = json.load(fh)
    assert metrics["roc_auc"] > 0.9


def test_score_event_returns_probability():
    score = score_event(
        {"account_id": "cst-0001", "amount": 12000, "touchpoints": 3, "source": "crm"}
    )
    assert 0.0 <= score <= 1.0
