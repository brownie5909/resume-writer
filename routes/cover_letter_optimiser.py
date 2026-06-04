from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

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


class CoverLetterOptimiseRequest(BaseModel):
    cover_letter_text: str
    title: Optional[str] = None
    target_role: Optional[str] = None
    company_name: Optional[str] = None
    job_posting: Optional[str] = None


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


@router.post("/cover-letter-optimiser/optimise")
async def optimise_cover_letter(
    payload: CoverLetterOptimiseRequest,
    current_user: dict = Depends(get_current_user),
):
    """Optimise a pasted cover letter, return analysis and save the result."""
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

    cover_letter_text = (payload.cover_letter_text or "").strip()
    if len(cover_letter_text) < 50:
        raise HTTPException(
            status_code=400,
            detail="Cover letter text is too short. Please paste a complete cover letter.",
        )

    try:
        analysis = await ai_analyze_cover_letter(
            cover_letter_text=cover_letter_text,
            target_role=payload.target_role,
            job_posting=payload.job_posting,
            company_name=payload.company_name,
        )

        improved_cover_letter = await ai_improve_cover_letter(
            original_text=cover_letter_text,
            analysis=analysis,
            target_role=payload.target_role,
            company_name=payload.company_name,
            job_posting=payload.job_posting,
        )

        saved_result = save_cover_letter_optimisation(
            user_id=current_user["user_id"],
            title=payload.title,
            original_text=cover_letter_text,
            analysis=analysis,
            improved_cover_letter=improved_cover_letter,
            target_role=payload.target_role,
            company_name=payload.company_name,
            job_posting=payload.job_posting,
        )

        increment_cover_letter_optimiser_usage(current_user["user_id"])
        updated_usage_status = can_run_cover_letter_optimiser(current_user)

        return JSONResponse(content=jsonable_encoder({
            "success": True,
            "optimisation_id": saved_result.get("optimisation_id"),
            "analysis": analysis,
            "improved_cover_letter": improved_cover_letter,
            "saved_result": saved_result,
            "usage": updated_usage_status,
        }))

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
