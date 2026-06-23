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
- If a role has more than 5 bullet points, consolidate or remove lower-value points while keeping the strongest achievements.
- Do not recommend removing bullet points from experience sections unless they are excessive, unclear, duplicated or poorly formatted.
- Avoid dense paragraphs in Professional Experience.
- A short 3 to 5 line Professional Summary is acceptable.
- Key Skills should be a concise keyword-rich list, not a long paragraph.
- Prefer measurable achievements where supported by the resume text.
- Do not invent employers, dates, qualifications, certifications, systems, metrics or achievements.
- Missing keywords should be relevant to the target role and should be incorporated naturally where truthful.
- The improved resume must directly apply every fixable weakness, missing keyword and ATS recommendation.
- The improved resume should normally maintain or improve ATS readability compared with the original resume.
"""


FIXABLE_IMPROVEMENT_RULES = """
Critical improved resume rules:
- The improved_resume must implement every recommendation that can be completed without inventing information.
- If you identify a formatting issue, fix it in improved_resume.
- If you identify a section heading issue, fix it in improved_resume.
- If you identify an education wording issue, fix it in improved_resume.
- If education dates appear to be future completion dates, rewrite them as "In Progress - Expected Completion YYYY" where appropriate.
- If you identify a bullet point count issue, fix it in improved_resume by consolidating to 3 to 5 concise bullet points per role where possible.
- If you identify dense or complex bullet points, simplify them in improved_resume.
- If you identify ATS readability issues, fix them in improved_resume.
- If you identify keyword placement issues, fix them in improved_resume where truthful.
- Do not leave correctable weaknesses in improved_resume.
- Weaknesses should focus on remaining issues that require user input, evidence, additional achievements, missing metrics, missing certifications, or missing details that cannot be safely inferred.
- Do not include a weakness that has already been corrected in improved_resume.

Final validation before returning JSON:
- Compare weaknesses, specific_improvements and ats_recommendations against improved_resume.
- If an item can be fixed through formatting, wording, headings, structure, bullet consolidation, date clarification or keyword placement, implement it in improved_resume before returning JSON.
- After applying fixable items, remove those items from weaknesses.
- Keep recommendations only when they require information the user must provide, such as quantified achievements, project examples, certification details, referee details or other facts not present in the original resume.
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


def _keyword_exists_in_resume(keyword: str, resume_text: str) -> bool:
    """Return true when a keyword or close phrase already appears in the resume."""
    if not keyword or not resume_text:
        return False

    normalised_resume = re.sub(r"\s+", " ", resume_text.lower())
    normalised_keyword = re.sub(r"\s+", " ", keyword.lower()).strip()

    if not normalised_keyword:
        return False

    if normalised_keyword in normalised_resume:
        return True

    keyword_words = [word for word in re.split(r"[^a-z0-9]+", normalised_keyword) if word]
    if len(keyword_words) > 1:
        return all(re.search(rf"\b{re.escape(word)}\b", normalised_resume) for word in keyword_words)

    return bool(re.search(rf"\b{re.escape(normalised_keyword)}\b", normalised_resume))


def _dedupe_case_insensitive(items: List[str]) -> List[str]:
    seen = set()
    output = []

    for item in items:
        key = item.lower().strip()
        if not key or key in seen:
            continue
        seen.add(key)
        output.append(item)

    return output


def _normalise_analysis(raw: Dict[str, Any], resume_text: str = "") -> Dict[str, Any]:
    """Ensure the API always returns the same safe JSON shape to the frontend."""
    keyword_analysis = _as_dict(raw.get("keyword_analysis"))
    sections_analysis = _as_dict(raw.get("sections_analysis"))

    missing_keywords = _dedupe_case_insensitive(_as_list(keyword_analysis.get("missing_keywords")))
    present_keywords = _dedupe_case_insensitive(_as_list(keyword_analysis.get("present_keywords")))

    verified_missing_keywords = [
        keyword for keyword in missing_keywords
        if not _keyword_exists_in_resume(keyword, resume_text)
    ]

    verified_present_keywords = _dedupe_case_insensitive(
        present_keywords + [
            keyword for keyword in missing_keywords
            if _keyword_exists_in_resume(keyword, resume_text)
        ]
    )

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
            "missing_keywords": verified_missing_keywords,
            "present_keywords": verified_present_keywords,
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
                    "formatting advice across analyses. Do not list a keyword as missing "
                    "if it already appears anywhere in the resume text. The improved_resume "
                    "must apply all fixable recommendations before JSON is returned."
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

{FIXABLE_IMPROVEMENT_RULES}

Important rules:
- Return ONLY valid JSON.
- Do not include markdown fences.
- Scores must be integers from 0 to 100.
- Be specific and practical.
- Keep feedback consistent with the Hire Ready Resume Standard.
- Carefully check the full resume text before listing missing keywords.
- Do not list a keyword as missing if it already appears anywhere in the resume, even once.
- If a keyword appears in the resume but could be used more strongly, list that as an ATS recommendation instead of a missing keyword.
- Do not recommend removing bullet points from Professional Experience if the issue is that the resume needs clearer achievement-focused bullet points.
- Do not invent employers, qualifications, dates, certifications, systems, software, metrics, responsibilities, or achievements not supported by the resume.
- If the resume lacks detail, improve wording but keep the candidate's background truthful.
- If you list a missing keyword, include it naturally in the improved_resume where it is truthful and relevant.
- The improved_resume must address the weaknesses, keyword gaps, section feedback and ATS recommendations you provide.
- The improved_resume should be at least as ATS-friendly as the original resume and should not intentionally reduce formatting quality.
- If the original resume is already strong, make careful refinements rather than unnecessary rewrites.
- Do not include a weakness or specific improvement for a fixable formatting or structure issue unless it remains unresolved in improved_resume.
- Remaining weaknesses should mainly identify items requiring user-supplied facts, such as metrics, examples, certifications, project details, dates, referee details or achievements not present in the original resume.

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
        return _normalise_analysis(raw_result, cleaned_resume_text)
    except Exception as exc:
        raise Exception(f"AI returned invalid analysis JSON: {str(exc)}")
