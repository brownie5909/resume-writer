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

RESUME_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; margin: 30px; }
        h1 { font-size: 28px; margin-bottom: 5px; }
        h2 { font-size: 22px; margin-top: 20px; margin-bottom: 5px; border-bottom: 1px solid #ddd; }
        p { margin: 5px 0; line-height: 1.5; }
        .section { margin-top: 15px; }
    </style>
</head>
<body>
    <h1>{{ name }}</h1>
    <p>{{ email }}</p>
    <p>{{ phone }}</p>

    <div class="section">
        <h2>Summary</h2>
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
        <h2>Cover Letter</h2>
        <p>{{ cover_letter }}</p>
    </div>
    {% endif %}
</body>
</html>
"""

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
        "summary": data.get("summary", ""),
        "experience": data.get("responsibilities", ""),
        "education": f"{data.get('degree', '')} - {data.get('school', '')}",
        "skills": data.get("skills", ""),
        "cover_letter": ai_output.split("Cover Letter:")[-1].strip() if generate_cover_letter and "Cover Letter:" in ai_output else ""
    }

    # Render HTML template
    template = Template(RESUME_TEMPLATE)
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
