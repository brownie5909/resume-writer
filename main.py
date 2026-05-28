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
from app.services.admin_setup import auto_create_admin_from_env

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
    version="2.2.3"
)

setup_middleware(app)

# Automatically create/repair admin account during startup if enabled.
try:
    admin_setup_result = auto_create_admin_from_env()
    print(f"🔐 Admin setup: {admin_setup_result}")
except Exception as admin_error:
    print(f"❌ Admin auto-setup failed: {str(admin_error)}")


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