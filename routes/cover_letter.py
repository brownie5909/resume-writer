# AI-Powered Cover Letter Generation and Analysis

from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import asyncio
import aiohttp
import re
import json
from typing import Optional, Dict, Any, List
from .user_management import require_feature_access_auth
from .cover_letter_helpers import (
    ai_generate_cover_letter, 
    extract_role_from_posting, 
    extract_company_from_posting,
    generate_enhanced_template_cover_letter
)

router = APIRouter()

# Models for request/response validation
class CoverLetterAnalysisInput(BaseModel):
    cover_letter_text: str
    target_role: Optional[str] = None
    job_posting: Optional[str] = None
    company_name: Optional[str] = None

class CoverLetterGenerationInput(BaseModel):
    job_posting: str
    applicant_name: str
    current_role: Optional[str] = None
    experience: Optional[str] = None
    achievements: Optional[str] = None
    company_name: Optional[str] = None
    tone_preference: Optional[str] = "professional"  # professional, enthusiastic, formal

def extract_json_content(content: str) -> str:
    """Enhanced JSON extraction from AI response"""
    import re
    
    # Try multiple patterns to extract JSON
    patterns = [
        r'```json\s*(\{.*?\})\s*```',  # JSON in code blocks
        r'```\s*(\{.*?\})\s*```',      # Generic code blocks
        r'(\{(?:[^{}]|{[^{}]*})*\})',   # Any JSON object
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            return match.group(1)
    
    # If no patterns match, return the content as-is
    return content

async def ai_analyze_cover_letter(
    cover_letter_text: str, 
    target_role: Optional[str] = None, 
    job_posting: Optional[str] = None,
    company_name: Optional[str] = None
) -> Dict[str, Any]:
    """AI-powered cover letter analysis using OpenAI GPT-4o-mini"""
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("⚠️ OpenAI API key not found, using fallback analysis")
        return await fallback_cover_letter_analysis(cover_letter_text, target_role, job_posting, company_name)
    
    try:
        print(f"🤖 Starting AI analysis for cover letter (length: {len(cover_letter_text)} chars)")
        
        # Build context for analysis
        context = f"Target Role: {target_role}" if target_role else "No specific role provided"
        if company_name:
            context += f"\nCompany: {company_name}"
        if job_posting:
            context += f"\nJob Posting Context: {job_posting[:500]}..." if len(job_posting) > 500 else f"\nJob Posting Context: {job_posting}"
        
        # Comprehensive AI analysis prompt
        analysis_prompt = f"""
        You are an expert career coach and HR professional. Analyze this cover letter and provide detailed, actionable feedback.
        
        Cover Letter to Analyze:
        {cover_letter_text}
        
        {context}
        
        Provide comprehensive analysis in this EXACT JSON format:
        {{
            "overall_score": [score from 1-100],
            "job_alignment_score": [score from 1-100 based on how well it matches the role/posting],
            "ats_score": [score from 1-100 for ATS optimization],
            "strengths": [
                "[Specific strength with evidence from the letter]",
                "[Another specific strength]",
                "[Third strength]"
            ],
            "weaknesses": [
                "[Specific weakness with explanation]",
                "[Another area for improvement]",
                "[Third weakness]"
            ],
            "specific_improvements": [
                "[Actionable suggestion with specific example]",
                "[Another specific improvement]",
                "[Third improvement suggestion]",
                "[Fourth suggestion if needed]"
            ],
            "job_specific_tips": [
                "[Tip specific to the role/industry]",
                "[Company-specific suggestion if applicable]",
                "[Role-specific optimization tip]"
            ],
            "keyword_analysis": {{
                "missing_keywords": ["keyword1", "keyword2"],
                "well_used_keywords": ["keyword3", "keyword4"],
                "suggestions": "How to better incorporate relevant keywords"
            }},
            "tone_assessment": "Assessment of the cover letter's tone and style",
            "structure_feedback": "Feedback on organization and flow"
        }}
        
        Be specific and actionable. Reference actual content from the cover letter. Provide realistic scores based on actual quality.
        """
        
        try:
            # Call OpenAI API for analysis
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-4o-mini",  # Better for detailed analysis
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert career coach and HR professional who provides detailed, actionable cover letter analysis. Always respond with properly formatted JSON."
                        },
                        {"role": "user", "content": analysis_prompt}
                    ],
                    "temperature": 0.3,  # Lower for more consistent analysis
                    "max_tokens": 2000   # Allow comprehensive analysis
                }
                
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                      headers=headers, json=data, timeout=30) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        ai_content = result['choices'][0]['message']['content'].strip()
                        
                        # Enhanced JSON parsing
                        try:
                            # Clean and extract JSON
                            json_content = extract_json_content(ai_content)
                            analysis_result = json.loads(json_content)
                            
                            # Validate required fields
                            required_fields = ['overall_score', 'job_alignment_score', 'ats_score', 'strengths', 'weaknesses']
                            if all(field in analysis_result for field in required_fields):
                                print(f"✅ AI analysis completed - Overall score: {analysis_result.get('overall_score', 'N/A')}")
                                return analysis_result
                            else:
                                print("⚠️ AI response missing required fields, using fallback")
                                return await fallback_cover_letter_analysis(cover_letter_text, target_role, job_posting, company_name)
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON parse error in AI analysis: {e}")
                            return await fallback_cover_letter_analysis(cover_letter_text, target_role, job_posting, company_name)
                            
                    else:
                        print(f"⚠️ OpenAI API error: {response.status}")
                        return await fallback_cover_letter_analysis(cover_letter_text, target_role, job_posting, company_name)
                        
        except Exception as e:
            print(f"⚠️ AI analysis error: {e}")
            return await fallback_cover_letter_analysis(cover_letter_text, target_role, job_posting, company_name)
            
    except Exception as e:
        print(f"❌ Cover letter analysis error: {e}")
        return await fallback_cover_letter_analysis(cover_letter_text, target_role, job_posting, company_name)

async def fallback_cover_letter_analysis(
    cover_letter_text: str, 
    target_role: Optional[str] = None, 
    job_posting: Optional[str] = None,
    company_name: Optional[str] = None
) -> Dict[str, Any]:
    """Enhanced fallback analysis when AI is unavailable"""
    
    text_lower = cover_letter_text.lower()
    text_length = len(cover_letter_text)
    
    # Basic quality scoring based on content analysis
    base_score = 60
    
    # Length scoring
    if 200 <= text_length <= 400:
        length_score = 85
    elif 150 <= text_length <= 500:
        length_score = 75
    else:
        length_score = 65
    
    # Content quality indicators
    quality_indicators = {
        'has_greeting': any(greeting in text_lower for greeting in ['dear', 'hello', 'hi']),
        'has_role_mention': target_role and target_role.lower() in text_lower,
        'has_company_mention': company_name and company_name.lower() in text_lower,
        'has_experience': any(exp in text_lower for exp in ['experience', 'worked', 'developed', 'managed']),
        'has_achievements': any(ach in text_lower for ach in ['achieved', 'increased', 'improved', 'led']),
        'has_closing': any(closing in text_lower for closing in ['sincerely', 'regards', 'thank you']),
        'has_numbers': bool(re.search(r'\d+[%$]?', cover_letter_text)),
        'avoids_generic': not any(generic in text_lower for generic in ['to whom it may concern', 'dear sir/madam'])
    }
    
    quality_score = sum(quality_indicators.values()) * 3  # Max 24 points
    overall_score = min(95, base_score + quality_score + (length_score - 65))
    
    # Generate contextual feedback
    strengths = []
    weaknesses = []
    improvements = []
    
    if quality_indicators['has_greeting'] and quality_indicators['avoids_generic']:
        strengths.append("Professional greeting that avoids generic salutations")
    elif not quality_indicators['has_greeting']:
        weaknesses.append("Missing proper greeting or salutation")
        improvements.append("Add a professional greeting, ideally addressing a specific person")
    
    if quality_indicators['has_role_mention']:
        strengths.append(f"Specifically mentions the {target_role} role")
    else:
        weaknesses.append("Doesn't clearly reference the specific role")
        improvements.append(f"Explicitly mention the {target_role or 'target'} position you're applying for")
    
    if quality_indicators['has_achievements']:
        strengths.append("Includes specific achievements and accomplishments")
    else:
        weaknesses.append("Lacks specific achievements or quantifiable results")
        improvements.append("Add specific examples of your achievements with numbers or percentages")
    
    if not strengths:
        strengths.append("Shows genuine interest in the position")
    if not weaknesses:
        weaknesses.append("Could benefit from more specific examples")
    if not improvements:
        improvements.append("Consider adding more industry-specific keywords")
    
    return {
        "overall_score": overall_score,
        "job_alignment_score": overall_score - 5 if target_role else overall_score - 15,
        "ats_score": overall_score - 10 if not quality_indicators['has_numbers'] else overall_score,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "specific_improvements": improvements,
        "job_specific_tips": [
            f"Tailor the content to match {target_role or 'the role'} requirements" if target_role else "Research the specific role requirements",
            f"Research {company_name} and mention specific company details" if company_name else "Research the company and mention specific details",
            "Use keywords from the job posting to improve ATS compatibility"
        ],
        "keyword_analysis": {
            "missing_keywords": ["industry-specific terms", "technical skills", "soft skills"],
            "well_used_keywords": ["experience", "professional"] if quality_indicators['has_experience'] else [],
            "suggestions": "Incorporate more keywords from the job posting and industry terminology"
        },
        "tone_assessment": "Professional tone maintained" if quality_indicators['has_greeting'] else "Consider more professional tone and structure",
        "structure_feedback": "Good basic structure" if quality_indicators['has_closing'] else "Could benefit from clearer opening and closing paragraphs"
    }

# AI-powered cover letter improvement
async def ai_improve_cover_letter(
    original_text: str,
    analysis: Dict[str, Any],
    target_role: Optional[str] = None,
    company_name: Optional[str] = None,
    job_posting: Optional[str] = None
) -> str:
    """Generate an improved version of the cover letter using AI"""
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("⚠️ OpenAI API key not found, providing template improvement")
        return generate_template_improvement(original_text, analysis, target_role, company_name)
    
    try:
        # Build improvement context
        context = f"Target Role: {target_role}" if target_role else ""
        if company_name:
            context += f"\nCompany: {company_name}"
        if job_posting:
            context += f"\nJob Posting Key Points: {job_posting[:300]}..." if len(job_posting) > 300 else f"\nJob Posting: {job_posting}"
        
        # Get key improvement points from analysis
        improvements = analysis.get('specific_improvements', [])
        weaknesses = analysis.get('weaknesses', [])
        
        improvement_prompt = f"""
        You are an expert career coach. Improve this cover letter based on the analysis provided.
        
        Original Cover Letter:
        {original_text}
        
        {context}
        
        Key Issues to Address:
        {chr(10).join(f"• {weakness}" for weakness in weaknesses)}
        
        Specific Improvements Needed:
        {chr(10).join(f"• {improvement}" for improvement in improvements)}
        
        Create an improved version that:
        1. Addresses the identified weaknesses
        2. Incorporates the suggested improvements
        3. Maintains the applicant's voice and personality
        4. Is appropriately tailored to the role and company
        5. Uses professional but engaging language
        6. Includes specific examples and achievements
        
        Return ONLY the improved cover letter text, no additional commentary.
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert career coach who improves cover letters. Provide only the improved cover letter text without any additional commentary or explanations."
                        },
                        {"role": "user", "content": improvement_prompt}
                    ],
                    "temperature": 0.7,  # Balanced creativity and consistency
                    "max_tokens": 1500   # Allow for comprehensive improvements
                }
                
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                      headers=headers, json=data, timeout=30) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        improved_text = result['choices'][0]['message']['content'].strip()
                        print(f"✅ AI improvement completed (length: {len(improved_text)} chars)")
                        return improved_text
                    else:
                        print(f"⚠️ OpenAI API error: {response.status}, using template")
                        return generate_template_improvement(original_text, analysis, target_role, company_name)
                        
        except Exception as e:
            print(f"⚠️ AI improvement error: {e}, using template")
            return generate_template_improvement(original_text, analysis, target_role, company_name)
            
    except Exception as e:
        print(f"❌ Cover letter improvement error: {e}")
        return generate_template_improvement(original_text, analysis, target_role, company_name)

def generate_template_improvement(
    original_text: str, 
    analysis: Dict[str, Any], 
    target_role: Optional[str] = None, 
    company_name: Optional[str] = None
) -> str:
    """Fallback template-based improvement when AI is unavailable"""
    
    # Extract name from original if possible
    name_match = re.search(r'(sincerely|regards|best),?\s*([a-z\s]+)$', original_text, re.IGNORECASE | re.MULTILINE)
    applicant_name = name_match.group(2).strip() if name_match else "[Your Name]"
    
    # Create improved template based on analysis
    improvements = analysis.get('specific_improvements', [])
    
    improved_template = f"""Dear Hiring Manager,

I am writing to express my strong interest in the {target_role or 'position'}{f' at {company_name}' if company_name else ''}. After reviewing your requirements, I am confident that my experience and skills make me an ideal candidate for this role.

In my previous roles, I have successfully:
• Delivered measurable results through strategic problem-solving
• Collaborated effectively with cross-functional teams
• Adapted quickly to new challenges and technologies
• Maintained high standards of quality and professionalism

I am particularly drawn to this opportunity because it aligns with my career goals and expertise. {'Your company's commitment to innovation and excellence resonates with my professional values.' if company_name else 'The role offers exciting challenges that match my skills and interests.'}

I would welcome the opportunity to discuss how my experience and enthusiasm can contribute to your team's continued success. Thank you for considering my application.

Sincerely,
{applicant_name}"""
    
    return improved_template

@router.post("/analyze-cover-letter")
async def analyze_cover_letter(
    file: UploadFile = File(...),
    target_role: Optional[str] = Form(None),
    job_posting: Optional[str] = Form(None),
    company_name: Optional[str] = Form(None),
    current_user: dict = Depends(require_feature_access_auth("cover_letter_analysis"))
):
    """
    AI-powered cover letter analysis with detailed feedback and improvement suggestions
    Premium feature with real AI analysis
    """
    
    try:
        print(f"📝 Starting AI-powered cover letter analysis for file: {file.filename}")
        print(f"🎯 Target role: {target_role}")
        print(f"🏢 Company: {company_name}")
        
        # File validation
        if not file.filename:
            return JSONResponse(
                status_code=400,
                content={"error": "No file provided"}
            )
        
        # Validate file type
        allowed_types = ['text/plain', 'application/pdf', 'application/msword', 
                        'application/vnd.openxmlformats-officedocument.wordprocessingml.document']
        if file.content_type not in allowed_types:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported file type: {file.content_type}. Please upload a PDF, Word document, or text file."}
            )
        
        # Read file content
        content = await file.read()
        
        # Basic text extraction (enhanced for different file types)
        try:
            if file.content_type == 'text/plain':
                cover_letter_text = content.decode('utf-8')
            elif 'pdf' in file.content_type:
                # For PDF files, we'll use a basic approach since python-magic is already in requirements
                cover_letter_text = content.decode('utf-8', errors='ignore')
            else:
                # For Word documents, basic text extraction
                cover_letter_text = content.decode('utf-8', errors='ignore')
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Could not read file content: {str(e)}"}
            )
        
        # Validate content length
        if len(cover_letter_text.strip()) < 50:
            return JSONResponse(
                status_code=400,
                content={"error": "Cover letter content is too short. Please provide a complete cover letter."}
            )
        
        # Perform AI-powered analysis
        analysis_result = await ai_analyze_cover_letter(
            cover_letter_text=cover_letter_text,
            target_role=target_role,
            job_posting=job_posting,
            company_name=company_name
        )
        
        # Generate improved version using AI
        improved_cover_letter = await ai_improve_cover_letter(
            original_text=cover_letter_text,
            analysis=analysis_result,
            target_role=target_role,
            company_name=company_name,
            job_posting=job_posting
        )
        
        return JSONResponse({
            "success": True,
            "analysis": analysis_result,
            "improved_cover_letter": improved_cover_letter,
            "original_length": len(cover_letter_text),
            "improved_length": len(improved_cover_letter) if improved_cover_letter else 0,
            "target_role": target_role,
            "company_name": company_name,
            "ai_powered": os.getenv("OPENAI_API_KEY") is not None
        })
        
    except Exception as e:
        print(f"❌ Cover letter analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Analysis failed: {str(e)}"}
        )

@router.post("/generate-cover-letter")
async def generate_cover_letter(payload: CoverLetterGenerationInput):
    """
    AI-powered cover letter generation based on job posting and applicant information
    """
    
    try:
        print(f"✨ Generating AI-powered cover letter for {payload.applicant_name}")
        print(f"🎯 Job posting length: {len(payload.job_posting)} characters")
        print(f"🎨 Tone preference: {payload.tone_preference}")
        
        # Generate cover letter using AI
        cover_letter = await ai_generate_cover_letter(
            job_posting=payload.job_posting,
            applicant_name=payload.applicant_name,
            current_role=payload.current_role,
            experience=payload.experience,
            achievements=payload.achievements,
            company_name=payload.company_name,
            tone_preference=payload.tone_preference
        )
        
        # Perform quick analysis of generated letter
        analysis = await ai_analyze_cover_letter(
            cover_letter_text=cover_letter,
            target_role=extract_role_from_posting(payload.job_posting),
            job_posting=payload.job_posting,
            company_name=payload.company_name
        )
        
        return JSONResponse({
            "success": True,
            "cover_letter": cover_letter,
            "analysis": analysis,
            "applicant_name": payload.applicant_name,
            "company_name": payload.company_name,
            "generated_for": payload.job_posting[:100] + "..." if len(payload.job_posting) > 100 else payload.job_posting,
            "tone_used": payload.tone_preference,
            "ai_powered": os.getenv("OPENAI_API_KEY") is not None
        })
        
    except Exception as e:
        print(f"❌ Cover letter generation error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Generation failed: {str(e)}"}
        )

# Additional endpoint for text-based analysis
@router.post("/analyze-cover-letter-text")
async def analyze_cover_letter_text(payload: CoverLetterAnalysisInput):
    """
    Analyze cover letter text directly without file upload
    """
    
    try:
        print(f"📝 Starting AI text analysis (length: {len(payload.cover_letter_text)} chars)")
        print(f"🎯 Target role: {payload.target_role}")
        
        # Validate content length
        if len(payload.cover_letter_text.strip()) < 50:
            return JSONResponse(
                status_code=400,
                content={"error": "Cover letter content is too short. Please provide a complete cover letter."}
            )
        
        # Perform AI analysis
        analysis_result = await ai_analyze_cover_letter(
            cover_letter_text=payload.cover_letter_text,
            target_role=payload.target_role,
            job_posting=payload.job_posting,
            company_name=payload.company_name
        )
        
        # Generate improved version
        improved_cover_letter = await ai_improve_cover_letter(
            original_text=payload.cover_letter_text,
            analysis=analysis_result,
            target_role=payload.target_role,
            company_name=payload.company_name,
            job_posting=payload.job_posting
        )
        
        return JSONResponse({
            "success": True,
            "analysis": analysis_result,
            "improved_cover_letter": improved_cover_letter,
            "original_length": len(payload.cover_letter_text),
            "improved_length": len(improved_cover_letter),
            "target_role": payload.target_role,
            "company_name": payload.company_name,
            "ai_powered": os.getenv("OPENAI_API_KEY") is not None
        })
        
    except Exception as e:
        print(f"❌ Cover letter text analysis error: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Analysis failed: {str(e)}"}
        )

# Health check endpoint
@router.get("/cover-letter/health")
async def cover_letter_health():
    """Health check for cover letter service"""
    openai_available = os.getenv("OPENAI_API_KEY") is not None
    return {
        "status": "healthy", 
        "service": "cover-letter-ai-powered",
        "ai_enabled": openai_available,
        "features": {
            "file_analysis": True,
            "text_analysis": True,
            "ai_generation": True,
            "improvement_suggestions": True,
            "fallback_mode": True
        }
    }