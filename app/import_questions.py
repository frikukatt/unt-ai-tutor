
import argparse
import json

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Question, TestContext


ALLOWED_TYPES = {"single", "multiple", "matching"}

REQUIRED_FIELDS = {
    "subject",
    "topic",
    "ent_section",
    "question",
    "correct_answer",
    "explanation",
}

QUESTION_FIELDS = {
    "subject",
    "topic",
    "ent_section",
    "question_type",
    "context_id",
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "option_e",
    "option_f",
    "matching_a",
    "matching_b",
    "matching_1",
    "matching_2",
    "matching_3",
    "matching_4",
    "correct_answer",
    "explanation",
}

OPTION_FIELDS = (
    "option_a",
    "option_b",
    "option_c",
    "option_d",
)


def validate_question(item, index):
    errors = []

    if not isinstance(item, dict):
        return [f"Вопрос #{index} должен быть JSON-объектом"]

    for field in REQUIRED_FIELDS:
        value = item.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"Вопрос #{index}: заполните поле {field}")

    question_type = item.get("question_type", "single")

    if question_type not in ALLOWED_TYPES:
        errors.append(
            f"Вопрос #{index}: неподдерживаемый тип {question_type}"
        )
        return errors

    if question_type in {"single", "multiple"}:
        for field in OPTION_FIELDS:
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"Для {question_type} заполните {field}")

        answer = item.get("correct_answer", "")
        valid_keys = {"A", "B", "C", "D", "E", "F"}
        answers = [part.strip().upper() for part in answer.split(",")]

        if not answers or any(part not in valid_keys for part in answers):
            errors.append(
                f"Вопрос #{index}: некорректный correct_answer"
            )
        elif len(set(answers)) != len(answers):
            errors.append(
                f"Вопрос #{index}: повторяющиеся варианты ответа"
            )
        elif question_type == "single" and len(answers) != 1:
            errors.append(
                f"Вопрос #{index}: single должен иметь один правильный ответ"
            )
        elif question_type == "multiple" and len(answers) < 2:
            errors.append(
                f"Вопрос #{index}: multiple должен иметь минимум два ответа"
            )

    if question_type == "matching":
        for field in (
            "matching_a",
            "matching_b",
            "matching_1",
            "matching_2",
            "matching_3",
            "matching_4",
        ):
            if not isinstance(item.get(field), str) or not item[field].strip():
                errors.append(f"Для matching заполните {field}")

    context_title = item.get("context_title")
    context_text = item.get("context_text")

    if bool(context_title) != bool(context_text):
        errors.append(
            f"Вопрос #{index}: context_title и context_text "
            "должны быть заполнены вместе"
        )

    return errors


def find_existing(db: Session, item):
    return (
        db.query(Question)
        .filter(
            Question.subject == item["subject"].strip(),
            Question.topic == item["topic"].strip(),
            Question.question == item["question"].strip(),
        )
        .first()
    )


def get_or_create_context(db: Session, item):
    title = item.get("context_title")
    content = item.get("context_text")

    if not title or not content:
        return item.get("context_id")

    title = title.strip()
    content = content.strip()
    subject = item["subject"].strip()

    context = (
        db.query(TestContext)
        .filter(
            TestContext.subject == subject,
            TestContext.title == title,
            TestContext.content == content,
        )
        .first()
    )

    if context is None:
        context = TestContext(
            subject=subject,
            title=title,
            content=content,
        )
        db.add(context)
        db.flush()

    return context.id


def prepare_fields(item, context_id):
    fields = {
        key: value
        for key, value in item.items()
        if key in QUESTION_FIELDS
    }

    fields["context_id"] = context_id
    fields.setdefault("question_type", "single")

    for key, value in fields.items():
        if isinstance(value, str):
            fields[key] = value.strip()

    # SQLite требует непустое или хотя бы не-NULL значение
    # для option_a, option_b, option_c и option_d.
    if fields["question_type"] == "matching":
        for key in OPTION_FIELDS:
            if not fields.get(key):
                fields[key] = ""

    return fields


def main():
    parser = argparse.ArgumentParser(
        description="Импорт и обновление вопросов ЕНТ из JSON"
    )
    parser.add_argument("file", help="Путь к JSON-файлу")
    args = parser.parse_args()

    try:
        with open(args.file, "r", encoding="utf-8-sig") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Не удалось прочитать JSON: {exc}")
        return 1

    if not isinstance(data, list):
        print("Корневое содержимое JSON должно быть списком вопросов.")
        return 1

    db = SessionLocal()
    added = 0
    updated = 0
    rejected = 0

    try:
        for index, item in enumerate(data, start=1):
            errors = validate_question(item, index)

            if errors:
                rejected += 1
                for error in errors:
                    print(f"[ОШИБКА] {error}")
                continue

            existing = find_existing(db, item)
            context_id = get_or_create_context(db, item)
            fields = prepare_fields(item, context_id)

            if existing is not None:
                for key, value in fields.items():
                    setattr(existing, key, value)

                updated += 1
                print(f"[ОБНОВЛЕНО] Вопрос #{index}")

            else:
                db.add(Question(**fields))
                added += 1
                print(f"[ДОБАВЛЕНО] Вопрос #{index}")

        if rejected:
            db.rollback()
            print(
                f"\nИмпорт отменён: найдено ошибок в вопросах: {rejected}. "
                "Изменения не сохранены."
            )
            return 2

        db.commit()

    except Exception as exc:
        db.rollback()
        print(f"Импорт отменён из-за ошибки: {exc}")
        return 1

    finally:
        db.close()

    print("\n--- Результат импорта ---")
    print(f"Добавлено: {added}")
    print(f"Обновлено: {updated}")
    print(f"Отклонено: {rejected}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
