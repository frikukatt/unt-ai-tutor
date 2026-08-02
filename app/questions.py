from fastapi import APIRouter, Depends
import app
from app.schemas import QuestionCreate
from app.models import Question
from sqlalchemy.orm import Session
from app.database import get_db
from fastapi import HTTPException


router = APIRouter()

@router.post("/questions")
def create_question(question: QuestionCreate, db: Session = Depends(get_db)):
    db_question = Question(**question.dict())
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

@router.get("/questions")
def get_questions(
    subject: str | None = None,
    topic: str | None = None,
    db: Session = Depends(get_db)
):
    query = db.query(Question)

    if subject:
        query = query.filter(Question.subject == subject)

    if topic:
        query = query.filter(Question.topic == topic)

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
