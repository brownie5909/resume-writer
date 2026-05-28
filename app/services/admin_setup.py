import os
import uuid
from typing import Dict

from app.core.security import get_password_hash
from app.database.db import get_db, init_database


def auto_create_admin_from_env() -> Dict:
    """
    Create or repair an admin account from Render environment variables.

    Required:
      AUTO_CREATE_ADMIN=true
      ADMIN_EMAIL=...
      ADMIN_PASSWORD=...

    Optional:
      ADMIN_FULL_NAME=...

    This is intentionally not exposed as an API endpoint.
    """
    if os.getenv("AUTO_CREATE_ADMIN", "").lower() != "true":
        return {"enabled": False, "message": "Auto admin creation disabled"}

    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    full_name = os.getenv("ADMIN_FULL_NAME", "Admin User").strip() or "Admin User"

    if not email or not password:
        return {
            "enabled": True,
            "success": False,
            "message": "ADMIN_EMAIL and ADMIN_PASSWORD are required"
        }

    if len(password) < 10:
        return {
            "enabled": True,
            "success": False,
            "message": "ADMIN_PASSWORD must be at least 10 characters"
        }

    init_database()
    password_hash = get_password_hash(password)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE email = ?", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            user_id = existing_user["user_id"]
            cursor.execute(
                """
                UPDATE users
                SET password_hash = ?,
                    full_name = ?,
                    tier = 'professional',
                    is_verified = TRUE,
                    is_active = TRUE,
                    is_admin = TRUE,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
                """,
                (password_hash, full_name, user_id),
            )
            action = "updated"
        else:
            user_id = str(uuid.uuid4())
            cursor.execute(
                """
                INSERT INTO users (
                    user_id, email, password_hash, full_name, tier,
                    is_verified, is_active, is_admin
                )
                VALUES (?, ?, ?, ?, 'professional', TRUE, TRUE, TRUE)
                """,
                (user_id, email, password_hash, full_name),
            )
            action = "created"

        conn.commit()

    return {
        "enabled": True,
        "success": True,
        "action": action,
        "email": email,
        "tier": "professional",
        "is_admin": True
    }
