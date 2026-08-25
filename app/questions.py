from fastapi import APIRouter, Depends, HTTPException
from app.schemas import AnswerResult, QuestionAnswer, QuestionCreate, TestResult, QuestionPublic, AttemptPublic
from app.models import Question, TestAttempt, User, TestSession, QuestionResult
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.security import get_current_user
from datetime import datetime, timedelta
from app.scoring import calculate_question_score

router = APIRouter()

@router.post("/questions")
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    db_question = Question(**question.model_dump())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

@router.get("/questions")
def get_questions(
    subject: str | None = None,
    topic: str | None = None,
    topic_id: int | None = None,
    search: str | None = None,
    page: int = 1,
    db: Session = Depends(get_db)
):
    query = db.query(Question)
    limit = 10

    if subject:
        query = query.filter(Question.subject == subject)

    if topic:
        query = query.filter(Question.topic == topic)

    if topic_id:
        query = query.filter(Question.topic_id == topic_id)

    if search:
        query = query.filter(
            Question.question.ilike(f"%{search}%")
        )

    offset = (page - 1) * limit

    return query.offset(offset).limit(limit).all()

@router.get("/questions/{question_id}")
def get_question(question_id: int, db: Session = Depends(get_db)):
    question = db.query(Question).filter(Question.id == question_id).first()

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )
    return question

@router.put("/questions/{question_id}")
def update_question(
    question_id: int,
    question_data: QuestionCreate,
    db: Session = Depends(get_db)
):
    question = db.query(Question).filter(Question.id == question_id).first()

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )
    for key, value in question_data.model_dump().items():
        setattr(question, key, value)

    db.commit()
    db.refresh(question)
    return question

@router.delete("/questions/{question_id}")
def delete_question(
    question_id: int,
    db: Session = Depends(get_db)
):
    question = db.query(Question).filter(Question.id == question_id).first()

    if question is None:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    db.delete(question)
    db.commit()
    return {"message": "Question deleted successfully"}

@router.post("/start-test")
def start_test(
    test_type: str = "practice",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    started_at = datetime.utcnow()
    expires_at = started_at + timedelta(minutes=240)

    session = TestSession(
        user_id=current_user.id,
        test_type=test_type,
        started_at=started_at,
        expires_at=expires_at
    )

    db.add(session)
    db.commit()
    db.refresh(session)

    return {
        "session_id": session.id,
        "started_at": session.started_at,
        "expires_at": session.expires_at,
        "duration_minutes": 240
    }

@router.post("/submit-test", response_model=TestResult)
def submit_test(
    answers: list[QuestionAnswer],
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    session = (
        db.query(TestSession)
        .filter(
            TestSession.id == session_id,
            TestSession.user_id == current_user.id
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=404,
            detail="Test session not found"
        )

    if datetime.utcnow() > session.expires_at:
        raise HTTPException(
            status_code=400,
            detail="Test time has expired"
        )

    score = 0
    max_score = 0

    results = []

    question_results = []

    for answer in answers:

        question = (
            db.query(Question)
            .filter(
                Question.id == answer.question_id
            )
            .first()
        )

        if not question:
            continue

        points, question_max_score = (
            calculate_question_score(
                question,
                answer.answer
            )
        )

        score += points
        max_score += question_max_score

        results.append(
            AnswerResult(
                question_id=answer.question_id,
                user_answer=answer.answer,
                correct_answer=question.correct_answer,
                points_earned=points,
                max_points=question_max_score,
                explanation=question.explanation
            )
        )

        question_results.append(
            {
                "question_id": question.id,
                "user_answer": answer.answer,
                "points_earned": points,
                "max_points": question_max_score
            }
        )

    total_questions = len(results)

    percentage = (
        round(
            (score / max_score) * 100,
            2
        )
        if max_score > 0
        else 0
    )

    attempt = TestAttempt(
        user_id=current_user.id,
        score=score,
        max_score=max_score,
        total_questions=total_questions,
        percentage=percentage,

        test_type=session.test_type
    )

    db.add(attempt)

    db.flush()

    for result in question_results:

        question_result = QuestionResult(
            attempt_id=attempt.id,
            question_id=result["question_id"],
            user_answer=result["user_answer"],
            points_earned=result["points_earned"],
            max_points=result["max_points"]
        )

        db.add(question_result)

    db.commit()

    return TestResult(
        score=score,
        max_score=max_score,
        total_questions=total_questions,
        percentage=percentage,
        results=results
    )

@router.get(
    "/attempts/{attempt_id}",
    response_model=AttemptPublic
)
def get_attempt(
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
            detail="Attempt not found"
        )

    return attempt


def get_profile_questions(
    db: Session,
    subject: str
):
    questions = []

    single = (
        db.query(Question)
        .filter(
            Question.ent_section == "profile",
            Question.subject == subject,
            Question.question_type == "single",
            Question.context_id.is_(None)
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
        Question.context_id.isnot(None)
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
            Question.question_type == "matching"
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
            Question.question_type == "multiple"
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


@router.get("/ent-test", response_model=list[QuestionPublic])
def get_ent_test(
    profile_subject: str,
    profile_subject_2: str,
    db: Session = Depends(get_db)
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
    profile_subject
)

    profile_2 = get_profile_questions(
    db,
    profile_subject_2
)

    questions.extend(math_literacy)
    questions.extend(reading_literacy)
    questions.extend(history)
    questions.extend(profile_1)
    questions.extend(profile_2)

    if len(questions) != 120:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough questions. Only {len(questions)} available."
        )

    return questions

@router.get("/random-test", response_model=list[QuestionPublic])
def get_random_test(
    count: int = 20,
    subject: str | None = None,
    db: Session = Depends(get_db)
):
    if count < 1 or count > 50:
        raise HTTPException(
            status_code=400,
            detail="Count must be between 1 and 50"
        )

    query = db.query(Question)

    if subject:
        query = query.filter(Question.subject == subject)

    return [QuestionPublic.model_validate(question) for question in query.order_by(func.random()).limit(count).all()]