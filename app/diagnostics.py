
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import (
    Question,
    QuestionResult,
    TestAttempt,
)


def calculate_accuracy(points: int, max_points: int) -> float:
    if max_points <= 0:
        return 0.0

    return round(points / max_points * 100, 2)


def get_answer_status(
    points_earned: int,
    max_points: int,
) -> str:
    if points_earned >= max_points:
        return "correct"

    if points_earned > 0:
        return "partial"

    return "incorrect"


def build_attempt_diagnostics(
    db: Session,
    user_id: int,
    attempt_id: int,
) -> dict:
    """
    Builds deterministic diagnostic data for one test attempt.

    This module does not guess why a student made a mistake.
    It collects measurable evidence for later AI interpretation.
    """

    attempt = (
        db.query(TestAttempt)
        .filter(
            TestAttempt.id == attempt_id,
            TestAttempt.user_id == user_id,
        )
        .first()
    )

    if attempt is None:
        raise ValueError("Attempt not found")

    current_rows = (
        db.query(QuestionResult, Question)
        .join(
            Question,
            Question.id == QuestionResult.question_id,
        )
        .filter(
            QuestionResult.attempt_id == attempt_id,
        )
        .all()
    )

    question_details = []

    topic_stats = defaultdict(
        lambda: {
            "subject": "",
            "topic": "",
            "questions": 0,
            "correct": 0,
            "partial": 0,
            "incorrect": 0,
            "points": 0,
            "max_points": 0,
        }
    )

    type_stats = defaultdict(
        lambda: {
            "questions": 0,
            "points": 0,
            "max_points": 0,
        }
    )

    for result, question in current_rows:
        status = get_answer_status(
            result.points_earned,
            result.max_points,
        )

        question_details.append({
            "question_id": question.id,
            "subject": question.subject,
            "topic": question.topic,
            "section": question.ent_section,
            "question_type": question.question_type,
            "points_earned": result.points_earned,
            "max_points": result.max_points,
            "status": status,
        })

        topic_key = (
            question.subject,
            question.topic,
        )

        topic = topic_stats[topic_key]
        topic["subject"] = question.subject
        topic["topic"] = question.topic
        topic["questions"] += 1
        topic["points"] += result.points_earned
        topic["max_points"] += result.max_points

        if status == "correct":
            topic["correct"] += 1
        elif status == "partial":
            topic["partial"] += 1
        else:
            topic["incorrect"] += 1

        type_key = (
            question.subject,
            question.question_type,
        )

        question_type = type_stats[type_key]
        question_type["questions"] += 1
        question_type["points"] += result.points_earned
        question_type["max_points"] += result.max_points

    topics = []

    for topic in topic_stats.values():
        topics.append({
            **topic,
            "accuracy": calculate_accuracy(
                topic["points"],
                topic["max_points"],
            ),
        })

    question_types = []

    for (subject, question_type), stats in type_stats.items():
        question_types.append({
            "subject": subject,
            "question_type": question_type,
            "questions": stats["questions"],
            "points": stats["points"],
            "max_points": stats["max_points"],
            "accuracy": calculate_accuracy(
                stats["points"],
                stats["max_points"],
            ),
        })

    # Collect previous full mock attempts from the same user.
    previous_rows = (
        db.query(
            QuestionResult,
            Question,
            TestAttempt,
        )
        .join(
            TestAttempt,
            TestAttempt.id == QuestionResult.attempt_id,
        )
        .join(
            Question,
            Question.id == QuestionResult.question_id,
        )
        .filter(
            TestAttempt.user_id == user_id,
            TestAttempt.id != attempt_id,
            TestAttempt.test_type.in_([
                "mock",
                "ent_full",
            ]),
        )
        .all()
    )

    historical_topics = defaultdict(
        lambda: {
            "subject": "",
            "topic": "",
            "questions": 0,
            "points": 0,
            "max_points": 0,
        }
    )

    historical_types = defaultdict(
        lambda: {
            "subject": "",
            "question_type": "",
            "questions": 0,
            "points": 0,
            "max_points": 0,
        }
    )

    for result, question, previous_attempt in previous_rows:
        topic_key = (
            question.subject,
            question.topic,
        )

        topic = historical_topics[topic_key]
        topic["subject"] = question.subject
        topic["topic"] = question.topic
        topic["questions"] += 1
        topic["points"] += result.points_earned
        topic["max_points"] += result.max_points

        type_key = (
            question.subject,
            question.question_type,
        )

        question_type = historical_types[type_key]
        question_type["subject"] = question.subject
        question_type["question_type"] = question.question_type
        question_type["questions"] += 1
        question_type["points"] += result.points_earned
        question_type["max_points"] += result.max_points

    historical_topic_results = []

    for topic in historical_topics.values():
        historical_topic_results.append({
            **topic,
            "accuracy": calculate_accuracy(
                topic["points"],
                topic["max_points"],
            ),
        })

    historical_type_results = []

    for stats in historical_types.values():
        historical_type_results.append({
            **stats,
            "accuracy": calculate_accuracy(
                stats["points"],
                stats["max_points"],
            ),
        })

    # Generate evidence-based signals.
    signals = []

    for current_topic in topics:
        matching_history = next(
            (
                item
                for item in historical_topic_results
                if (
                    item["subject"] == current_topic["subject"]
                    and item["topic"] == current_topic["topic"]
                )
            ),
            None,
        )

        if matching_history is None:
            signals.append({
                "type": "insufficient_history",
                "subject": current_topic["subject"],
                "topic": current_topic["topic"],
                "message": (
                    "There is not enough previous data "
                    "to determine whether this is a recurring weakness."
                ),
                "confidence": "low",
            })
            continue

        if (
            matching_history["questions"] >= 5
            and matching_history["accuracy"] <= 70
            and current_topic["accuracy"] <= 70
        ):
            signals.append({
                "type": "recurring_topic_weakness",
                "subject": current_topic["subject"],
                "topic": current_topic["topic"],
                "current_accuracy": current_topic["accuracy"],
                "historical_accuracy": matching_history["accuracy"],
                "historical_questions": matching_history["questions"],
                "message": (
                    "Low performance in this topic appears "
                    "in multiple test attempts."
                ),
                "confidence": (
                    "high"
                    if matching_history["questions"] >= 10
                    else "medium"
                ),
            })

    for current_type in question_types:
        matching_history = next(
            (
                item
                for item in historical_type_results
                if (
                    item["subject"] == current_type["subject"]
                    and item["question_type"]
                    == current_type["question_type"]
                )
            ),
            None,
        )

        if (
            matching_history
            and matching_history["questions"] >= 5
            and matching_history["accuracy"] <= 65
        ):
            signals.append({
                "type": "question_type_pattern",
                "subject": current_type["subject"],
                "question_type": current_type["question_type"],
                "historical_accuracy": matching_history["accuracy"],
                "historical_questions": matching_history["questions"],
                "message": (
                    "Performance in this question format "
                    "has been consistently low."
                ),
                "confidence": (
                    "high"
                    if matching_history["questions"] >= 10
                    else "medium"
                ),
            })

    return {
        "attempt": {
            "id": attempt.id,
            "test_type": attempt.test_type,
            "score": attempt.score,
            "max_score": attempt.max_score,
            "percentage": attempt.percentage,
            "total_questions": attempt.total_questions,
        },
        "questions": question_details,
        "topic_performance": topics,
        "question_type_performance": question_types,
        "historical_topic_performance": historical_topic_results,
        "historical_question_type_performance": historical_type_results,
        "diagnostic_signals": signals,
        "diagnostic_notes": [
            "A wrong answer alone does not prove a knowledge gap.",
            "A single attempt is insufficient to confirm a recurring weakness.",
            "Time management and answer changes are not measured yet.",
            "Diagnostic signals describe patterns, not certain psychological causes.",
        ],
    }