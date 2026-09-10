from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    TestAttempt,
    QuestionResult,
    Question,
    AIAnalysis
)
from app.security import get_current_user
from app.ai_service import explain_answer, analyze_ent_results


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
    # Проверяем, что попытка принадлежит текущему пользователю
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

    saved_analysis = (
        db.query(AIAnalysis)
        .filter(
            AIAnalysis.attempt_id == attempt.id
        )
        .first()
    )

    if saved_analysis:
        import json

        return {
            "attempt_id": attempt.id,
            "analysis": json.loads(saved_analysis.analysis_json),
            "cached": True
        }

    # Максимум 3 НОВЫХ анализа в сутки
    today_start = datetime.utcnow().replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )

    analyses_today = (
        db.query(func.count(AIAnalysis.id))
        .filter(
            AIAnalysis.attempt_id.in_(
                db.query(TestAttempt.id)
                .filter(
                    TestAttempt.user_id == current_user.id
                )
            ),
            AIAnalysis.created_at >= today_start
        )
        .scalar()
    )

    if analyses_today >= 3:
        raise HTTPException(
            status_code=429,
            detail="Daily AI analysis limit reached. Try again tomorrow."
        )

    # Получаем результаты вопросов
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

    # Формируем данные для AI
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

        import json

        analysis_data = analysis.model_dump()

        saved_analysis = AIAnalysis(
            attempt_id=attempt.id,
            summary=analysis_data["summary"],
            analysis_json=json.dumps(
                analysis_data,
                ensure_ascii=False
            )
        )

        db.add(saved_analysis)
        db.commit()
        db.refresh(saved_analysis)

        return {
            "attempt_id": attempt.id,
            "analysis": analysis_data,
            "cached": False
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"AI analysis error: {str(e)}"
        )