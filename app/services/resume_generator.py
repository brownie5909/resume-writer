import asyncio
import json
import os
import re
from typing import Any, Dict, Optional

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def _extract_json_object(content: str) -> Dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            raise ValueError("AI returned no JSON object")
        return json.loads(match.group(0))


def _safe_text(value: Any, fallback: str = "") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def _normalise_generated_resume(raw: Dict[str, Any]) -> Dict[str, str]:
    """Return a predictable structure for the API and PDF renderer."""
    resume_text = _safe_text(raw.get("resume_text"))
    cover_letter = _safe_text(raw.get("cover_letter"))
    ats_notes = _safe_text(raw.get("ats_notes"))

    if not resume_text:
        raise ValueError("AI did not generate resume_text")

    return {
        "resume_text": resume_text,
        "cover_letter": cover_letter,
        "ats_notes": ats_notes,
    }


def _call_openai(prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert Australian resume writer and ATS specialist. "
                    "You write truthful, polished, ATS-friendly resumes using only the information supplied. "
                    "Return valid JSON only."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.35,
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content or "{}"


async def generate_resume_with_ai(
    data: Any,
    template_choice: Optional[str] = "default",
    generate_cover_letter: bool = False,
) -> Dict[str, str]:
    """Generate a resume and optional cover letter using OpenAI."""

    candidate_payload = {
        "full_name": data.full_name,
        "email": str(data.email),
        "phone": data.phone,
        "job_title": data.job_title,
        "company": data.company,
        "summary": data.summary,
        "responsibilities": data.responsibilities,
        "degree": data.degree,
        "school": data.school,
        "skills": data.skills,
        "template_choice": template_choice,
        "generate_cover_letter": generate_cover_letter,
    }

    prompt = f"""
Create an ATS-friendly resume for an Australian job seeker using only the details below.

Candidate details:
{json.dumps(candidate_payload, ensure_ascii=False, indent=2)}

Rules:
- Return ONLY valid JSON.
- Do not use markdown fences.
- Do not invent employers, dates, qualifications, certifications, or measurable results unless the user supplied them.
- Use a clean single-column ATS-friendly structure.
- Use standard section headings: Contact Information, Professional Summary, Key Skills, Professional Experience, Education.
- Avoid tables, columns, graphics, icons, text boxes, and overly complex formatting.
- Keep language professional, confident, and easy to scan.
- Improve weak wording, but preserve truthfulness.
- If responsibilities are supplied as rough notes, convert them into strong bullet points.
- If details are missing, use sensible wording without pretending the missing details exist.
- The resume must be suitable for the target job title.

Return JSON in this exact structure:
{{
  "resume_text": "Full polished resume as plain text with clear section headings and bullet points",
  "cover_letter": "Cover letter text if requested, otherwise empty string",
  "ats_notes": "Brief note explaining why the generated resume is ATS-friendly"
}}
"""

    content = await asyncio.to_thread(_call_openai, prompt)
    raw = _extract_json_object(content)
    return _normalise_generated_resume(raw)
