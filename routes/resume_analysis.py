from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from app.utils.file_parser import extract_text_from_file
from app.services.openai_service import analyze_resume_with_ai
from app.services.resume_analysis_service import (
    can_run_resume_analysis,
    create_or_update_analysis_resume_document,
    get_latest_resume_analysis_for_document,
    increment_resume_analysis_usage,
    list_resume_analysis_results,
    prune_basic_analysis_results,
    save_resume_analysis_result,
)
from routes.user_management import get_current_user
import os
from typing import Optional

router = APIRouter()

# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",  # Some browsers/uploaders use this
    "text/plain",
    "text/rtf"
}
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}


def validate_file(file: UploadFile) -> None:
    """Comprehensive file validation."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: PDF, Word documents, plain text"
        )


def build_analysis_payload(ai_result: dict) -> dict:
    """Build the stable analysis payload returned to the frontend and saved to the database."""
    return {
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


@router.get("/resume-analysis/can-run")
async def can_run_analysis(current_user: dict = Depends(get_current_user)):
    """Return whether the authenticated user can run another resume analysis this month."""
    usage_status = can_run_resume_analysis(current_user)
    return {
        "success": True,
        **usage_status,
    }


@router.get("/resume-analysis/history")
async def get_resume_analysis_history(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's saved resume analysis history, newest first."""
    analyses = list_resume_analysis_results(current_user["user_id"])

    return JSONResponse(content=jsonable_encoder({
        "success": True,
        "analyses": analyses,
        "count": len(analyses),
    }))


@router.get("/resume-analysis/document/{document_id}")
async def get_resume_analysis_for_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return the latest saved analysis linked to one of the user's saved resumes."""
    analysis_result = get_latest_resume_analysis_for_document(
        user_id=current_user["user_id"],
        document_id=document_id,
    )

    if not analysis_result:
        raise HTTPException(status_code=404, detail="No analysis found for this resume")

    return JSONResponse(content=jsonable_encoder({
        "success": True,
        "analysis_id": analysis_result.get("analysis_id"),
        "document_id": analysis_result.get("document_id"),
        "original_filename": analysis_result.get("original_filename"),
        "target_role": analysis_result.get("target_role"),
        "overall_score": analysis_result.get("overall_score"),
        "ats_score": analysis_result.get("ats_score"),
        "improved_resume": analysis_result.get("improved_resume"),
        "original_resume_text": analysis_result.get("original_resume_text"),
        "analysis": analysis_result.get("analysis", {}),
        "created_at": analysis_result.get("created_at"),
        "updated_at": analysis_result.get("updated_at"),
    }))


@router.post("/analyze-resume")
async def analyze_resume(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Resume analysis with parsing, tier usage enforcement, persistence and editable resume creation."""
    try:
        print(f"🔬 Starting analysis for file: {file.filename}")
        print(f"🎯 Target role: {target_role}")

        usage_status = can_run_resume_analysis(current_user)
        if not usage_status["can_run"]:
            return JSONResponse(
                status_code=403,
                content=jsonable_encoder({
                    "success": False,
                    "error": usage_status["message"],
                    **usage_status,
                }),
            )

        validate_file(file)

        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB"
            )

        await file.seek(0)

        text_content = await extract_text_from_file(file)

        if not text_content or len(text_content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract enough text from the resume. "
                    "Please upload a clearer PDF, DOCX, or TXT file."
                )
            )

        print(f"📄 Extracted resume text length: {len(text_content)}")

        ai_result = await analyze_resume_with_ai(
            resume_text=text_content,
            target_role=target_role
        )

        analysis = build_analysis_payload(ai_result)
        improved_resume = ai_result.get("improved_resume", "No improved resume generated.")
        resume_title = f"Analysed Resume - {target_role}" if target_role else f"Analysed Resume - {file.filename}"

        saved_document = create_or_update_analysis_resume_document(
            current_user=current_user,
            title=resume_title,
            improved_resume=improved_resume,
        )

        saved_analysis = save_resume_analysis_result(
            user_id=current_user["user_id"],
            document_id=saved_document["document_id"],
            original_filename=file.filename,
            original_content_type=file.content_type or "",
            original_resume_text=text_content,
            target_role=target_role,
            analysis=analysis,
            improved_resume=improved_resume,
        )

        prune_basic_analysis_results(current_user=current_user, keep_latest=1)
        increment_resume_analysis_usage(current_user["user_id"])

        updated_usage_status = can_run_resume_analysis(current_user)

        response_payload = {
            "success": True,
            "analysis": analysis,
            "improved_resume": improved_resume,
            "document_id": saved_document.get("document_id"),
            "saved_resume": {
                "document_id": saved_document.get("document_id"),
                "title": saved_document.get("title"),
                "template": saved_document.get("template"),
                "created_at": saved_document.get("created_at"),
                "updated_at": saved_document.get("updated_at"),
            },
            "analysis_id": saved_analysis.get("analysis_id"),
            "usage": updated_usage_status,
            "original_length": len(text_content),
            "target_role": target_role,
            "debug_info": {
                "file_type": file.content_type,
                "filename": file.filename,
                "characters_extracted": len(text_content)
            }
        }

        return JSONResponse(content=jsonable_encoder(response_payload))

    except HTTPException:
        raise

    except Exception as e:
        print(f"❌ Resume analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Analysis failed: {str(e)}"
            }
        )


@router.get("/resume-analysis/health")
async def resume_analysis_health():
    return {"status": "healthy", "service": "resume-analysis"}
