import os

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not configured"
    )

client = OpenAI(api_key=api_key)


class TopicRecommendation(BaseModel):
    subject: str
    topic: str
    accuracy: float
    weakness_reason: str
    action_plan: str


class ENTAnalysisResult(BaseModel):
    summary: str
    strengths: list[str]
    weak_topics: list[TopicRecommendation]
    next_steps: list[str]


def analyze_ent_results(student_data: str) -> ENTAnalysisResult:
    instructions = """
Ты — AI-методист по подготовке школьников к ЕНТ в Казахстане.

Проанализируй результаты ученика и дай персональные рекомендации.

Твои задачи:
1. Определить общую картину результатов.
2. Найти сильные стороны ученика.
3. Найти наиболее слабые темы.
4. Объяснить возможные причины слабых результатов.
5. Дать конкретные следующие шаги для подготовки.

Правила:
- Отвечай на русском языке.
- Обращайся к ученику на "ты".
- Используй только предоставленные данные.
- Не придумывай вопросы, ответы или результаты.
- Не называй тему слабой, если данных недостаточно.
- Приоритет отдавай темам с низкой точностью и достаточным количеством вопросов.
- Не давай бессмысленных советов вроде "просто больше учись".
- Рекомендации должны быть конкретными.
- Для математики и математической грамотности используй Markdown/LaTeX для формул, когда это необходимо.
- Для истории учитывай хронологию и причинно-следственные связи.
- Для грамотности чтения учитывай понимание текста, главной мысли и логики автора.
- Учитывай разные типы заданий ЕНТ.
"""

    response = client.responses.parse(
        model="gpt-5.6-luna",
        instructions=instructions,
        input=student_data,
        text_format=ENTAnalysisResult,
    )

    return response.output_parsed


def explain_answer(
    question: str,
    user_answer: str,
    correct_answer: str,
    subject: str,
    topic: str
) -> str:

    instructions = """
Ты — AI-репетитор для подготовки школьников к ЕНТ.

Твоя задача — объяснять ошибки ученика простым,
понятным и образовательным языком.

Правила:
- отвечай на русском языке;
- обращайся к ученику на "ты";
- объясни, где именно ошибка;
- объясни правильное решение;
- покажи ход рассуждения;
- не придумывай отсутствующие условия;
- используй только информацию из вопроса и ответов;
- в конце дай короткий совет, как избежать такой ошибки
  в будущем.
"""

    prompt = f"""
Предмет: {subject}

Тема: {topic}

Вопрос:
{question}

Ответ ученика:
{user_answer}

Правильный ответ:
{correct_answer}

Проанализируй ответ ученика и объясни его ошибку.
"""

    response = client.responses.create(
        model="gpt-5.6-luna",
        instructions=instructions,
        input=prompt
    )

    return response.output_text