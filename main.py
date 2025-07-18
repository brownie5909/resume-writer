from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from weasyprint import HTML
import openai
import tempfile
import os
import json
import uuid
from openai import OpenAI

app = FastAPI()

# Allow Elementor form origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://hireready-3a5b8.ingress-erytho.ewp.live"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_resume_text(data):
    prompt = f"""
Generate a professional resume based on the following:

Full Name: {data.get('full_name', 'N/A')}
Email: {data.get('email', 'N/A')}
Phone: {data.get('phone', 'N/A')}
Job Title: {data.get('job_title', 'N/A')}
Company: {data.get('company', 'N/A')}
Years Worked: {data.get('years_worked', 'N/A')}
Responsibilities: {data.get('responsibilities', 'N/A')}
Degree: {data.get('degree', 'N/A')}
School: {data.get('school', 'N/A')}
Skills: {data.get('skills', 'N/A')}
Summary: {data.get('summary', 'N/A')}

Style: {data.get('template_style', 'Conservative')}

Write this in professional resume style.
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700
    )
    return response.choices[0].message.content

def generate_html_resume(data, resume_text):
    download_link = f"/download_pdf/{data['resume_id']}.pdf"
    return f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.5; padding: 20px; }}
        h1 {{ font-size: 24px; }}
        .section {{ margin-bottom: 20px; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
    </head>
    <body>
        <h1>{data.get('full_name', 'N/A')}</h1>
        <div class="section"><strong>Email:</strong> {data.get('email', 'N/A')}<br><strong>Phone:</strong> {data.get('phone', 'N/A')}</div>
        <div class="section"><pre>{resume_text}</pre></div>
        <div class="section">
            <a href="{download_link}" target="_blank">Download PDF</a>
        </div>
    </body>
    </html>
    """

def generate_pdf(content, filename):
    output_path = f"/tmp/{filename}.pdf"
    HTML(string=content).write_pdf(output_path)
    return output_path

@app.post("/submit_resume")
async def submit_resume(request: Request):
    form = await request.form()
    data = {key.lower().replace(" ", "_"): form.get(key) for key in form.keys()}

    # Generate resume
    resume_text = generate_resume_text(data)

    # Generate unique ID for PDF
    resume_id = str(uuid.uuid4())
    data['resume_id'] = resume_id

    html_resume = generate_html_resume(data, resume_text)

    # Save PDF
    generate_pdf(html_resume, resume_id)

    # Return EXACTLY what Elementor expects:
    return JSONResponse({
        "success": True,
        "data": {
            "message": "Resume generated successfully.",
            "fields": {
                "resume_output": html_resume
            }
        }
    }, status_code=200)

@app.get("/download_pdf/{filename}")
async def download_pdf(filename: str):
    file_path = f"/tmp/{filename}"
    return FileResponse(file_path, media_type='application/pdf', filename=filename)
