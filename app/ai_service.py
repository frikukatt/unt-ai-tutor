import os

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise RuntimeError(
        "OPENAI_API_KEY is not configured"
    )

client = OpenAI(api_key=api_key)


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