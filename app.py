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

# Serve a styled test HTML page for quick debugging
@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset='utf-8'>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <title>Resume Builder Test</title>
      <style>
        body { font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 0; }
        .container { max-width: 700px; margin: 40px auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        h1 { text-align: center; color: #333; }
        form { display: grid; grid-gap: 15px; }
        label { font-weight: bold; color: #555; }
        input, textarea { width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 1rem; }
        button { padding: 12px 20px; background: #0073e6; color: #fff; border: none; border-radius: 4px; font-size: 1rem; cursor: pointer; }
        button:hover { background: #005bb5; }
        pre#output { background: #272822; color: #f8f8f2; padding: 15px; border-radius: 4px; overflow-x: auto; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>AI Resume Builder Test</h1>
        <form id="testForm">
          <div>
            <label for="name">Full Name</label><br>
            <input id="name" name="name" placeholder="John Doe" value="John Doe" required>
          </div>
          <div>
            <label for="contact_info">Email</label><br>
            <input id="contact_info" name="contact_info" placeholder="john@example.com" value="john@example.com" required>
          </div>
          <div>
            <label for="work_history">Work History</label><br>
            <textarea id="work_history" name="work_history" rows="4" required>Worked at XYZ for 5 years.</textarea>
          </div>
          <div>
            <label for="job_description">Job Description</label><br>
            <textarea id="job_description" name="job_description" rows="4" required>Sales role requiring leadership.</textarea>
          </div>
          <div style="text-align:center;">
            <button type="submit">Generate Resume</button>
          </div>
        </form>

        <h2>Generated Resume</h2>
        <pre id="output">Submit the form to generate your resume...</pre>
      </div>

      <script>
        document.getElementById('testForm').addEventListener('submit', function(e){
          e.preventDefault();
          const output = document.getElementById('output');
          output.innerText = 'Loading…';
          fetch('/generate-resume', {
            method: 'POST',
            body: new FormData(this)
          })
          .then(r => r.json())
          .then(json => {
            output.innerText = json.data?.resume || ('ERROR: ' + JSON.stringify(json));
          })
          .catch(err => {
            output.innerText = 'Fetch failed: ' + err;
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
