import os
from datetime import datetime, timedelta

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Question,
    TestAttempt,
    User,
    TestSession,
    QuestionResult,
    SkillProfile,
)
from app.schemas import (
    AnswerResult,
    QuestionAnswer,
    QuestionCreate,
    TestResult,
    QuestionPublic,
    AttemptPublic,
)
from app.scoring import calculate_question_score
from app.security import get_current_user


load_dotenv()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "").strip().lower()

router = APIRouter()


def require_admin(current_user: User = Depends(get_current_user)):
    if not ADMIN_EMAIL:
        raise HTTPException(
            status_code=503,
            detail="Admin access is not configured",
        )

    if current_user.email.lower() != ADMIN_EMAIL:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return current_user


# =========================================================
# QUESTIONS: ADMIN CRUD
# =========================================================

@router.post("/questions")
def create_question(
    question: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    db_question = Question(**question.model_dump())

    db.add(db_question)
    db.commit()
    db.refresh(db_question)

    return db_question


@router.get(
    "/questions",
    response_model=list[QuestionPublic],
)
def get_questions(
    subject: str | None = None,
    topic: str | None = None,
    topic_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db),
):
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail="Page must be at least 1",
        )

    query = db.query(Question)
    limit = 10

    if subject:
        query = query.filter(Question.subject == subject)

    if topic:
        query = query.filter(Question.topic == topic)

    # В модели Question нет topic_id, поэтому параметр
    # пока сохранён для совместимости, но не используется.
    if topic_id:
        pass

    if search:
        query = query.filter(
            Question.question.ilike(f"%{search}%")
        )

    offset = (page - 1) * limit

    questions = (
        query
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        QuestionPublic.model_validate(question)
        for question in questions
    ]


@router.get(
    "/questions/{question_id}",
    response_model=QuestionPublic,
)
def get_question(
    question_id: int,
    db: Session = Depends(get_db),
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    return question


@router.put("/questions/{question_id}")
def update_question(
    question_id: int,
    question_data: QuestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    for key, value in question_data.model_dump().items():
        setattr(question, key, value)

    db.commit()
    db.refresh(question)

    return question


@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    question = (
        db.query(Question)
        .filter(Question.id == question_id)
        .first()
    )

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found",
        )

    db.delete(question)
    db.commit()

    return {
        "message": "Question deleted successfully"
    }


# =========================================================
# TEST SESSION
# =========================================================

@router.post("/start-test")
def start_test(
    test_type: str = "practice",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    started_at = datetime.utcnow()
    expires_at = started_at + timedelta(minutes=240)

    session = TestSession(
        user_id=current_user.id,
        test_type=test_type,
        started_at=started_at,
        expires_at=expires_at,
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "started_at": session.started_at,
        "expires_at": session.expires_at,
        "duration_minutes": 240,
    }


# =========================================================
# SUBMIT TEST
# =========================================================

@router.post(
    "/submit-test",
    response_model=TestResult,
)
def submit_test(
    answers: list[QuestionAnswer],
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = (
        db.query(TestSession)
        .filter(
            TestSession.id == session_id,
            TestSession.user_id == current_user.id,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found",
        )

    if datetime.utcnow() > session.expires_at:
        raise HTTPException(
            status_code=400,
            detail="Test time has expired",
        )

    if not answers:
        raise HTTPException(
            status_code=400,
            detail="Answers cannot be empty",
        )

    question_ids = [
        answer.question_id
        for answer in answers
    ]

    if len(question_ids) != len(set(question_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate question IDs are not allowed",
        )

    questions = (
        db.query(Question)
        .filter(Question.id.in_(question_ids))
        .all()
    )

    questions_by_id = {
        question.id: question
        for question in questions
    }

    missing_ids = [
        question_id
        for question_id in question_ids
        if question_id not in questions_by_id
    ]

    if missing_ids:
        raise HTTPException(
            status_code=400,
            detail=f"Questions not found: {missing_ids}",
        )

    score = 0
    max_score = 0

    results = []
    question_results = []

    for answer in answers:
        question = questions_by_id[answer.question_id]

        points, question_max_score = calculate_question_score(
            question,
            answer.answer,
        )

        score += points
        max_score += question_max_score

        results.append(
            AnswerResult(
                question_id=question.id,
                user_answer=answer.answer,
                correct_answer=question.correct_answer,
                points_earned=points,
                max_points=question_max_score,
                explanation=question.explanation,
            )
        )

        question_results.append(
            {
                "question_id": question.id,
                "user_answer": answer.answer,
                "points_earned": points,
                "max_points": question_max_score,
                "subject": question.subject,
                "topic": question.topic,
            }
        )

    total_questions = len(results)

    percentage = (
        round((score / max_score) * 100, 2)
        if max_score > 0
        else 0
    )

    try:
        attempt = TestAttempt(
            user_id=current_user.id,
            score=score,
            max_score=max_score,
            total_questions=total_questions,
            percentage=percentage,
            test_type=session.test_type,
        )

        db.add(attempt)
        db.flush()

        for result in question_results:
            question_result = QuestionResult(
                attempt_id=attempt.id,
                question_id=result["question_id"],
                user_answer=result["user_answer"],
                points_earned=result["points_earned"],
                max_points=result["max_points"],
            )

            db.add(question_result)

            skill_profile = (
                db.query(SkillProfile)
                .filter(
                    SkillProfile.user_id == current_user.id,
                    SkillProfile.subject == result["subject"],
                    SkillProfile.topic == result["topic"],
                )
                .first()
            )

            if not skill_profile:
                skill_profile = SkillProfile(
                    user_id=current_user.id,
                    subject=result["subject"],
                    topic=result["topic"],
                    total_questions=0,
                    correct_questions=0,
                    total_points=0,
                    max_points=0,
                    accuracy=0,
                )

                db.add(skill_profile)

            skill_profile.total_questions += 1
            skill_profile.total_points += result["points_earned"]
            skill_profile.max_points += result["max_points"]

            if (
                result["points_earned"]
                == result["max_points"]
            ):
                skill_profile.correct_questions += 1

            skill_profile.accuracy = round(
                (
                    skill_profile.correct_questions
                    / skill_profile.total_questions
                ) * 100,
                2,
            )

        db.commit()

    except Exception:
        db.rollback()
        raise

    return TestResult(
        score=score,
        max_score=max_score,
        total_questions=total_questions,
        percentage=percentage,
        results=results,
    )


# =========================================================
# TEST ATTEMPT HISTORY
# =========================================================

@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptPublic,
)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempt = (
        db.query(TestAttempt)
        .filter(
            TestAttempt.id == attempt_id,
            TestAttempt.user_id == current_user.id,
        )
        .first()
    )

    if not attempt:
        raise HTTPException(
            status_code=404,
            detail="Attempt not found",
        )

    return attempt


# =========================================================
# PROFILE SUBJECT QUESTIONS
# =========================================================

def get_profile_questions(
    db: Session,
    subject: str,
):
    questions = []

    single = (
        db.query(Question)
        .filter(
            Question.ent_section == "profile",
            Question.subject == subject,
            Question.question_type == "single",
            Question.context_id.is_(None),
        )
        .order_by(func.random())
        .limit(25)
        .all()
    )

    context = (
        db.query(Question)
        .filter(
            Question.ent_section == "profile",
            Question.subject == subject,
            Question.question_type == "single",
            Question.context_id.isnot(None),
        )
        .order_by(func.random())
        .limit(5)
        .all()
    )

    matching = (
        db.query(Question)
        .filter(
            Question.ent_section == "profile",
            Question.subject == subject,
            Question.question_type == "matching",
        )
        .order_by(func.random())
        .limit(5)
        .all()
    )

    multiple = (
        db.query(Question)
        .filter(
            Question.ent_section == "profile",
            Question.subject == subject,
            Question.question_type == "multiple",
        )
        .order_by(func.random())
        .limit(5)
        .all()
    )

    questions.extend(single)
    questions.extend(context)
    questions.extend(matching)
    questions.extend(multiple)

    return questions


# =========================================================
# FULL ENT TEST
# =========================================================

@router.get(
    "/ent-test",
    response_model=list[QuestionPublic],
)
def get_ent_test(
    profile_subject: str,
    profile_subject_2: str,
    db: Session = Depends(get_db),
):
    questions = []

    math_literacy = (
        db.query(Question)
        .filter(
            Question.ent_section == "mathematical_literacy"
        )
        .order_by(func.random())
        .limit(10)
        .all()
    )

    reading_literacy = (
        db.query(Question)
        .filter(
            Question.ent_section == "reading_literacy"
        )
        .order_by(func.random())
        .limit(10)
        .all()
    )

    history = (
        db.query(Question)
        .filter(
            Question.ent_section == "kazakhstan_history"
        )
        .order_by(func.random())
        .limit(20)
        .all()
    )

    profile_1 = get_profile_questions(
        db,
        profile_subject,
    )

    profile_2 = get_profile_questions(
        db,
        profile_subject_2,
    )

    questions.extend(math_literacy)
    questions.extend(reading_literacy)
    questions.extend(history)
    questions.extend(profile_1)
    questions.extend(profile_2)

    if len(questions) != 120:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Not enough questions. "
                f"Only {len(questions)} available."
            ),
        )

    return questions


# =========================================================
# RANDOM PRACTICE TEST
# =========================================================

@router.get(
    "/random-test",
    response_model=list[QuestionPublic],
)
def get_random_test(
    count: int = 20,
    subject: str | None = None,
    db: Session = Depends(get_db),
):
    if count < 1 or count > 50:
        raise HTTPException(
            status_code=400,
            detail="Count must be between 1 and 50",
        )

    query = db.query(Question)

    if subject:
        query = query.filter(
            Question.subject == subject
        )

    questions = (
        query
        .order_by(func.random())
        .limit(count)
        .all()
    )

    return [
        QuestionPublic.model_validate(question)
        for question in questions
    ]