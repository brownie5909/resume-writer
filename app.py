from fastapi import FastAPI, HTTPException, Request
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

# Request Models
class ATSRequest(BaseModel):
    resume_text: str
    job_description: str

# Resume Generation (Safe JSON/Form Handling)
@app.post("/generate-resume")
async def generate_resume(req: Request):
    try:
        data = await req.json()
    except Exception:
        form = await req.form()
        data = form

    name = data.get("name")
    contact_info = data.get("contact_info")
    work_history = data.get("work_history")
    job_description = data.get("job_description")

    if None in (name, contact_info, work_history, job_description):
        raise HTTPException(status_code=400, detail="Missing required fields.")

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

# Cover Letter Generation (Safe JSON/Form Handling)
@app.post("/generate-cover-letter")
async def generate_cover_letter(req: Request):
    try:
        data = await req.json()
    except Exception:
        form = await req.form()
        data = form

    name = data.get("name")
    contact_info = data.get("contact_info")
    work_history = data.get("work_history")
    job_description = data.get("job_description")

    if None in (name, contact_info, work_history, job_description):
        raise HTTPException(status_code=400, detail="Missing required fields.")

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

# ATS Match Checker (JSON input)
@app.post("/ats-check")
async def ats_check(request: ATSRequest):
    resume_words = set(request.resume_text.lower().split())
    job_words = set(request.job_description.lower().split())
    match = len(resume_words & job_words) / len(job_words)
    return {"ats_match_percentage": round(match * 100, 2)}

# Debug Webhook Endpoint
@app.post("/debug-webhook")
async def debug_webhook(request: Request):
    headers = dict(request.headers)
    body = await request.body()
    return {
        "headers": headers,
        "raw_body": body.decode("utf-8", errors="replace")
    }
