from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.security import get_password_hash, verify_password
from app.database.db import get_db
from routes.user_management import get_current_user

router = APIRouter()


class AccountPasswordUpdate(BaseModel):
    current_password: str
    new_password: str


def validate_password_rules(value: str):
    if (
        len(value) < 8
        or not any(char.isalpha() for char in value)
        or not any(char.isdigit() for char in value)
    ):
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters and include a letter and number",
        )


@router.post("/auth/change-password")
async def update_account_password(
    request: AccountPasswordUpdate,
    current_user: dict = Depends(get_current_user),
):
    validate_password_rules(request.new_password)

    if request.current_password == request.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from your current password",
        )

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT user_id, password_hash
            FROM users
            WHERE user_id = ? AND is_active = TRUE
            """,
            (current_user["user_id"],),
        )
        user = cursor.fetchone()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not verify_password(request.current_password, user["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        cursor.execute(
            """
            UPDATE users
            SET password_hash = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (get_password_hash(request.new_password), current_user["user_id"]),
        )

        cursor.execute(
            """
            UPDATE user_sessions
            SET is_active = FALSE
            WHERE user_id = ?
            """,
            (current_user["user_id"],),
        )

        conn.commit()

    return {
        "success": True,
        "message": "Password changed. Please login again with your new password.",
    }
