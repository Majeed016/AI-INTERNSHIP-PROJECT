
from collections import Counter


VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_TYPES = {"mcq", "short_answer", "long_answer"}


def validate_question_bank(questions):
    """Check the question bank for missing or invalid data."""

    errors = []
    seen_ids = set()

    for index, question in enumerate(questions):
        location = f"Question at index {index}"

        question_id = question.get("id")
        if not question_id:
            errors.append(f"{location} has no ID.")
        elif question_id in seen_ids:
            errors.append(f"Duplicate question ID: {question_id}")
        else:
            seen_ids.add(question_id)

        if question.get("subject") not in {"maths", "science"}:
            errors.append(f"{location} has an invalid subject.")

        if not question.get("topic", "").strip():
            errors.append(f"{location} has no topic.")

        if question.get("difficulty") not in VALID_DIFFICULTIES:
            errors.append(f"{location} has an invalid difficulty.")

        if question.get("type") not in VALID_TYPES:
            errors.append(f"{location} has an invalid question type.")

        marks = question.get("marks")
        if (
            isinstance(marks, bool)
            or not isinstance(marks, int)
            or marks <= 0
        ):
            errors.append(f"{location} must have positive integer marks.")

        if not isinstance(question.get("text"), str) or not question["text"].strip():
            errors.append(f"{location} has no question text.")

        if question.get("type") == "mcq":
            options = question.get("options")
            if not isinstance(options, list) or len(options) < 2:
                errors.append(f"{location} must have at least two MCQ options.")

    return errors


def get_bank_summary(questions):
    """Return counts by topic, difficulty, and question type."""

    return {
        "total_questions": len(questions),
        "subjects": dict(Counter(q["subject"] for q in questions)),
        "topics": dict(Counter(q["topic"] for q in questions)),
        "difficulty": dict(Counter(q["difficulty"] for q in questions)),
        "question_types": dict(Counter(q["type"] for q in questions)),
    }
