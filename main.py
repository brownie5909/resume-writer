
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pdfkit
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ResumeRequest(BaseModel):
    name: str
    email: str
    experience: str
    job_ad: str

@app.post("/generate-resume")
async def generate_resume(req: ResumeRequest):
    resume_text = f"""
    Name: {req.name}
    Email: {req.email}

    Experience:
    {req.experience}

    Matched Job Ad:
    {req.job_ad}
    """
    html_content = f"<h1>{req.name}'s Resume</h1><p>{req.experience}</p><h2>Job Match</h2><p>{req.job_ad}</p>"
    filename = f"resume_{uuid.uuid4().hex}.pdf"
    pdfkit.from_string(html_content, filename)
    return JSONResponse({"resume_text": resume_text, "pdf_url": filename})
