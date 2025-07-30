from fastapi import APIRouter
from pydantic import BaseModel
import os
from openai import AsyncOpenAI

router = APIRouter()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

# Interview prep route (your existing route)
@router.post("/interview-prep")
async def interview_prep(payload: InterviewInput):
    prompt = f"""
You are a career coach helping someone prepare for a job interview.

Company: {payload.company}
Role: {payload.role}

Return the following sections in markdown format:
## Interview Preparation
1. Company Research
2. Role Expectations
3. STAR Method Reminder
4. Smart Questions to Ask
5. Any relevant industry notes

## Likely Interview Questions
List 6 questions, one per line, each starting with:
Q: [question]
    """

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        raw_output = response.choices[0].message.content.strip()
        lines = raw_output.splitlines()

        questions = [line[3:].strip() for line in lines if line.startswith("Q: ")]
        prep_text = "\n".join([line for line in lines if not line.startswith("Q: ")])

        return {
            "success": True,
            "prep": prep_text,
            "questions": questions
        }

    except Exception as e:
        return { "success": False, "error": str(e) }

# Feedback route (your existing route)
@router.post("/interview-feedback")
async def interview_feedback(payload: FeedbackInput):
    prompt = f"""
You are an interview coach reviewing a job candidate's answer.

Question:
{payload.question}

Candidate's Answer:
{payload.answer}

Give specific, actionable feedback in 3–4 sentences.
Use a friendly, supportive tone.
"""

    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )

        feedback = response.choices[0].message.content.strip()

        return {
            "success": True,
            "feedback": feedback
        }

    except Exception as e:
        return { "success": False, "error": str(e) }

# NEW: Job Research route for the frontend tool
@router.post("/research-job")
async def research_job_application(payload: JobResearchInput):
    """Research a company and job role for interview preparation"""
    
    try:
        # Enhanced AI-powered company research
        company_prompt = f"""
        Research and provide information about {payload.company_name} for a job application. 
        
        Provide detailed information including:
        - Industry and sector
        - Company size (estimated employees)
        - Founded year (if known, otherwise reasonable estimate)
        - Headquarters location (if known, otherwise major business center)
        - Main products/services
        - Company culture and values
        - Recent developments or news
        
        If you don't have specific information, provide reasonable estimates based on industry standards.
        Format as a comprehensive but concise description.
        """
        
        questions_prompt = f"""
        Generate 6 smart, insightful questions that a candidate should ask when interviewing for a {payload.job_role} position at {payload.company_name}.
        
        These questions should:
        1. Show genuine interest in the role and company
        2. Help the candidate evaluate if the position is right for them
        3. Demonstrate knowledge of the industry
        4. Be specific and thoughtful, not generic
        5. Cover different aspects: role responsibilities, team dynamics, growth opportunities, challenges
        
        Return as a simple list of questions.
        """
        
        interview_prompt = f"""
        Generate 6 potential interview questions that {payload.company_name} might ask a candidate applying for a {payload.job_role} position.
        
        Include a mix of:
        1. General behavioral questions
        2. Role-specific skill questions
        3. Company-specific questions
        4. Situational/problem-solving questions
        5. Career motivation questions
        
        For each question, categorize it appropriately.
        Format as: [CATEGORY]: Question text
        """

        # Make AI calls for better results
        try:
            # Get company research
            company_response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a professional career research assistant providing accurate, helpful information for job seekers."},
                    {"role": "user", "content": company_prompt}
                ],
                temperature=0.3,
                max_tokens=600
            )
            
            # Get questions to ask
            questions_response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a career counselor helping candidates prepare smart interview questions."},
                    {"role": "user", "content": questions_prompt}
                ],
                temperature=0.7,
                max_tokens=400
            )
            
            # Get potential interview questions
            interview_response = await client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an experienced hiring manager creating realistic interview questions."},
                    {"role": "user", "content": interview_prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )
            
            # Parse AI responses
            company_description = company_response.choices[0].message.content.strip()
            
            # Parse questions to ask (simple list)
            questions_text = questions_response.choices[0].message.content.strip()
            questions_to_ask = []
            for line in questions_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or line.startswith('*') or line[0].isdigit()):
                    clean_question = line.lstrip('-•*0123456789. ').strip()
                    if clean_question:
                        questions_to_ask.append(clean_question)
            
            # Ensure we have 6 questions
            if len(questions_to_ask) < 6:
                fallback_questions = [
                    "What does a typical day look like in this role?",
                    "What are the biggest challenges facing the team right now?",
                    "How do you measure success in this position?",
                    "What opportunities are there for professional development?",
                    "Can you describe the company culture and team dynamics?",
                    "What are the next steps in the interview process?"
                ]
                questions_to_ask.extend(fallback_questions[len(questions_to_ask):])
            
            questions_to_ask = questions_to_ask[:6]  # Limit to 6
            
            # Parse interview questions with categories
            interview_text = interview_response.choices[0].message.content.strip()
            potential_questions = []
            
            for line in interview_text.split('\n'):
                line = line.strip()
                if ':' in line and len(line) > 10:
                    if line.startswith('[') and ']:' in line:
                        # Format: [CATEGORY]: Question
                        category = line.split(']:')[0].strip('[')
                        question = line.split(']:')[1].strip()
                    elif any(cat in line.upper() for cat in ['BEHAVIORAL', 'TECHNICAL', 'GENERAL', 'COMPANY', 'EXPERIENCE', 'CAREER']):
                        # Format: CATEGORY: Question
                        parts = line.split(':', 1)
                        category = parts[0].strip()
                        question = parts[1].strip()
                    else:
                        # Fallback: treat as general question
                        category = "General"
                        question = line.strip()
                    
                    if question:
                        potential_questions.append({
                            "question": question,
                            "category": category.title()
                        })
            
            # Ensure we have 6 interview questions
            if len(potential_questions) < 6:
                fallback_interview_questions = [
                    {"question": "Tell us about yourself and why you're interested in this role.", "category": "General"},
                    {"question": f"What experience do you have that makes you suitable for a {payload.job_role} position?", "category": "Experience"},
                    {"question": f"Why do you want to work at {payload.company_name}?", "category": "Company-specific"},
                    {"question": "Describe a challenging project you've worked on and how you overcame obstacles.", "category": "Behavioral"},
                    {"question": "Where do you see yourself in 5 years?", "category": "Career Goals"},
                    {"question": f"What skills do you think are most important for success in {payload.job_role}?", "category": "Role-specific"}
                ]
                potential_questions.extend(fallback_interview_questions[len(potential_questions):])
            
            potential_questions = potential_questions[:6]  # Limit to 6
            
            # Determine company info based on AI research and smart defaults
            company_info = {
                "name": payload.company_name,
                "industry": determine_industry(payload.company_name, company_description),
                "size": determine_company_size(payload.company_name, company_description),
                "founded": determine_founded_year(payload.company_name, company_description),
                "headquarters": determine_headquarters(payload.company_name, company_description),
                "website": f"www.{payload.company_name.lower().replace(' ', '').replace('.', '')}.com",
                "description": company_description
            }
            
        except Exception as ai_error:
            print(f"AI Error: {ai_error}")
            # Fallback to sample data if AI fails
            return get_fallback_research_data(payload.company_name, payload.job_role)
        
        return {
            "success": True,
            "data": {
                "company_info": company_info,
                "questions_to_ask": questions_to_ask,
                "potential_interview_questions": potential_questions
            }
        }
        
    except Exception as e:
        print(f"Research Error: {e}")
        return get_fallback_research_data(payload.company_name, payload.job_role)

def determine_industry(company_name, description):
    """Determine company industry from name and description"""
    name_lower = company_name.lower()
    desc_lower = description.lower()
    
    if any(tech in name_lower for tech in ["tech", "google", "microsoft", "apple", "meta", "amazon"]) or "technology" in desc_lower:
        return "Technology"
    elif any(fin in name_lower for fin in ["bank", "finance", "investment"]) or "financial" in desc_lower:
        return "Financial Services"
    elif any(health in name_lower for health in ["health", "medical", "pharma"]) or "healthcare" in desc_lower:
        return "Healthcare"
    elif "retail" in desc_lower or "ecommerce" in desc_lower:
        return "Retail"
    elif "consulting" in desc_lower or "advisory" in desc_lower:
        return "Consulting"
    else:
        return "Business Services"

def determine_company_size(company_name, description):
    """Determine company size"""
    name_lower = company_name.lower()
    desc_lower = description.lower()
    
    if name_lower in ["google", "microsoft", "apple", "amazon", "meta", "tesla"]:
        return "10,000+ employees"
    elif "large" in desc_lower or "multinational" in desc_lower:
        return "1,000-10,000 employees"
    elif "startup" in desc_lower or "small" in desc_lower:
        return "1-50 employees"
    else:
        return "100-1,000 employees"

def determine_founded_year(company_name, description):
    """Determine founded year"""
    name_lower = company_name.lower()
    
    # Known companies
    known_years = {
        "google": "1998",
        "microsoft": "1975",
        "apple": "1976",
        "amazon": "1994",
        "meta": "2004",
        "tesla": "2003"
    }
    
    for company, year in known_years.items():
        if company in name_lower:
            return year
    
    return "2000"  # Default fallback

def determine_headquarters(company_name, description):
    """Determine headquarters location"""
    name_lower = company_name.lower()
    desc_lower = description.lower()
    
    if "australia" in desc_lower or "sydney" in desc_lower:
        return "Sydney, Australia"
    elif name_lower in ["google", "apple", "meta"]:
        return "California, USA"
    elif "microsoft" in name_lower:
        return "Washington, USA"
    else:
        return "Sydney, Australia"  # Default for user's location

def get_fallback_research_data(company_name, job_role):
    """Fallback data when AI fails"""
    return {
        "success": True,
        "data": {
            "company_info": {
                "name": company_name,
                "industry": "Business Services",
                "size": "100-1,000 employees",
                "founded": "2000",
                "headquarters": "Sydney, Australia",
                "website": f"www.{company_name.lower().replace(' ', '')}.com",
                "description": f"{company_name} is a professional company in their industry. For more specific information, please visit their website and recent news articles."
            },
            "questions_to_ask": [
                "What does a typical day look like in this role?",
                "What are the biggest challenges facing the team right now?",
                "How do you measure success in this position?",
                "What opportunities are there for professional development?",
                "Can you describe the company culture and team dynamics?",
                "What are the next steps in the interview process?"
            ],
            "potential_interview_questions": [
                {"question": "Tell us about yourself and why you're interested in this role.", "category": "General"},
                {"question": f"What experience do you have that makes you suitable for a {job_role} position?", "category": "Experience"},
                {"question": f"Why do you want to work at {company_name}?", "category": "Company-specific"},
                {"question": "Describe a challenging project you've worked on and how you overcame obstacles.", "category": "Behavioral"},
                {"question": "Where do you see yourself in 5 years?", "category": "Career Goals"},
                {"question": f"What skills do you think are most important for success in {job_role}?", "category": "Role-specific"}
            ]
        }
    }
