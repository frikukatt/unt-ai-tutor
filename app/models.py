from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text
from datetime import datetime


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)


class TestContext(Base):
    __tablename__ = "test_contexts"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)

    subject = Column(String, nullable=False)
    name = Column(String, nullable=False)


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)

    subject = Column(String, nullable=False)
    topic = Column(String, nullable=False)
    ent_section = Column(String, nullable=False)

    question_type = Column(
        String,
        nullable=False,
        default="single"
    )

    context_id = Column(
        Integer,
        ForeignKey("test_contexts.id"),
        nullable=True
    )

    question = Column(String, nullable=False)

    # Обычные варианты ответа
    option_a = Column(String, nullable=False)
    option_b = Column(String, nullable=False)
    option_c = Column(String, nullable=False)
    option_d = Column(String, nullable=False)
    option_e = Column(String, nullable=True)
    option_f = Column(String, nullable=True)

    matching_a = Column(String, nullable=True)
    matching_b = Column(String, nullable=True)

    matching_1 = Column(String, nullable=True)
    matching_2 = Column(String, nullable=True)
    matching_3 = Column(String, nullable=True)
    matching_4 = Column(String, nullable=True)

    correct_answer = Column(String, nullable=False)

    explanation = Column(String, nullable=False)


class TestAttempt(Base):
    __tablename__ = "test_attempts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"))

    score = Column(Integer, nullable=False)

    max_score = Column(Integer, nullable=False)

    total_questions = Column(Integer, nullable=False)

    percentage = Column(Float, nullable=False)

    test_type = Column(
        String,
        nullable=False,
        default="practice"
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    test_type = Column(
        String,
        nullable=False,
        default="practice"
    )

    started_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    expires_at = Column(
        DateTime,
        nullable=False
    )


class BookmarkedQuestion(Base):
    __tablename__ = "bookmarked_questions"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        nullable=False
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class QuestionResult(Base):
    __tablename__ = "question_results"

    id = Column(Integer, primary_key=True, index=True)

    attempt_id = Column(
        Integer,
        ForeignKey("test_attempts.id"),
        nullable=False
    )

    question_id = Column(
        Integer,
        ForeignKey("questions.id"),
        nullable=False
    )

    user_answer = Column(String, nullable=False)

    points_earned = Column(Integer, nullable=False)

    max_points = Column(Integer, nullable=False)

    created_at = Column(
        DateTime,
        default=datetime.utcnow
    )


class SkillProfile(Base):
    __tablename__ = "skill_profiles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    subject = Column(
        String,
        nullable=False
    )

    topic = Column(
        String,
        nullable=False
    )

    total_questions = Column(
        Integer,
        nullable=False,
        default=0
    )

    correct_questions = Column(
        Integer,
        nullable=False,
        default=0
    )

    total_points = Column(
        Integer,
        nullable=False,
        default=0
    )

    max_points = Column(
        Integer,
        nullable=False,
        default=0
    )

    accuracy = Column(
        Float,
        nullable=False,
        default=0
    )