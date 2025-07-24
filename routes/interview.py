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
You are a professional interview coach helping a candidate prepare for a job interview.

Company: {payload.company}
Role: {payload.role}

Respond with:
1. A short but useful interview preparation summary
2. Then list exactly 6 likely interview questions, each starting with "Q#: "

Return your entire response in plain text (no markdown, no bullet points, no titles). Format like this:

[Summary text line 1]
[Summary text line 2]
...

Q1: First likely interview question
Q2: Second likely interview question
...
Q6: Sixth likely interview question
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw_output = response.choices[0].message.content.strip()

        # Parse out Q1–Q6 questions
        lines = raw_output.splitlines()
        questions = [line.split(":", 1)[1].strip() for line in lines if line.strip().lower().startswith("q") and ":" in line]

        # Remaining lines are summary
        prep_text = "\n".join([line for line in lines if not line.strip().lower().startswith("q")])

        return {
            "success": True,
            "prep": prep_text.strip(),
            "questions": questions
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
