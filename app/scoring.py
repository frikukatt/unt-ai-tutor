from app.models import Question


def parse_matching_answer(answer: str) -> set[str]:
    pairs = set()

    for pair in answer.split(","):
        pair = pair.strip().upper()

        if ":" not in pair:
            continue

        letter, number = pair.split(":", 1)

        if letter not in {"A", "B"}:
            continue

        if number not in {"1", "2", "3", "4"}:
            continue

        pairs.add(f"{letter}:{number}")

    return pairs


def calculate_question_score(
    question: Question,
    user_answer: str
) -> tuple[int, int]:

    question_type = question.question_type.strip().lower()

    # ------------------------------------------
    # SINGLE
    # ------------------------------------------

    if question_type == "single":
        max_points = 1

        score = (
            1
            if question.correct_answer.strip().upper()
            == user_answer.strip().upper()
            else 0
        )

        return score, max_points

    # ------------------------------------------
    # MULTIPLE
    # ------------------------------------------

    if question_type == "multiple":
        max_points = 2

        correct_answers = {
            answer.strip().upper()
            for answer in question.correct_answer.split(",")
            if answer.strip()
        }

        selected_answers = {
            answer.strip().upper()
            for answer in user_answer.split(",")
            if answer.strip()
        }

        # Полностью правильный ответ
        if selected_answers == correct_answers:
            return 2, max_points

        missing = correct_answers - selected_answers
        extra = selected_answers - correct_answers

        # Одна ошибка:
        # 1. пропущен один правильный ответ
        # 2. добавлен один неправильный ответ
        # 3. один правильный ответ заменён одним неправильным
        if (
            (len(missing) == 1 and len(extra) == 0)
            or
            (len(missing) == 0 and len(extra) == 1)
            or
            (len(missing) == 1 and len(extra) == 1)
        ):
            return 1, max_points

        return 0, max_points

    # ------------------------------------------
    # MATCHING
    # ------------------------------------------

    if question_type == "matching":
        max_points = 2

        correct_pairs = parse_matching_answer(
            question.correct_answer
        )

        selected_pairs = parse_matching_answer(
            user_answer
        )

        if not correct_pairs:
            return 0, max_points

        correct_count = len(
            correct_pairs & selected_pairs
        )

        if correct_count == len(correct_pairs):
            return 2, max_points

        if correct_count > 0:
            return 1, max_points

        return 0, max_points

    return 0, 0 