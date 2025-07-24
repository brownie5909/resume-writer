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
from routes.interview import router as interview_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview_router)


pdf_store = {}

openai.api_key = os.getenv("OPENAI_API_KEY")

TEMPLATES = {
    "default": """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Arial; margin: 30px; } h1 { font-size: 28px; } h2 { font-size: 22px; border-bottom: 1px solid #ddd; } p { margin: 5px 0; white-space: pre-wrap; }</style></head>
    <body>
        <h1>{{ name }}</h1>
        <p>{{ email }} | {{ phone }}</p>
        <h2>Summary</h2><p>{{ summary }}</p>
        <h2>Experience</h2><p>{{ experience }}</p>
        <h2>Education</h2><p>{{ education }}</p>
        <h2>Skills</h2><p>{{ skills }}</p>
        {% if cover_letter %}<h2>Cover Letter</h2><p>{{ cover_letter }}</p>{% endif %}
    </body></html>
    """,
    "conservative": """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Times New Roman; margin: 30px; color: #000; } h1 { font-size: 26px; } h2 { font-size: 20px; text-decoration: underline; } p { margin: 5px 0; white-space: pre-wrap; }</style></head>
    <body>
        <h1>{{ name }}</h1>
        <p>{{ email }} | {{ phone }}</p>
        <h2>Professional Summary</h2><p>{{ summary }}</p>
        <h2>Work History</h2><p>{{ experience }}</p>
        <h2>Education</h2><p>{{ education }}</p>
        <h2>Skills</h2><p>{{ skills }}</p>
        {% if cover_letter %}<h2>Cover Letter</h2><p>{{ cover_letter }}</p>{% endif %}
    </body></html>
    """,
"creative": """
<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: 'Helvetica Neue', Helvetica, sans-serif;
            color: #333;
            margin: 40px;
            padding: 0;
            font-size: 14px;
        }
        .header {
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
            margin-bottom: 25px;
        }
        .header h1 {
            font-size: 28px;
            color: #4CAF50;
            margin: 0;
        }
        .header p {
            font-style: italic;
            font-size: 14px;
            margin: 5px 0 0;
        }
        h2 {
            font-size: 18px;
            color: #2196F3;
            margin-top: 25px;
            margin-bottom: 8px;
            border-bottom: 1px solid #ccc;
            padding-bottom: 4px;
        }
        p {
            margin: 5px 0 15px;
            white-space: pre-wrap;
            line-height: 1.6;
        }
        .section {
            margin-bottom: 15px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>{{ name }}</h1>
        <p>{{ email }}{% if phone %} | {{ phone }}{% endif %}</p>
    </div>

    <div class="section">
        <h2>About Me</h2>
        <p>{{ summary }}</p>
    </div>

    <div class="section">
        <h2>Experience</h2>
        <p>{{ experience }}</p>
    </div>

    <div class="section">
        <h2>Education</h2>
        <p>{{ education }}</p>
    </div>

    <div class="section">
        <h2>Skills</h2>
        <p>{{ skills }}</p>
    </div>

    {% if cover_letter %}
    <div class="section">
        <h2>My Cover Letter</h2>
        <p>{{ cover_letter }}</p>
    </div>
    {% endif %}
</body>
</html>
"""

    "executive": """
    <!DOCTYPE html>
    <html>
    <head><style>body { font-family: Georgia; margin: 40px; } h1 { font-size: 32px; color: #000; } h2 { font-size: 24px; border-bottom: 2px solid #000; margin-top:20px; } p { margin: 8px 0; white-space: pre-wrap; }</style></head>
    <body>
        <h1>{{ name }}</h1>
        <p>{{ email }} | {{ phone }}</p>
        <h2>Executive Summary</h2><p>{{ summary }}</p>
        <h2>Professional Experience</h2><p>{{ experience }}</p>
        <h2>Education</h2><p>{{ education }}</p>
        <h2>Core Competencies</h2><p>{{ skills }}</p>
        {% if cover_letter %}<h2>Cover Letter</h2><p>{{ cover_letter }}</p>{% endif %}
    </body></html>
    """
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

    base_prompt = """You are a professional resume and cover letter writer.
Generate a {style} resume {ats_note} in structured plain text based on the following information:

{fields}

{output_instruction}
"""

    style = template_choice
    fields = "\n".join([f"{k}: {v}" for k, v in data.items()])
    ats_note = "that is ATS-friendly and plain text" if ats_mode else "with professional formatting"

    if generate_cover_letter:
        output_instruction = "Include a cover letter as a separate section after the resume."
    else:
        output_instruction = "Output only the resume."

    prompt = base_prompt.format(style=style, fields=fields, ats_note=ats_note, output_instruction=output_instruction)

    client = openai.OpenAI()

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional career assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"OpenAI API error: {str(e)}"})

    ai_output = response.choices[0].message.content

    # Extract sections for the template
    sections = {
        "name": data.get("full_name", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "summary": ai_output.split("Summary:")[-1].split("Experience:")[0].strip() if "Summary:" in ai_output and "Experience:" in ai_output else data.get("summary", ""),
        "experience": ai_output.split("Experience:")[-1].split("Education:")[0].strip() if "Experience:" in ai_output and "Education:" in ai_output else data.get("responsibilities", ""),
        "education": ai_output.split("Education:")[-1].split("Skills:")[0].strip() if "Education:" in ai_output and "Skills:" in ai_output else f"{data.get('degree', '')} - {data.get('school', '')}",
        "skills": ai_output.split("Skills:")[-1].split("Cover Letter:")[0].strip() if "Skills:" in ai_output else data.get("skills", ""),
        "cover_letter": ai_output.split("Cover Letter:")[-1].strip() if generate_cover_letter and "Cover Letter:" in ai_output else ""
    }

    # Render HTML template
    template_html = TEMPLATES.get(template_choice, TEMPLATES["default"])
    template = Template(template_html)
    html_out = template.render(**sections)

    # Generate PDF using WeasyPrint
    pdf_bytes = BytesIO()
    HTML(string=html_out).write_pdf(pdf_bytes)

    pdf_id = str(uuid.uuid4())
    pdf_store[pdf_id] = pdf_bytes.getvalue()

    download_url = f"https://resume-writer.onrender.com/download-resume/{pdf_id}"

    return JSONResponse({
        "resume_text": ai_output.strip(),
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
