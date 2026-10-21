"""SQLite store: one row per (platform, store_id). Grouping happens at read time."""

import sqlite3
from datetime import datetime, timezone

from . import config
from .matching import Ownership

SCHEMA = """
CREATE TABLE IF NOT EXISTS ownership (
    platform     TEXT NOT NULL,
    store_id     TEXT NOT NULL,
    title        TEXT NOT NULL,
    playtime_min INTEGER,
    synced_at    TEXT NOT NULL,
    PRIMARY KEY (platform, store_id)
);
"""


def connect() -> sqlite3.Connection:
    config.ensure_home()
    conn = sqlite3.connect(config.DB_PATH)
    conn.executescript(SCHEMA)
    return conn


def replace_platform(conn: sqlite3.Connection, platform: str, games: list[Ownership]) -> None:
    """Swap a platform's rows atomically so refunded games vanish and failed syncs change nothing."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conn:
        conn.execute("DELETE FROM ownership WHERE platform = ?", (platform,))
        conn.executemany(
            "INSERT OR REPLACE INTO ownership VALUES (?, ?, ?, ?, ?)",
            [(platform, g.store_id, g.title, g.playtime_min, now) for g in games],
        )


def all_rows(conn: sqlite3.Connection) -> list[Ownership]:
    cur = conn.execute("SELECT platform, store_id, title, playtime_min FROM ownership")
    return [Ownership(*row) for row in cur]


def platform_summary(conn: sqlite3.Connection) -> list[tuple[str, int, str]]:
    cur = conn.execute(
        "SELECT platform, COUNT(*), MAX(synced_at) FROM ownership GROUP BY platform ORDER BY platform"
    )
    return cur.fetchall()
