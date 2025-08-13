# Copy this EXACTLY into: routes/interview.py

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os

router = APIRouter()

# Models
class InterviewInput(BaseModel):
    company: str
    role: str

class FeedbackInput(BaseModel):
    question: str
    answer: str

class JobResearchInput(BaseModel):
    company_name: str
    job_role: str

# Basic interview prep route
@router.post("/interview-prep")
async def interview_prep(payload: InterviewInput):
    """Basic interview preparation - works without OpenAI for testing"""
    
    # Mock response for testing
    prep_text = f"""# Interview Preparation for {payload.role} at {payload.company}

## Company Research
- Research {payload.company}'s mission and values
- Look up recent news and developments
- Understand their products/services

## Role Expectations
- Review the job description carefully
- Identify key skills and requirements
- Prepare examples of relevant experience

## STAR Method Reminder
- Situation: Set the context
- Task: Describe what you needed to do
- Action: Explain what you did
- Result: Share the outcome

## Smart Questions to Ask
- What does success look like in this role?
- What are the biggest challenges facing the team?
- How do you measure performance?
- What opportunities are there for growth?
"""

    questions = [
        f"Why do you want to work at {payload.company}?",
        f"What interests you about this {payload.role} position?",
        "Tell me about yourself and your background.",
        "What are your greatest strengths?",
        "Describe a challenging project you've worked on.",
        "Where do you see yourself in 5 years?"
    ]

    return {
        "success": True,
        "prep": prep_text,
        "questions": questions
    }

# Basic feedback route
@router.post("/interview-feedback")
async def interview_feedback(payload: FeedbackInput):
    """Basic interview feedback - works without OpenAI for testing"""
    
    # Mock feedback for testing
    feedback = f"""Your answer to '{payload.question}' shows good structure. Consider adding more specific examples and quantifiable results. Make sure to highlight your unique value proposition and how it relates to the role you're applying for."""

    return {
        "success": True,
        "feedback": feedback
    }

# Job research route - FIXED VERSION
@router.post("/research-job")
async def research_job_application(payload: JobResearchInput):
    """Research a company and job role - enhanced version"""
    
    try:
        print(f"🔍 Research request for: {payload.company_name} - {payload.job_role}")
        
        # Mock company data for testing - enhanced with more realistic data
        company_info = {
            "name": payload.company_name,
            "industry": "Technology" if any(word in payload.company_name.lower() for word in ['tech', 'software', 'app', 'digital']) else "Professional Services",
            "size": "500-1000 employees",
            "founded": "2010",
            "headquarters": "Sydney, Australia" if "australia" in payload.company_name.lower() else "Melbourne, Australia",
            "website": f"www.{payload.company_name.lower().replace(' ', '').replace('.', '')}.com.au",
            "description": f"{payload.company_name} is a growing company in their industry focused on innovation and customer success. They value teamwork, professional development, and delivering exceptional results for their clients."
        }
        
        # Smart questions tailored to the role
        questions_to_ask = [
            f"What does a typical day look like in this {payload.job_role} role?",
            "What are the biggest challenges facing the team right now?",
            "How do you measure success in this position?",
            "What opportunities are there for professional development and career growth?",
            "Can you describe the company culture and team dynamics?",
            "What are the next steps in the interview process?",
            f"What skills do you think are most important for success as a {payload.job_role}?",
            "How does this role contribute to the company's overall goals?"
        ]
        
        # Potential interview questions based on role
        potential_interview_questions = [
            {"question": "Tell us about yourself and why you're interested in this role.", "category": "General"},
            {"question": f"What experience do you have that makes you suitable for a {payload.job_role} position?", "category": "Experience"},
            {"question": f"Why do you want to work at {payload.company_name} specifically?", "category": "Company-specific"},
            {"question": "Describe a challenging project you've worked on and how you overcame obstacles.", "category": "Behavioral"},
            {"question": "Where do you see yourself in 5 years?", "category": "Career Goals"},
            {"question": f"What skills do you think are most important for success in {payload.job_role}?", "category": "Role-specific"},
            {"question": "How do you handle working under pressure or tight deadlines?", "category": "Behavioral"},
            {"question": "What interests you most about this industry?", "category": "Industry Knowledge"}
        ]
        
        result = {
            "success": True,
            "data": {
                "company_info": company_info,
                "questions_to_ask": questions_to_ask,
                "potential_interview_questions": potential_interview_questions
            }
        }
        
        print(f"✅ Research completed successfully for {payload.company_name}")
        return result
        
    except Exception as e:
        print(f"❌ Research error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": f"Research failed: {str(e)}"
            }
        )

# Alternative route that accepts form data instead of JSON
@router.post("/research-job-form")
async def research_job_form(request: Request):
    """Research job - accepts form data"""
    try:
        # Handle both JSON and form data
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            body = await request.json()
        else:
            form = await request.form()
            body = dict(form)
        
        company_name = body.get("company_name", "").strip()
        job_role = body.get("job_role", "").strip()
        
        if not company_name or not job_role:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Company name and job role are required"}
            )
        
        # Use the same logic as the main research function
        payload = JobResearchInput(company_name=company_name, job_role=job_role)
        return await research_job_application(payload)
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": f"Request processing failed: {str(e)}"}
        )

# Health check for interview routes
@router.get("/interview/health")
async def interview_health():
    """Health check for interview endpoints"""
    return {
        "status": "healthy",
        "service": "interview-api",
        "endpoints": [
            "/interview-prep",
            "/interview-feedback", 
            "/research-job",
            "/research-job-form"
        ]
    }