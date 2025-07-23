from fastapi import APIRouter, Request
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
    prompt = f"""You are a career coach helping someone prepare for a job interview.

Company: {payload.company}
Role: {payload.role}

Return:
1. A clear, structured interview preparation summary
2. 6 likely interview questions — numbered clearly

Format:
Return the interview prep in markdown-style text.
Then list the 6 likely questions on separate lines in this format:
Q: [question]"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw_output = response.choices[0].message.content.strip()

        # Extract questions from markdown-style output
        lines = raw_output.splitlines()
        questions = [line[3:].strip() for line in lines if line.startswith("Q: ")]

        # Remove questions from prep text
        prep_text = "\n".join(line for line in lines if not line.startswith("Q: ")).strip()

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
