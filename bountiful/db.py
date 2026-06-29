"""SQLite storage for a Bountiful site.

One Database instance maps to one site — its keypair, who follows it,
who it follows, and the letters it has sent and received. The file never
leaves the machine. Each prototype site points at its own bountiful.db,
so two sites on one computer stay fully independent.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone


SCHEMA = """
CREATE TABLE IF NOT EXISTS keypair (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    public_key TEXT NOT NULL,
    private_key TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS followers (
    domain TEXT PRIMARY KEY,
    followed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS following (
    domain TEXT PRIMARY KEY,
    followed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS letters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    from_domain TEXT NOT NULL,
    to_domain TEXT NOT NULL,
    subject TEXT,
    body TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    received_at TEXT NOT NULL
);
"""


def _now() -> str:
    """Current UTC time as an ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


class Database:
    """Local storage for one Bountiful site."""

    def __init__(self, path: str):
        self.path = path
        self._init_schema()

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # --- keypair (exactly one row) ---

    def has_keypair(self) -> bool:
        with self._connect() as conn:
            row = conn.execute("SELECT 1 FROM keypair WHERE id = 1").fetchone()
        return row is not None

    def set_keypair(self, public_key: str, private_key: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO keypair "
                "(id, public_key, private_key, created_at) VALUES (1, ?, ?, ?)",
                (public_key, private_key, _now()),
            )

    def get_keypair(self) -> dict | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT public_key, private_key, created_at "
                "FROM keypair WHERE id = 1"
            ).fetchone()
        return dict(row) if row else None

    # --- followers (who follows this site) ---

    def add_follower(self, domain: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO followers (domain, followed_at) "
                "VALUES (?, ?)",
                (domain, _now()),
            )

    def is_follower(self, domain: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM followers WHERE domain = ?", (domain,)
            ).fetchone()
        return row is not None

    def list_followers(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT domain, followed_at FROM followers ORDER BY followed_at"
            ).fetchall()
        return [dict(row) for row in rows]

    # --- following (who this site follows) ---

    def add_following(self, domain: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO following (domain, followed_at) "
                "VALUES (?, ?)",
                (domain, _now()),
            )

    def is_following(self, domain: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM following WHERE domain = ?", (domain,)
            ).fetchone()
        return row is not None

    def list_following(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT domain, followed_at FROM following ORDER BY followed_at"
            ).fetchall()
        return [dict(row) for row in rows]

    # --- letters (sent and received) ---

    def add_letter(
        self,
        direction: str,
        from_domain: str,
        to_domain: str,
        body: str,
        timestamp: str,
        subject: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO letters (direction, from_domain, to_domain, "
                "subject, body, timestamp, received_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (direction, from_domain, to_domain, subject, body,
                 timestamp, _now()),
            )

    def list_letters(self, direction: str | None = None) -> list[dict]:
        query = "SELECT * FROM letters"
        params: tuple = ()
        if direction is not None:
            query += " WHERE direction = ?"
            params = (direction,)
        query += " ORDER BY received_at DESC"
        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]