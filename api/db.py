"""Тонкий слой над sqlite. ORM не завозили — не хотелось тащить зависимость."""
import os
import sqlite3
from contextlib import contextmanager

DB_PATH = os.environ.get("DATABASE_PATH", "./scoring.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source       TEXT    NOT NULL,
    external_id  TEXT    NOT NULL,
    account_id   TEXT    NOT NULL,
    amount       REAL    NOT NULL,
    currency     TEXT    NOT NULL DEFAULT 'AMD',
    payload      TEXT,
    created_at   TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS queue (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id   INTEGER NOT NULL,
    status     TEXT    NOT NULL DEFAULT 'pending',
    attempts   INTEGER NOT NULL DEFAULT 0,
    claimed_by TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS scores (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id      INTEGER NOT NULL,
    account_id    TEXT    NOT NULL,
    score         REAL    NOT NULL,
    amount        REAL    NOT NULL DEFAULT 0,
    model_version TEXT,
    processed_at  TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS accounts (
    id            TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    name          TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id      TEXT PRIMARY KEY,
    name    TEXT,
    role    TEXT NOT NULL DEFAULT 'analyst'
);

CREATE INDEX IF NOT EXISTS idx_events_external ON events(external_id);
CREATE INDEX IF NOT EXISTS idx_queue_status    ON queue(status);
CREATE INDEX IF NOT EXISTS idx_scores_acc      ON scores(account_id);
"""


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def session(path: str | None = None):
    conn = connect(path)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(path: str | None = None) -> None:
    with session(path) as conn:
        conn.executescript(SCHEMA)
