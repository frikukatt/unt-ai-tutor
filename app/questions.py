from fastapi import APIRouter, Depends
import app
from app.schemas import QuestionCreate
from app.models import Question
from sqlalchemy.orm import Session
from app.database import get_db


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
