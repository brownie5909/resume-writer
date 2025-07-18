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

# Setup CORS to allow frontend origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://hireready-3a5b8.ingress-erytho.ewp.live"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Read OpenAI API Key from environment variable
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Function to generate resume text using GPT

def generate_resume_text(data):
    prompt = f"""
Generate a professional resume based on the following details:

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
Template Style: {data.get('template_choice', 'conservative')}

Format it in professional resume tone.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=700
    )

    return response.choices[0].message.content

# Function to generate styled HTML resume

def generate_html_resume(data, resume_text):
    return f"""
    <html>
    <head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.5; padding: 20px; }}
        h1 {{ font-size: 24px; margin-bottom: 10px; }}
        .section {{ margin-bottom: 20px; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
    </head>
    <body>
        <h1>{data.get('full_name', 'N/A')}</h1>
        <div class="section">
            <strong>Email:</strong> {data.get('email', 'N/A')}<br>
            <strong>Phone:</strong> {data.get('phone', 'N/A')}
        </div>
        <div class="section">
            <pre>{resume_text}</pre>
        </div>
    </body>
    </html>
    """

# Function to generate PDF using WeasyPrint

def generate_pdf(content):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf", dir="/tmp") as tmp:
        HTML(string=content).write_pdf(tmp.name)
        return tmp.name

# API endpoint to receive resume data and return HTML directly

@app.post("/submit_resume")
async def submit_resume(request: Request):
    print("Received request at /submit_resume")

    content_type = request.headers.get('content-type', '')
    print(f"Content-Type: {content_type}")

    data = {}

    if 'application/json' in content_type:
        data = await request.json()
        print(f"Received JSON data: {json.dumps(data, indent=2)}")
    else:
        form = await request.form()
        print(f"Received form data: {form}")
        for key, value in form.items():
            if key.startswith("fields[") and key.endswith("[value]"):
                field_id = key.split("[")[1].split("]")[0]
                data[field_id] = value
        print(f"Parsed data: {json.dumps(data, indent=2)}")

    print("Generating resume text...")
    resume_text = generate_resume_text(data)
    print("Resume text generated.")

    resume_id = str(uuid.uuid4())
    data['resume_id'] = resume_id

    html_resume = generate_html_resume(data, resume_text)
    print("HTML resume generated.")

    pdf_path = generate_pdf(html_resume)
    print(f"PDF generated at: {pdf_path}")

    # Save cache
    cache_data = {
        "html_resume": html_resume,
        "download_link": f"/download_pdf/{os.path.basename(pdf_path)}",
        "template_choice": data.get('template_choice', 'conservative')
    }
    cache_file = f"/tmp/{resume_id}.json"
    print(f"Saving cache data to {cache_file}")
    with open(cache_file, "w") as f:
        json.dump(cache_data, f)

    # Return EXACTLY what Elementor expects
    return JSONResponse({
        "success": True,
        "data": {
            "message": "Resume generated successfully.",
            "resume_output": html_resume
        }
    }, status_code=200)

# API endpoint to download generated PDF

@app.get("/download_pdf/{filename}")
async def download_pdf(filename: str):
    file_path = f"/tmp/{filename}"
    return FileResponse(file_path, media_type='application/pdf', filename=filename)
