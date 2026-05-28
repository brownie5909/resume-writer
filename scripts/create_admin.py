"""
One-time admin account creation script.

Run this from the server shell or locally, never from the browser.

Required environment variables:
  ADMIN_EMAIL
  ADMIN_PASSWORD

Optional:
  ADMIN_FULL_NAME

Example:
  ADMIN_EMAIL="you@example.com" ADMIN_PASSWORD="StrongPassword123" python scripts/create_admin.py
"""

import os
import sys
import uuid
from pathlib import Path

# Allow script to import app modules when run from project root or scripts folder
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.database.db import get_db, init_database
from app.core.security import get_password_hash


def main():
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    full_name = os.getenv("ADMIN_FULL_NAME", "Admin User").strip() or "Admin User"

    if not email:
        raise SystemExit("ADMIN_EMAIL is required")

    if not password:
        raise SystemExit("ADMIN_PASSWORD is required")

    if len(password) < 10:
        raise SystemExit("ADMIN_PASSWORD must be at least 10 characters")

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

    print(f"Admin account {action}: {email}")
    print("Tier: professional")
    print("Admin: true")
    print("Login endpoint: /api/auth/login")


if __name__ == "__main__":
    main()
