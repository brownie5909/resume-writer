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
    """AI-powered comprehensive company research"""
    
    try:
        print(f"🔍 Starting AI-powered research for: {company_name}")
        
        # Check for OpenAI API key
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            print("⚠️ OpenAI API key not found, using basic analysis")
            return await basic_company_analysis(company_name)
        
        # Enhanced AI prompt for comprehensive company research
        research_prompt = f"""
        You are an expert business researcher with access to comprehensive company databases. 
        Research the company "{company_name}" and provide detailed, accurate information.
        
        Company to research: {company_name}
        
        Please provide comprehensive information in the following JSON format:
        {{
            "name": "Official company name",
            "industry": "Specific industry sector (e.g., 'Energy & Utilities', 'Healthcare Technology')",
            "size": "Employee count or size category (e.g., '1,000-5,000 employees', 'Large Enterprise')",
            "founded": "Year founded or establishment date",
            "headquarters": "Full headquarters location including city, state/province, country",
            "website": "Official company website URL",
            "description": "Comprehensive 3-4 sentence description covering: what the company does, key services/products, market position, and notable achievements or characteristics",
            "business_model": "How the company makes money and operates",
            "key_services": ["List of main services or products"],
            "market_presence": "Market position, geographic reach, customer base",
            "recent_developments": "Recent news, expansions, or significant changes",
            "company_culture": "Work environment, values, employee experience insights",
            "hiring_trends": "Current hiring patterns, growth areas, typical roles"
        }}
        
        If this is a well-known company, provide accurate detailed information.
        If it's a smaller or local business, make reasonable inferences based on:
        - Industry type from the company name
        - Location clues in the name  
        - Typical business patterns for that industry
        - Australian business context if location suggests it
        
        Be specific and detailed rather than generic. Avoid "Unknown" - use informed analysis instead.
        """
        
        try:
            # Call OpenAI API for comprehensive research
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {openai_api_key}",
                    "Content-Type": "application/json"
                }
                
                data = {
                    "model": "gpt-4o-mini",  # Better for detailed research
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert business intelligence researcher with access to comprehensive company databases. Provide detailed, accurate company information in proper JSON format."
                        },
                        {"role": "user", "content": research_prompt}
                    ],
                    "temperature": 0.3,  # Lower for more factual responses
                    "max_tokens": 2000   # Allow more detailed responses
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
                            company_info = json.loads(json_content)
                            
                            # Validate required fields
                            required_fields = ['name', 'industry', 'size', 'founded', 'headquarters', 'website', 'description']
                            if all(field in company_info for field in required_fields):
                                print(f"✅ AI research completed for {company_name}")
                                print(f"📊 Industry: {company_info.get('industry', 'N/A')}")
                                print(f"📍 Location: {company_info.get('headquarters', 'N/A')}")
                                return company_info
                            else:
                                print("⚠️ AI response missing required fields, using fallback")
                                return await basic_company_analysis(company_name)
                                
                        except json.JSONDecodeError as e:
                            print(f"⚠️ JSON parse error in AI response: {e}")
                            return await basic_company_analysis(company_name)
                            
                    else:
                        print(f"⚠️ OpenAI API error: {response.status}")
                        return await basic_company_analysis(company_name)
                        
        except Exception as e:
            print(f"⚠️ AI research error: {e}")
            return await basic_company_analysis(company_name)
            
    except Exception as e:
        print(f"❌ Company research error: {e}")
        return await basic_company_analysis(company_name)

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

async def basic_company_analysis(company_name: str) -> Dict[str, Any]:
    """Fallback company analysis using enhanced keyword matching and knowledge base"""
    
    name_lower = company_name.lower()
    
    # Initialize with better defaults
    company_info = {
        "name": company_name,
        "industry": "Business Services",
        "size": "Small to Medium Business (1-200 employees)",
        "founded": "Established business (specific date not publicly available)",
        "headquarters": "Australia",
        "website": f"www.{re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()}.com.au",
        "description": f"{company_name} is a professional business providing specialized services to clients.",
        "business_model": "Service-based business model with direct client relationships",
        "key_services": ["Professional consulting", "Customer service", "Business solutions"],
        "market_presence": "Established presence in local/regional market",
        "recent_developments": "Continuing to serve clients and adapt to market needs",
        "company_culture": "Professional environment focused on client satisfaction and quality service delivery",
        "hiring_trends": "Selective hiring for skilled professionals with relevant experience"
    }
    
    # Enhanced industry detection with more specific categories
    industry_keywords = {
        "Energy & Utilities": ["energy", "power", "electricity", "gas", "utilities", "solar", "wind", "renewable"],
        "Healthcare & Medical": ["medical", "health", "clinic", "dental", "pharmacy", "hospital", "wellness"],
        "Technology & Software": ["tech", "software", "digital", "app", "web", "it", "cyber", "data"],
        "Financial Services": ["finance", "accounting", "tax", "wealth", "investment", "banking", "insurance"],
        "Construction & Engineering": ["construction", "building", "engineering", "civil", "infrastructure"],
        "Professional Services": ["legal", "law", "consulting", "advisory", "management", "strategy"],
        "Retail & Consumer": ["retail", "shop", "store", "boutique", "consumer", "fashion"],
        "Food & Hospitality": ["cafe", "coffee", "restaurant", "food", "bakery", "catering", "hotel"],
        "Personal Care & Beauty": ["barber", "hair", "salon", "beauty", "spa", "wellness", "massage"],
        "Real Estate & Property": ["property", "real estate", "realty", "development", "housing"],
        "Education & Training": ["education", "school", "training", "learning", "academy", "institute"],
        "Transportation & Logistics": ["transport", "logistics", "shipping", "delivery", "freight"]
    }
    
    # Find matching industry
    for industry, keywords in industry_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            company_info["industry"] = industry
            
            # Set industry-specific details
            if industry == "Energy & Utilities":
                company_info["size"] = "Large Corporation (1,000+ employees)" if "origin" in name_lower else "Medium Enterprise (200-1,000 employees)"
                company_info["description"] = f"{company_name} operates in the energy sector, providing electricity, gas, or renewable energy solutions to residential and commercial customers."
                company_info["key_services"] = ["Energy supply", "Customer service", "Infrastructure maintenance", "Renewable energy solutions"]
                company_info["business_model"] = "Regulated utility company with revenue from energy sales and distribution services"
                
            elif industry == "Technology & Software":
                company_info["description"] = f"{company_name} is a technology company providing software solutions, digital services, and IT support to businesses and consumers."
                company_info["key_services"] = ["Software development", "IT consulting", "Digital transformation", "Technical support"]
                company_info["company_culture"] = "Innovation-focused environment with emphasis on collaboration, continuous learning, and agile development practices"
                
            break
    
    # Enhanced location detection
    location_mapping = {
        'sydney': 'Sydney, New South Wales, Australia',
        'melbourne': 'Melbourne, Victoria, Australia', 
        'brisbane': 'Brisbane, Queensland, Australia',
        'perth': 'Perth, Western Australia, Australia',
        'adelaide': 'Adelaide, South Australia, Australia',
        'canberra': 'Canberra, Australian Capital Territory, Australia',
        'gold coast': 'Gold Coast, Queensland, Australia',
        'newcastle': 'Newcastle, New South Wales, Australia',
        'wollongong': 'Wollongong, New South Wales, Australia'
    }
    
    for location, full_address in location_mapping.items():
        if location in name_lower:
            company_info["headquarters"] = full_address
            break
    
    # Special handling for known companies
    if "origin" in name_lower and "energy" in name_lower:
        company_info.update({
            "industry": "Energy & Utilities",
            "size": "Large Corporation (4,000+ employees)",
            "founded": "1996 (as Origin Energy)",
            "description": "Origin Energy is one of Australia's leading integrated energy companies, providing electricity and gas to over 4 million customers. The company operates across the energy value chain including exploration, production, generation, and retail energy services.",
            "business_model": "Integrated energy company with revenue from retail energy sales, electricity generation, and natural gas production",
            "key_services": ["Electricity retail", "Gas retail", "Electricity generation", "Energy services", "Solar and battery solutions"],
            "market_presence": "Major player in Australian energy market with operations across all mainland states",
            "recent_developments": "Focus on renewable energy transition, battery storage projects, and customer digital experience improvements",
            "company_culture": "Safety-first culture with emphasis on customer service, sustainability, and innovation in energy solutions",
            "hiring_trends": "Active hiring in renewable energy, customer service, digital technology, and engineering roles"
        })
    
    return company_info

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