import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.database.db import get_db
from routes.user_management import get_user_tier_enhanced

FEATURE_NAME = "cover_letter_optimiser"


def row_to_dict(row) -> Optional[Dict]:
    return dict(row) if row else None


def current_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_cover_letter_optimiser_limit(current_user: dict) -> Optional[int]:
    """Return monthly cover letter optimiser limit for the user's tier."""
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])
    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_cover_letter_optimiser_usage(user_id: str, month_year: Optional[str] = None) -> int:
    """Return monthly cover letter optimiser usage."""
    month_year = month_year or current_month_key()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count
            FROM usage_tracking
            WHERE user_id = ? AND feature_name = ? AND month_year = ?
            """,
            (user_id, FEATURE_NAME, month_year),
        )
        row = cursor.fetchone()
        return int(row["usage_count"] if row else 0)


def can_run_cover_letter_optimiser(current_user: dict) -> Dict:
    """Return whether a user can run another cover letter optimisation this month."""
    user_id = current_user["user_id"]
    limit = get_cover_letter_optimiser_limit(current_user)
    current_usage = get_cover_letter_optimiser_usage(user_id)

    if limit is None:
        return {
            "can_run": True,
            "current_usage": current_usage,
            "monthly_limit": None,
            "unlimited": True,
            "message": "Unlimited cover letter optimisation is included in your plan.",
        }

    can_run = current_usage < limit
    return {
        "can_run": can_run,
        "current_usage": current_usage,
        "monthly_limit": limit,
        "unlimited": False,
        "upgrade_required": not can_run,
        "upgrade_url": "/pricing" if not can_run else None,
        "message": (
            "You can optimise another cover letter this month."
            if can_run
            else "Your Basic plan includes 1 cover letter optimisation per month. Upgrade to Premium for unlimited optimisation."
        ),
    }


def increment_cover_letter_optimiser_usage(user_id: str, month_year: Optional[str] = None) -> None:
    """Increment monthly cover letter optimiser usage."""
    month_year = month_year or current_month_key()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count
            FROM usage_tracking
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


def save_cover_letter_optimisation(
    user_id: str,
    original_text: str,
    analysis: Dict,
    improved_cover_letter: str,
    title: Optional[str] = None,
    target_role: Optional[str] = None,
    company_name: Optional[str] = None,
    job_posting: Optional[str] = None,
) -> Dict:
    """Save a cover letter optimisation result."""
    optimisation_id = str(uuid.uuid4())
    analysis = analysis or {}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO cover_letter_optimiser_results (
                optimisation_id,
                user_id,
                title,
                original_text,
                target_role,
                company_name,
                job_posting,
                analysis_json,
                overall_score,
                ats_score,
                improved_cover_letter
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                optimisation_id,
                user_id,
                title or "Optimised Cover Letter",
                original_text,
                target_role,
                company_name,
                job_posting,
                json.dumps(analysis),
                analysis.get("overall_score"),
                analysis.get("ats_score") or analysis.get("job_alignment_score"),
                improved_cover_letter,
            ),
        )
        conn.commit()

    return get_cover_letter_optimisation(user_id=user_id, optimisation_id=optimisation_id)


def get_cover_letter_optimisation(user_id: str, optimisation_id: str) -> Optional[Dict]:
    """Return one saved cover letter optimisation result owned by the user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT *
            FROM cover_letter_optimiser_results
            WHERE user_id = ? AND optimisation_id = ?
            """,
            (user_id, optimisation_id),
        )
        result = row_to_dict(cursor.fetchone())

    if result and result.get("analysis_json"):
        try:
            result["analysis"] = json.loads(result["analysis_json"])
        except Exception:
            result["analysis"] = {}

    return result


def list_cover_letter_optimisations(user_id: str) -> List[Dict]:
    """Return saved cover letter optimisation results for a user, newest first."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                optimisation_id,
                user_id,
                title,
                target_role,
                company_name,
                overall_score,
                ats_score,
                created_at,
                updated_at
            FROM cover_letter_optimiser_results
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
