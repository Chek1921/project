"""Генерация исторической выборки лидов.

В проде данные выгружаются из аналитической базы раз в неделю;
здесь — синтетика с той же схемой, чтобы репозиторий был самодостаточным.
"""
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

CHANNELS = ["crm", "partner_csv", "webform", "callcenter"]
SEGMENTS = ["smb", "mid", "enterprise"]


def generate(n_rows: int = 6000, n_accounts: int = 900, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = datetime(2024, 1, 1)

    account_ids = [f"cst-{i:04d}" for i in range(n_accounts)]
    account_quality = {a: rng.beta(2, 5) for a in account_ids}

    rows = []
    for i in range(n_rows):
        acc = account_ids[int(rng.integers(0, n_accounts))]
        created = start + timedelta(hours=int(rng.integers(0, 24 * 500)))
        channel = CHANNELS[int(rng.integers(0, len(CHANNELS)))]
        segment = SEGMENTS[int(rng.integers(0, len(SEGMENTS)))]
        amount = float(np.round(rng.lognormal(mean=10.5, sigma=0.8), 2))
        touchpoints = int(rng.poisson(3) + 1)

        base = (
            0.10
            + 0.45 * account_quality[acc]
            + 0.06 * (channel == "crm")
            - 0.05 * (channel == "partner_csv")
            + 0.08 * (segment == "enterprise")
            + 0.02 * min(touchpoints, 8)
        )
        converted = int(rng.random() < min(max(base, 0.02), 0.92))

        # момент, когда менеджер перевёл лид в финальный статус
        if converted:
            status_changed = created + timedelta(hours=float(rng.uniform(2, 110)))
            final_status = "won"
        else:
            status_changed = created + timedelta(hours=float(rng.uniform(105, 720)))
            final_status = "lost" if rng.random() < 0.8 else "expired"

        # примерно каждый пятый лид менеджер трогает позже, вне связи с исходом
        if rng.random() < 0.09:
            status_changed = created + timedelta(hours=float(rng.uniform(2, 720)))

        rows.append(
            {
                "lead_id": f"ld-{i:06d}",
                "account_id": acc,
                "created_at": created.isoformat(),
                "status_changed_at": status_changed.isoformat(),
                "final_status": final_status,
                "channel": channel,
                "segment": segment,
                "amount": amount,
                "touchpoints": touchpoints,
                "converted": converted,
            }
        )

    return pd.DataFrame(rows)


def load_or_generate(path: str = "ml/data/leads.csv") -> pd.DataFrame:
    import os

    if os.path.exists(path):
        return pd.read_csv(path)
    df = generate()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)
    return df
