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

# Initialize OpenAI client - FIXED VERSION
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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
        print(f"🔬 Starting analysis for file: {file.filename}")
        print(f"🎯 Target role: {target_role}")
        
        # Extract text from uploaded file
        resume_text = await extract_text_from_file(file)
        print(f"📄 Extracted {len(resume_text)} characters")
        
        if not resume_text or len(resume_text.strip()) < 100:
            return JSONResponse(
                status_code=400,
                content={"error": "Could not extract sufficient text from the resume. Please ensure the file is readable."}
            )
        
        # Analyze the resume with AI
        print("🤖 Starting AI analysis...")
        analysis_result = await analyze_resume_with_ai(resume_text, target_role)
        print("✅ AI analysis completed")
        
        # Generate improved version
        print("🚀 Generating improved resume...")
        improved_resume = await generate_improved_resume(resume_text, target_role, analysis_result)
        print("✅ Improved resume generated")
        
        return JSONResponse({
            "success": True,
            "analysis": analysis_result,
            "improved_resume": improved_resume,
            "original_length": len(resume_text),
            "target_role": target_role
        })
        
    except Exception as e:
        print(f"❌ Resume analysis error: {str(e)}")
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
    """Use AI to analyze the resume and provide detailed feedback - FIXED VERSION"""
    
    role_context = f" for a {target_role} position" if target_role else ""
    
    # Simplified analysis prompt that's more reliable
    analysis_prompt = f"""
Analyze this resume{role_context} and provide specific, actionable feedback.

Resume Text:
{resume_text[:3000]}  

Provide analysis in this exact format:

OVERALL_SCORE: [number 0-100]
ATS_SCORE: [number 0-100] 
FORMATTING_SCORE: [number 0-100]

STRENGTHS:
- [strength 1]
- [strength 2] 
- [strength 3]

WEAKNESSES:
- [weakness 1]
- [weakness 2]
- [weakness 3]

MISSING_KEYWORDS: [keyword1, keyword2, keyword3]
PRESENT_KEYWORDS: [keyword1, keyword2, keyword3]

SPECIFIC_IMPROVEMENTS:
1. [improvement 1]
2. [improvement 2] 
3. [improvement 3]

ATS_RECOMMENDATIONS:
1. [ats tip 1]
2. [ats tip 2]

SECTION_FEEDBACK:
Contact: [score]/100 - [feedback]
Summary: [score]/100 - [feedback]  
Experience: [score]/100 - [feedback]
Education: [score]/100 - [feedback]
Skills: [score]/100 - [feedback]
"""

    try:
        print("📤 Sending request to OpenAI...")
        
        # Use synchronous client - this was the issue!
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert resume reviewer with 15+ years of experience. Provide specific, actionable feedback in the exact format requested."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            max_tokens=1500
        )
        
        ai_response = response.choices[0].message.content
        print("📥 Received AI response")
        
        # Parse the structured response
        analysis_data = parse_structured_analysis(ai_response)
        
        # Add keyword density calculation
        if analysis_data.get('keyword_analysis'):
            missing_count = len(analysis_data['keyword_analysis'].get('missing_keywords', []))
            present_count = len(analysis_data['keyword_analysis'].get('present_keywords', []))
            total_keywords = missing_count + present_count
            
            if total_keywords > 0:
                density = int((present_count / total_keywords) * 100)
                analysis_data['keyword_analysis']['keyword_density'] = density
        
        return analysis_data
        
    except Exception as e:
        print(f"❌ AI analysis error: {str(e)}")
        # Return enhanced fallback with some real analysis
        return get_enhanced_fallback_analysis(resume_text, target_role)

def parse_structured_analysis(ai_response: str) -> dict:
    """Parse the structured AI response"""
    
    try:
        # Extract scores
        overall_score = extract_score(ai_response, "OVERALL_SCORE")
        ats_score = extract_score(ai_response, "ATS_SCORE") 
        formatting_score = extract_score(ai_response, "FORMATTING_SCORE")
        
        # Extract lists
        strengths = extract_list(ai_response, "STRENGTHS:", "WEAKNESSES:")
        weaknesses = extract_list(ai_response, "WEAKNESSES:", "MISSING_KEYWORDS:")
        
        # Extract keywords
        missing_keywords = extract_keywords(ai_response, "MISSING_KEYWORDS:")
        present_keywords = extract_keywords(ai_response, "PRESENT_KEYWORDS:")
        
        # Extract improvements
        improvements = extract_numbered_list(ai_response, "SPECIFIC_IMPROVEMENTS:")
        ats_recommendations = extract_numbered_list(ai_response, "ATS_RECOMMENDATIONS:")
        
        # Extract section feedback
        sections = parse_section_feedback(ai_response)
        
        return {
            "overall_score": overall_score,
            "ats_score": ats_score,
            "formatting_score": formatting_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "keyword_analysis": {
                "missing_keywords": missing_keywords,
                "present_keywords": present_keywords,
                "keyword_density": 70  # Will be calculated later
            },
            "sections_analysis": sections,
            "specific_improvements": improvements,
            "ats_recommendations": ats_recommendations
        }
        
    except Exception as e:
        print(f"⚠️ Parsing error: {str(e)}")
        return get_enhanced_fallback_analysis("", "")

def extract_score(text: str, keyword: str) -> int:
    """Extract score from text"""
    try:
        pattern = rf"{keyword}:\s*(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except:
        pass
    return 75  # Default score

def extract_list(text: str, start_keyword: str, end_keyword: str) -> list:
    """Extract bullet point list between keywords"""
    try:
        start_pos = text.find(start_keyword)
        end_pos = text.find(end_keyword)
        
        if start_pos == -1:
            return []
            
        if end_pos == -1:
            end_pos = len(text)
            
        section = text[start_pos + len(start_keyword):end_pos]
        
        items = []
        for line in section.split('\n'):
            line = line.strip()
            if line.startswith('-') or line.startswith('•'):
                items.append(line[1:].strip())
        
        return items[:5]  # Limit to 5 items
        
    except:
        return []

def extract_keywords(text: str, keyword: str) -> list:
    """Extract comma-separated keywords"""
    try:
        start_pos = text.find(keyword)
        if start_pos == -1:
            return []
            
        # Get the line after the keyword
        start_pos += len(keyword)
        end_pos = text.find('\n', start_pos)
        if end_pos == -1:
            end_pos = start_pos + 200  # Max length
            
        line = text[start_pos:end_pos].strip()
        
        # Remove brackets and split by comma
        line = line.strip('[]{}()')
        keywords = [k.strip() for k in line.split(',') if k.strip()]
        
        return keywords[:8]  # Limit to 8 keywords
        
    except:
        return []

def extract_numbered_list(text: str, keyword: str) -> list:
    """Extract numbered list items"""
    try:
        start_pos = text.find(keyword)
        if start_pos == -1:
            return []
            
        # Find next section or end
        next_section = text.find('\n\n', start_pos + len(keyword))
        if next_section == -1:
            next_section = len(text)
            
        section = text[start_pos + len(keyword):next_section]
        
        items = []
        for line in section.split('\n'):
            line = line.strip()
            if re.match(r'^\d+\.', line):
                items.append(re.sub(r'^\d+\.\s*', '', line))
        
        return items[:5]  # Limit to 5 items
        
    except:
        return []

def parse_section_feedback(text: str) -> dict:
    """Parse section-by-section feedback"""
    sections = {}
    
    section_names = ['Contact', 'Summary', 'Experience', 'Education', 'Skills']
    
    for section in section_names:
        try:
            pattern = rf"{section}:\s*(\d+)/100\s*-\s*([^\n]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                score = int(match.group(1))
                feedback = match.group(2).strip()
            else:
                score = 75
                feedback = f"{section} section appears standard"
                
            sections[section.lower() + '_info' if section == 'Contact' else section.lower()] = {
                "score": score,
                "feedback": feedback
            }
        except:
            sections[section.lower() + '_info' if section == 'Contact' else section.lower()] = {
                "score": 75,
                "feedback": f"{section} section needs review"
            }
    
    return sections

async def generate_improved_resume(resume_text: str, target_role: Optional[str], analysis: dict) -> str:
    """Generate an improved version of the resume - FIXED VERSION"""
    
    role_context = f" for {target_role} positions" if target_role else ""
    
    # Simplified improvement prompt
    improvement_prompt = f"""
Improve this resume{role_context} based on the analysis. Keep all original information but enhance presentation.

Original Resume:
{resume_text[:2000]}

Key Issues to Fix:
{chr(10).join(analysis.get('specific_improvements', [])[:3])}

Create an improved version that:
1. Keeps all original experience and information
2. Uses stronger action verbs
3. Adds quantifiable achievements where possible
4. Improves formatting and structure
5. Makes it more ATS-friendly

Return only the improved resume text.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert resume writer. Improve resumes while keeping all original information."},
                {"role": "user", "content": improvement_prompt}
            ],
            temperature=0.4,
            max_tokens=1500
        )
        
        improved_resume = response.choices[0].message.content.strip()
        return improved_resume
        
    except Exception as e:
        print(f"❌ Resume improvement error: {str(e)}")
        return f"Resume analysis completed successfully. Improved version generation temporarily unavailable.\n\nOriginal resume content preserved:\n\n{resume_text[:1000]}..."

def get_enhanced_fallback_analysis(resume_text: str, target_role: Optional[str]) -> dict:
    """Enhanced fallback with basic text analysis"""
    
    # Do some basic text analysis
    word_count = len(resume_text.split())
    has_email = '@' in resume_text
    has_phone = any(char.isdigit() for char in resume_text)
    has_experience = any(word in resume_text.lower() for word in ['experience', 'worked', 'managed', 'led'])
    has_education = any(word in resume_text.lower() for word in ['university', 'college', 'degree', 'bachelor', 'master'])
    has_skills = any(word in resume_text.lower() for word in ['skills', 'proficient', 'experienced'])
    
    # Calculate basic scores
    overall_score = 60
    if has_email: overall_score += 5
    if has_phone: overall_score += 5  
    if has_experience: overall_score += 10
    if has_education: overall_score += 10
    if has_skills: overall_score += 5
    if word_count > 200: overall_score += 5
    
    return {
        "overall_score": min(overall_score, 85),
        "ats_score": max(overall_score - 10, 50),
        "formatting_score": overall_score - 5,
        "strengths": [
            f"Resume contains {word_count} words showing good detail" if word_count > 150 else "Resume structure detected",
            "Contact information present" if has_email else "Readable format confirmed",
            "Professional experience documented" if has_experience else "Content successfully processed"
        ],
        "weaknesses": [
            "AI analysis temporarily unavailable for detailed feedback",
            "Please try again for comprehensive analysis",
            "Basic structure analysis completed"
        ],
        "keyword_analysis": {
            "missing_keywords": ["leadership", "results-driven", "collaborative"],
            "present_keywords": ["experience", "skills", "professional"],
            "keyword_density": 65
        },
        "sections_analysis": {
            "contact_info": {"score": 85 if has_email else 60, "feedback": "Contact information detected" if has_email else "Contact info needs verification"},
            "summary": {"score": 65, "feedback": "Summary section analysis pending"},
            "experience": {"score": 80 if has_experience else 50, "feedback": "Experience section found" if has_experience else "Experience section needs review"},
            "education": {"score": 75 if has_education else 60, "feedback": "Education background present" if has_education else "Education section standard"},
            "skills": {"score": 75 if has_skills else 65, "feedback": "Skills section identified" if has_skills else "Skills section detected"}
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

# Health check
@router.get("/resume-analysis/health")
async def resume_analysis_health():
    return {"status": "healthy", "service": "resume-analysis"}
