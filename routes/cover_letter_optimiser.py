import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.utils.file_parser import extract_text_from_file
from routes.user_management import get_current_user
from routes.cover_letter import ai_analyze_cover_letter, ai_improve_cover_letter
from app.services.cover_letter_optimiser_service import (
    can_run_cover_letter_optimiser,
    increment_cover_letter_optimiser_usage,
    get_cover_letter_optimisation,
    list_cover_letter_optimisations,
    save_cover_letter_optimisation,
)

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
    "text/plain",
    "text/rtf",
}
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}


class CoverLetterOptimiseRequest(BaseModel):
    cover_letter_text: str
    title: Optional[str] = None
    target_role: Optional[str] = None
    company_name: Optional[str] = None
    job_posting: Optional[str] = None


class CoverLetterReviewRequest(BaseModel):
    cover_letter_text: str
    target_role: Optional[str] = None
    company_name: Optional[str] = None
    job_posting: Optional[str] = None


def validate_upload_file(file: UploadFile) -> None:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Allowed: PDF, Word documents, plain text",
        )


async def review_cover_letter_text(
    current_user: dict,
    cover_letter_text: str,
    target_role: Optional[str] = None,
    company_name: Optional[str] = None,
    job_posting: Optional[str] = None,
):
    usage_status = can_run_cover_letter_optimiser(current_user)
    if not usage_status.get("can_run"):
        return JSONResponse(
            status_code=403,
            content=jsonable_encoder({
                "success": False,
                "error": usage_status.get("message"),
                **usage_status,
            }),
        )

    cover_letter_text = (cover_letter_text or "").strip()
    if len(cover_letter_text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Cover letter text is too short. Please provide a complete cover letter.",
        )

    analysis = await ai_analyze_cover_letter(
        cover_letter_text=cover_letter_text,
        target_role=target_role,
        job_posting=job_posting,
        company_name=company_name,
    )

    increment_cover_letter_optimiser_usage(current_user["user_id"])
    updated_usage_status = can_run_cover_letter_optimiser(current_user)

    return JSONResponse(content=jsonable_encoder({
        "success": True,
        "mode": "review",
        "analysis": analysis,
        "original_cover_letter": cover_letter_text,
        "usage": updated_usage_status,
    }))


async def optimise_cover_letter_text(
    current_user: dict,
    cover_letter_text: str,
    title: Optional[str] = None,
    target_role: Optional[str] = None,
    company_name: Optional[str] = None,
    job_posting: Optional[str] = None,
):
    usage_status = can_run_cover_letter_optimiser(current_user)
    if not usage_status.get("can_run"):
        return JSONResponse(
            status_code=403,
            content=jsonable_encoder({
                "success": False,
                "error": usage_status.get("message"),
                **usage_status,
            }),
        )

    cover_letter_text = (cover_letter_text or "").strip()
    if len(cover_letter_text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Cover letter text is too short. Please provide a complete cover letter.",
        )

    analysis = await ai_analyze_cover_letter(
        cover_letter_text=cover_letter_text,
        target_role=target_role,
        job_posting=job_posting,
        company_name=company_name,
    )

    improved_cover_letter = await ai_improve_cover_letter(
        original_text=cover_letter_text,
        analysis=analysis,
        target_role=target_role,
        company_name=company_name,
        job_posting=job_posting,
    )

    saved_result = save_cover_letter_optimisation(
        user_id=current_user["user_id"],
        title=title,
        original_text=cover_letter_text,
        analysis=analysis,
        improved_cover_letter=improved_cover_letter,
        target_role=target_role,
        company_name=company_name,
        job_posting=job_posting,
    )

    increment_cover_letter_optimiser_usage(current_user["user_id"])
    updated_usage_status = can_run_cover_letter_optimiser(current_user)

    return JSONResponse(content=jsonable_encoder({
        "success": True,
        "mode": "optimise",
        "optimisation_id": saved_result.get("optimisation_id"),
        "analysis": analysis,
        "original_cover_letter": cover_letter_text,
        "improved_cover_letter": improved_cover_letter,
        "saved_result": saved_result,
        "usage": updated_usage_status,
    }))


@router.get("/cover-letter-optimiser/health")
async def cover_letter_optimiser_health():
    return {"status": "healthy", "service": "cover-letter-optimiser"}


@router.get("/cover-letter-optimiser/can-run")
async def can_run_cover_letter_optimiser_route(current_user: dict = Depends(get_current_user)):
    """Return whether the authenticated user can run another cover letter optimisation this month."""
    usage_status = can_run_cover_letter_optimiser(current_user)
    return {
        "success": True,
        **usage_status,
    }


@router.post("/cover-letter-optimiser/review")
async def review_cover_letter(
    payload: CoverLetterReviewRequest,
    current_user: dict = Depends(get_current_user),
):
    """Review a pasted cover letter and return analysis only, without rewriting or saving a new version."""
    try:
        return await review_cover_letter_text(
            current_user=current_user,
            cover_letter_text=payload.cover_letter_text,
            target_role=payload.target_role,
            company_name=payload.company_name,
            job_posting=payload.job_posting,
        )
    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Cover letter review error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Cover letter review failed: {str(error)}",
            },
        )


@router.post("/cover-letter-optimiser/review-file")
async def review_cover_letter_file(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    job_posting: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Review an uploaded cover letter file and return analysis only."""
    try:
        usage_status = can_run_cover_letter_optimiser(current_user)
        if not usage_status.get("can_run"):
            return JSONResponse(
                status_code=403,
                content=jsonable_encoder({
                    "success": False,
                    "error": usage_status.get("message"),
                    **usage_status,
                }),
            )

        validate_upload_file(file)
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        await file.seek(0)
        text_content = await extract_text_from_file(file)

        if not text_content or len(text_content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract enough text from the cover letter. "
                    "Please upload a clearer PDF, DOCX, or TXT file, or paste the text instead."
                ),
            )

        return await review_cover_letter_text(
            current_user=current_user,
            cover_letter_text=text_content,
            target_role=target_role,
            company_name=company_name,
            job_posting=job_posting,
        )

    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Cover letter file review error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Cover letter file review failed: {str(error)}",
            },
        )


@router.post("/cover-letter-optimiser/optimise")
async def optimise_cover_letter(
    payload: CoverLetterOptimiseRequest,
    current_user: dict = Depends(get_current_user),
):
    """Optimise a pasted cover letter, return analysis and save the result."""
    try:
        return await optimise_cover_letter_text(
            current_user=current_user,
            cover_letter_text=payload.cover_letter_text,
            title=payload.title,
            target_role=payload.target_role,
            company_name=payload.company_name,
            job_posting=payload.job_posting,
        )
    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Cover letter optimiser error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Cover letter optimisation failed: {str(error)}",
            },
        )


@router.post("/cover-letter-optimiser/optimise-file")
async def optimise_cover_letter_file(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    target_role: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    job_posting: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
):
    """Optimise an uploaded cover letter file, return analysis and save the result."""
    try:
        usage_status = can_run_cover_letter_optimiser(current_user)
        if not usage_status.get("can_run"):
            return JSONResponse(
                status_code=403,
                content=jsonable_encoder({
                    "success": False,
                    "error": usage_status.get("message"),
                    **usage_status,
                }),
            )

        validate_upload_file(file)
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        if len(file_bytes) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
            )

        await file.seek(0)
        text_content = await extract_text_from_file(file)

        if not text_content or len(text_content.strip()) < 50:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Could not extract enough text from the cover letter. "
                    "Please upload a clearer PDF, DOCX, or TXT file, or paste the text instead."
                ),
            )

        return await optimise_cover_letter_text(
            current_user=current_user,
            cover_letter_text=text_content,
            title=title or file.filename,
            target_role=target_role,
            company_name=company_name,
            job_posting=job_posting,
        )

    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Cover letter file optimiser error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Cover letter file optimisation failed: {str(error)}",
            },
        )


@router.get("/cover-letter-optimiser/history")
async def cover_letter_optimiser_history(current_user: dict = Depends(get_current_user)):
    """Return saved cover letter optimisation history for the authenticated user."""
    return {
        "success": True,
        "results": list_cover_letter_optimisations(current_user["user_id"]),
    }


@router.get("/cover-letter-optimiser/{optimisation_id}")
async def get_cover_letter_optimiser_result(
    optimisation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return one saved cover letter optimisation result."""
    result = get_cover_letter_optimisation(
        user_id=current_user["user_id"],
        optimisation_id=optimisation_id,
    )

    if not result:
        raise HTTPException(status_code=404, detail="Cover letter optimisation result not found")

    return {
        "success": True,
        "result": result,
    }
