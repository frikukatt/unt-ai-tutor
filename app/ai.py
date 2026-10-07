from datetime import datetime
import json

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
    AIAnalysis,
    SkillProfile
)
from app.security import get_current_user
from app.ai_service import explain_answer, analyze_ent_results
from app.knowledge import build_knowledge_context


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
def explain_question(
    data: ExplainRequest,
    db: Session = Depends(get_db)
):
    try:
        knowledge_context = build_knowledge_context(
            db=db,
            query=f"{data.question} {data.topic}",
            subject=data.subject,
            limit=5
        )

        explanation = explain_answer(
            question=data.question,
            user_answer=data.user_answer,
            correct_answer=data.correct_answer,
            subject=data.subject,
            topic=data.topic,
            knowledge_context=knowledge_context
        )

        return {
            "explanation": explanation,
            "knowledge_used": bool(knowledge_context)
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

    saved_analysis = (
        db.query(AIAnalysis)
        .filter(
            AIAnalysis.attempt_id == attempt.id
        )
        .first()
    )

    if saved_analysis:
        return {
            "attempt_id": attempt.id,
            "analysis": json.loads(saved_analysis.analysis_json),
            "cached": True,
            "knowledge_used": False
        }

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

    skill_profiles = (
        db.query(SkillProfile)
        .filter(
            SkillProfile.user_id == current_user.id
        )
        .order_by(
            SkillProfile.subject,
            SkillProfile.topic
        )
        .all()
    )

    student_data = f"""
Результат тестирования ученика:

Общий результат:
- Баллы: {attempt.score}/{attempt.max_score}
- Процент: {attempt.percentage}%
- Количество вопросов: {attempt.total_questions}
- Тип теста: {attempt.test_type}

Накопленная статистика ученика:
"""

    if skill_profiles:
        for skill in skill_profiles:
            student_data += f"""
- Предмет: {skill.subject}
- Тема: {skill.topic}
- Всего вопросов: {skill.total_questions}
- Правильных ответов: {skill.correct_questions}
- Точность: {skill.accuracy}%
"""
    else:
        student_data += """
Данных накопленной статистики пока нет.
"""

    errors = []

    for result, question in results:
        is_correct = (
            result.points_earned == result.max_points
        )

        if not is_correct:
            errors.append(
                {
                    "subject": question.subject,
                    "topic": question.topic,
                    "ent_section": question.ent_section,
                    "question_type": question.question_type,
                    "question": question.question,
                    "user_answer": result.user_answer,
                    "correct_answer": question.correct_answer,
                    "points_earned": result.points_earned,
                    "max_points": result.max_points
                }
            )

    student_data += """

Ошибки в текущем тесте:

"""

    if errors:
        for index, error in enumerate(errors, start=1):
            student_data += f"""
Ошибка #{index}

Предмет:
{error["subject"]}

Тема:
{error["topic"]}

Раздел ЕНТ:
{error["ent_section"]}

Тип вопроса:
{error["question_type"]}

Вопрос:
{error["question"]}

Ответ ученика:
{error["user_answer"]}

Правильный ответ:
{error["correct_answer"]}

Получено баллов:
{error["points_earned"]}/{error["max_points"]}

---
"""
    else:
        student_data += """
В текущем тесте ошибок нет.
"""

    knowledge_context = ""

    if errors:
        knowledge_parts = []

        for error in errors:
            try:
                context = build_knowledge_context(
                    db=db,
                    query=f'{error["question"]} {error["topic"]}',
                    subject=error["subject"],
                    limit=3
                )

                if context:
                    knowledge_parts.append(
                        f"""
Материал для ошибки:

Предмет:
{error["subject"]}

Тема:
{error["topic"]}

Вопрос:
{error["question"]}

Найденный учебный материал:
{context}
"""
                    )

            except Exception:
                continue

        if knowledge_parts:
            knowledge_context = "\n".join(
                knowledge_parts
            )

    student_data += """

Правила анализа:

1. Не объявляй тему слабой только потому, что в текущем тесте
   была одна ошибка по этой теме.

2. Используй накопленную статистику SkillProfile, чтобы определить,
   действительно ли проблема повторяется.

3. Обращай внимание на повторяющиеся ошибки по одному предмету,
   теме или типу навыка.

4. Если одна тема встречается несколько раз и точность по ней
   низкая, это более сильный сигнал слабого места.

5. Если накопленной статистики недостаточно, прямо учитывай
   это ограничение и не делай слишком уверенных выводов.

6. При анализе ошибки старайся определить не только название темы,
   но и конкретный навык или концепцию, которая проверяется вопросом,
   если это действительно можно определить из текста вопроса.

7. Не выдумывай концепции, которых нет в предоставленных данных.

8. В рекомендациях отдавай приоритет конкретным действиям:
   что повторить, какой тип задач потренировать и на что обратить
   внимание при следующих попытках.

9. Не повторяй просто название темы в качестве рекомендации.
   Рекомендация должна объяснять, ЧТО именно ученику нужно улучшить,
   если это можно определить из данных.

10. Разделяй:
   - случайную единичную ошибку;
   - повторяющуюся проблему;
   - устойчиво слабую тему по накопленной статистике.

11. Если предоставлен материал из Knowledge Base, используй его
    для определения конкретного учебного содержания.

12. Не утверждай, что информация взята из учебника, если
    соответствующий материал отсутствует в Knowledge Base.

13. Если Knowledge Base не содержит подходящего материала,
    продолжай анализировать данные ученика без него.

14. Не используй нерелевантный учебный материал как доказательство
    слабости ученика.

Теперь проанализируй результаты ученика.
"""

    try:
        analysis = analyze_ent_results(
            student_data=student_data,
            knowledge_context=knowledge_context
        )

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
            "cached": False,
            "knowledge_used": bool(knowledge_context)
        }

    except Exception as e:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"AI analysis error: {str(e)}"
        )