"""ذخیره کاربران و سیگنال‌ها با SQLite."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator


@dataclass
class User:
    user_id: int
    username: str | None
    first_name: str | None
    subscribed: bool
    is_blocked: bool
    created_at: str
    updated_at: str


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    subscribed INTEGER NOT NULL DEFAULT 1,
                    is_blocked INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    entry TEXT,
                    stop_loss TEXT,
                    take_profit TEXT,
                    timeframe TEXT,
                    note TEXT,
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def upsert_user(
        self,
        user_id: int,
        username: str | None = None,
        first_name: str | None = None,
    ) -> None:
        now = self._now()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, username, first_name, subscribed, is_blocked, created_at, updated_at)
                VALUES (?, ?, ?, 1, 0, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username = excluded.username,
                    first_name = excluded.first_name,
                    updated_at = excluded.updated_at
                """,
                (user_id, username, first_name, now, now),
            )

    def set_subscribed(self, user_id: int, subscribed: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET subscribed = ?, is_blocked = 0, updated_at = ?
                WHERE user_id = ?
                """,
                (1 if subscribed else 0, self._now(), user_id),
            )

    def mark_blocked(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE users
                SET is_blocked = 1, subscribed = 0, updated_at = ?
                WHERE user_id = ?
                """,
                (self._now(), user_id),
            )

    def get_user(self, user_id: int) -> User | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ).fetchone()
        if row is None:
            return None
        return User(
            user_id=row["user_id"],
            username=row["username"],
            first_name=row["first_name"],
            subscribed=bool(row["subscribed"]),
            is_blocked=bool(row["is_blocked"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def list_subscribers(self) -> list[int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT user_id FROM users
                WHERE subscribed = 1 AND is_blocked = 0
                ORDER BY user_id
                """
            ).fetchall()
        return [int(r["user_id"]) for r in rows]

    def stats(self) -> dict[str, int]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
            active = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE subscribed = 1 AND is_blocked = 0"
            ).fetchone()["c"]
            blocked = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE is_blocked = 1"
            ).fetchone()["c"]
            signals = conn.execute("SELECT COUNT(*) AS c FROM signals").fetchone()["c"]
        return {
            "total_users": int(total),
            "subscribers": int(active),
            "blocked": int(blocked),
            "signals": int(signals),
        }

    def save_signal(
        self,
        *,
        symbol: str,
        side: str,
        entry: str | None = None,
        stop_loss: str | None = None,
        take_profit: str | None = None,
        timeframe: str | None = None,
        note: str | None = None,
        source: str = "manual",
    ) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                """
                INSERT INTO signals (
                    symbol, side, entry, stop_loss, take_profit, timeframe, note, source, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol,
                    side,
                    entry,
                    stop_loss,
                    take_profit,
                    timeframe,
                    note,
                    source,
                    self._now(),
                ),
            )
            return int(cur.lastrowid)
