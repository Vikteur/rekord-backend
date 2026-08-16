"""DJ-app accounts and sessions: who may open the app, and what they own.

Two kinds of signed-in users:

- **admin** — the owner. Sees and manages everything, and is the only one who
  creates accounts: every DJ gets a login handed to them, there is no sign-up.
- **dj** — sees and manages only their own couples and their own libraries.

Couples are deliberately *not* users: their magic link (`/g/<token>`, see
`server/couples.py`) is their login, so this module never touches them.

Passwords are stored as salted scrypt hashes (stdlib only, no new deps).
Sessions are server-side rows in the same SQLite file; the browser cookie
holds a random 256-bit token and the database stores only its SHA-256, so a
leaked database file cannot be replayed as a login. Deleting the row signs
the browser out instantly.

The one admin account is bootstrapped from `ADMIN_USERNAME`/`ADMIN_PASSWORD`
environment variables on first start (never overwritten afterwards), or with
`python -m server.create_user` — which also resets forgotten passwords.
"""

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from server.db import connect

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT NOT NULL UNIQUE COLLATE NOCASE,
    display_name  TEXT NOT NULL,
    password_hash TEXT NOT NULL,            -- scrypt$N$r$p$<salt hex>$<hash hex>
    role          TEXT NOT NULL CHECK (role IN ('admin', 'dj')),
    disabled      INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,            -- sha256 of the cookie value
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sessions_user ON sessions(user_id);
"""

SESSION_TTL_DAYS = 30
MIN_PASSWORD_CHARS = 8

# scrypt cost parameters; recorded in every hash so they can be raised later
# without breaking existing passwords.
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P, _SCRYPT_DKLEN = 16384, 8, 1, 32

# Failed sign-ins per (client, username): 5 failures inside 5 minutes locks
# that pair out until the window slides. Successes are never counted, so a
# busy legitimate user can't rate-limit themselves.
RATE_WINDOW_SEC = 300
RATE_MAX_FAILURES = 5
_rate_lock = threading.Lock()
_recent_failures: dict[str, deque] = {}


class AuthError(Exception):
    """A domain rule was broken; `code` maps onto an HTTP error."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class CurrentUser:
    id: int
    username: str
    display_name: str
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- passwords --------------------------------------------------------------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"), salt=salt,
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_SCRYPT_DKLEN,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"), salt=bytes.fromhex(salt_hex),
            n=int(n), r=int(r), p=int(p), dklen=len(bytes.fromhex(digest_hex)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _check_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_CHARS:
        raise AuthError(
            "WEAK_PASSWORD",
            f"Passwords need at least {MIN_PASSWORD_CHARS} characters.",
        )


# --- users ------------------------------------------------------------------

def _user_from_row(row) -> CurrentUser:
    return CurrentUser(
        id=row["id"], username=row["username"],
        display_name=row["display_name"], role=row["role"],
    )


def create_user(username: str, display_name: str, password: str, role: str) -> int:
    username = username.strip().lower()
    if not username:
        raise AuthError("EMPTY_USERNAME", "Give the account a username.")
    if role not in ("admin", "dj"):
        raise AuthError("BAD_ROLE", "Role must be 'admin' or 'dj'.")
    _check_password_strength(password)
    display_name = display_name.strip() or username
    with connect() as conn:
        try:
            cursor = conn.execute(
                "INSERT INTO users (username, display_name, password_hash, role,"
                " created_at) VALUES (?, ?, ?, ?, ?)",
                (username, display_name, hash_password(password), role,
                 _now().isoformat()),
            )
        except Exception as exc:  # sqlite3.IntegrityError on the UNIQUE username
            raise AuthError(
                "DUPLICATE_USERNAME", f"There is already an account named {username!r}."
            ) from exc
        return int(cursor.lastrowid)


def get_user(user_id: int) -> CurrentUser | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return _user_from_row(row) if row else None


def find_by_username(username: str):
    with connect() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip().lower(),)
        ).fetchone()


def list_users() -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT id, username, display_name, role, disabled, created_at"
            " FROM users ORDER BY role, username"
        ).fetchall()
    return [dict(row) | {"disabled": bool(row["disabled"])} for row in rows]


def user_names() -> dict[int, str]:
    """{user id: display name} — for labelling couples with their DJ."""
    with connect() as conn:
        rows = conn.execute("SELECT id, display_name FROM users").fetchall()
    return {row["id"]: row["display_name"] for row in rows}


def set_password(user_id: int, password: str) -> bool:
    _check_password_strength(password)
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(password), user_id),
        )
        return cursor.rowcount > 0


def set_display_name(user_id: int, display_name: str) -> bool:
    display_name = display_name.strip()
    if not display_name:
        raise AuthError("EMPTY_NAME", "The display name can't be empty.")
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id)
        )
        return cursor.rowcount > 0


def set_disabled(user_id: int, disabled: bool) -> bool:
    """Switch an account off (or back on). Disabling kills its sessions too."""
    with connect() as conn:
        cursor = conn.execute(
            "UPDATE users SET disabled = ? WHERE id = ?",
            (1 if disabled else 0, user_id),
        )
        if cursor.rowcount == 0:
            return False
        if disabled:
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        return True


def delete_user(user_id: int) -> bool:
    """Remove an account. Their couples and libraries survive, unowned —
    visible to the admin, who can hand them to another DJ."""
    with connect() as conn:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        if cursor.rowcount == 0:
            return False
        # Sessions cascade; ownership columns live in other modules' tables.
        for table, column in (("couples", "dj_id"), ("libraries", "owner_id")):
            if _has_column(conn, table, column):
                conn.execute(
                    f"UPDATE {table} SET {column} = NULL WHERE {column} = ?",
                    (user_id,),
                )
        return True


def _has_column(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(row["name"] == column for row in rows)


def ensure_admin_from_env() -> None:
    """First-start bootstrap: create the admin from env if none exists yet.

    Changing the env variables later does nothing on purpose — passwords are
    reset with `python -m server.create_user <username> --reset`.
    """
    username = os.environ.get("ADMIN_USERNAME", "").strip()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not username or not password:
        return
    with connect() as conn:
        exists = conn.execute(
            "SELECT 1 FROM users WHERE role = 'admin' LIMIT 1"
        ).fetchone()
    if exists:
        return
    create_user(username, username, password, "admin")


# --- sign-in ----------------------------------------------------------------

# Verified against when the username doesn't exist, so unknown and wrong-
# password attempts take the same time and the response can't leak usernames.
_DUMMY_HASH: str | None = None


def authenticate(username: str, password: str) -> CurrentUser:
    global _DUMMY_HASH
    row = find_by_username(username)
    if row is None:
        if _DUMMY_HASH is None:
            _DUMMY_HASH = hash_password(secrets.token_urlsafe(8))
        verify_password(password, _DUMMY_HASH)
        raise AuthError("BAD_CREDENTIALS", "Wrong username or password.")
    if not verify_password(password, row["password_hash"]):
        raise AuthError("BAD_CREDENTIALS", "Wrong username or password.")
    if row["disabled"]:
        raise AuthError("ACCOUNT_DISABLED", "This account was switched off by the admin.")
    return _user_from_row(row)


# --- sessions ---------------------------------------------------------------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int) -> str:
    """Start a session; returns the raw token that goes into the cookie."""
    token = secrets.token_urlsafe(32)
    now = _now()
    with connect() as conn:
        conn.execute(
            "DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),)
        )
        conn.execute(
            "INSERT INTO sessions (token_hash, user_id, created_at, expires_at)"
            " VALUES (?, ?, ?, ?)",
            (
                _token_hash(token), user_id, now.isoformat(),
                (now + timedelta(days=SESSION_TTL_DAYS)).isoformat(),
            ),
        )
    return token


def session_user(token: str) -> CurrentUser | None:
    if not token:
        return None
    with connect() as conn:
        row = conn.execute(
            "SELECT u.*, s.expires_at FROM sessions s"
            " JOIN users u ON u.id = s.user_id WHERE s.token_hash = ?",
            (_token_hash(token),),
        ).fetchone()
    if row is None or row["disabled"]:
        return None
    if datetime.fromisoformat(row["expires_at"]) < _now():
        return None
    return _user_from_row(row)


def delete_session(token: str) -> None:
    if not token:
        return
    with connect() as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


# --- sign-in rate limit -----------------------------------------------------

def login_rate_check(key: str) -> None:
    now = time.time()
    with _rate_lock:
        window = _recent_failures.get(key)
        if window is None:
            return
        while window and now - window[0] > RATE_WINDOW_SEC:
            window.popleft()
        if len(window) >= RATE_MAX_FAILURES:
            raise AuthError(
                "RATE_LIMITED", "Too many failed sign-ins — wait a few minutes."
            )


def login_rate_record_failure(key: str) -> None:
    with _rate_lock:
        _recent_failures.setdefault(key, deque()).append(time.time())


def reset_rate_limits() -> None:
    """Test hook: forget every recorded failure."""
    with _rate_lock:
        _recent_failures.clear()
