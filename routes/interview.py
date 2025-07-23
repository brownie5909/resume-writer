from fastapi import APIRouter, Request
from pydantic import BaseModel
import os
from openai import OpenAI

router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class InterviewPrepRequest(BaseModel):
    company: str
    role: str

class FeedbackRequest(BaseModel):
    question: str
    answer: str

@router.post("/interview-prep")
async def interview_prep(data: InterviewPrepRequest):
    prompt = f"""You are a career coach. Provide insights about the company '{data.company}' and the role '{data.role}'.
1. Summary of what the company does
2. What this company looks for in a {data.role}
3. Recent news or trends that may affect the company
4. Questions a candidate should ask in an interview
5. Cultural values or unique points about the company
6. 6 likely interview questions for this role"""

    chat = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    response_text = chat.choices[0].message.content
    return {"success": True, "prep": response_text}


@router.post("/interview-feedback")
async def interview_feedback(data: FeedbackRequest):
    prompt = f"""You are a job interview coach. A candidate was asked the question: "{data.question}"
They answered: "{data.answer}"

Give friendly but direct feedback on how they could improve their response, including what was strong and what was missing."""

    chat = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return {"success": True, "feedback": chat.choices[0].message.content}
