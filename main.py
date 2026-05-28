# Copy this EXACTLY into: main.py

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from app.core.middleware import setup_middleware
from typing import Optional, Dict, Any
from io import BytesIO
import uuid
import os
import json
import re
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, validator
from app.core.config import SECRET_KEY, ENVIRONMENT
from app.services.resume_generator import generate_resume_with_ai
from app.services.pdf_service import generate_resume_pdf

# Import your route modules
from routes.interview import router as interview_router
from routes.resume_analysis import router as resume_analysis_router
from routes.cover_letter import router as cover_letter_router
from routes.user_management import (
    router as user_management_router,
    get_current_user,
    require_feature_access_auth,
    get_user_tier_enhanced,
    TIER_LIMITS,
    get_db
)
from routes.admin import router as admin_router
from routes.subscriptions import router as subscriptions_router


app = FastAPI(
    title="Hire Ready API",
    description="AI-powered job application tools with comprehensive user and subscription management",
    version="2.2.2"
)

setup_middleware(app)


# Request validation models
class ResumeData(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    job_title: str
    company: Optional[str] = None
    summary: Optional[str] = None
    responsibilities: Optional[str] = None
    degree: Optional[str] = None
    school: Optional[str] = None
    skills: Optional[str] = None

    @validator('full_name')
    def validate_full_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters')
        if len(v) > 100:
            raise ValueError('Full name too long')
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", v):
            raise ValueError('Full name contains invalid characters')
        return v.strip()

    @validator('job_title')
    def validate_job_title(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError('Job title must be at least 2 characters')
        if len(v) > 200:
            raise ValueError('Job title too long')
        return v.strip()

    @validator('phone')
    def validate_phone(cls, v):
        if v and len(v) > 50:
            raise ValueError('Phone number too long')
        return v


class ResumeRequest(BaseModel):
    data: ResumeData
    template_choice: Optional[str] = "default"
    generate_cover_letter: Optional[bool] = False

    @validator('template_choice')
    def validate_template(cls, v):
        allowed_templates = ["default", "conservative", "creative", "executive"]
        if v not in allowed_templates:
            raise ValueError(f'Invalid template. Allowed: {", ".join(allowed_templates)}')
        return v


# Include all routers
app.include_router(user_management_router, prefix="/api", tags=["Authentication & Users"])
app.include_router(admin_router, prefix="/api", tags=["Admin Management"])
app.include_router(subscriptions_router, prefix="/api", tags=["Subscription Management"])
app.include_router(interview_router, prefix="/api", tags=["Interview"])
app.include_router(resume_analysis_router, prefix="/api", tags=["Resume Analysis"])
app.include_router(cover_letter_router, prefix="/api", tags=["Cover Letter"])


# Temporary in-memory PDF storage. Later we should move this to persistent storage.
pdf_store = {}
PDF_EXPIRY_HOURS = 24


def clean_pdf_store():
    """Remove expired PDFs from memory"""
    current_time = datetime.now()
    expired_keys = []

    for pdf_id, data in pdf_store.items():
        if isinstance(data, dict) and 'created_at' in data:
            if current_time - data['created_at'] > timedelta(hours=PDF_EXPIRY_HOURS):
                expired_keys.append(pdf_id)

    for key in expired_keys:
        del pdf_store[key]


def track_pdf_usage(user_id: str):
    """Track PDF download usage for the user"""
    current_month = datetime.now().strftime("%Y-%m")

    with get_db() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
        """, (user_id, current_month))

        result = cursor.fetchone()

        if result:
            new_count = result[0] + 1
            cursor.execute("""
                UPDATE usage_tracking
                SET usage_count = ?, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
            """, (new_count, user_id, current_month))
        else:
            cursor.execute("""
                INSERT INTO usage_tracking (usage_id, user_id, feature_name, usage_count, month_year)
                VALUES (?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), user_id, 'pdf_downloads', 1, current_month))

        conn.commit()


def check_pdf_download_limit(user_id: str) -> bool:
    """Check if user can download more PDFs this month"""
    user_tier = get_user_tier_enhanced(user_id)

    tier_limits = {
        "basic": {"pdf_downloads_per_month": 1},
        "free": {"pdf_downloads_per_month": 1},
        "premium": {"pdf_downloads_per_month": -1},
        "professional": {"pdf_downloads_per_month": -1}
    }

    limit = tier_limits.get(user_tier.value, {"pdf_downloads_per_month": 1})["pdf_downloads_per_month"]

    if limit == -1:
        return True

    current_month = datetime.now().strftime("%Y-%m")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
        """, (user_id, current_month))

        result = cursor.fetchone()
        current_usage = result[0] if result else 0

        return current_usage < limit


async def build_resume_response(
    resume_request: ResumeRequest,
    owner_id: Optional[str] = None,
    is_guest: bool = False
):
    """Shared resume generation logic for guest previews and logged-in PDF generation."""
    clean_pdf_store()

    data = resume_request.data
    template_choice = resume_request.template_choice
    generate_cover_letter = resume_request.generate_cover_letter

    ai_result = await generate_resume_with_ai(
        data=data,
        template_choice=template_choice,
        generate_cover_letter=generate_cover_letter
    )

    resume_text = ai_result.get("resume_text", "")
    cover_letter = ai_result.get("cover_letter", "")
    ats_notes = ai_result.get("ats_notes", "")

    response_payload = {
        "success": True,
        "resume_text": resume_text,
        "cover_letter": cover_letter,
        "ats_notes": ats_notes,
        "template_used": template_choice,
        "requires_login_for_pdf": is_guest,
        "pdf_url": None,
        "user_info": {
            "tier": "guest" if is_guest else "authenticated",
            "message": "AI resume generated successfully. Log in to download a PDF." if is_guest else "AI resume generated successfully. PDF download is available for your account."
        }
    }

    # Guests can preview generated output, but cannot create/download PDFs.
    if is_guest:
        return JSONResponse(response_payload)

    pdf_bytes = generate_resume_pdf(
        resume_text=resume_text,
        cover_letter=cover_letter
    )

    pdf_id = str(uuid.uuid4())
    safe_name = data.full_name.replace(' ', '_')

    pdf_store[pdf_id] = {
        'data': pdf_bytes,
        'created_at': datetime.now(),
        'filename': f"resume_{safe_name}_{template_choice}.pdf",
        'user_id': owner_id,
        'is_guest': False,
        'downloaded': False
    }

    response_payload["pdf_url"] = f"/api/download-resume/{pdf_id}"
    response_payload["requires_login_for_pdf"] = False

    return JSONResponse(response_payload)


@app.post("/api/generate-resume-guest")
async def generate_resume_guest(resume_request: ResumeRequest):
    """Guest endpoint used by WordPress to preview AI output before login."""
    try:
        return await build_resume_response(
            resume_request=resume_request,
            owner_id=None,
            is_guest=True
        )
    except Exception as e:
        print(f"❌ Guest resume generation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Guest resume generation failed: {str(e)}"
            }
        )


@app.post("/api/generate-resume")
async def generate_resume(resume_request: ResumeRequest, current_user: dict = Depends(get_current_user)):
    """Generate AI-powered ATS-friendly resumes and PDFs for logged-in users."""
    try:
        return await build_resume_response(
            resume_request=resume_request,
            owner_id=current_user["user_id"],
            is_guest=False
        )
    except Exception as e:
        print(f"❌ Resume generation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Resume generation failed: {str(e)}"
            }
        )


@app.get("/api/download-resume-guest/{pdf_id}")
async def download_resume_guest(pdf_id: str):
    """Guest PDF downloads are intentionally blocked."""
    raise HTTPException(
        status_code=403,
        detail={
            "error": "PDF downloads require a logged-in account",
            "login_required": True,
            "login_url": "/login"
        }
    )


@app.get("/api/download-resume/{pdf_id}")
async def download_resume(pdf_id: str, current_user: dict = Depends(get_current_user)):
    """Authenticated PDF download with user verification and usage tracking."""
    pdf_entry = pdf_store.get(pdf_id)

    if not pdf_entry:
        raise HTTPException(status_code=404, detail="Resume not found or expired")

    if pdf_entry.get('user_id') != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if not pdf_entry.get('downloaded', False):
        if not check_pdf_download_limit(current_user["user_id"]):
            user_tier = get_user_tier_enhanced(current_user["user_id"])
            raise HTTPException(status_code=403, detail={
                "error": "Monthly PDF download limit reached for your current plan",
                "upgrade_required": True,
                "current_tier": user_tier.value,
                "upgrade_url": "/pricing"
            })

        track_pdf_usage(current_user["user_id"])
        pdf_entry['downloaded'] = True

    pdf_data = pdf_entry['data']
    filename = pdf_entry.get('filename', f'resume_{pdf_id}.pdf')

    return StreamingResponse(
        BytesIO(pdf_data),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.get("/")
def root():
    return {"message": "Hire Ready API is running", "version": "2.2.2"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "hire-ready-api"}
