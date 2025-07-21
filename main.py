from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from io import BytesIO
from fpdf import FPDF
import uuid
import os
import openai

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

    base_prompt = """You are a professional resume and cover letter writer.
Generate a {style} resume {ats_note} based on the following information:

{fields}

Output:
- Resume:
{cover_note}
"""

    style = template_choice
    fields = "\n".join([f"{k}: {v}" for k, v in data.items()])
    ats_note = "that is ATS-friendly and plain text" if ats_mode else "with professional formatting"
    cover_note = "- Cover Letter:" if generate_cover_letter else ""

    prompt = base_prompt.format(style=style, fields=fields, ats_note=ats_note, cover_note=cover_note)

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

    # Split output into sections
    resume_text = ""
    cover_letter_text = ""
    current_section = None
    for line in ai_output.strip().split("\n"):
        if line.strip().lower().startswith("resume"):
            current_section = "resume"
            continue
        elif line.strip().lower().startswith("cover letter"):
            current_section = "cover_letter"
            continue
        if current_section == "resume":
            resume_text += line + "\n"
        elif current_section == "cover_letter":
            cover_letter_text += line + "\n"

    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Format Resume
    pdf.set_font("Arial", style="B", size=16)
    pdf.cell(0, 10, "Resume", ln=True)
    pdf.set_font("Arial", size=12)
    for line in resume_text.strip().split("\n"):
        pdf.multi_cell(0, 8, line.strip() or " ")

    # Format Cover Letter if exists
    if generate_cover_letter and cover_letter_text.strip():
        pdf.ln(10)
        pdf.set_font("Arial", style="B", size=16)
        pdf.cell(0, 10, "Cover Letter", ln=True)
        pdf.set_font("Arial", size=12)
        for line in cover_letter_text.strip().split("\n"):
            pdf.multi_cell(0, 8, line.strip() or " ")

    pdf_output = pdf.output(dest='S')
    pdf_bytes = BytesIO(pdf_output)

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
