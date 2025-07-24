from fastapi import APIRouter
from pydantic import BaseModel
import os
from openai import AsyncOpenAI

router = APIRouter()
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class InterviewInput(BaseModel):
    company: str
    role: str

@router.post("/interview-prep")
async def interview_prep(payload: InterviewInput):
    try:
        response = await client.chat.completions.create(
            model="gpt-4",
            temperature=0.7,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert interview coach. "
                        "Always return a structured interview prep summary followed by exactly 6 clearly numbered questions."
                        "\nFormat:\n"
                        "## Interview Preparation\n"
                        "(detailed prep summary here, using **bold** section headers)\n\n"
                        "## Interview Questions\n"
                        "Q1: ...\nQ2: ...\nQ3: ...\nQ4: ...\nQ5: ...\nQ6: ..."
                    )
                },
                {
                    "role": "user",
                    "content": f"Company: {payload.company}\nRole: {payload.role}"
                }
            ]
        )

        full_output = response.choices[0].message.content.strip()

        # Split content by the Q1 marker
        split_point = full_output.find("Q1:")
        if split_point == -1:
            return {"success": False, "error": "No questions found in AI response."}

        prep = full_output[:split_point].strip()
        questions_block = full_output[split_point:].strip()
        questions = [line.strip() for line in questions_block.splitlines() if line.startswith("Q")]

        return {
            "success": True,
            "prep": prep,
            "questions": questions
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
