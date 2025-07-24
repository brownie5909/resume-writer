from fastapi import APIRouter
from pydantic import BaseModel
import os
from openai import AsyncOpenAI

router = APIRouter()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Models
class InterviewInput(BaseModel):
    company: str
    role: str

class FeedbackInput(BaseModel):
    question: str
    answer: str

# Interview prep route
@router.post("/interview-prep")
async def interview_prep(payload: InterviewInput):
    prompt = f"""
You are a career coach helping someone prepare for a job interview.

Company: {payload.company}
Role: {payload.role}

Return the following sections in markdown format:
## Interview Preparation
1. Company Research
2. Role Expectations
3. STAR Method Reminder
4. Smart Questions to Ask
5. Any relevant industry notes

## Likely Interview Questions
List 6 questions, one per line, each starting with:
Q: [question]
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw_output = response.choices[0].message.content.strip()
        lines = raw_output.splitlines()

        questions = [line[3:].strip() for line in lines if line.startswith("Q: ")]
        prep_text = "\n".join([line for line in lines if not line.startswith("Q: ")])

        return {
            "success": True,
            "prep": prep_text,
            "questions": questions
        }

    except Exception as e:
        return { "success": False, "error": str(e) }


# Feedback route
@router.post("/interview-feedback")
async def interview_feedback(payload: FeedbackInput):
    prompt = f"""
You are an interview coach reviewing a job candidate's answer.

Question:
{payload.question}

Candidate's Answer:
{payload.answer}

Give specific, actionable feedback in 3–4 sentences.
Use a friendly, supportive tone.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        feedback = response.choices[0].message.content.strip()

        return {
            "success": True,
            "feedback": feedback
        }

    except Exception as e:
        return { "success": False, "error": str(e) }
