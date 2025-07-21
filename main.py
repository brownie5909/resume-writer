from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from io import BytesIO
from fpdf import FPDF
import uuid

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store for PDFs
pdf_store = {}

class ResumeRequest(BaseModel):
    full_name: str
    email: str
    phone: str
    job_title: str
    company: str
    years_worked: str
    responsibilities: str
    degree: str
    school: str
    skills: str
    summary: str
    template_choice: str

@app.post("/generate-resume")
async def generate_resume(req: ResumeRequest):
    resume_text = f"""
{req.full_name}
Email: {req.email}
Phone: {req.phone}

Professional Summary:
{req.summary}

Work Experience:
{req.job_title} at {req.company}
Years Worked: {req.years_worked}
Responsibilities: {req.responsibilities}

Education:
{req.degree} - {req.school}

Skills:
{req.skills}
    """

    # Generate PDF in memory
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in resume_text.strip().split("\n"):
        pdf.multi_cell(0, 10, line)

    pdf_bytes = BytesIO()
    pdf.output(pdf_bytes)
    pdf_bytes.seek(0)

    # Store in-memory with a unique ID
    pdf_id = str(uuid.uuid4())
    pdf_store[pdf_id] = pdf_bytes.getvalue()

    download_url = f"/download-resume/{pdf_id}"

    return JSONResponse({
        "resume_text": resume_text.strip(),
        "pdf_url": download_url
    })

@app.get("/download-resume/{pdf_id}")
async def download_resume(pdf_id: str):
    pdf_data = pdf_store.get(pdf_id)
    if not pdf_data:
        return JSONResponse(status_code=404, content={"error": "Resume not found."})

    return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=resume_{pdf_id}.pdf"
    })
