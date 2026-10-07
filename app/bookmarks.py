from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Question, BookmarkedQuestion, User
from app.security import get_current_user

router = APIRouter()


@router.post("/questions/{question_id}/bookmark")
def bookmark_question(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question = db.query(Question).filter(
        Question.id == question_id
    ).first()

    if not question:
        raise HTTPException(
            status_code=404,
            detail="Question not found"
        )

    existing = (
        db.query(BookmarkedQuestion)
        .filter(
            BookmarkedQuestion.user_id == current_user.id,
            BookmarkedQuestion.question_id == question_id
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Question already bookmarked"
        )

    bookmark = BookmarkedQuestion(
        user_id=current_user.id,
        question_id=question_id
    )

    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)

    return {
        "message": "Question bookmarked",
        "question_id": question_id
    }


@router.delete("/questions/{question_id}/bookmark")
def remove_bookmark(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookmark = (
        db.query(BookmarkedQuestion)
        .filter(
            BookmarkedQuestion.user_id == current_user.id,
            BookmarkedQuestion.question_id == question_id
        )
        .first()
    )

    if not bookmark:
        raise HTTPException(
            status_code=404,
            detail="Question is not bookmarked"
        )

    db.delete(bookmark)
    db.commit()

    return {
        "message": "Question removed from bookmarks",
        "question_id": question_id
    }


@router.get("/bookmarks")
def get_bookmarks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    bookmarks = (
        db.query(BookmarkedQuestion)
        .filter(BookmarkedQuestion.user_id == current_user.id)
        .all()
    )

    questions = []

    for bookmark in bookmarks:
        question = (
            db.query(Question)
            .filter(Question.id == bookmark.question_id)
            .first()
        )

        if question:
            questions.append({
                "id": question.id,
                "subject": question.subject,
                "topic": question.topic,
                "question": question.question,
                "option_a": question.option_a,
                "option_b": question.option_b,
                "option_c": question.option_c,
                "option_d": question.option_d,
            })

    return {
        "count": len(questions),
        "questions": questions
    }