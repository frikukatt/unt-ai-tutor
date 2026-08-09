from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, TestAttempt
from app.security import get_current_user

router = APIRouter()


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    attempts = (
        db.query(TestAttempt)
        .filter(
            TestAttempt.user_id == current_user.id,
            TestAttempt.test_type == "mock"
        )
        .order_by(TestAttempt.id.desc())
        .all()
    )

    if not attempts:
        return {
            "username": current_user.username,
            "tests_completed": 0,
            "best_score": "0/140",
            "average_score": "0/140",
            "last_score": "0/140"
        }

    best = max(attempts, key=lambda x: x.percentage)
    average_score = round(
        sum(a.score for a in attempts) / len(attempts)
    )

    return {
        "username": current_user.username,
        "tests_completed": len(attempts),
        "best_score": f"{best.score}/{best.total}",
        "average_score": f"{average_score}/140",
        "last_score": f"{attempts[0].score}/{attempts[0].total}"
    }