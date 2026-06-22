import os
import json
import re
import asyncio
from typing import Any, Dict, List, Optional

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


HIRE_READY_RESUME_STANDARD = """
Hire Ready Resume Standard:
- Use a clean, text-based, single-column resume structure.
- Use standard section headings such as Professional Summary, Key Skills, Professional Experience, Education, Certifications and Referees.
- Bullet points are recommended for Professional Experience sections.
- Use 3 to 5 concise bullet points per recent role where enough detail exists.
- Do not recommend removing bullet points from experience sections unless they are excessive, unclear, duplicated or poorly formatted.
- Avoid dense paragraphs in Professional Experience.
- A short 3 to 5 line Professional Summary is acceptable.
- Key Skills should be a concise keyword-rich list, not a long paragraph.
- Prefer measurable achievements where supported by the resume text.
- Do not invent employers, dates, qualifications, certifications, systems, metrics or achievements.
- Missing keywords should be relevant to the target role and should be incorporated naturally where truthful.
- The improved resume should directly address the listed weaknesses, missing keywords and ATS recommendations.
- The improved resume should normally maintain or improve ATS readability compared with the original resume.
"""


def _clamp_score(value: Any, default: int = 70) -> int:
    """Return a safe integer score between 0 and 100."""
    try:
        score = int(float(value))
    except (TypeError, ValueError):
        score = default
    return max(0, min(100, score))


def _as_list(value: Any) -> List[str]:
    """Normalise OpenAI output into a clean list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    return [str(value).strip()] if str(value).strip() else []


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalise_analysis(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the API always returns the same safe JSON shape to the frontend."""
    keyword_analysis = _as_dict(raw.get("keyword_analysis"))
    sections_analysis = _as_dict(raw.get("sections_analysis"))

    def section(name: str) -> Dict[str, Any]:
        section_data = _as_dict(sections_analysis.get(name))
        return {
            "score": _clamp_score(section_data.get("score"), 70),
            "feedback": str(section_data.get("feedback", "")).strip(),
        }

    improved_resume = str(raw.get("improved_resume", "")).strip()
    if not improved_resume:
        improved_resume = "No improved resume generated."

    return {
        "overall_score": _clamp_score(raw.get("overall_score"), 70),
        "ats_score": _clamp_score(raw.get("ats_score"), 70),
        "formatting_score": _clamp_score(raw.get("formatting_score"), 70),
        "strengths": _as_list(raw.get("strengths")),
        "weaknesses": _as_list(raw.get("weaknesses")),
        "keyword_analysis": {
            "missing_keywords": _as_list(keyword_analysis.get("missing_keywords")),
            "present_keywords": _as_list(keyword_analysis.get("present_keywords")),
            "keyword_density": _clamp_score(keyword_analysis.get("keyword_density"), 0),
        },
        "sections_analysis": {
            "summary": section("summary"),
            "experience": section("experience"),
            "skills": section("skills"),
        },
        "specific_improvements": _as_list(raw.get("specific_improvements")),
        "ats_recommendations": _as_list(raw.get("ats_recommendations")),
        "improved_resume": improved_resume,
    }


def _extract_json_object(content: str) -> Dict[str, Any]:
    """Parse strict JSON first, then fall back to extracting the first object."""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("AI returned no JSON object")
        return json.loads(match.group(0))


def _call_openai(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert Australian resume reviewer, ATS specialist, "
                    "and career coach. Return valid JSON only. Apply the Hire Ready "
                    "Resume Standard consistently on every analysis. Do not invent facts "
                    "that are not supported by the resume text. Do not give contradictory "
                    "formatting advice across analyses."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"


async def analyze_resume_with_ai(resume_text: str, target_role: Optional[str] = None) -> Dict[str, Any]:
    """
    Use OpenAI to analyse and improve resumes.
    Returns a stable JSON structure for the frontend.
    """
    cleaned_resume_text = (resume_text or "").strip()
    cleaned_target_role = (target_role or "General professional role").strip()

    if len(cleaned_resume_text) < 50:
        raise ValueError("Resume text is too short to analyse")

    prompt = f"""
You are an expert ATS resume reviewer and career coach.

Analyse the resume below for Applicant Tracking System compatibility and hiring-manager quality.
Use the Hire Ready Resume Standard below as the fixed evaluation standard for every analysis.
Do not change the standard between analyses.

{HIRE_READY_RESUME_STANDARD}

Important rules:
- Return ONLY valid JSON.
- Do not include markdown fences.
- Scores must be integers from 0 to 100.
- Be specific and practical.
- Keep feedback consistent with the Hire Ready Resume Standard.
- Do not recommend removing bullet points from Professional Experience if the issue is that the resume needs clearer achievement-focused bullet points.
- Do not invent employers, qualifications, dates, certifications, systems, software, metrics, responsibilities, or achievements not supported by the resume.
- If the resume lacks detail, improve wording but keep the candidate's background truthful.
- If you list a missing keyword, include it naturally in the improved_resume where it is truthful and relevant.
- The improved_resume must address the weaknesses, keyword gaps, section feedback and ATS recommendations you provide.
- The improved_resume should be at least as ATS-friendly as the original resume and should not intentionally reduce formatting quality.
- If the original resume is already strong, make careful refinements rather than unnecessary rewrites.

Resume:
{cleaned_resume_text}

Target Role:
{cleaned_target_role}

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
"""

    content = await asyncio.to_thread(_call_openai, prompt)

    try:
        raw_result = _extract_json_object(content)
        return _normalise_analysis(raw_result)
    except Exception as exc:
        raise Exception(f"AI returned invalid analysis JSON: {str(exc)}")
