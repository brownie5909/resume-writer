import os
import json
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


async def analyze_resume_with_ai(resume_text: str, target_role: str = None):
    """
    Use OpenAI to analyze and improve resumes.
    """

    prompt = f"""
You are an expert ATS resume reviewer and career coach.

Analyze the following resume and return ONLY valid JSON.

Resume:
{resume_text}

Target Role:
{target_role or "General professional role"}

Return JSON in this EXACT format:

{{
  "overall_score": 0,
  "ats_score": 0,
  "formatting_score": 0,
  "strengths": [],
  "weaknesses": [],
  "keyword_analysis": {{
    "missing_keywords": [],
    "present_keywords": [],
    "keyword_density": 0
  }},
  "sections_analysis": {{
    "summary": {{
      "score": 0,
      "feedback": ""
    }},
    "experience": {{
      "score": 0,
      "feedback": ""
    }},
    "skills": {{
      "score": 0,
      "feedback": ""
    }}
  }},
  "specific_improvements": [],
  "ats_recommendations": [],
  "improved_resume": ""
}}

Rules:
- Return ONLY JSON
- Scores must be between 0 and 100
- Give detailed ATS recommendations
- Provide realistic professional improvements
- Rewrite the resume professionally in improved_resume
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You are an expert resume reviewer."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.4
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except Exception:
        raise Exception(f"AI returned invalid JSON: {content}")
