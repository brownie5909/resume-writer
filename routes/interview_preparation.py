import json
import os
from typing import Dict, Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from routes.user_management import get_current_user
from app.services.interview_preparation_service import (
    can_run_interview_preparation,
    get_interview_preparation,
    increment_interview_preparation_usage,
    list_interview_preparations,
    save_interview_preparation,
)

router = APIRouter()


class InterviewPreparationRequest(BaseModel):
    title: Optional[str] = None
    company_name: Optional[str] = None
    role_title: str
    job_posting: str


def extract_json_content(content: str) -> str:
    content = (content or "").strip()
    if content.startswith("```json"):
        content = content.replace("```json", "", 1).strip()
    if content.startswith("```"):
        content = content.replace("```", "", 1).strip()
    if content.endswith("```"):
        content = content[:-3].strip()
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        return content[start:end + 1]
    return content


def fallback_interview_preparation(role_title: str, company_name: Optional[str], job_posting: str) -> Dict:
    company = company_name or "the employer"
    role = role_title or "this role"
    return {
        "company_snapshot": [
            f"Review {company}'s website, values, services and recent updates before the interview.",
            f"Connect your answers to how the {role} role supports {company}'s customers, team or business goals.",
            "Look for clues in the job advertisement about the organisation's priorities, culture and expectations.",
            "Prepare a short explanation of why this organisation interests you, not just why you want the job."
        ],
        "company_interview_themes": [
            f"Why do you want to work with {company}?",
            f"What do you understand about {company} and the work they do?",
            f"How would your experience help you contribute to {company} in the {role} role?",
            "What have you learned from researching the organisation?"
        ],
        "likely_questions": [
            f"Tell me about your experience relevant to the {role} role.",
            f"Why are you interested in working with {company}?",
            "Can you describe a time you solved a difficult problem at work?",
            "How do you prioritise competing deadlines?",
            "Tell me about a time you received feedback and how you responded.",
            "What strengths would you bring to this role?",
            "Describe a time you worked successfully as part of a team.",
            "How would you handle a challenging stakeholder or customer?",
            "What do you understand about this role from the job advertisement?",
            "Do you have any questions for us?"
        ],
        "key_skills": [
            "Communication",
            "Problem solving",
            "Time management",
            "Role-specific technical skills",
            "Teamwork"
        ],
        "employer_priorities": [
            f"Evidence that you understand the {role} responsibilities.",
            "Clear examples of past achievements.",
            "Confidence, professionalism and reliability.",
            "Ability to match your experience to the job requirements."
        ],
        "red_flags": [
            "Vague answers without examples.",
            "Not researching the company before the interview.",
            "Focusing only on what you want rather than what you can contribute.",
            "Not preparing questions for the interviewer."
        ],
        "questions_to_ask": [
            "What does success look like in this role after the first 90 days?",
            "What are the biggest priorities for the team right now?",
            "How would you describe the team culture?",
            "What are the next steps in the recruitment process?"
        ],
        "preparation_tips": [
            "Prepare 4-5 STAR examples before the interview.",
            "Review the job advertisement and match your examples to the key criteria.",
            "Research the company website, values and recent news.",
            "Prepare a concise explanation of why you want this role.",
            "Practise answering questions out loud before the interview."
        ]
    }


async def generate_interview_preparation_with_ai(role_title: str, company_name: Optional[str], job_posting: str) -> Dict:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return fallback_interview_preparation(role_title, company_name, job_posting)

    prompt = f"""
You are an expert interview coach and recruiter. Create a practical interview preparation report for a job seeker.

Company: {company_name or 'Not provided'}
Role: {role_title}
Job Advertisement / Role Description:
{job_posting}

Return ONLY valid JSON in this exact structure:
{{
  "company_snapshot": ["4 concise points about the company context, likely priorities, values, customers/stakeholders, or what the candidate should research"],
  "company_interview_themes": ["company-specific interview themes and questions the candidate should prepare for"],
  "likely_questions": ["10 likely interview questions tailored to the role and company"],
  "key_skills": ["skills the interview is likely to assess"],
  "employer_priorities": ["what the employer is likely looking for"],
  "red_flags": ["common mistakes or concerns to avoid"],
  "questions_to_ask": ["smart questions the candidate can ask the interviewer"],
  "preparation_tips": ["practical preparation tips"]
}}

Be specific to the role, company name, and job advertisement. If limited company information is provided, infer carefully from the company name, role and job advertisement without inventing unverifiable facts. Keep each item clear and useful.
"""

    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You create concise, practical interview preparation reports. Always return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.4,
                "max_tokens": 2600
            }
            async with session.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=45) as response:
                if response.status != 200:
                    return fallback_interview_preparation(role_title, company_name, job_posting)
                result = await response.json()
                content = result["choices"][0]["message"]["content"].strip()
                parsed = json.loads(extract_json_content(content))
                required = [
                    "company_snapshot",
                    "company_interview_themes",
                    "likely_questions",
                    "key_skills",
                    "employer_priorities",
                    "red_flags",
                    "questions_to_ask",
                    "preparation_tips"
                ]
                if not all(key in parsed for key in required):
                    return fallback_interview_preparation(role_title, company_name, job_posting)
                return parsed
    except Exception as error:
        print(f"⚠️ Interview preparation AI fallback: {str(error)}")
        return fallback_interview_preparation(role_title, company_name, job_posting)


@router.get("/interview-preparation/health")
async def interview_preparation_health():
    return {"status": "healthy", "service": "interview-preparation"}


@router.get("/interview-preparation/can-run")
async def can_run_interview_preparation_route(current_user: dict = Depends(get_current_user)):
    usage_status = can_run_interview_preparation(current_user)
    return {"success": True, **usage_status}


@router.post("/interview-preparation/generate")
async def generate_interview_preparation(payload: InterviewPreparationRequest, current_user: dict = Depends(get_current_user)):
    usage_status = can_run_interview_preparation(current_user)
    if not usage_status.get("can_run"):
        return JSONResponse(
            status_code=403,
            content=jsonable_encoder({"success": False, "error": usage_status.get("message"), **usage_status}),
        )

    if len((payload.role_title or "").strip()) < 2:
        raise HTTPException(status_code=400, detail="Role title is required")
    if len((payload.job_posting or "").strip()) < 50:
        raise HTTPException(status_code=400, detail="Please paste a fuller job advertisement or role description")

    try:
        preparation = await generate_interview_preparation_with_ai(
            role_title=payload.role_title,
            company_name=payload.company_name,
            job_posting=payload.job_posting,
        )

        saved_result = save_interview_preparation(
            user_id=current_user["user_id"],
            title=payload.title,
            company_name=payload.company_name,
            role_title=payload.role_title,
            job_posting=payload.job_posting,
            preparation=preparation,
        )

        increment_interview_preparation_usage(current_user["user_id"])
        updated_usage = can_run_interview_preparation(current_user)

        return JSONResponse(content=jsonable_encoder({
            "success": True,
            "prep_id": saved_result.get("prep_id"),
            "preparation": preparation,
            "saved_result": saved_result,
            "usage": updated_usage,
        }))

    except HTTPException:
        raise
    except Exception as error:
        print(f"❌ Interview preparation error: {str(error)}")
        return JSONResponse(status_code=500, content={"success": False, "error": f"Interview preparation failed: {str(error)}"})


@router.get("/interview-preparation/history")
async def interview_preparation_history(current_user: dict = Depends(get_current_user)):
    return {"success": True, "results": list_interview_preparations(current_user["user_id"])}


@router.get("/interview-preparation/{prep_id}")
async def get_interview_preparation_result(prep_id: str, current_user: dict = Depends(get_current_user)):
    result = get_interview_preparation(current_user["user_id"], prep_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interview preparation result not found")
    return {"success": True, "result": result}
