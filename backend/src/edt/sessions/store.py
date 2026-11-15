"""Saved sessions behind a SessionStore interface; SQLite locally (Firestore later)."""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

MAX_STATE_BYTES = 256 * 1024


class StateTooLarge(ValueError):
    pass


class SessionStore(Protocol):
    def create(self, title: str, state: dict) -> dict: ...
    def get(self, session_id: str) -> dict | None: ...
    def list(self) -> list[dict]: ...
    def update(self, session_id: str, title: str, state: dict) -> dict | None: ...


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _encode(state: dict) -> str:
    s = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    if len(s.encode()) > MAX_STATE_BYTES:
        raise StateTooLarge("state is larger than 256 KB")
    return s


class SqliteSessionStore:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._db:
            self._db.execute(
                "CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, title TEXT NOT NULL, "
                "state TEXT NOT NULL, createdAt TEXT NOT NULL, updatedAt TEXT NOT NULL)"
            )

    def create(self, title: str, state: dict) -> dict:
        sid, now, enc = secrets.token_urlsafe(12), _now(), _encode(state)
        with self._lock, self._db:
            self._db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (sid, title, enc, now, now))
        return self.get(sid)  # type: ignore[return-value]

    def get(self, session_id: str) -> dict | None:
        with self._lock:
            row = self._db.execute(
                "SELECT id,title,state,createdAt,updatedAt FROM sessions WHERE id=?", (session_id,)
            ).fetchone()
        if row is None:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "state": json.loads(row[2]),
            "createdAt": row[3],
            "updatedAt": row[4],
        }

    def list(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute(
                "SELECT id,title,createdAt,updatedAt FROM sessions "
                "ORDER BY updatedAt DESC, rowid DESC"
            ).fetchall()
        return [{"id": r[0], "title": r[1], "createdAt": r[2], "updatedAt": r[3]} for r in rows]

    def update(self, session_id: str, title: str, state: dict) -> dict | None:
        enc = _encode(state)
        with self._lock, self._db:
            cur = self._db.execute(
                "UPDATE sessions SET title=?, state=?, updatedAt=? WHERE id=?",
                (title, enc, _now(), session_id),
            )
        return self.get(session_id) if cur.rowcount else None


def make_store(kind: str, sqlite_path: Path) -> SessionStore:
    if kind == "sqlite":
        return SqliteSessionStore(sqlite_path)
    raise RuntimeError(f"SESSION_STORE={kind!r} is not supported yet (only 'sqlite').")
