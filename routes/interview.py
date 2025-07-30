class JobResearchInput(BaseModel):
    company_name: str
    job_role: str

@router.post("/research-job")
async def research_job_application(payload: JobResearchInput):
    """Research a company and job role for interview preparation"""
    
    try:
        # Company research prompt
        company_prompt = f"""
        Research and provide information about {payload.company_name} for a job application. 
        
        Provide a JSON response with:
        - industry
        - size (employee count estimate)
        - founded (year estimate)
        - headquarters (location)
        - description (brief company overview)
        
        If you don't know specifics, provide reasonable estimates.
        """
        
        # Questions prompts
        questions_prompt = f"""
        Generate 6 smart questions a candidate should ask when interviewing for a {payload.job_role} position at {payload.company_name}.
        Return as a JSON array of strings.
        """
        
        interview_prompt = f"""
        Generate 6 potential interview questions for a {payload.job_role} position at {payload.company_name}.
        Return as JSON array with objects containing 'question' and 'category' keys.
        """

        # For now, return sample data (you can enhance with AI calls later)
        return {
            "success": True,
            "data": {
                "company_info": {
                    "name": payload.company_name,
                    "industry": "Technology" if any(tech in payload.company_name.lower() for tech in ["tech", "google", "microsoft", "apple"]) else "Business Services",
                    "size": "1000+ employees" if payload.company_name.lower() in ["google", "microsoft", "apple", "amazon", "meta"] else "100-1000 employees",
                    "founded": "1998" if "google" in payload.company_name.lower() else "2000",
                    "headquarters": "Sydney, Australia",
                    "website": f"www.{payload.company_name.lower().replace(' ', '')}.com",
                    "description": f"{payload.company_name} is a leading company in their industry, known for innovation and professional excellence."
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
                    {"question": f"What experience do you have that makes you suitable for a {payload.job_role} position?", "category": "Experience"},
                    {"question": f"Why do you want to work at {payload.company_name}?", "category": "Company-specific"},
                    {"question": "Describe a challenging project you've worked on and how you overcame obstacles.", "category": "Behavioral"},
                    {"question": "Where do you see yourself in 5 years?", "category": "Career Goals"},
                    {"question": f"What skills do you think are most important for success in {payload.job_role}?", "category": "Role-specific"}
                ]
            }
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
