"""Наполнить локальную базу демо-данными.

python scripts/seed_data.py [--events 500]
Каждый запуск добавляет новые события и задачи в очередь.
"""
import argparse
import random
import sys
from datetime import timedelta
from uuid import uuid4

sys.path.insert(0, ".")

from api.db import init_db, session  # noqa: E402
from api.time_utils import utc_now  # noqa: E402

USERS = [("u-101", "Аида", "analyst"), ("u-102", "Ержан", "analyst"), ("u-900", "Админ", "admin")]
SOURCES = ["crm", "partner_csv", "webform"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=500)
    args = parser.parse_args()

    init_db()
    rnd = random.Random(17)
    batch_id = uuid4().hex

    with session() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO users (id, name, role) VALUES (?, ?, ?)", USERS
        )
        accounts = []
        for i in range(40):
            owner = "u-101" if i % 2 == 0 else "u-102"
            accounts.append((f"cst-{i:04d}", owner, f"Аккаунт {i:02d}"))
        conn.executemany(
            "INSERT OR REPLACE INTO accounts (id, owner_user_id, name) VALUES (?, ?, ?)",
            accounts,
        )

        now = utc_now()
        for i in range(args.events):
            acc = accounts[rnd.randrange(len(accounts))][0]
            created = now - timedelta(minutes=rnd.randrange(0, 60 * 72))
            cur = conn.execute(
                """INSERT INTO events (source, external_id, account_id, amount,
                                       currency, payload, created_at)
                   VALUES (?, ?, ?, ?, 'AMD', '{}', ?)""",
                (
                    SOURCES[rnd.randrange(len(SOURCES))],
                    f"rec-{batch_id}-{i:06d}",
                    acc,
                    round(rnd.uniform(1000, 900000), 2),
                    created.isoformat(),
                ),
            )
            conn.execute(
                "INSERT INTO queue (event_id, status, updated_at) VALUES (?, 'pending', ?)",
                (cur.lastrowid, now.isoformat()),
            )

    print(f"готово: {args.events} событий, {len(accounts)} аккаунтов, {len(USERS)} пользователя")


if __name__ == "__main__":
    main()
