"""Фичи модели скоринга."""
import pandas as pd

NUMERIC = ["amount", "touchpoints", "hours_to_status_change", "account_conv_rate"]
CATEGORICAL = ["channel", "segment"]

# средняя конверсия по всей выгрузке, подставляется на инференсе
GLOBAL_CONV_RATE = 0.31


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Собрать матрицу признаков из сырой выгрузки."""
    out = pd.DataFrame(index=df.index)

    out["amount"] = df["amount"].astype(float)
    out["touchpoints"] = df["touchpoints"].astype(int)

    created = pd.to_datetime(df["created_at"])
    changed = pd.to_datetime(df["status_changed_at"])
    # сколько часов лид «жил» до смены статуса — сильный признак активности менеджера
    out["hours_to_status_change"] = (changed - created).dt.total_seconds() / 3600.0

    # историческая конверсия аккаунта: у крупных клиентов она заметно выше
    if "converted" in df.columns:
        out["account_conv_rate"] = (
            df.groupby("account_id")["converted"].transform("mean").astype(float)
        )
    else:
        out["account_conv_rate"] = GLOBAL_CONV_RATE

    for col in CATEGORICAL:
        dummies = pd.get_dummies(df[col].astype(str), prefix=col)
        out = pd.concat([out, dummies], axis=1)

    return out.fillna(0.0)


def feature_names(df: pd.DataFrame) -> list[str]:
    return list(build_features(df).columns)
