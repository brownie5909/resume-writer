from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

class InterviewPrepRequest(BaseModel):
    company: str
    role: str

class PracticeFeedbackRequest(BaseModel):
    question: str
    answer: str

@app.post("/interview-prep")
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

@app.post("/interview-feedback")
async def interview_feedback(payload: PracticeFeedbackRequest):
    prompt = f"""
You are an AI interview coach. Give helpful, specific feedback on this answer to the interview question below.

Question: {payload.question}
Candidate's Answer: {payload.answer}

Focus on strengths, clarity, and what could be improved. Keep it supportive.
"""
    try:
        completion = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert interview coach."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        reply = completion.choices[0].message.content.strip()
        return {"success": True, "feedback": reply}
    except Exception as e:
        return {"success": False, "error": str(e)}
