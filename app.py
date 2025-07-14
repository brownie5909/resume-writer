from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
from fastapi.responses import FileResponse, HTMLResponse
import os

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ATSRequest(BaseModel):
    resume_text: str
    job_description: str

# Serve a test HTML page for quick debugging
@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head><meta charset='utf-8'><title>Resume Builder Test</title></head>
    <body>
      <form id="testForm">
        <input name="name" placeholder="Name" value="John Doe"><br>
        <input name="contact_info" placeholder="Email" value="john@example.com"><br>
        <textarea name="work_history">Worked at XYZ for 5 years.</textarea><br>
        <textarea name="job_description">Sales role requiring leadership.</textarea><br>
        <button type="submit">Submit</button>
      </form>

      <pre id="output" style="border:1px solid#ccc;padding:10px;"></pre>

      <script>
        document.getElementById('testForm').addEventListener('submit', function(e){
          e.preventDefault();
          document.getElementById('output').innerText = 'Loading…';
          fetch('/generate-resume', {
            method: 'POST',
            body: new FormData(this)
          })
          .then(r=>r.json())
          .then(json=>{
            document.getElementById('output').innerText =
              json.data?.resume || 'ERROR: '+JSON.stringify(json);
          })
          .catch(err=>{
            document.getElementById('output').innerText = 'Fetch failed: '+err;
          });
        });
      </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)

@app.post("/generate-resume")
async def generate_resume(req: Request):
    try:
        data = await req.json()
        if not data:
            raise ValueError("Empty JSON payload.")
        data = {k.lower(): v for k, v in data.items()}
    except Exception:
        form = await req.form()
        data = {}
        for k, v in form.items():
            data[k.lower()] = v

    name = str(data.get("name", "")).strip()
    contact_info = str(data.get("contact_info", "")).strip()
    work_history = str(data.get("work_history", "")).strip()
    job_description = str(data.get("job_description", "")).strip()

    missing = []
    if not name: missing.append("name")
    if not contact_info: missing.append("contact_info")
    if not work_history: missing.append("work_history")
    if not job_description: missing.append("job_description")

    if missing:
        return {"data": {"error": f"Missing fields: {', '.join(missing)}"}}

    prompt = f'''Create a professional resume for {name}. Contact Info: {contact_info} Work History: {work_history} Tailor the resume to the following job description: {job_description} Make it ATS-friendly with action verbs and concise bullet points. '''

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800
        )
        return {"data": {"resume": response.choices[0].message.content}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-cover-letter")
async def generate_cover_letter(req: Request):
    try:
        data = await req.json()
        if not data:
            raise ValueError("Empty JSON payload.")
        data = {k.lower(): v for k, v in data.items()}
    except Exception:
        form = await req.form()
        data = {}
        for k, v in form.items():
            data[k.lower()] = v

    name = str(data.get("name", "")).strip()
    contact_info = str(data.get("contact_info", "")).strip()
    work_history = str(data.get("work_history", "")).strip()
    job_description = str(data.get("job_description", "")).strip()

    if not all([name, contact_info, work_history, job_description]):
        raise HTTPException(status_code=400, detail="All fields are required.")

    prompt = f'''Write a cover letter for {name}. Contact Info: {contact_info} Work History: {work_history} Tailor it to the following job description: {job_description} Use a professional and confident tone. '''

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=600
        )
        return {"data": {"cover_letter": response.choices[0].message.content}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ats-check")
async def ats_check(request: ATSRequest):
    resume_words = set(request.resume_text.lower().split())
    job_words = set(request.job_description.lower().split())
    match = len(resume_words & job_words) / len(job_words)
    return {"data": {"ats_match_percentage": round(match * 100, 2)}}

@app.post("/debug-webhook")
async def debug_webhook(request: Request):
    headers = dict(request.headers)
    body = await request.body()
    decoded_body = body.decode("utf-8", errors="replace")

    log_entry = f"=== New Request ===\nHeaders: {headers}\nBody: {decoded_body}\n\n"

    log_path = "elementor_debug.log"

    with open(log_path, "a") as f:
        f.write(log_entry)

    return {"headers": headers, "raw_body": decoded_body}

@app.get("/download-debug-log")
async def download_debug_log():
    log_path = "elementor_debug.log"
    if os.path.exists(log_path):
        return FileResponse(log_path, filename="elementor_debug.log")
    else:
        raise HTTPException(status_code=404, detail="Log file not found.")
