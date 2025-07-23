from fastapi import APIRouter
from pydantic import BaseModel
import os
import openai

router = APIRouter()

openai.api_key = os.getenv("OPENAI_API_KEY")

class InterviewPrepRequest(BaseModel):
    company: str
    role: str

@router.post("/interview-prep")
async def interview_prep(payload: InterviewPrepRequest):
    prompt = f"""
You are an AI career coach helping someone prepare for an interview.
Company: {payload.company}
Role: {payload.role}

Provide:
1. A short summary of what this company does
2. Why this role is important to them
3. 6 likely interview questions for this role
4. 3 company-specific insights (culture, values, recent news)
5. Final tips for impressing in the interview
"""
    try:
        completion = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful career advisor."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        reply = completion.choices[0].message.content.strip()
        return {"success": True, "prep": reply}
    except Exception as e:
        return {"success": False, "error": str(e)}
Enter file contents here
