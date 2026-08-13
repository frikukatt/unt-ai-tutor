from pydantic import BaseModel, EmailStr

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
    topic_id: int | None = None
    question: str
    option_a: str
    option_b: str
    option_c: str
    option_d: str
    correct_answer: str
    explanation: str


class QuestionAnswer(BaseModel):
    question_id: int
    answer: str


class AnswerResult(BaseModel):
    question_id: int
    user_answer: str
    correct_answer: str
    correct: bool
    explanation: str


class TestResult(BaseModel):
    score: int
    total: int
    percentage: float
    results: list[AnswerResult]


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