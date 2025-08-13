# Helper functions for AI cover letter generation
import os
import re
import json
import aiohttp
from typing import Optional, Dict, Any, List

# AI-powered cover letter generation function
async def ai_generate_cover_letter(
    job_posting: str,
    applicant_name: str,
    current_role: Optional[str] = None,
    experience: Optional[str] = None,
    achievements: Optional[str] = None,
    company_name: Optional[str] = None,
    tone_preference: str = "professional"
) -> str:
    """Generate a personalized cover letter using AI"""
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("⚠️ OpenAI API key not found, using enhanced template generation")
        return generate_enhanced_template_cover_letter(
            job_posting, applicant_name, current_role, experience, achievements, company_name, tone_preference
        )
    
    try:
        # Extract key information from job posting
        role_title = extract_role_from_posting(job_posting)
        company_from_posting = extract_company_from_posting(job_posting) if not company_name else company_name
        
        # Build applicant context
        applicant_context = f"Applicant Name: {applicant_name}\n"
        if current_role:
            applicant_context += f"Current Role: {current_role}\n"
        if experience:
            applicant_context += f"Experience: {experience}\n"
        if achievements:
            applicant_context += f"Key Achievements: {achievements}\n"
        
        # Tone-specific instructions
        tone_instructions = {
            "professional": "Maintain a professional, confident tone throughout",
            "enthusiastic": "Show enthusiasm and passion while remaining professional",
            "formal": "Use formal language and structure, very professional tone"
        }
        
        generation_prompt = f"""
        You are an expert career coach specializing in cover letter writing. Create a compelling, personalized cover letter for this job application.
        
        Job Posting:
        {job_posting}
        
        {applicant_context}
        
        Requirements:
        1. Address the specific role and company mentioned in the job posting
        2. {tone_instructions.get(tone_preference, tone_instructions['professional'])}
        3. Highlight relevant experience and achievements that match the job requirements
        4. Show genuine interest in the company and role
        5. Include specific examples and quantifiable achievements when possible
        6. Use keywords from the job posting for ATS optimization
        7. Keep the letter concise but comprehensive (250-400 words)
        8. Include proper greeting, body paragraphs, and professional closing
        
        Structure:
        - Professional greeting (try to find hiring manager name from posting, otherwise use "Dear Hiring Manager")
        - Strong opening paragraph expressing interest
        - 1-2 body paragraphs highlighting relevant qualifications
        - Closing paragraph with call to action
        - Professional sign-off with the applicant's name
        
        Return ONLY the complete cover letter text, no additional commentary.
        """
        
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-4o-mini",  # Better for creative generation
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert career coach and professional writer who creates compelling, personalized cover letters. Always provide only the cover letter content without additional commentary."
                        },
                        {"role": "user", "content": generation_prompt}
                    ],
                    "temperature": 0.8,  # Higher creativity for generation
                    "max_tokens": 1200   # Allow for comprehensive cover letters
                }
                
                async with session.post("https://api.openai.com/v1/chat/completions", 
                                      headers=headers, json=data, timeout=30) as response:
                    
                    if response.status == 200:
                        result = await response.json()
                        generated_letter = result['choices'][0]['message']['content'].strip()
                        print(f"✅ AI generation completed (length: {len(generated_letter)} chars)")
                        return generated_letter
                    else:
                        print(f"⚠️ OpenAI API error: {response.status}, using enhanced template")
                        return generate_enhanced_template_cover_letter(
                            job_posting, applicant_name, current_role, experience, achievements, company_name, tone_preference
                        )
                        
        except Exception as e:
            print(f"⚠️ AI generation error: {e}, using enhanced template")
            return generate_enhanced_template_cover_letter(
                job_posting, applicant_name, current_role, experience, achievements, company_name, tone_preference
            )
            
    except Exception as e:
        print(f"❌ Cover letter generation error: {e}")
        return generate_enhanced_template_cover_letter(
            job_posting, applicant_name, current_role, experience, achievements, company_name, tone_preference
        )

def extract_role_from_posting(job_posting: str) -> Optional[str]:
    """Extract job role/title from posting text"""
    lines = job_posting.split('\n')[:5]  # Check first 5 lines
    
    # Common patterns for job titles
    role_patterns = [
        r'(?:position|role|job|title):\s*(.+)',
        r'hiring\s+(?:for\s+)?(?:a\s+)?([a-zA-Z\s]+)',
        r'seeking\s+(?:a\s+)?([a-zA-Z\s]+)',
        r'([A-Z][a-zA-Z\s]+(?:Manager|Developer|Analyst|Engineer|Specialist|Assistant|Coordinator))',
    ]
    
    for line in lines:
        for pattern in role_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    return None

def extract_company_from_posting(job_posting: str) -> Optional[str]:
    """Extract company name from posting text"""
    lines = job_posting.split('\n')[:10]  # Check first 10 lines
    
    # Common patterns for company names
    company_patterns = [
        r'(?:company|organization|firm):\s*(.+)',
        r'at\s+([A-Z][a-zA-Z\s&]+(?:Inc|Corp|LLC|Ltd|Company)?)',
        r'join\s+([A-Z][a-zA-Z\s&]+)',
    ]
    
    for line in lines:
        for pattern in company_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip()
    
    return None

def generate_enhanced_template_cover_letter(
    job_posting: str,
    applicant_name: str,
    current_role: Optional[str] = None,
    experience: Optional[str] = None,
    achievements: Optional[str] = None,
    company_name: Optional[str] = None,
    tone_preference: str = "professional"
) -> str:
    """Enhanced fallback template generation when AI is unavailable"""
    
    role_title = extract_role_from_posting(job_posting) or "position"
    company_from_posting = extract_company_from_posting(job_posting) if not company_name else company_name
    company_text = company_from_posting or "your organization"
    
    # Tone-specific language adjustments
    if tone_preference == "enthusiastic":
        opening_phrase = "I am thrilled to apply"
        interest_phrase = "genuinely excited about this opportunity"
        closing_phrase = "I would be delighted to discuss"
    elif tone_preference == "formal":
        opening_phrase = "I am writing to formally apply"
        interest_phrase = "deeply interested in this position"
        closing_phrase = "I would appreciate the opportunity to discuss"
    else:  # professional
        opening_phrase = "I am writing to express my strong interest"
        interest_phrase = "particularly drawn to this opportunity"
        closing_phrase = "I would welcome the opportunity to discuss"
    
    # Build experience section
    experience_section = ""
    if current_role and experience:
        experience_section = f"As a {current_role} with experience in {experience}, I bring valuable expertise to this role."
    elif current_role:
        experience_section = f"In my current role as {current_role}, I have developed strong skills relevant to this position."
    elif experience:
        experience_section = f"With my experience in {experience}, I am well-prepared for the challenges of this role."
    else:
        experience_section = "My professional background has prepared me well for the responsibilities of this position."
    
    # Build achievements section
    achievements_section = ""
    if achievements:
        achievements_section = f"\n\nKey highlights of my qualifications include:\n• {achievements}\n• Proven track record of delivering high-quality results\n• Strong problem-solving and analytical skills"
    else:
        achievements_section = "\n\nMy qualifications include:\n• Proven track record of delivering exceptional results\n• Strong problem-solving abilities and attention to detail\n• Excellent communication and collaboration skills"
    
    enhanced_template = f"""Dear Hiring Manager,

{opening_phrase} for the {role_title} role at {company_text}. {experience_section} I am {interest_phrase} because it aligns perfectly with my career goals and expertise.{achievements_section}

I am particularly impressed by {'your company\'s commitment to excellence' if not company_from_posting else f'{company_text}\'s reputation in the industry'} and would be honored to contribute to your continued success. My approach to work emphasizes quality, collaboration, and continuous improvement.

{closing_phrase} how my skills and enthusiasm can benefit your team. Thank you for considering my application.

Sincerely,
{applicant_name}"""
    
    return enhanced_template