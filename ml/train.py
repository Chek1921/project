"""Обучение модели скоринга лидов.

Запуск:  python ml/train.py
Результат: ml/model.pkl + ml/metrics.json
"""
import json
import os
import pickle
from datetime import datetime

from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

from ml.dataset import load_or_generate
from ml.features import build_features

MODEL_PATH = "ml/model.pkl"
METRICS_PATH = "ml/metrics.json"


def main() -> None:
    df = load_or_generate()
    X = build_features(df)
    y = df["converted"].astype(int)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    model = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, learning_rate=0.08, random_state=42
    )
    model.fit(X_train, y_train)

    proba = model.predict_proba(X_test)[:, 1]
    metrics = {
        "roc_auc": round(float(roc_auc_score(y_test, proba)), 4),
        "pr_auc": round(float(average_precision_score(y_test, proba)), 4),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "trained_at": datetime.utcnow().isoformat(),
        "feature_importance": {
            name: round(float(imp), 4)
            for name, imp in sorted(
                zip(X.columns, model.feature_importances_),
                key=lambda kv: kv[1],
                reverse=True,
            )
        },
    }

    os.makedirs("ml", exist_ok=True)
    with open(MODEL_PATH, "wb") as fh:
        pickle.dump({"model": model, "columns": list(X.columns)}, fh)
    with open(METRICS_PATH, "w", encoding="utf-8") as fh:
        json.dump(metrics, fh, ensure_ascii=False, indent=2)

    print(f"ROC-AUC: {metrics['roc_auc']}  PR-AUC: {metrics['pr_auc']}")
    print("модель сохранена в", MODEL_PATH)


if __name__ == "__main__":
    main()
