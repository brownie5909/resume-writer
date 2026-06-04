from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
from datetime import datetime
import uuid

from routes.user_management import get_current_user, get_user_tier_enhanced, TIER_LIMITS, get_db
from app.services.pdf_service import generate_resume_pdf
from app.services.resume_document_service import (
    list_resume_documents,
    get_resume_document,
    update_resume_document,
    duplicate_resume_document,
    delete_resume_document,
    list_resume_versions,
    get_resume_version,
)

router = APIRouter()


class ResumeDocumentUpdate(BaseModel):
    title: Optional[str] = None
    resume_text: Optional[str] = None
    cover_letter_text: Optional[str] = None
    template: Optional[str] = None


def get_version_limit_for_user(current_user: dict) -> Optional[int]:
    """Return the maximum stored resume versions for the user's access level."""
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])
    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_saved_resume_limit_for_user(current_user: dict) -> Optional[int]:
    """Return the maximum saved resumes for the user's access level."""
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])
    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_resume_analysis_limit_for_user(current_user: dict) -> Optional[int]:
    """Return monthly resume analysis limit for the user's access level."""
    if bool(current_user.get("is_admin")):
        return None

    user_tier = get_user_tier_enhanced(current_user["user_id"])
    if user_tier.value in ("premium", "professional"):
        return None

    return 1


def get_month_key() -> str:
    return datetime.now().strftime("%Y-%m")


def get_usage_count(user_id: str, feature_name: str, month_year: str) -> int:
    """Return a monthly usage counter from usage_tracking."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = ? AND month_year = ?
            """,
            (user_id, feature_name, month_year),
        )
        result = cursor.fetchone()
        return int(result["usage_count"] if result else 0)


def count_user_rows(user_id: str, table_name: str) -> int:
    """Count rows owned by a user in known safe tables only."""
    allowed_tables = {
        "resume_versions",
        "resume_analysis_results",
    }

    if table_name not in allowed_tables:
        return 0

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT COUNT(*) AS total FROM {table_name} WHERE user_id = ?",
            (user_id,),
        )
        result = cursor.fetchone()
        return int(result["total"] if result else 0)


def track_pdf_usage(user_id: str):
    current_month = datetime.now().strftime("%Y-%m")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
            """,
            (user_id, current_month),
        )
        result = cursor.fetchone()

        if result:
            cursor.execute(
                """
                UPDATE usage_tracking
                SET usage_count = ?, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
                """,
                (result[0] + 1, user_id, current_month),
            )
        else:
            cursor.execute(
                """
                INSERT INTO usage_tracking (usage_id, user_id, feature_name, usage_count, month_year)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, "pdf_downloads", 1, current_month),
            )

        conn.commit()


def check_pdf_download_limit(user_id: str) -> bool:
    user_tier = get_user_tier_enhanced(user_id)
    tier_limits = TIER_LIMITS[user_tier]
    limit = tier_limits["pdf_downloads_per_month"]

    if limit == -1:
        return True

    current_month = datetime.now().strftime("%Y-%m")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
            """,
            (user_id, current_month),
        )
        result = cursor.fetchone()
        current_usage = result[0] if result else 0
        return current_usage < limit


@router.get("/dashboard/usage")
async def dashboard_usage(current_user: dict = Depends(get_current_user)):
    """Return plan and usage summary for dashboard upsell cards."""
    user_id = current_user["user_id"]
    user_tier = get_user_tier_enhanced(user_id)
    tier_name = "admin" if bool(current_user.get("is_admin")) else ("basic" if user_tier.value == "free" else user_tier.value)
    month_key = get_month_key()

    saved_resumes = list_resume_documents(user_id)
    resume_limit = get_saved_resume_limit_for_user(current_user)
    version_limit = get_version_limit_for_user(current_user)
    analysis_limit = get_resume_analysis_limit_for_user(current_user)

    version_count = count_user_rows(user_id, "resume_versions")
    analysis_total_count = count_user_rows(user_id, "resume_analysis_results")
    analysis_month_count = get_usage_count(user_id, "resume_analysis", month_key)
    pdf_month_count = get_usage_count(user_id, "pdf_downloads", month_key)

    return {
        "success": True,
        "tier": tier_name,
        "month_year": month_key,
        "usage": {
            "resumes": {
                "used": len(saved_resumes),
                "limit": resume_limit,
                "unlimited": resume_limit is None,
            },
            "resume_versions": {
                "used": version_count,
                "limit": version_limit,
                "unlimited": version_limit is None,
            },
            "resume_analysis_monthly": {
                "used": analysis_month_count,
                "limit": analysis_limit,
                "unlimited": analysis_limit is None,
            },
            "resume_analysis_total": {
                "used": analysis_total_count,
                "limit": None,
                "unlimited": True,
            },
            "pdf_downloads_monthly": {
                "used": pdf_month_count,
                "limit": TIER_LIMITS[user_tier]["pdf_downloads_per_month"],
                "unlimited": TIER_LIMITS[user_tier]["pdf_downloads_per_month"] == -1,
            },
        },
        "upgrade": {
            "show": tier_name == "basic",
            "url": "/pricing",
            "message": "Upgrade to Premium for unlimited resumes, unlimited ATS analyses and full version history.",
        },
    }


@router.get("/resumes")
async def my_resumes(current_user: dict = Depends(get_current_user)):
    """List the authenticated user's saved resumes."""
    return {
        "success": True,
        "resumes": list_resume_documents(current_user["user_id"]),
    }


@router.get("/resumes/can-create")
async def can_create_resume(current_user: dict = Depends(get_current_user)):
    """Return whether the authenticated user can create another saved resume."""
    saved_resumes = list_resume_documents(current_user["user_id"])
    current_count = len(saved_resumes)
    saved_resume_limit = get_saved_resume_limit_for_user(current_user)
    can_create = saved_resume_limit is None or current_count < saved_resume_limit
    user_tier = get_user_tier_enhanced(current_user["user_id"])

    return {
        "success": True,
        "can_create": can_create,
        "current_count": current_count,
        "saved_resume_limit": saved_resume_limit,
        "current_tier": "basic" if user_tier.value == "free" else user_tier.value,
        "message": "You can create another resume." if can_create else "Your Basic plan includes 1 saved resume. Edit your existing resume or upgrade to save more resumes.",
        "upgrade_required": not can_create,
        "upgrade_url": "/pricing" if not can_create else None,
    }


@router.get("/resumes/{document_id}")
async def view_resume(document_id: str, current_user: dict = Depends(get_current_user)):
    """View one saved resume document."""
    document = get_resume_document(current_user["user_id"], document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    return {
        "success": True,
        "resume": document,
    }


@router.get("/resumes/{document_id}/versions")
async def resume_versions(document_id: str, current_user: dict = Depends(get_current_user)):
    """List version history for one saved resume."""
    document = get_resume_document(current_user["user_id"], document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    max_versions = get_version_limit_for_user(current_user)
    versions = list_resume_versions(current_user["user_id"], document_id)
    if max_versions is not None:
        versions = versions[:max_versions]

    return {
        "success": True,
        "versions": versions,
        "version_limit": max_versions,
    }


@router.get("/resumes/{document_id}/versions/{version_id}")
async def view_resume_version(
    document_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """View one previous resume version."""
    document = get_resume_document(current_user["user_id"], document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    version = get_resume_version(current_user["user_id"], document_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")

    return {
        "success": True,
        "version": version,
    }


@router.put("/resumes/{document_id}")
async def update_resume(
    document_id: str,
    update_data: ResumeDocumentUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update a saved resume document."""
    document = update_resume_document(
        user_id=current_user["user_id"],
        document_id=document_id,
        title=update_data.title,
        resume_text=update_data.resume_text,
        cover_letter_text=update_data.cover_letter_text,
        template=update_data.template,
        max_versions=get_version_limit_for_user(current_user),
    )

    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    return {
        "success": True,
        "message": "Resume updated successfully",
        "resume": document,
    }


@router.post("/resumes/{document_id}/versions/{version_id}/restore")
async def restore_resume_version(
    document_id: str,
    version_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Restore a saved resume from a previous version."""
    document = get_resume_document(current_user["user_id"], document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    version = get_resume_version(current_user["user_id"], document_id, version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")

    restored_document = update_resume_document(
        user_id=current_user["user_id"],
        document_id=document_id,
        title=version.get("title"),
        resume_text=version.get("resume_text"),
        cover_letter_text=version.get("cover_letter_text"),
        template=version.get("template"),
        max_versions=get_version_limit_for_user(current_user),
    )

    return {
        "success": True,
        "message": "Resume version restored successfully",
        "resume": restored_document,
    }


@router.post("/resumes/{document_id}/duplicate")
async def duplicate_resume(document_id: str, current_user: dict = Depends(get_current_user)):
    """Duplicate a saved resume document."""
    saved_resumes = list_resume_documents(current_user["user_id"])
    saved_resume_limit = get_saved_resume_limit_for_user(current_user)
    if saved_resume_limit is not None and len(saved_resumes) >= saved_resume_limit:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Saved resume limit reached for your current plan",
                "upgrade_required": True,
                "current_count": len(saved_resumes),
                "saved_resume_limit": saved_resume_limit,
                "upgrade_url": "/pricing",
            },
        )

    document = duplicate_resume_document(current_user["user_id"], document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    return {
        "success": True,
        "message": "Resume duplicated successfully",
        "resume": document,
    }


@router.delete("/resumes/{document_id}")
async def delete_resume(document_id: str, current_user: dict = Depends(get_current_user)):
    """Delete a saved resume document."""
    deleted = delete_resume_document(current_user["user_id"], document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resume document not found")

    return {
        "success": True,
        "message": "Resume deleted successfully",
    }


@router.post("/resumes/{document_id}/pdf")
async def regenerate_resume_pdf(document_id: str, current_user: dict = Depends(get_current_user)):
    """Generate and download a fresh PDF from a saved resume document."""
    document = get_resume_document(current_user["user_id"], document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    if not check_pdf_download_limit(current_user["user_id"]):
        user_tier = get_user_tier_enhanced(current_user["user_id"])
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Monthly PDF download limit reached for your current plan",
                "upgrade_required": True,
                "current_tier": user_tier.value,
                "upgrade_url": "/pricing",
            },
        )

    pdf_bytes = generate_resume_pdf(
        resume_text=document.get("resume_text", ""),
        cover_letter=document.get("cover_letter_text", ""),
    )

    track_pdf_usage(current_user["user_id"])

    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in document.get("title", "resume")).strip()
    safe_title = safe_title.replace(" ", "_") or "resume"

    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={safe_title}.pdf"},
    )
