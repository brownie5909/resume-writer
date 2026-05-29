from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from io import BytesIO
import uuid

from routes.user_management import get_current_user, get_user_tier_enhanced, TIER_LIMITS, get_db
from app.services.pdf_service import generate_resume_pdf
from app.services.resume_document_service import (
    list_resume_documents,
    get_resume_document,
    update_resume_document,
    duplicate_resume_document,
    delete_resume_document,
)

router = APIRouter()


class ResumeDocumentUpdate(BaseModel):
    title: Optional[str] = None
    resume_text: Optional[str] = None
    cover_letter_text: Optional[str] = None
    template: Optional[str] = None


def track_pdf_usage(user_id: str):
    from datetime import datetime

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
    from datetime import datetime

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


@router.get("/resumes")
async def my_resumes(current_user: dict = Depends(get_current_user)):
    """List the authenticated user's saved resumes."""
    return {
        "success": True,
        "resumes": list_resume_documents(current_user["user_id"]),
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
    )

    if not document:
        raise HTTPException(status_code=404, detail="Resume document not found")

    return {
        "success": True,
        "message": "Resume updated successfully",
        "resume": document,
    }


@router.post("/resumes/{document_id}/duplicate")
async def duplicate_resume(document_id: str, current_user: dict = Depends(get_current_user)):
    """Duplicate a saved resume document."""
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
