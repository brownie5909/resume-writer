# Copy this EXACTLY into: main.py

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from typing import Optional, Dict, Any
from io import BytesIO
import uuid
import os
import json
import re
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr, validator

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

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Security configuration functions
def get_allowed_origins():
    """Get allowed origins from environment variable with proper defaults"""
    origins_env = os.getenv("ALLOWED_ORIGINS", "")
    
    if origins_env:
        origins = [origin.strip() for origin in origins_env.split(",") if origin.strip()]
    else:
        # Default origins for development and production
        origins = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8000",
            "https://jobreadytools.com.au",
            "https://www.jobreadytools.com.au"
        ]
    
    print(f"🌐 CORS allowed origins: {origins}")
    return origins

def get_trusted_hosts():
    """Get trusted hosts from environment variable with proper defaults"""
    hosts_env = os.getenv("TRUSTED_HOSTS", "")
    
    if hosts_env:
        hosts = [host.strip() for host in hosts_env.split(",") if host.strip()]
    else:
        # Default hosts for development and production
        hosts = [
            "localhost", 
            "127.0.0.1", 
            "*.localhost",
            "resume-writer.onrender.com",
            "*.onrender.com",
            "jobreadytools.com.au",
            "www.jobreadytools.com.au",
            "*.jobreadytools.com.au"
        ]
    
    print(f"🔒 Trusted hosts: {hosts}")
    return hosts

# Validate SECRET_KEY for production
SECRET_KEY = os.getenv("SECRET_KEY", "")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

if ENVIRONMENT == "production":
    if not SECRET_KEY or SECRET_KEY == "hire-ready-super-secret-jwt-key-change-this-in-production-123456789":
        raise ValueError("❌ CRITICAL: You must set a secure SECRET_KEY for production!")
    print("✅ Production mode: SECRET_KEY is configured")
else:
    if not SECRET_KEY:
        print("⚠️  WARNING: Using default SECRET_KEY in development. Change for production!")

app = FastAPI(
    title="Hire Ready API",
    description="AI-powered job application tools with comprehensive user and subscription management",
    version="2.1.0"
)

# Add security middleware (order matters!)
# 1. Trusted Host Middleware first
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_trusted_hosts()
)

# 2. CORS Middleware second
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"]
)

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
        # Basic sanitization - allow only letters, spaces, hyphens, apostrophes
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

# Enhanced PDF storage with expiration and user association
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
        
        # Get or create usage record
        cursor.execute("""
            SELECT usage_count FROM usage_tracking 
            WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
        """, (user_id, current_month))
        
        result = cursor.fetchone()
        
        if result:
            # Update existing record
            new_count = result[0] + 1
            cursor.execute("""
                UPDATE usage_tracking 
                SET usage_count = ?, last_reset = CURRENT_TIMESTAMP
                WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
            """, (new_count, user_id, current_month))
        else:
            # Create new record
            cursor.execute("""
                INSERT INTO usage_tracking (usage_id, user_id, feature_name, usage_count, month_year)
                VALUES (?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), user_id, 'pdf_downloads', 1, current_month))
        
        conn.commit()

def check_pdf_download_limit(user_id: str) -> bool:
    """Check if user can download more PDFs this month"""
    user_tier = get_user_tier_enhanced(user_id)
    
    # Simple tier limits
    tier_limits = {
        "free": {"pdf_downloads_per_month": 1},
        "premium": {"pdf_downloads_per_month": -1},
        "professional": {"pdf_downloads_per_month": -1}
    }
    
    limit = tier_limits.get(user_tier.value, {"pdf_downloads_per_month": 1})["pdf_downloads_per_month"]
    
    # Unlimited downloads for premium users
    if limit == -1:
        return True
    
    # Check current month usage
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

@app.post("/api/generate-resume")
async def generate_resume(resume_request: ResumeRequest, current_user: dict = Depends(get_current_user)):
    """Enhanced resume generation with user authentication and comprehensive validation"""
    
    # Clean expired PDFs
    clean_pdf_store()

    # Extract validated data
    data = resume_request.data
    template_choice = resume_request.template_choice
    generate_cover_letter = resume_request.generate_cover_letter

    # Mock AI resume generation for testing
    resume_text = f"""# Professional Resume for {data.full_name}

## Contact Information
- **Name:** {data.full_name}
- **Email:** {data.email}
- **Phone:** {data.phone or 'Not provided'}

## Professional Summary
Results-driven {data.job_title} with proven experience in delivering exceptional outcomes. 
{data.summary or 'Dedicated professional with strong problem-solving skills and collaborative approach.'}

## Professional Experience
**{data.job_title}** - {data.company or 'Previous Company'}
- {data.responsibilities or 'Led key initiatives and delivered measurable results'}
- Achieved significant improvements in efficiency and performance
- Collaborated with cross-functional teams to drive success

## Education
{data.degree or 'Relevant Degree'} - {data.school or 'Educational Institution'}

## Key Skills
{data.skills or 'Leadership, Problem-solving, Communication, Technical expertise'}

{f'''
## Cover Letter

Dear Hiring Manager,

I am writing to express my strong interest in the {data.job_title} position. With my background and experience, I am confident that I would be a valuable addition to your team.

My experience includes {data.responsibilities or 'delivering exceptional results and leading successful projects'}. I am particularly drawn to this opportunity because it aligns perfectly with my career goals and expertise.

I would welcome the opportunity to discuss how my skills and enthusiasm can contribute to your organization's continued success.

Sincerely,
{data.full_name}
''' if generate_cover_letter else ''}"""

    # Create a mock PDF entry (but don't track usage yet)
    pdf_id = str(uuid.uuid4())
    pdf_store[pdf_id] = {
        'data': resume_text.encode('utf-8'),  # Mock PDF data
        'created_at': datetime.now(),
        'filename': f"resume_{data.full_name.replace(' ', '_')}_{template_choice}.pdf",
        'user_id': current_user["user_id"],
        'downloaded': False  # Track if actually downloaded
    }

    download_url = f"/api/download-resume/{pdf_id}"

    return JSONResponse({
        "resume_text": resume_text.strip(),
        "pdf_url": download_url,
        "template_used": template_choice,
        "success": True,
        "user_info": {
            "tier": current_user.get("tier", "free"),
            "message": "Resume generated. PDF download will count against your limit when downloaded."
        }
    })

@app.get("/api/download-resume/{pdf_id}")
async def download_resume(pdf_id: str, current_user: dict = Depends(get_current_user)):
    """Enhanced PDF download with user verification"""
    pdf_entry = pdf_store.get(pdf_id)
    if not pdf_entry:
        raise HTTPException(status_code=404, detail="Resume not found or expired")

    # Verify user owns this PDF
    if pdf_entry.get('user_id') != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check PDF download limit ONLY when actually downloading
    if not pdf_entry.get('downloaded', False):  # Only check limit for first download
        if not check_pdf_download_limit(current_user["user_id"]):
            user_tier = get_user_tier_enhanced(current_user["user_id"])
            raise HTTPException(status_code=403, detail={
                "error": f"Monthly PDF download limit reached (1 download for free tier)",
                "upgrade_required": True,
                "current_tier": user_tier.value,
                "upgrade_url": "/pricing"
            })
        
        # Track PDF usage only on actual download
        track_pdf_usage(current_user["user_id"])
        pdf_entry['downloaded'] = True

    pdf_data = pdf_entry['data'] if isinstance(pdf_entry, dict) else pdf_entry
    filename = pdf_entry.get('filename', f'resume_{pdf_id}.txt') if isinstance(pdf_entry, dict) else f'resume_{pdf_id}.txt'

    return StreamingResponse(
        BytesIO(pdf_data), 
        media_type="text/plain",  # Using text for testing instead of PDF
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/api/user/usage")
async def get_user_usage(current_user: dict = Depends(get_current_user)):
    """Get user's current usage statistics"""
    current_month = datetime.now().strftime("%Y-%m")
    user_tier = get_user_tier_enhanced(current_user["user_id"])
    tier_limits = TIER_LIMITS[user_tier]
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Get PDF downloads usage
        cursor.execute("""
            SELECT usage_count FROM usage_tracking 
            WHERE user_id = ? AND feature_name = 'pdf_downloads' AND month_year = ?
        """, (current_user["user_id"], current_month))
        
        pdf_result = cursor.fetchone()
        pdf_downloads_used = pdf_result[0] if pdf_result else 0
        
        # Get all usage for this month
        cursor.execute("""
            SELECT feature_name, usage_count FROM usage_tracking 
            WHERE user_id = ? AND month_year = ?
        """, (current_user["user_id"], current_month))
        
        all_usage = dict(cursor.fetchall())
    
    return {
        "current_tier": user_tier.value,
        "tier_description": tier_limits["description"],
        "current_month": current_month,
        "usage": {
            "pdf_downloads": {
                "used": pdf_downloads_used,
                "limit": tier_limits["pdf_downloads_per_month"],
                "unlimited": tier_limits["pdf_downloads_per_month"] == -1
            }
        },
        "all_features_usage": all_usage,
        "features_available": tier_limits["features"]
    }

@app.get("/api/user/documents")
async def get_user_documents(current_user: dict = Depends(get_current_user)):
    """Get user's generated documents (PDFs in memory)"""
    user_pdfs = []
    
    for pdf_id, pdf_data in pdf_store.items():
        if isinstance(pdf_data, dict) and pdf_data.get('user_id') == current_user["user_id"]:
            user_pdfs.append({
                "pdf_id": pdf_id,
                "filename": pdf_data.get('filename', 'resume.pdf'),
                "created_at": pdf_data.get('created_at').isoformat() if pdf_data.get('created_at') else None,
                "download_url": f"/api/download-resume/{pdf_id}"
            })
    
    # Sort by creation time (newest first)
    user_pdfs.sort(key=lambda x: x['created_at'] or '', reverse=True)
    
    return {
        "documents": user_pdfs,
        "total_count": len(user_pdfs),
        "user_tier": current_user.get("tier", "free")
    }

@app.get("/api/health")
async def health_check():
    """Health check endpoint with CORS info for debugging"""
    return {
        "status": "healthy", 
        "service": "hire-ready-api",
        "version": "2.1.0",
        "features": ["authentication", "resume-builder", "ai-analysis", "admin-panel"],
        "cors_origins": get_allowed_origins(),
        "environment": ENVIRONMENT
    }

@app.get("/api/templates")
async def get_templates():
    """Get available resume templates (public endpoint)"""
    return {
        "templates": [
            {"id": "default", "name": "Modern", "description": "Clean, professional design suitable for most industries"},
            {"id": "conservative", "name": "Conservative", "description": "Traditional format perfect for formal industries"},
            {"id": "creative", "name": "Creative", "description": "Eye-catching design for creative professionals"},
            {"id": "executive", "name": "Executive", "description": "Authoritative layout for senior positions"}
        ]
    }

# Public endpoint for checking if someone can register
@app.post("/api/auth/check-email")
async def check_email_availability(request: Request):
    """Check if email is available for registration"""
    try:
        body = await request.json()
        email = body.get("email", "").lower().strip()
        
        if not email:
            return JSONResponse(status_code=400, content={"error": "Email is required"})
        
        from routes.user_management import get_user_by_email
        existing_user = get_user_by_email(email)
        
        return {
            "email": email,
            "available": existing_user is None,
            "message": "Email is available" if existing_user is None else "Email is already registered"
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": "Check failed"})

# Enhanced route for generating anonymous resumes (for non-authenticated users)
@app.post("/api/generate-resume-guest")
async def generate_resume_guest(request: Request):
    """Generate resume for guest users (limited functionality)"""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid request format"})

    # Extract data
    data = body.get("data", {})
    template_choice = body.get("template_choice", "default")

    # Validation
    if not data.get("full_name") or not data.get("email") or not data.get("job_title"):
        return JSONResponse(status_code=400, content={
            "error": "Full Name, Email, and Job Title are required fields."
        })

    # Basic resume for guests
    resume_text = f"""# Resume for {data.get('full_name')} (Guest Mode)

Contact: {data.get('email')}
Position: {data.get('job_title')}

This is a basic resume generated in guest mode.
Register for full features including PDF downloads and AI analysis.
"""

    return JSONResponse({
        "resume_text": resume_text.strip(),
        "template_used": template_choice,
        "success": True,
        "guest_mode": True,
        "message": "Register for PDF downloads and advanced features",
        "register_url": "/api/auth/register"
    })

# Dashboard data endpoint
@app.get("/api/dashboard/data")
async def get_dashboard_data(current_user: dict = Depends(get_current_user)):
    """Get comprehensive dashboard data for user"""
    
    try:
        # Get usage stats
        usage_response = await get_user_usage(current_user)
        
        # Get documents
        documents_response = await get_user_documents(current_user)
        
        # Get tier info
        user_tier = get_user_tier_enhanced(current_user["user_id"])
        
        return {
            "user": {
                "user_id": current_user["user_id"],
                "email": current_user["email"],
                "full_name": current_user["full_name"],
                "tier": current_user["tier"],
                "is_verified": current_user["is_verified"],
                "created_at": current_user["created_at"],
                "last_login": current_user.get("last_login")
            },
            "usage": usage_response,
            "documents": documents_response,
            "tier_info": {
                "current_tier": user_tier.value,
                "description": TIER_LIMITS[user_tier]["description"],
                "features": TIER_LIMITS[user_tier]["features"]
            }
        }
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Failed to load dashboard data: {str(e)}"})

# Serve the dashboard HTML
@app.get("/dashboard", response_class=HTMLResponse)
async def serve_dashboard():
    """Serve the user dashboard HTML page"""
    # You can serve the dashboard HTML artifact here
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Hire Ready Dashboard</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body>
        <h1>Hire Ready Dashboard</h1>
        <p>Dashboard loading... (Add the HTML from the dashboard artifact here)</p>
        <p><a href="/docs">View API Documentation</a></p>
    </body>
    </html>
    """

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Welcome to Hire Ready API",
        "version": "2.1.0",
        "features": ["Authentication", "Resume Building", "AI Analysis", "Admin Panel"],
        "endpoints": {
            "docs": "/docs",
            "health": "/api/health",
            "dashboard": "/dashboard",
            "register": "/api/auth/register",
            "login": "/api/auth/login"
        },
        "test_users": {
            "regular": "test@hireready.com / testpass123",
            "admin": "admin@hireready.com / admin123"
        },
        "cors_configured_for": get_allowed_origins()
    }

# Add these debug routes to your main.py (before the "if __name__" section)

@app.get("/api/debug/routes")
async def debug_routes():
    """Debug endpoint to show all available routes"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, 'name', 'unnamed')
            })
    
    return {
        "total_routes": len(routes),
        "routes": sorted(routes, key=lambda x: x['path']),
        "api_routes": [r for r in routes if r['path'].startswith('/api/')]
    }

@app.get("/api/debug/test-research")
async def test_research_endpoint():
    """Test the research endpoint directly"""
    try:
        # Import the research function
        from routes.interview import research_job_application, JobResearchInput
        
        # Test with sample data
        test_payload = JobResearchInput(
            company_name="Test Company",
            job_role="Test Role"
        )
        
        result = await research_job_application(test_payload)
        return {
            "test_status": "success",
            "endpoint_working": True,
            "sample_result": result
        }
    except Exception as e:
        return {
            "test_status": "error",
            "endpoint_working": False,
            "error": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=int(os.getenv("PORT", 8000)),
        reload=True
    )