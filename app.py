
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

class ResumeRequest(BaseModel):
    name: str
    contact_info: str
    work_history: str
    job_description: str

class CoverLetterRequest(BaseModel):
    name: str
    contact_info: str
    work_history: str
    job_description: str

class ATSRequest(BaseModel):
    resume_text: str
    job_description: str

@app.post("/generate-resume")
async def generate_resume(request: ResumeRequest):
    prompt = f'''
    Create a professional resume for {request.name}.
    Contact Info: {request.contact_info}
    Work History: {request.work_history}
    Tailor the resume to the following job description:
    {request.job_description}
    Make it ATS-friendly with action verbs and concise bullet points.
    '''
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        return {"resume": response['choices'][0]['message']['content']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-cover-letter")
async def generate_cover_letter(request: CoverLetterRequest):
    prompt = f'''
    Write a cover letter for {request.name}.
    Contact Info: {request.contact_info}
    Work History: {request.work_history}
    Tailor it to the following job description:
    {request.job_description}
    Use a professional and confident tone.
    '''
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )
        return {"cover_letter": response['choices'][0]['message']['content']}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ats-check")
async def ats_check(request: ATSRequest):
    resume_words = set(request.resume_text.lower().split())
    job_words = set(request.job_description.lower().split())
    match = len(resume_words & job_words) / len(job_words)
    return {"ats_match_percentage": round(match * 100, 2)}
