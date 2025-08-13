# Copy this EXACTLY into: routes/resume_analysis.py

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import JSONResponse
import os
import magic
from typing import Optional

router = APIRouter()

# File validation constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/msword", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/rtf"
}
ALLOWED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}

def validate_file(file: UploadFile) -> None:
    """Comprehensive file validation"""
    
    # Check if file exists
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Check file extension
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size (if available)
    if hasattr(file, 'size') and file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail=f"File too large. Max size: {MAX_FILE_SIZE // (1024*1024)}MB"
        )
    
    # Check MIME type if provided
    if file.content_type and file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: PDF, Word documents, plain text"
        )

@router.post("/analyze-resume")
async def analyze_resume(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    user_id: Optional[str] = Form(None)
):
    """
    Basic resume analysis with comprehensive validation
    """
    
    try:
        print(f"🔬 Starting analysis for file: {file.filename}")
        print(f"🎯 Target role: {target_role}")
        
        # Comprehensive file validation
        validate_file(file)
        
        # Read file content (basic)
        content = await file.read()
        text_content = "Sample resume content for testing"
        
        # Mock analysis for testing
        analysis_result = {
            "overall_score": 75,
            "ats_score": 80,
            "formatting_score": 70,
            "strengths": [
                "Clear contact information",
                "Professional experience documented", 
                "Skills section present"
            ],
            "weaknesses": [
                "Could add more quantified achievements",
                "Consider adding a professional summary",
                "Improve keyword optimization"
            ],
            "keyword_analysis": {
                "missing_keywords": ["leadership", "results-driven", "collaborative"],
                "present_keywords": ["experience", "skills", "professional"],
                "keyword_density": 65
            },
            "sections_analysis": {
                "contact_info": {"score": 85, "feedback": "Contact information is clear and complete"},
                "summary": {"score": 60, "feedback": "Consider adding a compelling professional summary"},
                "experience": {"score": 75, "feedback": "Experience section is well-structured"},
                "education": {"score": 80, "feedback": "Education background is clearly presented"},
                "skills": {"score": 70, "feedback": "Skills section could be more specific"}
            },
            "specific_improvements": [
                "Add quantified achievements with specific numbers and percentages",
                "Include a compelling professional summary at the top",
                "Use stronger action verbs (achieved, implemented, optimized)",
                f"Optimize for {target_role} keywords" if target_role else "Add relevant industry keywords"
            ],
            "ats_recommendations": [
                "Use standard section headers (Experience, Education, Skills)",
                "Maintain consistent formatting throughout",
                "Include relevant keywords naturally in content"
            ]
        }
        
        # Mock improved resume
        improved_resume = f"""
IMPROVED RESUME FOR {target_role or 'TARGET ROLE'}

[Your Name]
[Email] | [Phone] | [Location]

PROFESSIONAL SUMMARY
Results-driven professional with proven experience in delivering exceptional outcomes.
Strong background in problem-solving and team collaboration.

EXPERIENCE
• Previous Role - Company Name
  - Achieved 25% improvement in efficiency through process optimization
  - Led cross-functional team of 5+ members
  - Implemented new systems resulting in $50K annual savings

EDUCATION
• Degree - Institution Name
• Relevant certifications and training

SKILLS
• Technical Skills: [Relevant to {target_role or 'role'}]
• Soft Skills: Leadership, Communication, Problem-solving
• Industry Knowledge: Best practices and current trends
        """
        
        return JSONResponse({
            "success": True,
            "analysis": analysis_result,
            "improved_resume": improved_resume,
            "original_length": len(text_content),
            "target_role": target_role,
            "debug_info": {
                "file_type": file.content_type,
                "filename": file.filename,
                "text_preview": "Resume analysis completed successfully"
            }
        })
        
    except Exception as e:
        print(f"❌ Resume analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Analysis failed: {str(e)}"}
        )

@router.get("/resume-analysis/health")
async def resume_analysis_health():
    return {"status": "healthy", "service": "resume-analysis"}