import sqlite3
import threading
import time

from app import config

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, ts REAL);
            CREATE TABLE IF NOT EXISTS history (
                user_id TEXT, role TEXT, text TEXT, ts REAL
            );
            CREATE TABLE IF NOT EXISTS replies (user_id TEXT, ts REAL);
            """
        )
    return _conn


def reset(path: str) -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
        config.DB_PATH = path
        _conn = None


def mark_seen(event_id: str) -> bool:
    """Returns False if this id was already processed."""
    with _lock:
        cur = conn().execute(
            "INSERT OR IGNORE INTO seen (id, ts) VALUES (?, ?)", (event_id, time.time())
        )
        conn().commit()
        return cur.rowcount == 1


def add_history(user_id: str, role: str, text: str) -> None:
    with _lock:
        conn().execute(
            "INSERT INTO history VALUES (?, ?, ?, ?)", (user_id, role, text, time.time())
        )
        conn().commit()


def get_history(user_id: str, limit: int = 10) -> list[tuple[str, str]]:
    with _lock:
        rows = conn().execute(
            "SELECT role, text FROM history WHERE user_id = ? ORDER BY ts DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return list(reversed(rows))


def can_reply(user_id: str, max_per_hour: int) -> bool:
    cutoff = time.time() - 3600
    with _lock:
        (count,) = conn().execute(
            "SELECT COUNT(*) FROM replies WHERE user_id = ? AND ts > ?", (user_id, cutoff)
        ).fetchone()
    return count < max_per_hour


def record_reply(user_id: str) -> None:
    with _lock:
        conn().execute("INSERT INTO replies VALUES (?, ?)", (user_id, time.time()))
        conn().commit()
