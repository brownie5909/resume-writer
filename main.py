from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from app.core.middleware import setup_middleware
from typing import Optional
from io import BytesIO
import uuid
import re
from routes.resume_documents import router as resume_documents_router
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, validator

from app.services.resume_generator import generate_resume_with_ai
from app.services.pdf_service import generate_resume_pdf
from app.services.admin_setup import auto_create_admin_from_env

from routes.interview import router as interview_router
from routes.resume_analysis import router as resume_analysis_router
from routes.cover_letter import router as cover_letter_router
from routes.user_management import (
    router as user_management_router,
    get_current_user,
    get_user_tier_enhanced,
    TIER_LIMITS,
    get_db
)
from routes.admin import router as admin_router
from routes.subscriptions import router as subscriptions_router


app = FastAPI(
    title="Hire Ready API",
    description="AI-powered job application tools with user, subscription, resume and PDF management",
    version="2.2.4"
)

setup_middleware(app)

try:
    admin_setup_result = auto_create_admin_from_env()
    print(f"🔐 Admin setup: {admin_setup_result}")
except Exception as admin_error:
    print(f"❌ Admin auto-setup failed: {str(admin_error)}")


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

    @validator("full_name")
    def validate_full_name(cls, value):
        if not value or len(value.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters")
        if len(value) > 100:
            raise ValueError("Full name too long")
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", value):
            raise ValueError("Full name contains invalid characters")
        return value.strip()

    @validator("job_title")
    def validate_job_title(cls, value):
        if not value or len(value.strip()) < 2:
            raise ValueError("Job title must be at least 2 characters")
        if len(value) > 200:
            raise ValueError("Job title too long")
        return value.strip()

    @validator("phone")
    def validate_phone(cls, value):
        if value and len(value) > 50:
            raise ValueError("Phone number too long")
        return value


class ResumeRequest(BaseModel):
    data: ResumeData
    template_choice: Optional[str] = "default"
    generate_cover_letter: Optional[bool] = False

    @validator("template_choice")
    def validate_template(cls, value):
        allowed_templates = ["default", "conservative", "creative", "executive"]
        if value not in allowed_templates:
            raise ValueError(f"Invalid template. Allowed: {', '.join(allowed_templates)}")
        return value


app.include_router(user_management_router, prefix="/api", tags=["Authentication & Users"])
app.include_router(admin_router, prefix="/api", tags=["Admin Management"])
app.include_router(subscriptions_router, prefix="/api", tags=["Subscription Management"])
app.include_router(interview_router, prefix="/api", tags=["Interview"])
app.include_router(resume_analysis_router, prefix="/api", tags=["Resume Analysis"])
app.include_router(cover_letter_router, prefix="/api", tags=["Cover Letter"])
app.include_router(
    resume_documents_router,
    prefix="/api",
    tags=["Resume Documents"]
)


pdf_store = {}
PDF_EXPIRY_HOURS = 24


def clean_pdf_store():
    current_time = datetime.now()
    expired_keys = []

    for pdf_id, data in pdf_store.items():
        if isinstance(data, dict) and data.get("created_at"):
            if current_time - data["created_at"] > timedelta(hours=PDF_EXPIRY_HOURS):
                expired_keys.append(pdf_id)

    for key in expired_keys:
        del pdf_store[key]


def track_pdf_usage(user_id: str):
    current_month = datetime.now().strftime("%Y-%m")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT usage_count FROM usage_tracking
            WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
            """,
            (user_id, current_month)
        )
        result = cursor.fetchone()

        if result:
            cursor.execute(
                """
                UPDATE usage_tracking
                SET usage_count = ?, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
                """,
                (result[0] + 1, user_id, current_month)
            )
        else:
            cursor.execute(
                """
                INSERT INTO usage_tracking (usage_id, user_id, feature_name, usage_count, month_year)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(uuid.uuid4()), user_id, "pdf_downloads", 1, current_month)
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
            (user_id, current_month)
        )
        result = cursor.fetchone()
        current_usage = result[0] if result else 0
        return current_usage < limit


async def build_resume_response(
    resume_request: ResumeRequest,
    owner_id: Optional[str] = None,
    is_guest: bool = False
):
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

    if is_guest:
        return JSONResponse(response_payload)

    pdf_bytes = generate_resume_pdf(
        resume_text=resume_text,
        cover_letter=cover_letter
    )

    pdf_id = str(uuid.uuid4())
    safe_name = data.full_name.replace(" ", "_")

    pdf_store[pdf_id] = {
        "data": pdf_bytes,
        "created_at": datetime.now(),
        "filename": f"resume_{safe_name}_{template_choice}.pdf",
        "user_id": owner_id,
        "is_guest": False,
        "downloaded": False
    }

    response_payload["pdf_url"] = f"/api/download-resume/{pdf_id}"
    response_payload["requires_login_for_pdf"] = False

    return JSONResponse(response_payload)


@app.post("/api/generate-resume-guest")
async def generate_resume_guest(resume_request: ResumeRequest):
    try:
        return await build_resume_response(
            resume_request=resume_request,
            owner_id=None,
            is_guest=True
        )
    except Exception as error:
        print(f"❌ Guest resume generation error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Guest resume generation failed: {str(error)}"}
        )


@app.post("/api/generate-resume")
async def generate_resume(resume_request: ResumeRequest, current_user: dict = Depends(get_current_user)):
    try:
        return await build_resume_response(
            resume_request=resume_request,
            owner_id=current_user["user_id"],
            is_guest=False
        )
    except Exception as error:
        print(f"❌ Resume generation error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Resume generation failed: {str(error)}"}
        )


@app.get("/api/download-resume-guest/{pdf_id}")
async def download_resume_guest(pdf_id: str):
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
    pdf_entry = pdf_store.get(pdf_id)

    if not pdf_entry:
        raise HTTPException(status_code=404, detail="Resume not found or expired")

    if pdf_entry.get("user_id") != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    if not pdf_entry.get("downloaded", False):
        if not check_pdf_download_limit(current_user["user_id"]):
            user_tier = get_user_tier_enhanced(current_user["user_id"])
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Monthly PDF download limit reached for your current plan",
                    "upgrade_required": True,
                    "current_tier": user_tier.value,
                    "upgrade_url": "/pricing"
                }
            )

        track_pdf_usage(current_user["user_id"])
        pdf_entry["downloaded"] = True

    return StreamingResponse(
        BytesIO(pdf_entry["data"]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={pdf_entry.get('filename', f'resume_{pdf_id}.pdf')}"}
    )


@app.get("/")
def root():
    return {"message": "Hire Ready API is running", "version": "2.2.4"}


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "hire-ready-api", "version": "2.2.4"}
