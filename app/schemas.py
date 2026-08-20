from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr

class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class QuestionCreate(BaseModel):
    subject: str
    topic: str
    ent_section: str

    question_type: str = "single"
    context_id: int | None = None

    question: str

    option_a: str
    option_b: str
    option_c: str
    option_d: str
    option_e: str | None = None
    option_f: str | None = None

    correct_answer: str
    explanation: str

class QuestionPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    topic: str
    ent_section: str
    
    question_type: str
    context_id: int | None

    question: str

    option_a: str
    option_b: str
    option_c: str
    option_d: str
    
    option_e: str | None = None
    option_f: str | None = None


class QuestionAnswer(BaseModel):
    question_id: int
    answer: str


class AnswerResult(BaseModel):
    question_id: int
    user_answer: str
    correct_answer: str
    points_earned: int
    max_points: int
    explanation: str


class TestResult(BaseModel):
    score: int
    max_score: int
    total_questions: int
    percentage: float
    results: list[AnswerResult]


class ContextCreate(BaseModel):
    subject: str
    title: str
    content: str


class ContextPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    title: str
    content: str


class TopicCreate(BaseModel):
    name: str
    subject: str


class TopicResponse(BaseModel):
    id: int
    name: str
    subject: str

    model_config = {
        "from_attributes": True
    }


class TestContextCreate(BaseModel):
    subject: str
    title: str
    content: str


class TestContextPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    title: str
    content: str


class AttemptPublic(BaseModel):
    id: int
    score: int
    max_score: int
    total_questions: int
    percentage: float
    test_type: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)