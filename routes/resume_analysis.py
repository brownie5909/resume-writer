# Copy this EXACTLY into: routes/resume_analysis.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
from app.utils.file_parser import extract_text_from_file
from app.services.openai_service import analyze_resume_with_ai
import os
import magic
from typing import Optional

router = APIRouter()

# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/rtf"
}
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}

def validate_file(file: UploadFile) -> None:
    """Comprehensive file validation"""
    
    # Check if file exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (if available)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Check MIME type if provided
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: PDF, Word documents, plain text"
        )

@router.post("/analyze-resume")
async def analyze_resume(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """
    Basic resume analysis with comprehensive validation
    """
    
    try:
        print(f"🔬 Starting analysis for file: {file.filename}")
        print(f"🎯 Target role: {target_role}")
        
        # Comprehensive file validation
        validate_file(file)
        
        # Extract real resume text
        text_content = await extract_text_from_file(file)
        
        if not text_content or len(text_content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail="Could not extract enough text from the resume. Please upload a clearer PDF, DOCX, or TXT file."
            )
        
        print(f"📄 Extracted resume text length: {len(text_content)}")
        
        # Real AI analysis
        ai_result = await analyze_resume_with_ai(
            resume_text=text_content,
            target_role=target_role
        )
        
        analysis_result = {
            "overall_score": ai_result.get("overall_score", 70),
            "ats_score": ai_result.get("ats_score", 70),
            "formatting_score": ai_result.get("formatting_score", 70),
            "strengths": ai_result.get("strengths", []),
            "weaknesses": ai_result.get("weaknesses", []),
            "keyword_analysis": ai_result.get("keyword_analysis", {}),
            "sections_analysis": ai_result.get("sections_analysis", {}),
            "specific_improvements": ai_result.get("specific_improvements", []),
            "ats_recommendations": ai_result.get("ats_recommendations", [])
        }
    
    improved_resume = ai_result.get(
        "improved_resume",
        "No improved resume generated."
    )
        
        return JSONResponse({
            "success": True,
            "analysis": analysis_result,
            "improved_resume": improved_resume,
            "original_length": len(text_content),
            "target_role": target_role,
            "debug_info": {
                "file_type": file.content_type,
                "filename": file.filename,
                "text_preview": "Resume analysis completed successfully"
            }
        })
        
    except Exception as e:
        print(f"❌ Resume analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Analysis failed: {str(e)}"}
        )

@router.get("/resume-analysis/health")
async def resume_analysis_health():
    return {"status": "healthy", "service": "resume-analysis"}
