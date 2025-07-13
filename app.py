from fastapi import FastAPI, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For production, replace * with your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI Client Initialization
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ATS Checker Request Model (JSON)
class ATSRequest(BaseModel):
    resume_text: str
    job_description: str

# Resume Generation (Elementor compatible)
@app.post("/generate-resume")
async def generate_resume(
    name: str = Form(...),
    contact_info: str = Form(...),
    work_history: str = Form(...),
    job_description: str = Form(...)
):
    prompt = f'''
    Create a professional resume for {name}.
    Contact Info: {contact_info}
    Work History: {work_history}
    Tailor the resume to the following job description:
    {job_description}
    Make it ATS-friendly with action verbs and concise bullet points.
    '''
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        return {"resume": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Cover Letter Generation (Elementor compatible)
@app.post("/generate-cover-letter")
async def generate_cover_letter(
    name: str = Form(...),
    contact_info: str = Form(...),
    work_history: str = Form(...),
    job_description: str = Form(...)
):
    prompt = f'''
    Write a cover letter for {name}.
    Contact Info: {contact_info}
    Work History: {work_history}
    Tailor it to the following job description:
    {job_description}
    Use a professional and confident tone.
    '''
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )
        return {"cover_letter": response.choices[0].message.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ATS Match Checker (JSON input, no change)
@app.post("/ats-check")
async def ats_check(request: ATSRequest):
    resume_words = set(request.resume_text.lower().split())
    job_words = set(request.job_description.lower().split())
    match = len(resume_words & job_words) / len(job_words)
    return {"ats_match_percentage": round(match * 100, 2)}
