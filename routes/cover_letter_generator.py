from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from routes.user_management import get_current_user
from routes.cover_letter import ai_analyze_cover_letter
from routes.cover_letter_helpers import ai_generate_cover_letter, ai_retarget_cover_letter
from app.services.cover_letter_generator_service import (
    can_run_cover_letter_generator,
    get_cover_letter_generation,
    increment_cover_letter_generator_usage,
    list_cover_letter_generations,
    save_cover_letter_generation,
)

router = APIRouter()


class CoverLetterGeneratorRequest(BaseModel):
    title: Optional[str] = None
    applicant_name: str
    target_role: str
    company_name: Optional[str] = None
    job_posting: str
    experience: Optional[str] = None
    achievements: Optional[str] = None
    tone_preference: Optional[str] = "professional"


class CoverLetterRetargetRequest(BaseModel):
    title: Optional[str] = None
    applicant_name: Optional[str] = None
    source_cover_letter: str
    target_role: str
    company_name: Optional[str] = None
    job_posting: str
    tone_preference: Optional[str] = "professional"


@router.get("/cover-letter-generator/health")
async def cover_letter_generator_health():
    return {"status": "healthy", "service": "cover-letter-generator"}


@router.get("/cover-letter-generator/can-run")
async def can_run_generator(current_user: dict = Depends(get_current_user)):
    usage_status = can_run_cover_letter_generator(current_user)
    return {"success": True, **usage_status}


@router.post("/cover-letter-generator/generate")
async def generate_cover_letter(payload: CoverLetterGeneratorRequest, current_user: dict = Depends(get_current_user)):
    usage_status = can_run_cover_letter_generator(current_user)
    if not usage_status.get("can_run"):
        return JSONResponse(
            status_code=403,
            content=jsonable_encoder({
                "success": False,
                "error": usage_status.get("message"),
                **usage_status,
            }),
        )

    if len((payload.applicant_name or "").strip()) < 2:
        raise HTTPException(status_code=400, detail="Applicant name is required")
    if len((payload.target_role or "").strip()) < 2:
        raise HTTPException(status_code=400, detail="Target role is required")
    if len((payload.job_posting or "").strip()) < 50:
        raise HTTPException(status_code=400, detail="Please paste a fuller job advertisement or role description")

    try:
        generated_cover_letter = await ai_generate_cover_letter(
            job_posting=payload.job_posting,
            applicant_name=payload.applicant_name,
            current_role=payload.target_role,
            experience=payload.experience,
            achievements=payload.achievements,
            company_name=payload.company_name,
            tone_preference=payload.tone_preference or "professional",
        )

        analysis = await ai_analyze_cover_letter(
            cover_letter_text=generated_cover_letter,
            target_role=payload.target_role,
            job_posting=payload.job_posting,
            company_name=payload.company_name,
        )

        saved_result = save_cover_letter_generation(
            user_id=current_user["user_id"],
            title=payload.title,
            applicant_name=payload.applicant_name,
            target_role=payload.target_role,
            company_name=payload.company_name,
            job_posting=payload.job_posting,
            experience=payload.experience,
            achievements=payload.achievements,
            tone_preference=payload.tone_preference or "professional",
            generated_cover_letter=generated_cover_letter,
            analysis=analysis,
        )

        increment_cover_letter_generator_usage(current_user["user_id"])
        updated_usage = can_run_cover_letter_generator(current_user)

        return JSONResponse(content=jsonable_encoder({
            "success": True,
            "generation_id": saved_result.get("generation_id"),
            "cover_letter": generated_cover_letter,
            "analysis": analysis,
            "saved_result": saved_result,
            "usage": updated_usage,
        }))

    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Cover letter generator error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Cover letter generation failed: {str(error)}",
            },
        )


@router.post("/cover-letter-generator/retarget")
async def retarget_cover_letter(payload: CoverLetterRetargetRequest, current_user: dict = Depends(get_current_user)):
    usage_status = can_run_cover_letter_generator(current_user)
    if not usage_status.get("can_run"):
        return JSONResponse(
            status_code=403,
            content=jsonable_encoder({
                "success": False,
                "error": usage_status.get("message"),
                **usage_status,
            }),
        )

    if len((payload.source_cover_letter or "").strip()) < 50:
        raise HTTPException(status_code=400, detail="Please provide a fuller existing cover letter to retarget")
    if len((payload.target_role or "").strip()) < 2:
        raise HTTPException(status_code=400, detail="New target role is required")
    if len((payload.job_posting or "").strip()) < 50:
        raise HTTPException(status_code=400, detail="Please paste a fuller job advertisement or role description")

    try:
        retargeted_cover_letter = await ai_retarget_cover_letter(
            source_cover_letter=payload.source_cover_letter,
            job_posting=payload.job_posting,
            target_role=payload.target_role,
            company_name=payload.company_name,
            tone_preference=payload.tone_preference or "professional",
        )

        analysis = await ai_analyze_cover_letter(
            cover_letter_text=retargeted_cover_letter,
            target_role=payload.target_role,
            job_posting=payload.job_posting,
            company_name=payload.company_name,
        )

        saved_result = save_cover_letter_generation(
            user_id=current_user["user_id"],
            title=payload.title or f"Retargeted Cover Letter - {payload.target_role}",
            applicant_name=payload.applicant_name,
            target_role=payload.target_role,
            company_name=payload.company_name,
            job_posting=payload.job_posting,
            experience="Retargeted from existing cover letter",
            achievements=None,
            tone_preference=payload.tone_preference or "professional",
            generated_cover_letter=retargeted_cover_letter,
            analysis=analysis,
        )

        increment_cover_letter_generator_usage(current_user["user_id"])
        updated_usage = can_run_cover_letter_generator(current_user)

        return JSONResponse(content=jsonable_encoder({
            "success": True,
            "mode": "retarget",
            "generation_id": saved_result.get("generation_id"),
            "cover_letter": retargeted_cover_letter,
            "source_cover_letter": payload.source_cover_letter,
            "analysis": analysis,
            "saved_result": saved_result,
            "usage": updated_usage,
        }))

    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Cover letter retarget error: {str(error)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Cover letter retargeting failed: {str(error)}",
            },
        )


@router.get("/cover-letter-generator/history")
async def generator_history(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "results": list_cover_letter_generations(current_user["user_id"]),
    }


@router.get("/cover-letter-generator/{generation_id}")
async def get_generator_result(generation_id: str, current_user: dict = Depends(get_current_user)):
    result = get_cover_letter_generation(current_user["user_id"], generation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Cover letter generation result not found")
    return {"success": True, "result": result}
