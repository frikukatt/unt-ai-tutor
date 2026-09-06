from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.ai_service import explain_answer


router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)


class ExplainRequest(BaseModel):
    question: str
    user_answer: str
    correct_answer: str
    subject: str
    topic: str


@router.post("/explain")
def explain_question(data: ExplainRequest):

    try:
        explanation = explain_answer(
            question=data.question,
            user_answer=data.user_answer,
            correct_answer=data.correct_answer,
            subject=data.subject,
            topic=data.topic
        )

        return {
            "explanation": explanation
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI service error: {str(e)}"
        )