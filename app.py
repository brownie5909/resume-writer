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
    allow_origins=["*"],       # allow any origin
    allow_credentials=False,   # disable credentials so wildcard origin works
    allow_methods=["*"],       # allow all methods
    allow_headers=["*"],       # allow all headers
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class ATSRequest(BaseModel):
    resume_text: str
    job_description: str

# Serve a styled test HTML page for quick debugging with Bootstrap
@app.get("/", response_class=HTMLResponse)
async def index():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset='utf-8'>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <title>Resume Builder Test</title>
      <!-- Bootstrap CSS -->
      <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/bootstrap/4.6.1/css/bootstrap.min.css" integrity="sha512-T584y5Q7jL+z9OYnN5aXsX5G3PVZ4ab7RR6KIDe3G0lI+HXc1iXkEHc1h8s6bJdN9u1em7B7XhKpU9Wcu6F5nQ==" crossorigin="anonymous" referrerpolicy="no-referrer" />
      <style>
        body { background: #f8f9fa; }
        pre#output { background: #343a40; color: #f8f9fa; padding: 15px; border-radius: 4px; max-height: 400px; overflow-y: auto; }
      </style>
    </head>
    <body>
      <div class="container mt-5 mb-5">
        <h1 class="text-center mb-4">AI Resume Builder Test</h1>
        <form id="testForm">
          <div class="form-group">
            <label for="name">Full Name</label>
            <input id="name" name="name" class="form-control" placeholder="John Doe" value="John Doe" required>
          </div>
          <div class="form-group">
            <label for="contact_info">Email</label>
            <input id="contact_info" name="contact_info" type="email" class="form-control" placeholder="john@example.com" value="john@example.com" required>
          </div>
          <div class="form-group">
            <label for="work_history">Work History</label>
            <textarea id="work_history" name="work_history" class="form-control" rows="4" required>Worked at XYZ for 5 years.</textarea>
          </div>
          <div class="form-group">
            <label for="job_description">Job Description</label>
            <textarea id="job_description" name="job_description" class="form-control" rows="4" required>Sales role requiring leadership.</textarea>
          </div>
          <div class="text-center">
            <button type="submit" class="btn btn-primary px-5">Generate Resume</button>
          </div>
        </form>

        <h2 class="mt-5">Generated Resume</h2>
        <pre id="output">Submit the form to generate your resume...</pre>
      </div>

      <!-- Optional JavaScript for form submission -->
      <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js" integrity="sha256-DfXdz2htPH0lsSSs5nCTpuj/zy4C+OGpamoFVy38E0=" crossorigin="anonymous"></script>
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

      <!-- Auto‐resize iframe snippet -->
      <script>
        function sendHeight() {
          window.parent.postMessage(
            { iframeHeight: document.documentElement.scrollHeight },
            '*'
          );
        }
        window.addEventListener('load', sendHeight);
        window.addEventListener('resize', sendHeight);
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

        # ─── START FLATTEN PATCH ───────────────────────────────────────────────────
    # Elementor nests inputs as form_fields[name]=…; we grab those here
    flattened = {}
    for key, val in data.items():
        if key.startswith("form_fields[") and key.endswith("]"):
            inner = key[len("form_fields["):-1]   # extract name inside brackets
            flattened[inner.lower()] = val
    if flattened:
        data = flattened
    # ─── END FLATTEN PATCH ─────────────────────────────────────────────────────

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

# ... remaining endpoints unchanged ...
