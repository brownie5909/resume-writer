import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from app.database.db import get_db
from app.services.resume_document_service import (
    create_resume_document,
    list_resume_documents,
    update_resume_document,
)
from routes.user_management import get_user_tier_enhanced

RESUME_ANALYSIS_FEATURE = "resume_analysis"


def row_to_dict(row) -> Optional[Dict]:
    return dict(row) if row else None


def get_resume_analysis_monthly_limit(current_user: dict) -> Optional[int]:
    """Return monthly resume analysis limit for the user's current access level."""
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])

    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_saved_resume_limit(current_user: dict) -> Optional[int]:
    """Return saved resume document limit for the user's current access level."""
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])

    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_resume_version_limit(current_user: dict) -> Optional[int]:
    """Return resume version retention limit for the user's current access level."""
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])

    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_resume_analysis_usage(user_id: str) -> int:
    """Return this month's resume analysis usage count."""
    month_key = get_month_key()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = ? AND month_year = ?
            """,
            (user_id, RESUME_ANALYSIS_FEATURE, month_key),
        )
        result = cursor.fetchone()
        return int(result["usage_count"] if result else 0)


def can_run_resume_analysis(current_user: dict) -> Dict:
    """Return whether the user can run another resume analysis this month."""
    monthly_limit = get_resume_analysis_monthly_limit(current_user)
    current_usage = get_resume_analysis_usage(current_user["user_id"])
    can_run = monthly_limit is None or current_usage < monthly_limit
    user_tier = get_user_tier_enhanced(current_user["user_id"])

    return {
        "can_run": can_run,
        "current_usage": current_usage,
        "monthly_limit": monthly_limit,
        "current_tier": "basic" if user_tier.value == "free" else user_tier.value,
        "upgrade_required": not can_run,
        "upgrade_url": "/pricing" if not can_run else None,
        "message": "Resume analysis is available." if can_run else "You have used your monthly Resume Analysis. Upgrade to Premium for unlimited analyses, analysis history and ATS tracking.",
    }


def increment_resume_analysis_usage(user_id: str) -> None:
    """Increment this month's resume analysis usage count."""
    month_key = get_month_key()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = ? AND month_year = ?
            """,
            (user_id, RESUME_ANALYSIS_FEATURE, month_key),
        )
        result = cursor.fetchone()

        if result:
            cursor.execute(
                """
                UPDATE usage_tracking
                SET usage_count = ?, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ? AND feature_name = ? AND month_year = ?
                """,
                (int(result["usage_count"]) + 1, user_id, RESUME_ANALYSIS_FEATURE, month_key),
            )
        else:
            cursor.execute(
                """
                INSERT INTO usage_tracking (usage_id, user_id, feature_name, usage_count, month_year)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, RESUME_ANALYSIS_FEATURE, 1, month_key),
            )

        conn.commit()


def create_or_update_analysis_resume_document(
    current_user: dict,
    title: str,
    improved_resume: str,
) -> Dict:
    """Save the improved analysed resume into the user's editable resume documents."""
    user_id = current_user["user_id"]
    saved_resume_limit = get_saved_resume_limit(current_user)
    saved_resumes = list_resume_documents(user_id)

    if saved_resume_limit is not None and len(saved_resumes) >= saved_resume_limit and saved_resumes:
        return update_resume_document(
            user_id=user_id,
            document_id=saved_resumes[0]["document_id"],
            title=title,
            resume_text=improved_resume,
            cover_letter_text="",
            template="default",
            pdf_filename=None,
            max_versions=get_resume_version_limit(current_user),
        )

    return create_resume_document(
        user_id=user_id,
        title=title,
        resume_text=improved_resume,
        cover_letter_text="",
        template="default",
        pdf_filename=None,
    )


def save_resume_analysis_result(
    user_id: str,
    document_id: str,
    original_filename: str,
    original_content_type: str,
    original_resume_text: str,
    target_role: Optional[str],
    analysis: Dict,
    improved_resume: str,
) -> Dict:
    """Persist one resume analysis result linked to a saved resume document."""
    analysis_id = str(uuid.uuid4())
    analysis_json = json.dumps(analysis or {})

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO resume_analysis_results (
                analysis_id,
                document_id,
                user_id,
                original_filename,
                original_content_type,
                original_file_base64,
                original_resume_text,
                target_role,
                analysis_json,
                overall_score,
                ats_score,
                improved_resume
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                analysis_id,
                document_id,
                user_id,
                original_filename,
                original_content_type,
                "",
                original_resume_text,
                target_role,
                analysis_json,
                analysis.get("overall_score", 70),
                analysis.get("ats_score", 70),
                improved_resume,
            ),
        )
        conn.commit()

    return get_resume_analysis_result(user_id=user_id, analysis_id=analysis_id)


def prune_basic_analysis_results(current_user: dict, keep_latest: int = 1) -> None:
    """Keep only the latest analysis result for limited-tier users."""
    if get_resume_analysis_monthly_limit(current_user) is None:
        return

    user_id = current_user["user_id"]

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT analysis_id
            FROM resume_analysis_results
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        analysis_ids_to_delete = [row["analysis_id"] for row in rows[keep_latest:]]

        for analysis_id in analysis_ids_to_delete:
            cursor.execute(
                """
                DELETE FROM resume_analysis_results
                WHERE user_id = ? AND analysis_id = ?
                """,
                (user_id, analysis_id),
            )

        if analysis_ids_to_delete:
            conn.commit()


def get_resume_analysis_result(user_id: str, analysis_id: str) -> Optional[Dict]:
    """Return one analysis result owned by the user."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM resume_analysis_results
            WHERE user_id = ? AND analysis_id = ?
            """,
            (user_id, analysis_id),
        )
        result = row_to_dict(cursor.fetchone())

    if result and result.get("analysis_json"):
        try:
            result["analysis"] = json.loads(result["analysis_json"])
        except json.JSONDecodeError:
            result["analysis"] = {}

    return result


def list_resume_analysis_results(user_id: str) -> List[Dict]:
    """Return saved analysis results for the user, newest first."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                analysis_id,
                document_id,
                user_id,
                original_filename,
                target_role,
                overall_score,
                ats_score,
                created_at,
                updated_at
            FROM resume_analysis_results
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
