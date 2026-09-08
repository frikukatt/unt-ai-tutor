from app.ai_service import (
    explain_answer,
    analyze_ent_results,
)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    User,
    TestAttempt,
    QuestionResult,
    Question,
)
from app.security import get_current_user


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


@router.post("/analyze/{attempt_id}")
def analyze_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempt = (
        db.query(TestAttempt)
        .filter(
            TestAttempt.id == attempt_id,
            TestAttempt.user_id == current_user.id
        )
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Test attempt not found"
        )

    results = (
        db.query(
            QuestionResult,
            Question
        )
        .join(
            Question,
            Question.id == QuestionResult.question_id
        )
        .filter(
            QuestionResult.attempt_id == attempt.id
        )
        .all()
    )

    if not results:
        raise HTTPException(
            status_code=400,
            detail="No question results found for this attempt"
        )

    student_data = f"""
Результат тестирования ученика:

Общий результат:
- Баллы: {attempt.score}/{attempt.max_score}
- Процент: {attempt.percentage}%
- Количество вопросов: {attempt.total_questions}
- Тип теста: {attempt.test_type}

Результаты по вопросам:
"""

    for result, question in results:
        student_data += f"""
---
Предмет: {question.subject}
Тема: {question.topic}
Раздел ЕНТ: {question.ent_section}
Тип вопроса: {question.question_type}

Вопрос:
{question.question}

Ответ ученика:
{result.user_answer}

Правильный ответ:
{question.correct_answer}

Получено баллов:
{result.points_earned}/{result.max_points}
"""

    try:
        analysis = analyze_ent_results(student_data)

        return {
            "attempt_id": attempt.id,
            "analysis": analysis.model_dump()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI analysis error: {str(e)}"
        )