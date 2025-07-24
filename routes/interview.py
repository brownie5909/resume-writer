from fastapi import APIRouter
from pydantic import BaseModel
import os
from openai import AsyncOpenAI

router = APIRouter()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class InterviewInput(BaseModel):
    company: str
    role: str

@router.post("/interview-prep")
async def interview_prep(payload: InterviewInput):
    prompt = f"""
You are a professional interview coach helping someone prepare for a job interview.

Company: {payload.company}
Role: {payload.role}

Return:
1. A brief summary of the company and role
2. Key points the candidate should know (use bullets or short paragraphs)
3. Then provide exactly 6 likely interview questions, in this exact format:

Q1: [question]
Q2: [question]
...
Q6: [question]

Do NOT add section titles or markdown. Return a clean plain text response.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw_output = response.choices[0].message.content.strip()

        # Separate questions
        lines = raw_output.splitlines()
        questions = [line.split(":", 1)[1].strip() for line in lines if line.startswith("Q")]
        prep_text = "\n".join([line for line in lines if not line.startswith("Q")]).strip()

        return {
            "success": True,
            "prep": prep_text,
            "questions": questions
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
