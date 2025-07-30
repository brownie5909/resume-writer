from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import os
import openai
from io import BytesIO
import PyPDF2
import docx
import json
import re
from typing import Optional

router = APIRouter()

# Initialize OpenAI client
openai.api_key = os.getenv("OPENAI_API_KEY")

@router.post("/analyze-resume")
async def analyze_resume(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)  # For premium user verification
):
    """
    Analyze an uploaded resume and provide detailed feedback
    Premium feature only
    """
    
    # TODO: Add premium user verification here
    # if not is_premium_user(user_id):
    #     raise HTTPException(status_code=403, detail="Premium subscription required")
    
    try:
        # Extract text from uploaded file
        resume_text = await extract_text_from_file(file)
        
        if not resume_text or len(resume_text.strip()) < 100:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not extract sufficient text from the resume. Please ensure the file is readable."}
            )
        
        # Analyze the resume with AI
        analysis_result = await analyze_resume_with_ai(resume_text, target_role)
        
        # Generate improved version
        improved_resume = await generate_improved_resume(resume_text, target_role, analysis_result)
        
        return JSONResponse({
            "success": True,
            "analysis": analysis_result,
            "improved_resume": improved_resume,
            "original_length": len(resume_text),
            "target_role": target_role
        })
        
    except Exception as e:
        print(f"Resume analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Analysis failed: {str(e)}"}
        )

async def extract_text_from_file(file: UploadFile) -> str:
    """Extract text from PDF, DOCX, or TXT files"""
    
    content = await file.read()
    file_extension = file.filename.lower().split('.')[-1]
    
    try:
        if file_extension == 'pdf':
            return extract_pdf_text(content)
        elif file_extension in ['docx', 'doc']:
            return extract_docx_text(content)
        elif file_extension == 'txt':
            return content.decode('utf-8')
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")
            
    except Exception as e:
        raise ValueError(f"Could not extract text from {file_extension} file: {str(e)}")

def extract_pdf_text(content: bytes) -> str:
    """Extract text from PDF content"""
    try:
        pdf_file = BytesIO(content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"PDF extraction failed: {str(e)}")

def extract_docx_text(content: bytes) -> str:
    """Extract text from DOCX content"""
    try:
        docx_file = BytesIO(content)
        doc = docx.Document(docx_file)
        
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        
        return text.strip()
    except Exception as e:
        raise ValueError(f"DOCX extraction failed: {str(e)}")

async def analyze_resume_with_ai(resume_text: str, target_role: Optional[str] = None) -> dict:
    """Use AI to analyze the resume and provide detailed feedback"""
    
    role_context = f" for a {target_role} position" if target_role else ""
    
    analysis_prompt = f"""
You are an expert resume reviewer and career coach. Analyze this resume{role_context} and provide a comprehensive evaluation.

Resume Text:
{resume_text}

Provide your analysis in the following JSON format:
{{
    "overall_score": [number from 0-100],
    "ats_score": [number from 0-100],
    "strengths": ["strength 1", "strength 2", "strength 3"],
    "weaknesses": ["weakness 1", "weakness 2", "weakness 3"],
    "keyword_analysis": {{
        "missing_keywords": ["keyword1", "keyword2"],
        "present_keywords": ["keyword1", "keyword2"],
        "keyword_density": [number from 0-100]
    }},
    "sections_analysis": {{
        "contact_info": {{"score": [0-100], "feedback": "detailed feedback"}},
        "summary": {{"score": [0-100], "feedback": "detailed feedback"}},
        "experience": {{"score": [0-100], "feedback": "detailed feedback"}},
        "education": {{"score": [0-100], "feedback": "detailed feedback"}},
        "skills": {{"score": [0-100], "feedback": "detailed feedback"}}
    }},
    "formatting_score": [number from 0-100],
    "specific_improvements": [
        "Specific actionable improvement 1",
        "Specific actionable improvement 2",
        "Specific actionable improvement 3"
    ],
    "ats_recommendations": [
        "ATS improvement 1",
        "ATS improvement 2"
    ]
}}

Focus on:
1. ATS compatibility and keyword optimization{" for " + target_role if target_role else ""}
2. Content quality and achievement quantification
3. Professional formatting and structure
4. Missing sections or information
5. Specific, actionable improvements
"""

    try:
        client = openai.OpenAI()
        response = await client.chat.completions.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert resume reviewer with 15+ years of experience helping professionals optimize their resumes for ATS systems and hiring managers."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )
        
        ai_response = response.choices[0].message.content
        
        # Try to parse JSON response
        try:
            # Extract JSON from response if it's wrapped in markdown
            if "```json" in ai_response:
                json_start = ai_response.find("```json") + 7
                json_end = ai_response.find("```", json_start)
                ai_response = ai_response[json_start:json_end]
            elif "```" in ai_response:
                json_start = ai_response.find("```") + 3
                json_end = ai_response.find("```", json_start)
                ai_response = ai_response[json_start:json_end]
            
            analysis_data = json.loads(ai_response.strip())
            return analysis_data
            
        except json.JSONDecodeError:
            # If JSON parsing fails, create structured response from text
            return parse_analysis_from_text(ai_response)
            
    except Exception as e:
        print(f"AI analysis error: {str(e)}")
        return get_fallback_analysis()

async def generate_improved_resume(resume_text: str, target_role: Optional[str], analysis: dict) -> str:
    """Generate an improved version of the resume based on analysis"""
    
    role_context = f" optimized for {target_role} positions" if target_role else ""
    
    improvement_prompt = f"""
Based on the resume analysis, create an improved version of this resume{role_context}.

Original Resume:
{resume_text}

Key improvements to make:
{json.dumps(analysis.get('specific_improvements', []), indent=2)}

ATS improvements needed:
{json.dumps(analysis.get('ats_recommendations', []), indent=2)}

Missing keywords to include:
{json.dumps(analysis.get('keyword_analysis', {}).get('missing_keywords', []), indent=2)}

Create an improved version that:
1. Maintains all original information and experience
2. Improves formatting and structure
3. Adds missing keywords naturally
4. Quantifies achievements where possible
5. Uses strong action verbs
6. Follows ATS-friendly formatting
7. Includes a compelling professional summary if missing

Return only the improved resume text, formatted professionally.
"""

    try:
        client = openai.OpenAI()
        response = await client.chat.completions.acreate(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert resume writer who creates ATS-optimized, professional resumes that help candidates get interviews."},
                {"role": "user", "content": improvement_prompt}
            ],
            temperature=0.4,
            max_tokens=2000
        )
        
        improved_resume = response.choices[0].message.content.strip()
        return improved_resume
        
    except Exception as e:
        print(f"Resume improvement error: {str(e)}")
        return "Unable to generate improved version. Please try again."

def parse_analysis_from_text(text: str) -> dict:
    """Parse analysis from plain text if JSON parsing fails"""
    
    # Basic text parsing for fallback
    overall_score = 75  # Default score
    
    # Try to extract scores from text
    score_pattern = r'(\d+)/100|(\d+)%|score[:\s]*(\d+)'
    scores = re.findall(score_pattern, text.lower())
    if scores:
        overall_score = int([s for s in scores[0] if s][0])
    
    return {
        "overall_score": overall_score,
        "ats_score": max(60, overall_score - 10),
        "strengths": [
            "Professional experience documented",
            "Clear contact information",
            "Relevant skills listed"
        ],
        "weaknesses": [
            "Could benefit from more quantified achievements",
            "May need keyword optimization",
            "Consider adding a professional summary"
        ],
        "keyword_analysis": {
            "missing_keywords": ["leadership", "results-driven", "collaborative"],
            "present_keywords": ["experience", "skills", "education"],
            "keyword_density": 65
        },
        "sections_analysis": {
            "contact_info": {"score": 85, "feedback": "Contact information is clear and professional"},
            "summary": {"score": 50, "feedback": "Consider adding a compelling professional summary"},
            "experience": {"score": 75, "feedback": "Good experience documentation, add more quantified achievements"},
            "education": {"score": 80, "feedback": "Education section is well formatted"},
            "skills": {"score": 70, "feedback": "Skills are relevant, consider grouping by category"}
        },
        "formatting_score": 80,
        "specific_improvements": [
            "Add quantified achievements (percentages, dollar amounts, etc.)",
            "Include a professional summary at the top",
            "Use more action verbs (achieved, implemented, optimized)",
            "Add relevant industry keywords",
            "Ensure consistent formatting throughout"
        ],
        "ats_recommendations": [
            "Use standard section headers (Experience, Education, Skills)",
            "Avoid tables, columns, and graphics that ATS cannot read",
            "Include keywords from the job description naturally in content"
        ]
    }

def get_fallback_analysis() -> dict:
    """Fallback analysis if AI completely fails"""
    return {
        "overall_score": 70,
        "ats_score": 65,
        "strengths": [
            "Resume successfully uploaded and processed",
            "Readable format detected",
            "Standard resume structure identified"
        ],
        "weaknesses": [
            "Detailed analysis temporarily unavailable",
            "Please try again for complete feedback"
        ],
        "keyword_analysis": {
            "missing_keywords": ["Analysis pending"],
            "present_keywords": ["Content detected"],
            "keyword_density": 50
        },
        "sections_analysis": {
            "contact_info": {"score": 70, "feedback": "Analysis in progress"},
            "summary": {"score": 70, "feedback": "Analysis in progress"},
            "experience": {"score": 70, "feedback": "Analysis in progress"},
            "education": {"score": 70, "feedback": "Analysis in progress"},
            "skills": {"score": 70, "feedback": "Analysis in progress"}
        },
        "formatting_score": 70,
        "specific_improvements": [
            "Detailed analysis temporarily unavailable",
            "Please try again for specific recommendations"
        ],
        "ats_recommendations": [
            "Use standard section headers",
            "Maintain clean, simple formatting"
        ]
    }

# Health check for resume analysis service
@router.get("/resume-analysis/health")
async def resume_analysis_health():
    return {"status": "healthy", "service": "resume-analysis"}
