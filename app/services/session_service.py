import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.core.security import REFRESH_TOKEN_EXPIRE_DAYS
from app.database.db import get_db


def hash_refresh_token(refresh_token: str) -> str:
    return hashlib.sha256(refresh_token.encode("utf-8")).hexdigest()


def create_session(user_id: str, refresh_token: str) -> str:
    session_id = str(uuid.uuid4())
    refresh_token_hash = hash_refresh_token(refresh_token)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_sessions (session_id, user_id, refresh_token_hash, expires_at)
            VALUES (?, ?, ?, ?)
        """, (session_id, user_id, refresh_token_hash, expires_at.isoformat()))
        conn.commit()

    return session_id


def validate_session(user_id: str, refresh_token: str) -> bool:
    refresh_token_hash = hash_refresh_token(refresh_token)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, expires_at
            FROM user_sessions
            WHERE user_id = ? AND refresh_token_hash = ? AND is_active = TRUE
        """, (user_id, refresh_token_hash))
        row = cursor.fetchone()

        if not row:
            return False

        expires_at = datetime.fromisoformat(str(row["expires_at"]))
        if expires_at < datetime.utcnow():
            revoke_session(refresh_token)
            return False

        cursor.execute("""
            UPDATE user_sessions
            SET last_used = CURRENT_TIMESTAMP
            WHERE session_id = ?
        """, (row["session_id"],))
        conn.commit()

        return True


def revoke_session(refresh_token: str) -> bool:
    refresh_token_hash = hash_refresh_token(refresh_token)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_sessions
            SET is_active = FALSE, last_used = CURRENT_TIMESTAMP
            WHERE refresh_token_hash = ? AND is_active = TRUE
        """, (refresh_token_hash,))
        conn.commit()
        return cursor.rowcount > 0


def revoke_all_sessions(user_id: str) -> int:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE user_sessions
            SET is_active = FALSE, last_used = CURRENT_TIMESTAMP
            WHERE user_id = ? AND is_active = TRUE
        """, (user_id,))
        conn.commit()
        return cursor.rowcount


def list_sessions(user_id: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT session_id, created_at, last_used, expires_at, is_active
            FROM user_sessions
            WHERE user_id = ?
            ORDER BY last_used DESC
            LIMIT 20
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
