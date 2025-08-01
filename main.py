from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
from io import BytesIO
import uuid
import os
import openai
from jinja2 import Template
from weasyprint import HTML, CSS
from datetime import datetime, timedelta
import json
from routes.interview import router as interview_router
from routes.resume_analysis import router as resume_analysis_router
from routes.cover_letter import router as cover_letter_router
from routes.user_management import router as user_management_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(interview_router)
app.include_router(resume_analysis_router)
app.include_router(cover_letter_router)
app.include_router(user_management_router)

# Enhanced PDF storage with expiration
pdf_store = {}
PDF_EXPIRY_HOURS = 24

openai.api_key = os.getenv("OPENAI_API_KEY")

# Enhanced templates with better styling and structure
TEMPLATES = {
    "default": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                color: #333;
                line-height: 1.6;
                margin: 0;
                font-size: 11pt;
            }
            .header {
                text-align: center;
                border-bottom: 2px solid #4CAF50;
                padding-bottom: 15px;
                margin-bottom: 25px;
            }
            .header h1 {
                font-size: 24pt;
                color: #2c3e50;
                margin: 0 0 8px 0;
                font-weight: 600;
            }
            .contact-info {
                font-size: 10pt;
                color: #555;
                margin: 0;
            }
            .section {
                margin-bottom: 20px;
                page-break-inside: avoid;
            }
            .section h2 {
                font-size: 14pt;
                color: #4CAF50;
                border-bottom: 1px solid #4CAF50;
                padding-bottom: 5px;
                margin-bottom: 12px;
                font-weight: 600;
            }
            .section p, .section ul {
                margin: 8px 0;
                text-align: justify;
            }
            .experience-item {
                margin-bottom: 15px;
            }
            .job-title {
                font-weight: 600;
                color: #2c3e50;
            }
            .company-info {
                font-style: italic;
                color: #666;
                font-size: 10pt;
            }
            ul {
                padding-left: 20px;
            }
            li {
                margin-bottom: 3px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{ name }}</h1>
            <p class="contact-info">{{ email }}{% if phone %} | {{ phone }}{% endif %}</p>
        </div>

        {% if summary %}
        <div class="section">
            <h2>Professional Summary</h2>
            <p>{{ summary }}</p>
        </div>
        {% endif %}

        {% if experience %}
        <div class="section">
            <h2>Professional Experience</h2>
            {{ experience | safe }}
        </div>
        {% endif %}

        {% if education %}
        <div class="section">
            <h2>Education</h2>
            <p>{{ education }}</p>
        </div>
        {% endif %}

        {% if skills %}
        <div class="section">
            <h2>Key Skills</h2>
            <p>{{ skills }}</p>
        </div>
        {% endif %}

        {% if cover_letter %}
        <div style="page-break-before: always;">
            <div class="section">
                <h2>Cover Letter</h2>
                <p>{{ cover_letter }}</p>
            </div>
        </div>
        {% endif %}
    </body>
    </html>
    """,
    
    "conservative": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {
                size: A4;
                margin: 2.5cm;
            }
            body {
                font-family: 'Times New Roman', serif;
                color: #000;
                line-height: 1.5;
                margin: 0;
                font-size: 12pt;
            }
            .header {
                text-align: center;
                border-bottom: 1px solid #000;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }
            .header h1 {
                font-size: 20pt;
                margin: 0 0 5px 0;
                font-weight: bold;
            }
            .contact-info {
                font-size: 11pt;
                margin: 0;
            }
            .section {
                margin-bottom: 18px;
            }
            .section h2 {
                font-size: 14pt;
                text-decoration: underline;
                margin-bottom: 10px;
                font-weight: bold;
            }
            .section p {
                margin: 6px 0;
                text-align: justify;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{ name }}</h1>
            <p class="contact-info">{{ email }}{% if phone %} | {{ phone }}{% endif %}</p>
        </div>

        {% if summary %}
        <div class="section">
            <h2>Professional Summary</h2>
            <p>{{ summary }}</p>
        </div>
        {% endif %}

        {% if experience %}
        <div class="section">
            <h2>Work History</h2>
            {{ experience | safe }}
        </div>
        {% endif %}

        {% if education %}
        <div class="section">
            <h2>Education</h2>
            <p>{{ education }}</p>
        </div>
        {% endif %}

        {% if skills %}
        <div class="section">
            <h2>Skills</h2>
            <p>{{ skills }}</p>
        </div>
        {% endif %}

        {% if cover_letter %}
        <div style="page-break-before: always;">
            <div class="section">
                <h2>Cover Letter</h2>
                <p>{{ cover_letter }}</p>
            </div>
        </div>
        {% endif %}
    </body>
    </html>
    """,

    "creative": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {
                size: A4;
                margin: 1.5cm;
            }
            body {
                font-family: 'Helvetica Neue', Helvetica, sans-serif;
                color: #333;
                margin: 0;
                font-size: 11pt;
                line-height: 1.6;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                min-height: 100vh;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 0 20px rgba(0,0,0,0.1);
                margin: 20px;
            }
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 25px;
                border-radius: 10px;
                text-align: center;
                margin-bottom: 25px;
            }
            .header h1 {
                font-size: 24pt;
                margin: 0 0 8px 0;
                font-weight: 300;
                letter-spacing: 1px;
            }
            .contact-info {
                font-size: 10pt;
                opacity: 0.9;
                margin: 0;
            }
            .section {
                margin-bottom: 25px;
            }
            .section h2 {
                font-size: 14pt;
                color: #667eea;
                margin-bottom: 12px;
                font-weight: 600;
                position: relative;
                padding-left: 15px;
            }
            .section h2::before {
                content: '';
                position: absolute;
                left: 0;
                top: 50%;
                transform: translateY(-50%);
                width: 4px;
                height: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 2px;
            }
            .section p {
                margin: 8px 0;
                text-align: justify;
            }
            .skill-tag {
                display: inline-block;
                background: #f0f2f5;
                color: #667eea;
                padding: 4px 12px;
                border-radius: 15px;
                font-size: 9pt;
                margin: 2px 4px 2px 0;
                border: 1px solid #e1e5e9;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>{{ name }}</h1>
                <p class="contact-info">{{ email }}{% if phone %} | {{ phone }}{% endif %}</p>
            </div>

            {% if summary %}
            <div class="section">
                <h2>About Me</h2>
                <p>{{ summary }}</p>
            </div>
            {% endif %}

            {% if experience %}
            <div class="section">
                <h2>Experience</h2>
                {{ experience | safe }}
            </div>
            {% endif %}

            {% if education %}
            <div class="section">
                <h2>Education</h2>
                <p>{{ education }}</p>
            </div>
            {% endif %}

            {% if skills %}
            <div class="section">
                <h2>Skills</h2>
                <p>{{ skills }}</p>
            </div>
            {% endif %}

            {% if cover_letter %}
            <div style="page-break-before: always;">
                <div class="section">
                    <h2>My Cover Letter</h2>
                    <p>{{ cover_letter }}</p>
                </div>
            </div>
            {% endif %}
        </div>
    </body>
    </html>
    """,

    "executive": """
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            @page {
                size: A4;
                margin: 2cm;
            }
            body {
                font-family: Georgia, serif;
                color: #2c3e50;
                line-height: 1.6;
                margin: 0;
                font-size: 11pt;
            }
            .header {
                border-bottom: 3px solid #2c3e50;
                padding-bottom: 15px;
                margin-bottom: 30px;
            }
            .header h1 {
                font-size: 28pt;
                color: #2c3e50;
                margin: 0 0 8px 0;
                font-weight: bold;
                letter-spacing: 1px;
            }
            .contact-info {
                font-size: 11pt;
                color: #555;
                margin: 0;
                font-style: italic;
            }
            .section {
                margin-bottom: 25px;
                page-break-inside: avoid;
            }
            .section h2 {
                font-size: 16pt;
                color: #2c3e50;
                border-bottom: 2px solid #2c3e50;
                padding-bottom: 5px;
                margin-bottom: 15px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            .section p {
                margin: 10px 0;
                text-align: justify;
            }
            .highlight {
                background-color: #f8f9fa;
                padding: 15px;
                border-left: 4px solid #2c3e50;
                margin: 15px 0;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>{{ name }}</h1>
            <p class="contact-info">{{ email }}{% if phone %} | {{ phone }}{% endif %}</p>
        </div>

        {% if summary %}
        <div class="section">
            <h2>Executive Summary</h2>
            <div class="highlight">
                <p>{{ summary }}</p>
            </div>
        </div>
        {% endif %}

        {% if experience %}
        <div class="section">
            <h2>Professional Experience</h2>
            {{ experience | safe }}
        </div>
        {% endif %}

        {% if education %}
        <div class="section">
            <h2>Education</h2>
            <p>{{ education }}</p>
        </div>
        {% endif %}

        {% if skills %}
        <div class="section">
            <h2>Core Competencies</h2>
            <p>{{ skills }}</p>
        </div>
        {% endif %}

        {% if cover_letter %}
        <div style="page-break-before: always;">
            <div class="section">
                <h2>Cover Letter</h2>
                <p>{{ cover_letter }}</p>
            </div>
        </div>
        {% endif %}
    </body>
    </html>
    """
}

def clean_pdf_store():
    """Remove expired PDFs from memory"""
    current_time = datetime.now()
    expired_keys = []
    
    for pdf_id, data in pdf_store.items():
        if isinstance(data, dict) and 'created_at' in data:
            if current_time - data['created_at'] > timedelta(hours=PDF_EXPIRY_HOURS):
                expired_keys.append(pdf_id)
    
    for key in expired_keys:
        del pdf_store[key]

def parse_ai_sections(ai_output: str, data: Dict[str, Any]) -> Dict[str, str]:
    """Enhanced section parsing with better fallbacks"""
    sections = {
        "name": data.get("full_name", ""),
        "email": data.get("email", ""),
        "phone": data.get("phone", ""),
        "summary": "",
        "experience": "",
        "education": "",
        "skills": "",
        "cover_letter": ""
    }
    
    # Try to parse AI output sections
    if "Summary:" in ai_output:
        summary_start = ai_output.find("Summary:") + len("Summary:")
        summary_end = ai_output.find("Experience:") if "Experience:" in ai_output else ai_output.find("Education:")
        if summary_end == -1:
            summary_end = len(ai_output)
        sections["summary"] = ai_output[summary_start:summary_end].strip()
    else:
        sections["summary"] = data.get("summary", "")
    
    if "Experience:" in ai_output:
        exp_start = ai_output.find("Experience:") + len("Experience:")
        exp_end = ai_output.find("Education:") if "Education:" in ai_output else ai_output.find("Skills:")
        if exp_end == -1:
            exp_end = len(ai_output)
        sections["experience"] = ai_output[exp_start:exp_end].strip()
    else:
        # Fallback to form data
        if data.get("job_title") or data.get("responsibilities"):
            experience_parts = []
            if data.get("job_title"):
                experience_parts.append(f"<div class='experience-item'>")
                experience_parts.append(f"<p class='job-title'>{data.get('job_title')}</p>")
                if data.get("company"):
                    experience_parts.append(f"<p class='company-info'>{data.get('company')}")
                    if data.get("years_worked"):
                        experience_parts.append(f" | {data.get('years_worked')} years")
                    experience_parts.append("</p>")
                if data.get("responsibilities"):
                    experience_parts.append(f"<p>{data.get('responsibilities')}</p>")
                experience_parts.append("</div>")
            sections["experience"] = "".join(experience_parts)
    
    if "Education:" in ai_output:
        edu_start = ai_output.find("Education:") + len("Education:")
        edu_end = ai_output.find("Skills:") if "Skills:" in ai_output else ai_output.find("Cover Letter:")
        if edu_end == -1:
            edu_end = len(ai_output)
        sections["education"] = ai_output[edu_start:edu_end].strip()
    else:
        edu_parts = []
        if data.get("degree"):
            edu_parts.append(data.get("degree"))
        if data.get("school"):
            edu_parts.append(data.get("school"))
        sections["education"] = " - ".join(edu_parts) if edu_parts else ""
    
    if "Skills:" in ai_output:
        skills_start = ai_output.find("Skills:") + len("Skills:")
        skills_end = ai_output.find("Cover Letter:") if "Cover Letter:" in ai_output else len(ai_output)
        sections["skills"] = ai_output[skills_start:skills_end].strip()
    else:
        sections["skills"] = data.get("skills", "")
    
    if "Cover Letter:" in ai_output:
        cover_start = ai_output.find("Cover Letter:") + len("Cover Letter:")
        sections["cover_letter"] = ai_output[cover_start:].strip()
    
    return sections

@app.post("/generate-resume")
async def generate_resume(request: Request):
    try:
        body = await request.json()
    except Exception:
        try:
            form = await request.form()
            body = dict(form)
        except Exception as e:
            return JSONResponse(status_code=400, content={"error": f"Invalid request format: {str(e)}"})

    # Clean expired PDFs
    clean_pdf_store()

    # Extract data
    data = body.get("data")
    if data is None:
        data = {k: v for k, v in body.items() if k not in ["template_choice", "generate_cover_letter", "ats_mode"]}

    template_choice = body.get("template_choice", "default")
    generate_cover_letter = body.get("generate_cover_letter", False)
    ats_mode = body.get("ats_mode", False)

    # Validation
    if not data.get("full_name") or not data.get("email") or not data.get("job_title"):
        return JSONResponse(status_code=400, content={
            "error": "Full Name, Email, and Job Title are required fields."
        })

    # Enhanced AI prompt
    style_descriptions = {
        "default": "modern and professional",
        "conservative": "traditional and formal", 
        "creative": "innovative and visually appealing",
        "executive": "senior-level and authoritative"
    }

    base_prompt = f"""You are an expert resume writer. Create a {style_descriptions.get(template_choice, 'professional')} resume {'that is ATS-friendly with simple formatting' if ats_mode else 'with rich formatting and structure'}.

Input Information:
{chr(10).join([f"{k}: {v}" for k, v in data.items() if v])}

Requirements:
1. Write in a professional, engaging tone
2. Use action verbs and quantifiable achievements where possible
3. Tailor content to the job title: {data.get('job_title')}
4. Structure with clear sections: Summary, Experience, Education, Skills
5. Make it compelling and interview-worthy
{'6. Include a personalized cover letter as a separate section' if generate_cover_letter else ''}

Format your response with clear section headers:
Summary:
[Professional summary paragraph]

Experience:
[Detailed work experience with achievements]

Education:
[Educational background]

Skills:
[Relevant skills list]

{'Cover Letter:' if generate_cover_letter else ''}
{'[Personalized cover letter]' if generate_cover_letter else ''}
"""

    # OpenAI API call
    client = openai.OpenAI()
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional career consultant and resume writer with 15+ years of experience helping people land their dream jobs."},
                {"role": "user", "content": base_prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": f"AI service temporarily unavailable: {str(e)}"
        })

    ai_output = response.choices[0].message.content

    # Parse sections with enhanced logic
    sections = parse_ai_sections(ai_output, data)

    # Generate PDF
    try:
        template_html = TEMPLATES.get(template_choice, TEMPLATES["default"])
        template = Template(template_html)
        html_out = template.render(**sections)

        # Enhanced PDF generation with better error handling
        pdf_bytes = BytesIO()
        HTML(string=html_out, base_url="").write_pdf(
            pdf_bytes,
            stylesheets=[],
            presentational_hints=True
        )

        pdf_id = str(uuid.uuid4())
        pdf_store[pdf_id] = {
            'data': pdf_bytes.getvalue(),
            'created_at': datetime.now(),
            'filename': f"resume_{data.get('full_name', 'user')}_{template_choice}.pdf"
        }

        download_url = f"https://resume-writer.onrender.com/download-resume/{pdf_id}"

        return JSONResponse({
            "resume_text": ai_output.strip(),
            "pdf_url": download_url,
            "template_used": template_choice,
            "success": True
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": f"PDF generation failed: {str(e)}",
            "resume_text": ai_output.strip()
        })

@app.get("/download-resume/{pdf_id}")
async def download_resume(pdf_id: str):
    pdf_entry = pdf_store.get(pdf_id)
    if not pdf_entry:
        raise HTTPException(status_code=404, detail="Resume not found or expired")

    pdf_data = pdf_entry['data'] if isinstance(pdf_entry, dict) else pdf_entry
    filename = pdf_entry.get('filename', f'resume_{pdf_id}.pdf') if isinstance(pdf_entry, dict) else f'resume_{pdf_id}.pdf'

    return StreamingResponse(
        BytesIO(pdf_data), 
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "resume-writer"}

# Additional endpoint for template previews
@app.get("/templates")
async def get_templates():
    return {
        "templates": [
            {"id": "default", "name": "Modern", "description": "Clean, professional design suitable for most industries"},
            {"id": "conservative", "name": "Conservative", "description": "Traditional format perfect for formal industries"},
            {"id": "creative", "name": "Creative", "description": "Eye-catching design for creative professionals"},
            {"id": "executive", "name": "Executive", "description": "Authoritative layout for senior positions"}
        ]
    }
