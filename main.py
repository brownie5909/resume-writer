# === CLEANED AND FIXED main.py ===

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from io import BytesIO
import uuid
import os
import openai
from jinja2 import Template
from weasyprint import HTML
import re
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

pdf_store = {}
openai.api_key = os.getenv("OPENAI_API_KEY")

TEMPLATES = {
    "default": """<html><body><h1>{{ name }}</h1><p>{{ email }} | {{ phone }}</p><h2>Summary</h2><p>{{ summary }}</p><h2>Experience</h2><p>{{ experience }}</p><h2>Education</h2><p>{{ education }}</p><h2>Skills</h2><p>{{ skills }}</p>{% if cover_letter %}<h2>Cover Letter</h2><p>{{ cover_letter }}</p>{% endif %}</body></html>""",
    "conservative": """<html><body><h1>{{ name }}</h1><p>{{ email }} | {{ phone }}</p><h2>Professional Summary</h2><p>{{ summary }}</p><h2>Work History</h2><p>{{ experience }}</p><h2>Education</h2><p>{{ education }}</p><h2>Skills</h2><p>{{ skills }}</p>{% if cover_letter %}<h2>Cover Letter</h2><p>{{ cover_letter }}</p>{% endif %}</body></html>""",
    "creative": """<html><body><h1>{{ name }}</h1><p>{{ email }}{% if phone %} | {{ phone }}{% endif %}</p><h2>About Me</h2><p>{{ summary }}</p><h2>Experience</h2><p>{{ experience }}</p><h2>Education</h2><p>{{ education }}</p><h2>Skills</h2><p>{{ skills }}</p>{% if cover_letter %}<h2>My Cover Letter</h2><p>{{ cover_letter }}</p>{% endif %}</body></html>""",
    "executive": """<html><body><h1>{{ name }}</h1><p>{{ email }} | {{ phone }}</p><h2>Executive Summary</h2><p>{{ summary }}</p><h2>Professional Experience</h2><p>{{ experience }}</p><h2>Education</h2><p>{{ education }}</p><h2>Core Competencies</h2><p>{{ skills }}</p>{% if cover_letter %}<h2>Cover Letter</h2><p>{{ cover_letter }}</p>{% endif %}</body></html>"""
}

@app.post("/generate-resume")
async def generate_resume(request: Request):
    try:
        body = await request.json()
    except Exception:
        form = await request.form()
        body = dict(form)

    data = body.get("data")
    if data is None:
        data = {k: v for k, v in body.items() if k not in ["template_choice", "generate_cover_letter", "ats_mode"]}

    template_choice = body.get("template_choice", "default")
    generate_cover_letter = body.get("generate_cover_letter", False)
    ats_mode = body.get("ats_mode", False)

    if not data.get("full_name") or not data.get("email") or not data.get("job_title"):
        return JSONResponse(status_code=400, content={"error": "Full Name, Email, and Job Title are required fields."})

    style = template_choice
    fields = "\n".join([f"{k}: {v}" for k, v in data.items()])
    ats_note = "that is ATS-friendly and plain text" if ats_mode else "with professional formatting"

    output_instruction = "Return the output as JSON with keys: summary, experience, education, skills, cover_letter."
    if not generate_cover_letter:
        output_instruction += " Do not include the cover_letter key."

    prompt = f"""
You are a professional resume and cover letter writer.
Generate a {style} resume {ats_note} in structured JSON format based on the following information:

{fields}

{output_instruction}
"""

    client = openai.OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional career assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"OpenAI API error: {str(e)}"})

    ai_output = response.choices[0].message.content.strip()

    try:
        parsed = json.loads(ai_output) if ai_output.startswith("{") else {}
    except:
        parsed = {}

    # Format experience
    exp_data = parsed.get("experience", data.get("responsibilities", ""))
    if isinstance(exp_data, list):
        experience = ""
        for job in exp_data:
            experience += f"- {job.get('job_title', '')} at {job.get('company', '')} ({job.get('years_worked', '')} yrs)\n"
            experience += f"  {job.get('responsibilities', '')}\n"
    else:
        experience = exp_data

    # Format education
    edu_data = parsed.get("education", "")
    if isinstance(edu_data, dict):
        education = f"{edu_data.get('degree', '')}, {edu_data.get('school', '')}"
    else:
        education = edu_data

    # Format skills
    skills_data = parsed.get("skills", "")
    if isinstance(skills_data, list):
        skills = ", ".join(skills_data)
    else:
        skills = skills_data

    sections = {
        "name": data.get("full_name", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "summary": parsed.get("summary", data.get("summary", "")),
        "experience": experience,
        "education": education,
        "skills": skills,
        "cover_letter": parsed.get("cover_letter", "") if generate_cover_letter else ""
    }

    template_html = TEMPLATES.get(template_choice, TEMPLATES["default"])
    html = Template(template_html).render(**sections)

    pdf_bytes = BytesIO()
    HTML(string=html).write_pdf(pdf_bytes)

    pdf_id = str(uuid.uuid4())
    pdf_store[pdf_id] = pdf_bytes.getvalue()

    download_url = f"https://resume-writer.onrender.com/download-resume/{pdf_id}"

    return JSONResponse({"resume_text": json.dumps(parsed), "pdf_url": download_url})

@app.get("/download-resume/{pdf_id}")
async def download_resume(pdf_id: str):
    pdf_data = pdf_store.get(pdf_id)
    if not pdf_data:
        return JSONResponse(status_code=404, content={"error": "Resume not found."})

    return StreamingResponse(BytesIO(pdf_data), media_type="application/pdf", headers={
        "Content-Disposition": f"attachment; filename=resume_{pdf_id}.pdf"
    })
