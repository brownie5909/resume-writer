from fastapi import APIRouter, UploadFile, File, Form, Request
from fastapi.responses import JSONResponse
import os
import openai
from typing import Optional
import re
from .resume_analysis import extract_text_from_file

router = APIRouter()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@router.post("/analyze-cover-letter")
async def analyze_cover_letter(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    document_type: Optional[str] = Form("cover_letter"),
    user_id: Optional[str] = Form(None)
):
    """
    Analyze an uploaded cover letter and provide detailed feedback
    """
    
    try:
        print(f"📝 Starting cover letter analysis for file: {file.filename}")
        print(f"🎯 Target role: {target_role}")
        
        # Extract text from uploaded file (reuse existing function)
        cover_letter_text = await extract_text_from_file(file)
        print(f"📄 Extracted {len(cover_letter_text)} characters")
        
        if not cover_letter_text or len(cover_letter_text.strip()) < 50:
            return JSONResponse(
                status_code=400,
                content={"error": f"Could not extract sufficient text from the cover letter. Extracted: {len(cover_letter_text)} characters."}
            )
        
        # Analyze the cover letter with AI
        print("🤖 Starting AI analysis...")
        analysis_result = await analyze_cover_letter_with_ai(cover_letter_text, target_role)
        print("✅ AI analysis completed")
        
        # Generate improved version
        print("🚀 Generating improved cover letter...")
        improved_cover_letter = await generate_improved_cover_letter(cover_letter_text, target_role, analysis_result)
        print("✅ Improved cover letter generated")
        
        return JSONResponse({
            "success": True,
            "analysis": analysis_result,
            "improved_cover_letter": improved_cover_letter,
            "original_length": len(cover_letter_text),
            "target_role": target_role
        })
        
    except Exception as e:
        print(f"❌ Cover letter analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Analysis failed: {str(e)}"}
        )

@router.post("/generate-cover-letter")
async def generate_cover_letter(request: Request):
    """
    Generate a new cover letter based on job posting and applicant information
    """
    
    try:
        body = await request.json()
        
        job_posting = body.get("job_posting", "").strip()
        applicant_name = body.get("applicant_name", "").strip()
        current_role = body.get("current_role", "").strip()
        experience = body.get("experience", "").strip()
        achievements = body.get("achievements", "").strip()
        
        if not job_posting or not applicant_name:
            return JSONResponse(
                status_code=400,
                content={"error": "Job posting and applicant name are required."}
            )
        
        print(f"✨ Generating cover letter for {applicant_name}")
        print(f"🎯 Job posting length: {len(job_posting)} characters")
        
        # Generate cover letter with AI
        cover_letter = await generate_cover_letter_with_ai(
            job_posting, applicant_name, current_role, experience, achievements
        )
        
        return JSONResponse({
            "success": True,
            "cover_letter": cover_letter,
            "applicant_name": applicant_name,
            "generated_for": job_posting[:100] + "..." if len(job_posting) > 100 else job_posting
        })
        
    except Exception as e:
        print(f"❌ Cover letter generation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Generation failed: {str(e)}"}
        )

async def analyze_cover_letter_with_ai(cover_letter_text: str, target_role: Optional[str] = None) -> dict:
    """Use AI to analyze the cover letter and provide detailed feedback"""
    
    role_context = f" for a {target_role} position" if target_role else ""
    
    analysis_prompt = f"""
Analyze this cover letter{role_context} and provide specific, actionable feedback.

Cover Letter Text:
{cover_letter_text[:2500]}

Provide analysis in this exact format:

OVERALL_SCORE: [number 0-100]
JOB_ALIGNMENT_SCORE: [number 0-100]
ATS_SCORE: [number 0-100]

STRENGTHS:
- [strength 1]
- [strength 2] 
- [strength 3]

WEAKNESSES:
- [weakness 1]
- [weakness 2]
- [weakness 3]

SPECIFIC_IMPROVEMENTS:
1. [improvement 1]
2. [improvement 2] 
3. [improvement 3]

JOB_SPECIFIC_TIPS:
1. [job-specific tip 1]
2. [job-specific tip 2]
3. [job-specific tip 3]

Focus on:
1. How well the letter demonstrates fit for the role
2. Storytelling and compelling narrative  
3. Professional tone and structure
4. Specific examples and achievements
5. Call to action and closing strength
"""

    try:
        print("📤 Sending cover letter to OpenAI for analysis...")
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert career coach specializing in cover letter optimization. Provide specific, actionable feedback."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0.3,
            max_tokens=1200
        )
        
        ai_response = response.choices[0].message.content
        print("📥 Received cover letter analysis from AI")
        
        # Parse the structured response
        analysis_data = parse_cover_letter_analysis(ai_response)
        
        return analysis_data
        
    except Exception as e:
        print(f"❌ AI analysis error: {str(e)}")
        return get_fallback_cover_letter_analysis(cover_letter_text, target_role)

def parse_cover_letter_analysis(ai_response: str) -> dict:
    """Parse the structured AI response for cover letters"""
    
    try:
        # Extract scores
        overall_score = extract_score(ai_response, "OVERALL_SCORE")
        job_alignment_score = extract_score(ai_response, "JOB_ALIGNMENT_SCORE")
        ats_score = extract_score(ai_response, "ATS_SCORE")
        
        # Extract lists
        strengths = extract_list(ai_response, "STRENGTHS:", "WEAKNESSES:")
        weaknesses = extract_list(ai_response, "WEAKNESSES:", "SPECIFIC_IMPROVEMENTS:")
        
        # Extract improvements and tips
        improvements = extract_numbered_list(ai_response, "SPECIFIC_IMPROVEMENTS:")
        job_tips = extract_numbered_list(ai_response, "JOB_SPECIFIC_TIPS:")
        
        return {
            "overall_score": overall_score,
            "job_alignment_score": job_alignment_score,
            "ats_score": ats_score,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "specific_improvements": improvements,
            "job_specific_tips": job_tips
        }
        
    except Exception as e:
        print(f"⚠️ Cover letter parsing error: {str(e)}")
        return get_fallback_cover_letter_analysis("", "")

def extract_score(text: str, keyword: str) -> int:
    """Extract score from text"""
    try:
        pattern = rf"{keyword}:\s*(\d+)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return int(match.group(1))
    except:
        pass
    return 75

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
        
        return items[:5]
        
    except:
        return []

def extract_numbered_list(text: str, keyword: str) -> list:
    """Extract numbered list items"""
    try:
        start_pos = text.find(keyword)
        if start_pos == -1:
            return []
            
        next_section = text.find('\n\n', start_pos + len(keyword))
        if next_section == -1:
            next_section = len(text)
            
        section = text[start_pos + len(keyword):next_section]
        
        items = []
        for line in section.split('\n'):
            line = line.strip()
            if re.match(r'^\d+\.', line):
                items.append(re.sub(r'^\d+\.\s*', '', line))
        
        return items[:5]
        
    except:
        return []

async def generate_improved_cover_letter(cover_letter_text: str, target_role: Optional[str], analysis: dict) -> str:
    """Generate an improved version of the cover letter based on analysis"""
    
    role_context = f" for {target_role} positions" if target_role else ""
    
    improvement_prompt = f"""
Improve this cover letter{role_context} based on the analysis feedback.

Original Cover Letter:
{cover_letter_text[:2000]}

Key Issues to Fix:
{chr(10).join(analysis.get('specific_improvements', [])[:3])}

Create an improved version that:
1. Maintains the original tone and personal voice
2. Fixes identified weaknesses
3. Strengthens the narrative and storytelling
4. Adds more specific examples and achievements
5. Improves the opening hook and closing call-to-action
6. Optimizes for ATS compatibility

Return only the improved cover letter text in proper business letter format.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert cover letter writer. Improve cover letters while maintaining the applicant's authentic voice and personal style."},
                {"role": "user", "content": improvement_prompt}
            ],
            temperature=0.4,
            max_tokens=1200
        )
        
        improved_cover_letter = response.choices[0].message.content.strip()
        return improved_cover_letter
        
    except Exception as e:
        print(f"❌ Cover letter improvement error: {str(e)}")
        return f"Cover letter analysis completed successfully. Improved version generation temporarily unavailable.\n\nOriginal cover letter content preserved:\n\n{cover_letter_text[:800]}..."

async def generate_cover_letter_with_ai(job_posting: str, applicant_name: str, current_role: str, experience: str, achievements: str) -> str:
    """Generate a new cover letter based on job posting and applicant information"""
    
    generation_prompt = f"""
Write a compelling, professional cover letter based on this information:

Job Posting/Role:
{job_posting[:1500]}

Applicant Information:
- Name: {applicant_name}
- Current Role: {current_role}
- Experience: {experience}
- Key Achievements: {achievements}

Create a cover letter that:
1. Opens with a strong hook that shows enthusiasm and relevance
2. Demonstrates clear understanding of the role and company
3. Highlights relevant experience and achievements with specific examples
4. Shows personality while maintaining professionalism
5. Includes a compelling call-to-action in the closing
6. Is properly formatted as a business letter
7. Is optimized for ATS systems with relevant keywords

The letter should be 3-4 paragraphs, approximately 250-350 words total.
Use a professional but engaging tone that stands out from generic templates.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an expert cover letter writer who creates compelling, personalized cover letters that help candidates stand out and get interviews."},
                {"role": "user", "content": generation_prompt}
            ],
            temperature=0.6,
            max_tokens=1000
        )
        
        cover_letter = response.choices[0].message.content.strip()
        return cover_letter
        
    except Exception as e:
        print(f"❌ Cover letter generation error: {str(e)}")
        return f"Dear Hiring Manager,\n\nI am writing to express my strong interest in the {current_role} position. With my background in {experience}, I am confident I would be a valuable addition to your team.\n\n[Cover letter generation temporarily unavailable - please try again later]\n\nSincerely,\n{applicant_name}"

def get_fallback_cover_letter_analysis(cover_letter_text: str, target_role: Optional[str]) -> dict:
    """Fallback analysis when AI is unavailable"""
    
    word_count = len(cover_letter_text.split())
    has_greeting = any(greeting in cover_letter_text.lower() for greeting in ['dear', 'hello', 'greetings'])
    has_closing = any(closing in cover_letter_text.lower() for closing in ['sincerely', 'regards', 'best'])
    has_company_ref = '[company' not in cover_letter_text.lower()
    
    overall_score = 65
    if has_greeting: overall_score += 10
    if has_closing: overall_score += 10
    if has_company_ref: overall_score += 10
    if word_count >= 200 and word_count <= 400: overall_score += 5
    
    return {
        "overall_score": min(overall_score, 85),
        "job_alignment_score": max(overall_score - 15, 50),
        "ats_score": max(overall_score - 10, 60),
        "strengths": [
            f"Cover letter length is {word_count} words",
            "Professional greeting found" if has_greeting else "Structure appears professional",
            "Proper closing included" if has_closing else "Content successfully processed"
        ],
        "weaknesses": [
            "Consider adding more specific examples and achievements",
            "Ensure company name and role are mentioned specifically",
            "Strengthen the opening hook to grab attention"
        ],
        "specific_improvements": [
            "Add quantified achievements and specific examples",
            "Research the company and mention specific details",
            "Create a stronger opening that shows enthusiasm",
            f"Optimize for {target_role} keywords" if target_role else "Include relevant industry keywords"
        ],
        "job_specific_tips": [
            "Tailor the content to match job requirements",
            "Use the same keywords as the job posting",
            "Show understanding of company culture and values"
        ]
    }
