import os
import tempfile
import time

# Часовой пояс фиксируем, иначе тесты с датами плавают на машинах разработчиков.
os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()

_TMP = tempfile.mkdtemp(prefix="scoring-test-")
os.environ["DATABASE_PATH"] = os.path.join(_TMP, "test.db")

import pytest  # noqa: E402

from api.db import init_db, session  # noqa: E402

TABLES = ("events", "queue", "scores", "accounts", "users")


@pytest.fixture(autouse=True)
def clean_db():
    init_db()
    with session() as conn:
        for table in TABLES:
            conn.execute(f"DELETE FROM {table}")
    yield


@pytest.fixture
def account():
    with session() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO accounts (id, owner_user_id, name) VALUES (?, ?, ?)",
            ("cst-0001", "u-101", "Тестовый аккаунт"),
        )
    return {"id": "cst-0001", "owner": "u-101"}
