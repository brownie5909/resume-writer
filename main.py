
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse
from weasyprint import HTML
import openai
import tempfile
import os

app = FastAPI()

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_resume_text(data):
    prompt = f"""
Generate a professional resume based on the following details:

Full Name: {data['full_name']}
Email: {data['email']}
Phone: {data['phone']}
Job Title: {data['job_title']}
Company: {data['company']}
Years Worked: {data['years_worked']}
Responsibilities: {data['responsibilities']}
Degree: {data['degree']}
School: {data['school']}
Skills: {data['skills']}
Summary: {data['summary']}
Template Style: {data['template_choice']}

Format it in professional resume tone.
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700
    )

    return response['choices'][0]['message']['content']

def generate_pdf(content):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir="/tmp") as tmp:
        HTML(string=content).write_pdf(tmp.name)
        return tmp.name

@app.post("/submit_resume")
async def submit_resume(request: Request):
    data = await request.json()
    resume_text = generate_resume_text(data)
    html_content = f"<h1>{data['full_name']}</h1><pre>{resume_text}</pre>"
    pdf_path = generate_pdf(html_content)

    return JSONResponse({
        "message": "Resume generated successfully.",
        "download_link": f"/download_pdf/{os.path.basename(pdf_path)}"
    })

@app.get("/download_pdf/{filename}")
async def download_pdf(filename: str):
    file_path = f"/tmp/{filename}"
    return FileResponse(file_path, media_type='application/pdf', filename=filename)
