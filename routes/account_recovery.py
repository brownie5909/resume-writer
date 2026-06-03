from datetime import datetime, timedelta
import hashlib
import secrets
import uuid

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr

from app.core.security import get_password_hash
from app.database.db import get_db
from routes.user_management import get_user_by_email

router = APIRouter()


class RecoveryRequest(BaseModel):
    email: EmailStr


class RecoveryCompleteRequest(BaseModel):
    token: str
    new_password: str


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def parse_datetime(value):
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


@router.post("/auth/forgot-password")
async def start_recovery(request: RecoveryRequest):
    user = get_user_by_email(request.email)
    response = {"success": True, "message": "If an account exists, a recovery link has been created."}

    if not user:
        return response

    token = secrets.token_urlsafe(32)
    reset_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(hours=1)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO password_reset_tokens (reset_id, user_id, token_hash, expires_at)
            VALUES (?, ?, ?, ?)
            """,
            (reset_id, user["user_id"], digest(token), expires_at)
        )
        conn.commit()

    response["reset_token"] = token
    response["reset_link"] = f"/reset-password/?token={token}"
    return response


@router.post("/auth/reset-password")
async def finish_recovery(request: RecoveryCompleteRequest):
    if len(request.new_password) < 8 or not any(c.isalpha() for c in request.new_password) or not any(c.isdigit() for c in request.new_password):
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters and include a letter and number")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM password_reset_tokens
            WHERE token_hash = ? AND used_at IS NULL
            ORDER BY created_at DESC
            """,
            (digest(request.token),)
        )
        row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired recovery link")

        expires_at = parse_datetime(row["expires_at"])
        if expires_at and expires_at < datetime.utcnow():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired recovery link")

        cursor.execute(
            """
            UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (get_password_hash(request.new_password), row["user_id"])
        )
        cursor.execute(
            """
            UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP
            WHERE reset_id = ?
            """,
            (row["reset_id"],)
        )
        cursor.execute("UPDATE user_sessions SET is_active = FALSE WHERE user_id = ?", (row["user_id"],))
        conn.commit()

    return {"success": True, "message": "Password updated. Please login again."}
