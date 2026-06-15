import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.database.db import get_db
from routes.user_management import get_user_tier_enhanced

FEATURE_NAME = "cover_letter_generator"


def current_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_cover_letter_generator_limit(current_user: dict) -> Optional[int]:
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])
    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_cover_letter_generator_usage(user_id: str, month_year: Optional[str] = None) -> int:
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


def can_run_cover_letter_generator(current_user: dict) -> Dict:
    user_id = current_user["user_id"]
    limit = get_cover_letter_generator_limit(current_user)
    usage = get_cover_letter_generator_usage(user_id)

    if limit is None:
        return {
            "can_run": True,
            "current_usage": usage,
            "monthly_limit": None,
            "unlimited": True,
            "message": "Unlimited cover letter generation is included in your plan.",
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
            "You can generate another cover letter this month."
            if can_run
            else "Cover Letter Generator is a Premium feature. Upgrade to Premium to generate tailored cover letters from scratch."
        ),
    }


def increment_cover_letter_generator_usage(user_id: str, month_year: Optional[str] = None) -> None:
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


def save_cover_letter_generation(
    user_id: str,
    generated_cover_letter: str,
    analysis: Optional[Dict] = None,
    title: Optional[str] = None,
    applicant_name: Optional[str] = None,
    target_role: Optional[str] = None,
    company_name: Optional[str] = None,
    job_posting: Optional[str] = None,
    experience: Optional[str] = None,
    achievements: Optional[str] = None,
    tone_preference: Optional[str] = None,
) -> Dict:
    generation_id = str(uuid.uuid4())
    analysis = analysis or {}

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO cover_letter_generator_results (
                generation_id,
                user_id,
                title,
                applicant_name,
                target_role,
                company_name,
                job_posting,
                experience,
                achievements,
                tone_preference,
                generated_cover_letter,
                analysis_json,
                overall_score,
                ats_score
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                generation_id,
                user_id,
                title or "Generated Cover Letter",
                applicant_name,
                target_role,
                company_name,
                job_posting,
                experience,
                achievements,
                tone_preference,
                generated_cover_letter,
                json.dumps(analysis),
                analysis.get("overall_score"),
                analysis.get("ats_score") or analysis.get("job_alignment_score"),
            ),
        )
        conn.commit()

    return get_cover_letter_generation(user_id, generation_id)


def get_cover_letter_generation(user_id: str, generation_id: str) -> Optional[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM cover_letter_generator_results
            WHERE user_id = ? AND generation_id = ?
            """,
            (user_id, generation_id),
        )
        row = cursor.fetchone()

    if not row:
        return None

    result = dict(row)
    try:
        result["analysis"] = json.loads(result.get("analysis_json") or "{}")
    except Exception:
        result["analysis"] = {}
    return result


def list_cover_letter_generations(user_id: str) -> List[Dict]:
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT generation_id, user_id, title, applicant_name, target_role,
                   company_name, tone_preference, overall_score, ats_score,
                   created_at, updated_at
            FROM cover_letter_generator_results
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
