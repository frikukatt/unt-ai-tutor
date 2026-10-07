from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    TestAttempt,
    SkillProfile
)
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

    best = max(
        attempts,
        key=lambda x: x.percentage
    )

    average_score = round(
        sum(a.score for a in attempts)
        / len(attempts)
    )

    return {
        "username": current_user.username,
        "tests_completed": len(attempts),
        "best_score": (
            f"{best.score}/{best.max_score}"
        ),
        "average_score": (
            f"{average_score}/140"
        ),
        "last_score": (
            f"{attempts[0].score}/{attempts[0].max_score}"
        )
    }


@router.get("/profile/skills")
def get_skill_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill_profiles = (
        db.query(SkillProfile)
        .filter(
            SkillProfile.user_id == current_user.id
        )
        .order_by(
            SkillProfile.accuracy.asc(),
            SkillProfile.subject.asc(),
            SkillProfile.topic.asc()
        )
        .all()
    )

    skills = []

    for skill in skill_profiles:
        skills.append(
            {
                "id": skill.id,
                "subject": skill.subject,
                "topic": skill.topic,
                "total_questions": skill.total_questions,
                "correct_questions": skill.correct_questions,
                "total_points": skill.total_points,
                "max_points": skill.max_points,
                "accuracy": skill.accuracy
            }
        )

    return {
        "skills": skills
    }


@router.get("/profile/weak-topics")
def get_weak_topics(
    min_questions: int = 3,
    max_accuracy: float = 70.0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    skill_profiles = (
        db.query(SkillProfile)
        .filter(
            SkillProfile.user_id == current_user.id,
            SkillProfile.total_questions >= min_questions,
            SkillProfile.accuracy <= max_accuracy
        )
        .order_by(
            SkillProfile.accuracy.asc()
        )
        .all()
    )

    weak_topics = []

    for skill in skill_profiles:
        weak_topics.append(
            {
                "id": skill.id,
                "subject": skill.subject,
                "topic": skill.topic,
                "total_questions": skill.total_questions,
                "correct_questions": skill.correct_questions,
                "accuracy": skill.accuracy
            }
        )

    return {
        "weak_topics": weak_topics,
        "criteria": {
            "min_questions": min_questions,
            "max_accuracy": max_accuracy
        }
    }