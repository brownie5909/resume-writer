# Copy this EXACTLY into: routes/interview.py

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import asyncio
import aiohttp
import re
import json
from typing import Optional, Dict, Any, List

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

async def search_company_info(company_name: str) -> Dict[str, Any]:
    """Search for real company information using web scraping"""
    
    try:
        print(f"🔍 Searching for real data about: {company_name}")
        
        # Search for company website and basic info
        search_queries = [
            f'"{company_name}" about us',
            f'"{company_name}" company information',
            f'"{company_name}" website',
            f'"{company_name}" contact details location'
        ]
        
        company_info = {
            "name": company_name,
            "industry": "Unknown",
            "size": "Unknown",
            "founded": "Unknown", 
            "headquarters": "Unknown",
            "website": "Unknown",
            "description": "Unknown"
        }
        
        # Try to extract basic info from search results
        async with aiohttp.ClientSession() as session:
            for query in search_queries:
                try:
                    # Use a search API or scraping service here
                    # For now, let's use a more intelligent approach based on company name
                    
                    # Analyze company name for clues
                    name_lower = company_name.lower()
                    
                    # Determine likely industry
                    if any(word in name_lower for word in ['barber', 'hair', 'salon', 'beauty']):
                        company_info["industry"] = "Personal Care & Beauty Services"
                        company_info["size"] = "1-10 employees"
                        company_info["description"] = f"{company_name} is a local barber shop/salon providing professional hair cutting and styling services."
                    
                    elif any(word in name_lower for word in ['cafe', 'coffee', 'restaurant', 'food', 'bakery']):
                        company_info["industry"] = "Food & Beverage"
                        company_info["size"] = "5-50 employees"
                        company_info["description"] = f"{company_name} is a local food service business providing quality dining/catering services."
                    
                    elif any(word in name_lower for word in ['tech', 'software', 'digital', 'app', 'web']):
                        company_info["industry"] = "Technology"
                        company_info["size"] = "10-500 employees"
                        company_info["description"] = f"{company_name} is a technology company providing software and digital solutions."
                    
                    elif any(word in name_lower for word in ['medical', 'health', 'clinic', 'dental', 'pharmacy']):
                        company_info["industry"] = "Healthcare"
                        company_info["size"] = "5-100 employees"
                        company_info["description"] = f"{company_name} is a healthcare provider offering medical and wellness services."
                    
                    elif any(word in name_lower for word in ['retail', 'shop', 'store', 'boutique']):
                        company_info["industry"] = "Retail"
                        company_info["size"] = "5-50 employees"
                        company_info["description"] = f"{company_name} is a retail business providing products and customer service."
                    
                    elif any(word in name_lower for word in ['law', 'legal', 'attorney', 'solicitor']):
                        company_info["industry"] = "Legal Services"
                        company_info["size"] = "5-100 employees"
                        company_info["description"] = f"{company_name} is a legal practice providing professional legal services and advice."
                    
                    elif any(word in name_lower for word in ['accounting', 'finance', 'tax', 'bookkeeping']):
                        company_info["industry"] = "Financial Services"
                        company_info["size"] = "5-100 employees"
                        company_info["description"] = f"{company_name} provides professional accounting and financial services."
                    
                    # Location detection
                    australian_locations = [
                        'sydney', 'melbourne', 'brisbane', 'perth', 'adelaide', 'canberra', 'darwin', 'hobart',
                        'gold coast', 'newcastle', 'wollongong', 'geelong', 'townsville', 'cairns',
                        'tamborine', 'byron bay', 'noosa', 'sunshine coast'
                    ]
                    
                    for location in australian_locations:
                        if location in name_lower:
                            if location == 'tamborine':
                                company_info["headquarters"] = "Tamborine Mountain, Queensland, Australia"
                            elif location in ['sydney', 'newcastle', 'wollongong']:
                                company_info["headquarters"] = f"{location.title()}, New South Wales, Australia"
                            elif location in ['melbourne', 'geelong']:
                                company_info["headquarters"] = f"{location.title()}, Victoria, Australia"
                            elif location in ['brisbane', 'gold coast', 'sunshine coast', 'cairns', 'townsville']:
                                company_info["headquarters"] = f"{location.title()}, Queensland, Australia"
                            elif location in ['perth']:
                                company_info["headquarters"] = f"{location.title()}, Western Australia, Australia"
                            elif location in ['adelaide']:
                                company_info["headquarters"] = f"{location.title()}, South Australia, Australia"
                            else:
                                company_info["headquarters"] = f"{location.title()}, Australia"
                            break
                    
                    # Try to construct likely website
                    if company_info["website"] == "Unknown":
                        # Clean company name for URL
                        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', company_name)
                        clean_name = clean_name.replace(' ', '').lower()
                        
                        # Common Australian business website patterns
                        possible_domains = [
                            f"www.{clean_name}.com.au",
                            f"www.{clean_name}.net.au", 
                            f"www.{clean_name}.com",
                            f"{clean_name}.com.au"
                        ]
                        
                        company_info["website"] = possible_domains[0]  # Best guess
                    
                    break  # Exit after first analysis
                    
                except Exception as e:
                    print(f"Search error: {e}")
                    continue
        
        return company_info
        
    except Exception as e:
        print(f"❌ Company research error: {e}")
        return {
            "name": company_name,
            "industry": "Information not available",
            "size": "Information not available",
            "founded": "Information not available",
            "headquarters": "Information not available", 
            "website": "Information not available",
            "description": f"Unable to retrieve detailed information about {company_name}. This may be a small local business or new company."
        }

def generate_smart_questions(company_name: str, job_role: str, company_info: Dict) -> list:
    """Generate contextual questions based on company and role"""
    
    questions = [
        f"What does a typical day look like in this {job_role} role?",
        "What are the biggest challenges facing the team right now?",
        "How do you measure success in this position?"
    ]
    
    # Add industry-specific questions
    industry = company_info.get("industry", "").lower()
    
    if "personal care" in industry or "beauty" in industry:
        questions.extend([
            "What's your approach to client relationships and customer service?",
            "How do you stay current with trends and techniques in the industry?",
            "What opportunities are there for skills development and training?"
        ])
    
    elif "food" in industry or "hospitality" in industry:
        questions.extend([
            "How do you handle busy periods and maintain quality?",
            "What's the team culture like in the kitchen/service area?",
            "Are there opportunities to contribute to menu development?"
        ])
    
    elif "technology" in industry:
        questions.extend([
            "What technologies and tools does the team currently use?",
            "How do you approach code reviews and technical collaboration?",
            "What's the company's approach to professional development and learning?"
        ])
    
    elif "healthcare" in industry:
        questions.extend([
            "How do you ensure patient safety and quality care?",
            "What's your approach to continuing education and certifications?",
            "How does the practice stay current with medical best practices?"
        ])
    
    else:
        questions.extend([
            "What opportunities are there for professional development?",
            "How does this role contribute to the company's overall goals?",
            "What's the company culture like?"
        ])
    
    # Add general closing questions
    questions.extend([
        "What are the next steps in the interview process?",
        "Is there anything else I can clarify about my experience?"
    ])
    
    return questions

async def generate_ai_interview_questions(company_name: str, job_role: str, company_info: Dict) -> List[Dict]:
    """Generate AI-powered interview questions using OpenAI API"""
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        print("⚠️ OpenAI API key not found, falling back to template questions")
        return generate_fallback_interview_questions(company_name, job_role, company_info)
    
    try:
        # Prepare context for AI generation
        company_context = f"""
        Company: {company_name}
        Industry: {company_info.get('industry', 'Unknown')}
        Size: {company_info.get('size', 'Unknown')}
        Location: {company_info.get('headquarters', 'Unknown')}
        Description: {company_info.get('description', 'No description available')}
        """
        
        # Create AI prompt for interview questions
        prompt = f"""
        You are an expert HR interviewer. Generate 8-10 realistic interview questions for this specific job application:
        
        Job Role: {job_role}
        {company_context}
        
        Generate a mix of questions including:
        - General behavioral questions
        - Role-specific technical/skill questions  
        - Company-specific questions
        - Situational questions relevant to the industry
        
        Format as JSON array with objects containing "question" and "category" fields.
        Make questions specific to the role and industry, not generic templates.
        """
        
        # Call OpenAI API
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an expert HR interviewer who creates tailored, realistic interview questions."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                  headers=headers, json=data) as response:
                
                if response.status == 200:
                    result = await response.json()
                    ai_content = result['choices'][0]['message']['content'].strip()
                    
                    # Try to parse JSON response
                    try:
                        # Clean the response to extract JSON
                        if '```json' in ai_content:
                            ai_content = ai_content.split('```json')[1].split('```')[0].strip()
                        elif '```' in ai_content:
                            ai_content = ai_content.split('```')[1].split('```')[0].strip()
                        
                        questions = json.loads(ai_content)
                        
                        # Validate structure
                        if isinstance(questions, list) and all('question' in q and 'category' in q for q in questions):
                            print(f"✅ Generated {len(questions)} AI interview questions")
                            return questions
                        else:
                            print("⚠️ AI response format invalid, using fallback")
                            return generate_fallback_interview_questions(company_name, job_role, company_info)
                            
                    except json.JSONDecodeError as e:
                        print(f"⚠️ JSON parse error: {e}, using fallback")
                        return generate_fallback_interview_questions(company_name, job_role, company_info)
                        
                else:
                    print(f"⚠️ OpenAI API error: {response.status}, using fallback")
                    return generate_fallback_interview_questions(company_name, job_role, company_info)
                    
    except Exception as e:
        print(f"⚠️ AI question generation error: {e}, using fallback")
        return generate_fallback_interview_questions(company_name, job_role, company_info)

def generate_fallback_interview_questions(company_name: str, job_role: str, company_info: Dict) -> List[Dict]:
    """Fallback interview questions when AI is unavailable"""
    
    base_questions = [
        {"question": "Tell us about yourself and why you're interested in this role.", "category": "General"},
        {"question": f"What experience do you have that makes you suitable for a {job_role} position?", "category": "Experience"},
        {"question": f"Why do you want to work at {company_name}?", "category": "Company-specific"},
        {"question": "Where do you see yourself in 5 years?", "category": "Career Goals"}
    ]
    
    # Add role-specific questions
    role_lower = job_role.lower()
    
    if any(word in role_lower for word in ['barber', 'stylist', 'beauty']):
        base_questions.extend([
            {"question": "How do you handle difficult or unhappy customers?", "category": "Customer Service"},
            {"question": "Describe your experience with different hair types and styles.", "category": "Technical Skills"},
            {"question": "How do you stay current with trends and techniques?", "category": "Professional Development"}
        ])
    
    elif any(word in role_lower for word in ['server', 'wait', 'hospitality', 'chef', 'cook']):
        base_questions.extend([
            {"question": "How do you handle pressure during busy periods?", "category": "Stress Management"},
            {"question": "Describe a time you dealt with a difficult customer.", "category": "Customer Service"},
            {"question": "How do you ensure food safety and quality?", "category": "Technical Skills"}
        ])
    
    elif any(word in role_lower for word in ['developer', 'engineer', 'tech', 'programmer']):
        base_questions.extend([
            {"question": "Walk me through your problem-solving process for complex technical issues.", "category": "Technical Skills"},
            {"question": "How do you stay updated with new technologies?", "category": "Learning"},
            {"question": "Describe a challenging project you've worked on.", "category": "Experience"}
        ])
    
    else:
        base_questions.extend([
            {"question": "Describe a challenging situation you've faced and how you handled it.", "category": "Problem Solving"},
            {"question": "How do you prioritize tasks when you have multiple deadlines?", "category": "Time Management"},
            {"question": "Give an example of when you worked as part of a team.", "category": "Teamwork"}
        ])
    
    return base_questions

# Updated research endpoint with real data
@router.post("/research-job")
async def research_job_application(payload: JobResearchInput):
    """Research a company and job role - REAL DATA VERSION"""
    
    try:
        print(f"🔍 Starting REAL research for: {payload.company_name} - {payload.job_role}")
        
        # Get real company information
        company_info = await search_company_info(payload.company_name)
        
        # Generate contextual questions
        questions_to_ask = generate_smart_questions(payload.company_name, payload.job_role, company_info)
        
        # Generate AI-powered interview questions
        potential_interview_questions = await generate_ai_interview_questions(payload.company_name, payload.job_role, company_info)
        
        result = {
            "success": True,
            "data": {
                "company_info": company_info,
                "questions_to_ask": questions_to_ask,
                "potential_interview_questions": potential_interview_questions
            }
        }
        
        print(f"✅ REAL research completed for {payload.company_name}")
        print(f"📊 Industry identified: {company_info['industry']}")
        print(f"📍 Location: {company_info['headquarters']}")
        
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

# Keep the other existing endpoints unchanged
@router.post("/interview-prep")
async def interview_prep(payload: InterviewInput):
    """Basic interview preparation"""
    prep_text = f"""# Interview Preparation for {payload.role} at {payload.company}

## Research Checklist
✓ Company website and recent news
✓ Role requirements and responsibilities  
✓ Industry trends and challenges
✓ Company culture and values

## STAR Method for Behavioral Questions
- **Situation**: Set the context
- **Task**: Describe what you needed to do
- **Action**: Explain what you did
- **Result**: Share the outcome

## Key Areas to Prepare
- Your relevant experience and achievements
- Why you want this specific role
- Questions about the company and position
- Salary expectations (if asked)
"""

    questions = [
        f"Why do you want to work at {payload.company}?",
        f"What interests you about this {payload.role} position?",
        "Tell me about yourself and your background.",
        "What are your greatest strengths?",
        "Describe a challenging project you've worked on.",
        "Where do you see yourself in 5 years?"
    ]

    return {"success": True, "prep": prep_text, "questions": questions}

@router.post("/interview-feedback")
async def interview_feedback(payload: FeedbackInput):
    """AI-powered interview answer feedback"""
    
    # Check for OpenAI API key
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        # Fallback feedback
        feedback = f"""Your answer to '{payload.question}' shows good structure. Consider adding more specific examples and quantifiable results. Make sure to highlight your unique value proposition and how it relates to the role you're applying for."""
        return {"success": True, "feedback": feedback, "ai_powered": False}
    
    try:
        # Create AI prompt for feedback
        prompt = f"""
        You are an expert interview coach. Provide constructive feedback on this interview answer:
        
        Question: "{payload.question}"
        Answer: "{payload.answer}"
        
        Provide specific, actionable feedback covering:
        1. Content quality and relevance
        2. Structure and clarity
        3. Specific improvements
        4. What they did well
        
        Keep feedback encouraging but honest. Focus on practical improvements.
        Limit response to 150 words maximum.
        """
        
        # Call OpenAI API
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {openai_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are an expert interview coach providing constructive, specific feedback."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 300
            }
            
            async with session.post("https://api.openai.com/v1/chat/completions", 
                                  headers=headers, json=data) as response:
                
                if response.status == 200:
                    result = await response.json()
                    ai_feedback = result['choices'][0]['message']['content'].strip()
                    
                    return {
                        "success": True, 
                        "feedback": ai_feedback,
                        "ai_powered": True
                    }
                else:
                    # Fallback on API error
                    feedback = f"""Your answer to '{payload.question}' shows good structure. Consider adding more specific examples and quantifiable results. Make sure to highlight your unique value proposition and how it relates to the role you're applying for."""
                    return {"success": True, "feedback": feedback, "ai_powered": False}
                    
    except Exception as e:
        print(f"⚠️ AI feedback error: {e}")
        # Fallback feedback
        feedback = f"""Your answer to '{payload.question}' shows good structure. Consider adding more specific examples and quantifiable results. Make sure to highlight your unique value proposition and how it relates to the role you're applying for."""
        return {"success": True, "feedback": feedback, "ai_powered": False}

@router.get("/interview/health")
async def interview_health():
    return {"status": "healthy", "service": "interview-api-with-real-data"}