from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, TestAttempt, Question, QuestionResult, SkillProfile 
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


@router.get("/profile/skills")
def get_skill_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    question_results = (
        db.query(
            QuestionResult,
            Question.subject,
            Question.topic
        )
        .join(
            Question,
            Question.id == QuestionResult.question_id
        )
        .join(
            TestAttempt,
            TestAttempt.id == QuestionResult.attempt_id
        )
        .filter(
            TestAttempt.user_id == current_user.id
        )
        .all()
    )

    skills = {}

    for result, subject, topic in question_results:

        key = (subject, topic)

        if key not in skills:
            skills[key] = {
                "subject": subject,
                "topic": topic,
                "total_questions": 0,
                "correct_questions": 0,
                "total_points": 0,
                "max_points": 0
            }

        skills[key]["total_questions"] += 1

        skills[key]["total_points"] += (
            result.points_earned
        )

        skills[key]["max_points"] += (
            result.max_points
        )

        # Вопрос считается полностью правильным,
        # если ученик получил за него максимум баллов.
        if (
            result.points_earned
            == result.max_points
        ):
            skills[key]["correct_questions"] += 1

    skill_profiles = []

    for data in skills.values():

        if data["max_points"] > 0:
            accuracy = round(
                (
                    data["total_points"]
                    / data["max_points"]
                ) * 100,
                2
            )
        else:
            accuracy = 0

        skill_profiles.append(
            {
                **data,
                "accuracy": accuracy
            }
        )

    skill_profiles.sort(
        key=lambda x: x["accuracy"]
    )

    return {
        "skills": skill_profiles
    }