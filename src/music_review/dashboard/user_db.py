"""SQLite-backed user store with password authentication and session tokens.

Tables
------
* **users** -- one row per registered profile (slug, bcrypt hash, profile JSON).
* **sessions** -- browser session tokens for cookie-based login persistence.

The database file lives at ``data/plattenradar.db`` (resolved via
:func:`music_review.config.resolve_data_path`).
"""

from __future__ import annotations

import json
import secrets
import sqlite3
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import bcrypt

from music_review.config import resolve_data_path

_DB_RELATIVE_PATH = "data/plattenradar.db"
_SESSION_TOKEN_BYTES = 48
DEFAULT_SESSION_LIFETIME_DAYS = 30

_SCHEMA_SQL = """\
CREATE TABLE IF NOT EXISTS users (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    slug                   TEXT    UNIQUE NOT NULL,
    password_hash          TEXT    NOT NULL,
    profile_data           TEXT,
    spotify_last_preview_at TEXT,
    spotify_client_id      TEXT,
    spotify_client_secret  TEXT,
    created_at             TEXT    NOT NULL,
    updated_at             TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_slug  TEXT NOT NULL REFERENCES users(slug) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""

_MIGRATE_SPOTIFY_COLS_SQL = (
    "ALTER TABLE users ADD COLUMN spotify_client_id TEXT",
    "ALTER TABLE users ADD COLUMN spotify_client_secret TEXT",
)


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_db_path() -> Path:
    """Resolved path to the SQLite database file."""
    return resolve_data_path(_DB_RELATIVE_PATH)


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open (or create) the database and ensure the schema exists."""
    path = db_path if db_path is not None else default_db_path()
    _ensure_parent(path)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(_SCHEMA_SQL)
    _run_migrations(conn)
    return conn


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Add columns that may be missing in databases created before Phase 2."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    for stmt in _MIGRATE_SPOTIFY_COLS_SQL:
        col_name = stmt.rsplit(None, 2)[-2]
        if col_name not in existing:
            conn.execute(stmt)
    conn.commit()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("ascii")


def _verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("ascii"))


# ---- User CRUD -------------------------------------------------------------


def create_user(
    conn: sqlite3.Connection,
    slug: str,
    password: str,
) -> bool:
    """Register a new user. Return True on success, False if slug is taken."""
    now = _utc_now_iso()
    pw_hash = _hash_password(password)
    try:
        conn.execute(
            "INSERT INTO users (slug, password_hash, created_at, updated_at) "
            "VALUES (?, ?, ?, ?)",
            (slug, pw_hash, now, now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        return False
    return True


def authenticate_user(
    conn: sqlite3.Connection,
    slug: str,
    password: str,
) -> bool:
    """Verify credentials. Return True if slug exists and password matches."""
    row = conn.execute(
        "SELECT password_hash FROM users WHERE slug = ?",
        (slug,),
    ).fetchone()
    if row is None:
        return False
    return _verify_password(password, row["password_hash"])


def user_exists(conn: sqlite3.Connection, slug: str) -> bool:
    """Return True when a user row with the given slug exists."""
    row = conn.execute(
        "SELECT 1 FROM users WHERE slug = ?",
        (slug,),
    ).fetchone()
    return row is not None


def change_password(
    conn: sqlite3.Connection,
    slug: str,
    new_password: str,
) -> bool:
    """Update the password hash. Return False if the slug does not exist."""
    pw_hash = _hash_password(new_password)
    now = _utc_now_iso()
    cur = conn.execute(
        "UPDATE users SET password_hash = ?, updated_at = ? WHERE slug = ?",
        (pw_hash, now, slug),
    )
    conn.commit()
    return cur.rowcount > 0


def list_user_slugs(conn: sqlite3.Connection) -> list[str]:
    """Return all registered slugs in alphabetical order."""
    rows = conn.execute("SELECT slug FROM users ORDER BY slug").fetchall()
    return [r["slug"] for r in rows]


# ---- Profile data ----------------------------------------------------------


def load_user_profile(
    conn: sqlite3.Connection,
    slug: str,
) -> dict[str, Any] | None:
    """Load the profile JSON blob for a user, or None if not found."""
    row = conn.execute(
        "SELECT profile_data FROM users WHERE slug = ?",
        (slug,),
    ).fetchone()
    if row is None:
        return None
    raw = row["profile_data"]
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def save_user_profile(
    conn: sqlite3.Connection,
    slug: str,
    data: Mapping[str, Any],
) -> None:
    """Persist the profile dict (communities, filters, weights, etc.)."""
    blob = json.dumps(dict(data), ensure_ascii=False, indent=2, sort_keys=True)
    now = _utc_now_iso()
    conn.execute(
        "UPDATE users SET profile_data = ?, updated_at = ? WHERE slug = ?",
        (blob, now, slug),
    )
    conn.commit()


# ---- Spotify preview rate-limit (per user) ----------------------------------


def load_spotify_last_preview_at(
    conn: sqlite3.Connection,
    slug: str,
) -> str | None:
    """Return the ISO timestamp of the last Spotify preview, or None."""
    row = conn.execute(
        "SELECT spotify_last_preview_at FROM users WHERE slug = ?",
        (slug,),
    ).fetchone()
    if row is None:
        return None
    val: str | None = row["spotify_last_preview_at"]
    return val


def save_spotify_last_preview_at(
    conn: sqlite3.Connection,
    slug: str,
    iso_ts: str,
) -> None:
    """Persist the Spotify preview timestamp."""
    now = _utc_now_iso()
    conn.execute(
        "UPDATE users SET spotify_last_preview_at = ?, updated_at = ? WHERE slug = ?",
        (iso_ts, now, slug),
    )
    conn.commit()


# ---- Per-user Spotify credentials -------------------------------------------


def save_spotify_credentials(
    conn: sqlite3.Connection,
    slug: str,
    client_id: str,
    client_secret: str,
) -> None:
    """Store the user's own Spotify Developer App credentials."""
    now = _utc_now_iso()
    conn.execute(
        "UPDATE users SET spotify_client_id = ?, spotify_client_secret = ?, "
        "updated_at = ? WHERE slug = ?",
        (client_id.strip(), client_secret.strip(), now, slug),
    )
    conn.commit()


def load_spotify_credentials(
    conn: sqlite3.Connection,
    slug: str,
) -> tuple[str, str] | None:
    """Return ``(client_id, client_secret)`` or None if not configured."""
    row = conn.execute(
        "SELECT spotify_client_id, spotify_client_secret FROM users WHERE slug = ?",
        (slug,),
    ).fetchone()
    if row is None:
        return None
    cid: str | None = row["spotify_client_id"]
    csec: str | None = row["spotify_client_secret"]
    if not cid or not csec:
        return None
    return (cid.strip(), csec.strip())


def clear_spotify_credentials(
    conn: sqlite3.Connection,
    slug: str,
) -> None:
    """Remove stored Spotify credentials for a user."""
    now = _utc_now_iso()
    conn.execute(
        "UPDATE users SET spotify_client_id = NULL, spotify_client_secret = NULL, "
        "updated_at = ? WHERE slug = ?",
        (now, slug),
    )
    conn.commit()


# ---- Session tokens ---------------------------------------------------------


def create_session_token(
    conn: sqlite3.Connection,
    slug: str,
    *,
    lifetime_days: int = DEFAULT_SESSION_LIFETIME_DAYS,
) -> str:
    """Create a random session token for the given user and persist it."""
    token = secrets.token_urlsafe(_SESSION_TOKEN_BYTES)
    now = datetime.now(UTC).replace(microsecond=0)
    expires = now + timedelta(days=lifetime_days)
    now_iso = now.isoformat().replace("+00:00", "Z")
    expires_iso = expires.isoformat().replace("+00:00", "Z")
    conn.execute(
        "INSERT INTO sessions (token, user_slug, created_at, expires_at) "
        "VALUES (?, ?, ?, ?)",
        (token, slug, now_iso, expires_iso),
    )
    conn.commit()
    return token


def validate_session_token(
    conn: sqlite3.Connection,
    token: str,
) -> str | None:
    """Return the user slug if the token is valid and not expired, else None."""
    row = conn.execute(
        "SELECT user_slug, expires_at FROM sessions WHERE token = ?",
        (token,),
    ).fetchone()
    if row is None:
        return None
    expires_raw = row["expires_at"]
    if isinstance(expires_raw, str):
        exp_str = expires_raw
        if exp_str.endswith("Z"):
            exp_str = exp_str[:-1] + "+00:00"
        try:
            expires = datetime.fromisoformat(exp_str)
        except ValueError:
            return None
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        if datetime.now(UTC) > expires:
            delete_session_token(conn, token)
            return None
    slug_val: str = str(row["user_slug"])
    return slug_val


def delete_session_token(
    conn: sqlite3.Connection,
    token: str,
) -> None:
    """Remove a single session (logout)."""
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()


def delete_all_sessions_for_user(
    conn: sqlite3.Connection,
    slug: str,
) -> None:
    """Remove every session for a user (e.g. after password change)."""
    conn.execute("DELETE FROM sessions WHERE user_slug = ?", (slug,))
    conn.commit()


def purge_expired_sessions(conn: sqlite3.Connection) -> int:
    """Delete expired sessions. Return the number removed."""
    now_iso = _utc_now_iso()
    cur = conn.execute(
        "DELETE FROM sessions WHERE expires_at < ?",
        (now_iso,),
    )
    conn.commit()
    return cur.rowcount
