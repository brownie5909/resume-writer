import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.database.db import get_db
from routes.user_management import get_user_tier_enhanced

FEATURE_NAME = "interview_preparation"


def current_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_interview_preparation_limit(current_user: dict) -> Optional[int]:
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])
    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_interview_preparation_usage(user_id: str, month_year: Optional[str] = None) -> int:
    month_year = month_year or current_month_key()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = ? AND month_year = ?
            """,
            (user_id, FEATURE_NAME, month_year),
        )
        row = cursor.fetchone()
        return int(row["usage_count"] if row else 0)


def can_run_interview_preparation(current_user: dict) -> Dict:
    user_id = current_user["user_id"]
    limit = get_interview_preparation_limit(current_user)
    usage = get_interview_preparation_usage(user_id)

    if limit is None:
        return {
            "can_run": True,
            "current_usage": usage,
            "monthly_limit": None,
            "unlimited": True,
            "message": "Unlimited interview preparation is included in your plan.",
        }

    can_run = usage < limit
    return {
        "can_run": can_run,
        "current_usage": usage,
        "monthly_limit": limit,
        "unlimited": False,
        "upgrade_required": not can_run,
        "upgrade_url": "/pricing" if not can_run else None,
        "message": (
            "You can generate another interview preparation report this month."
            if can_run
            else "Your Basic plan includes 1 interview preparation report per month. Upgrade to Premium for unlimited interview preparation."
        ),
    }


def increment_interview_preparation_usage(user_id: str, month_year: Optional[str] = None) -> None:
    month_year = month_year or current_month_key()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = ? AND month_year = ?
            """,
            (user_id, FEATURE_NAME, month_year),
        )
        row = cursor.fetchone()

        if row:
            cursor.execute(
                """
                UPDATE usage_tracking
                SET usage_count = ?, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ? AND feature_name = ? AND month_year = ?
                """,
                (int(row["usage_count"]) + 1, user_id, FEATURE_NAME, month_year),
            )
        else:
            cursor.execute(
                """
                INSERT INTO usage_tracking (usage_id, user_id, feature_name, usage_count, month_year)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, FEATURE_NAME, 1, month_year),
            )
        conn.commit()


def save_interview_preparation(
    user_id: str,
    preparation: Dict,
    title: Optional[str] = None,
    company_name: Optional[str] = None,
    role_title: Optional[str] = None,
    job_posting: Optional[str] = None,
) -> Dict:
    prep_id = str(uuid.uuid4())
    preparation = preparation or {}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO interview_preparation_results (
                prep_id,
                user_id,
                title,
                company_name,
                role_title,
                job_posting,
                preparation_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prep_id,
                user_id,
                title or "Interview Preparation",
                company_name,
                role_title,
                job_posting,
                json.dumps(preparation),
            ),
        )
        conn.commit()

    return get_interview_preparation(user_id, prep_id)


def get_interview_preparation(user_id: str, prep_id: str) -> Optional[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM interview_preparation_results
            WHERE user_id = ? AND prep_id = ?
            """,
            (user_id, prep_id),
        )
        row = cursor.fetchone()

    if not row:
        return None

    result = dict(row)
    try:
        result["preparation"] = json.loads(result.get("preparation_json") or "{}")
    except Exception:
        result["preparation"] = {}
    return result


def list_interview_preparations(user_id: str) -> List[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT prep_id, user_id, title, company_name, role_title, created_at, updated_at
            FROM interview_preparation_results
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
