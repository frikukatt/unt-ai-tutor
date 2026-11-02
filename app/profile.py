from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    User,
    TestAttempt,
    SkillProfile,
)
from app.security import get_current_user


router = APIRouter()


@router.get("/profile")
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attempts = (
        db.query(TestAttempt)
        .filter(
            TestAttempt.user_id == current_user.id,
            TestAttempt.test_type.in_(["mock", "ent_full"]),
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
            "last_score": "0/140",
        }

    best = max(
        attempts,
        key=lambda attempt: attempt.percentage,
    )

    average_score = round(
        sum(attempt.score for attempt in attempts)
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
        ),
    }


@router.get("/profile/skills")
def get_skill_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    skill_profiles = (
        db.query(SkillProfile)
        .filter(
            SkillProfile.user_id == current_user.id
        )
        .order_by(
            SkillProfile.accuracy.asc(),
            SkillProfile.subject.asc(),
            SkillProfile.topic.asc(),
        )
        .all()
    )

    skills = []

    for skill in skill_profiles:
        point_accuracy = (
            round(
                skill.total_points / skill.max_points * 100,
                2,
            )
            if skill.max_points > 0
            else 0
        )

        full_correct_rate = (
            round(
                skill.correct_questions
                / skill.total_questions * 100,
                2,
            )
            if skill.total_questions > 0
            else 0
        )

        skills.append({
            "id": skill.id,
            "subject": skill.subject,
            "topic": skill.topic,
            "total_questions": skill.total_questions,
            "correct_questions": skill.correct_questions,
            "total_points": skill.total_points,
            "max_points": skill.max_points,
            "accuracy": point_accuracy,
            "point_accuracy": point_accuracy,
            "full_correct_rate": full_correct_rate,
        })

    return {
        "skills": skills
    }


@router.get("/profile/weak-topics")
def get_weak_topics(
    min_questions: int = 3,
    max_accuracy: float = 70.0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    point_accuracy = (
        SkillProfile.total_points * 100.0
        / SkillProfile.max_points
    )

    skill_profiles = (
        db.query(SkillProfile)
        .filter(
            SkillProfile.user_id == current_user.id,
            SkillProfile.total_questions >= min_questions,
            SkillProfile.max_points > 0,
            point_accuracy <= max_accuracy,
        )
        .order_by(
            point_accuracy.asc()
        )
        .all()
    )

    weak_topics = []

    for skill in skill_profiles:
        point_accuracy_value = (
            round(
                skill.total_points / skill.max_points * 100,
                2,
            )
            if skill.max_points > 0
            else 0
        )

        full_correct_rate = (
            round(
                skill.correct_questions
                / skill.total_questions * 100,
                2,
            )
            if skill.total_questions > 0
            else 0
        )

        weak_topics.append({
            "id": skill.id,
            "subject": skill.subject,
            "topic": skill.topic,
            "total_questions": skill.total_questions,
            "correct_questions": skill.correct_questions,
            "total_points": skill.total_points,
            "max_points": skill.max_points,
            "accuracy": point_accuracy_value,
            "point_accuracy": point_accuracy_value,
            "full_correct_rate": full_correct_rate,
        })

    return {
        "weak_topics": weak_topics,
        "criteria": {
            "min_questions": min_questions,
            "max_accuracy": max_accuracy,
            "accuracy_type": "point_accuracy",
        },
    }