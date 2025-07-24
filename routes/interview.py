from fastapi import APIRouter
from pydantic import BaseModel
from openai import AsyncOpenAI
import os

router = APIRouter()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class InterviewInput(BaseModel):
    company: str
    role: str

@router.post("/interview-prep")
async def interview_prep(payload: InterviewInput):
    prompt = f"""
You are a career coach helping someone prepare for an interview for the role of {payload.role} at {payload.company}.

Return in this format:
## Interview Preparation Summary

[1-2 paragraphs about the company, role, expectations, and strategies]

## Likely Interview Questions

Q1: [question 1]  
Q2: [question 2]  
Q3: [question 3]  
Q4: [question 4]  
Q5: [question 5]  
Q6: [question 6]
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        full_text = response.choices[0].message.content.strip()

        # Parse questions separately
        lines = full_text.splitlines()
        questions = [line.split(": ", 1)[1].strip() for line in lines if line.strip().startswith("Q") and ": " in line]

        return {
            "success": True,
            "prep": full_text,
            "questions": questions
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
