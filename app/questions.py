from fastapi import APIRouter, Depends, HTTPException
from app.schemas import AnswerResult, QuestionAnswer, QuestionCreate, TestResult
from app.models import Question, TestAttempt, User
from sqlalchemy.orm import Session
from app.database import get_db
from app.security import get_current_user


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
    search: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Question)

    if subject:
        query = query.filter(Question.subject == subject)

    if topic:
        query = query.filter(Question.topic == topic)

    if search:
        query = query.filter(Question.question.ilike(f"%{search}%"))

    return query.all()

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

@router.post("/submit-test", response_model=TestResult)
def submit_test(
    answers: list[QuestionAnswer],
    test_type: str = "practice",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    score = 0
    total = len(answers)
    results = []

    for answer in answers:
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        if question and question.correct_answer == answer.answer:
            score += 1

        results.append(
    AnswerResult(
        question_id=answer.question_id,
        user_answer=answer.answer,
        correct_answer=question.correct_answer if question else "",
        correct=question.correct_answer == answer.answer if question else False,
        explanation=question.explanation if question else ""
    )
)
        percentage = round((score / total) * 100, 2) if total > 0 else 0
        attempt = TestAttempt(
    user_id=current_user.id,
    score=score,
    total=total,
    percentage=percentage,
    test_type=test_type
)
    db.add(attempt)
    db.commit()

    return TestResult(
    score=score,
    total=total,
    percentage=percentage,
    results=results
)

@router.get("/attempts")
def get_attempts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(TestAttempt)
        .filter(TestAttempt.user_id == current_user.id)
        .all()
    )