import hashlib
import hmac
import json
import uuid
import re
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import Request

from app.core.security import SECRET_KEY
from app.database.db import get_db
from app.services.resume_document_service import (
    create_resume_document,
    list_resume_documents,
    update_resume_document,
)
from routes.user_management import get_user_tier_enhanced

RESUME_ANALYSIS_FEATURE = "resume_analysis"

GUEST_RESUME_ANALYSIS_FEATURE = "guest_resume_analysis"
GUEST_IP_DAILY_LIMIT = 1
GUEST_GLOBAL_DAILY_LIMIT = 200
GUEST_GLOBAL_USAGE_KEY = "__global__"


def row_to_dict(row) -> Optional[Dict]:
    return dict(row) if row else None


def hydrate_analysis_json(result: Optional[Dict]) -> Optional[Dict]:
    """Attach parsed analysis JSON to a database result."""
    if not result:
        return None

    if result.get("analysis_json"):
        try:
            result["analysis"] = json.loads(result["analysis_json"])
        except json.JSONDecodeError:
            result["analysis"] = {}
    else:
        result["analysis"] = {}

    return result


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


def get_day_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def get_client_ip(request: Request) -> str:
    """Best-effort client IP behind Render's proxy: trust the first hop of X-Forwarded-For."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def hash_client_ip(ip_address: str) -> str:
    """HMAC the client IP so raw IPs are never stored, keyed off the app SECRET_KEY."""
    return hmac.new(SECRET_KEY.encode("utf-8"), ip_address.encode("utf-8"), hashlib.sha256).hexdigest()


def _get_guest_usage_count(ip_hash: str) -> int:
    day_key = get_day_key()

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM guest_usage_tracking
            WHERE ip_hash = ? AND feature_name = ? AND usage_date = ?
            """,
            (ip_hash, GUEST_RESUME_ANALYSIS_FEATURE, day_key),
        )
        result = cursor.fetchone()
        return int(result["usage_count"] if result else 0)


def can_run_guest_resume_analysis(request: Request) -> Dict:
    """Return whether an anonymous visitor can run a guest resume analysis today."""
    ip_hash = hash_client_ip(get_client_ip(request))
    ip_usage = _get_guest_usage_count(ip_hash)
    global_usage = _get_guest_usage_count(GUEST_GLOBAL_USAGE_KEY)

    if global_usage >= GUEST_GLOBAL_DAILY_LIMIT:
        return {
            "can_run": False,
            "ip_hash": ip_hash,
            "message": "Guest resume analysis is at capacity for today. Please try again tomorrow, or create a free account to continue.",
        }

    if ip_usage >= GUEST_IP_DAILY_LIMIT:
        return {
            "can_run": False,
            "ip_hash": ip_hash,
            "message": "You've used your free guest resume analysis for today. Create a free account for more analyses and to save your results.",
        }

    return {"can_run": True, "ip_hash": ip_hash, "message": "Guest resume analysis is available."}


def increment_guest_resume_analysis_usage(ip_hash: str) -> None:
    """Increment both the per-IP and site-wide daily guest usage counters."""
    day_key = get_day_key()

    with get_db() as conn:
        cursor = conn.cursor()
        for key in (ip_hash, GUEST_GLOBAL_USAGE_KEY):
            cursor.execute(
                """
                SELECT usage_count FROM guest_usage_tracking
                WHERE ip_hash = ? AND feature_name = ? AND usage_date = ?
                """,
                (key, GUEST_RESUME_ANALYSIS_FEATURE, day_key),
            )
            result = cursor.fetchone()

            if result:
                cursor.execute(
                    """
                    UPDATE guest_usage_tracking
                    SET usage_count = ?
                    WHERE ip_hash = ? AND feature_name = ? AND usage_date = ?
                    """,
                    (int(result["usage_count"]) + 1, key, GUEST_RESUME_ANALYSIS_FEATURE, day_key),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO guest_usage_tracking (usage_id, ip_hash, feature_name, usage_date, usage_count)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (str(uuid.uuid4()), key, GUEST_RESUME_ANALYSIS_FEATURE, day_key, 1),
                )

        conn.commit()


def build_guest_analysis_teaser(ai_result: Dict) -> Dict:
    """Return a limited teaser view of an analysis for anonymous guests."""
    return {
        "overall_score": ai_result.get("overall_score", 70),
        "ats_score": ai_result.get("ats_score", 70),
        "top_strengths": (ai_result.get("strengths") or [])[:2],
        "top_improvements": (ai_result.get("specific_improvements") or ai_result.get("weaknesses") or [])[:3],
    }


def clean_resume_label(value: Optional[str]) -> str:
    """Create a readable base label from a filename or saved resume title."""
    label = (value or "Resume").strip()
    label = re.sub(r"\.(pdf|docx?|txt|rtf)$", "", label, flags=re.IGNORECASE)
    label = re.sub(r"\s+-\s+Improved(\s+Resume)?(\s+for\s+.+)?$", "", label, flags=re.IGNORECASE)
    label = re.sub(r"^Analysed Resume\s+-\s+", "", label, flags=re.IGNORECASE)
    label = re.sub(r"\s+v\d+$", "", label, flags=re.IGNORECASE)
    return label.strip() or "Resume"


def build_improved_resume_title(
    original_label: Optional[str],
    target_role: Optional[str] = None,
) -> str:
    """Return a clear title for the first improved resume saved after upload analysis."""
    base_label = clean_resume_label(original_label)
    cleaned_role = (target_role or "").strip()

    if cleaned_role:
        return f"{base_label} - Improved for {cleaned_role}"

    return f"{base_label} - Improved Resume"


def next_resume_version_title(user_id: str, source_title: Optional[str]) -> str:
    """Return the next visible v2/v3/v4 title for an improved saved resume."""
    base_label = clean_resume_label(source_title)
    highest_version = 1

    for resume in list_resume_documents(user_id):
        title = (resume.get("title") or "").strip()
        if title == base_label:
            highest_version = max(highest_version, 1)
            continue

        match = re.match(rf"^{re.escape(base_label)}\s+v(\d+)$", title, flags=re.IGNORECASE)
        if match:
            highest_version = max(highest_version, int(match.group(1)))

    return f"{base_label} v{highest_version + 1}"


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
    """Save an improved uploaded resume into the user's editable resume documents."""
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


def save_improved_analysis_resume_document(
    current_user: dict,
    improved_resume: str,
    original_label: Optional[str],
    target_role: Optional[str] = None,
    source_document: Optional[Dict] = None,
) -> Dict:
    """
    Save the improved resume produced by analysis.

    Basic keeps the existing one-resume overwrite/version-history behaviour.
    Premium and Professional create a new visible resume document when analysing
    an existing saved resume, using v2/v3/v4 style titles.
    Uploaded files still create a clear improved resume document.
    """
    user_id = current_user["user_id"]
    saved_resume_limit = get_saved_resume_limit(current_user)

    if source_document and saved_resume_limit is None:
        new_title = next_resume_version_title(user_id, source_document.get("title") or original_label)
        return create_resume_document(
            user_id=user_id,
            title=new_title,
            resume_text=improved_resume,
            cover_letter_text=source_document.get("cover_letter_text", ""),
            template=source_document.get("template", "default"),
            pdf_filename=None,
        )

    title = build_improved_resume_title(original_label, target_role)

    if source_document:
        return update_resume_document(
            user_id=user_id,
            document_id=source_document["document_id"],
            title=title,
            resume_text=improved_resume,
            cover_letter_text=source_document.get("cover_letter_text", ""),
            template=source_document.get("template", "default"),
            pdf_filename=None,
            max_versions=get_resume_version_limit(current_user),
        )

    return create_or_update_analysis_resume_document(
        current_user=current_user,
        title=title,
        improved_resume=improved_resume,
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

    return hydrate_analysis_json(result)


def get_latest_resume_analysis_for_document(user_id: str, document_id: str) -> Optional[Dict]:
    """Return the latest analysis result linked to one of the user's saved resumes."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM resume_analysis_results
            WHERE user_id = ? AND document_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (user_id, document_id),
        )
        result = row_to_dict(cursor.fetchone())

    return hydrate_analysis_json(result)


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
