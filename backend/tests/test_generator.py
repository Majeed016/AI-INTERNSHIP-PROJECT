
import json
from pathlib import Path

import pytest

from generator import generate_paper
from validator import validate_question_bank


BASE_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def questions():
    """A small question bank with known marks and categories."""
    return [
        {
            "id": "Q1",
            "subject": "maths",
            "topic": "Algebra",
            "difficulty": "easy",
            "type": "mcq",
            "marks": 2,
            "text": "Solve x + 1 = 3.",
            "options": ["1", "2", "3", "4"],
            "answer": "2",
        },
        {
            "id": "Q2",
            "subject": "maths",
            "topic": "Geometry",
            "difficulty": "easy",
            "type": "mcq",
            "marks": 2,
            "text": "How many sides does a triangle have?",
            "options": ["2", "3", "4", "5"],
            "answer": "3",
        },
        {
            "id": "Q3",
            "subject": "maths",
            "topic": "Algebra",
            "difficulty": "medium",
            "type": "short_answer",
            "marks": 4,
            "text": "Factorize x² - 9.",
            "answer": "(x - 3)(x + 3)",
        },
        {
            "id": "Q4",
            "subject": "maths",
            "topic": "Geometry",
            "difficulty": "medium",
            "type": "short_answer",
            "marks": 4,
            "text": "Find the perimeter of a square of side 3 cm.",
            "answer": "12 cm",
        },
        {
            "id": "Q5",
            "subject": "maths",
            "topic": "Trigonometry",
            "difficulty": "hard",
            "type": "long_answer",
            "marks": 6,
            "text": "Prove that sin²x + cos²x = 1.",
            "answer": "Use the fundamental trigonometric identity.",
        },
        {
            "id": "Q6",
            "subject": "maths",
            "topic": "Algebra",
            "difficulty": "hard",
            "type": "long_answer",
            "marks": 6,
            "text": "Solve x² - 5x + 6 = 0.",
            "answer": "x = 2 or x = 3",
        },
    ]


@pytest.fixture
def config():
    return {
        "subject": "maths",
        "total_marks": 10,
        "difficulty": {
            "easy": 40,
            "medium": 40,
            "hard": 20,
        },
        "question_types": {
            "mcq": 40,
            "short_answer": 40,
            "long_answer": 20,
        },
        "topics": [
            {"name": "Algebra", "weight": 40},
            {"name": "Geometry", "weight": 30},
            {"name": "Trigonometry", "weight": 30},
        ],
    }


def test_generated_paper_has_exact_total_marks(questions, config):
    paper = generate_paper(questions, config)

    actual_total = sum(
        question["marks"]
        for section in paper["sections"]
        for question in section["questions"]
    )

    assert actual_total == config["total_marks"]
    assert paper["total_marks"] == config["total_marks"]


def test_generated_paper_has_no_duplicate_questions(questions, config):
    paper = generate_paper(questions, config)

    ids = [
        question["id"]
        for section in paper["sections"]
        for question in section["questions"]
    ]

    assert len(ids) == len(set(ids))


def test_generated_paper_contains_only_requested_subject(
    questions, config
):
    paper = generate_paper(questions, config)

    for section in paper["sections"]:
        for question in section["questions"]:
            assert question["id"].startswith("Q")


def test_distribution_report_is_present(questions, config):
    paper = generate_paper(questions, config)

    assert "distribution" in paper

    for group in ("difficulty", "topics", "question_types"):
        assert group in paper["distribution"]

        for values in paper["distribution"][group].values():
            assert "requested" in values
            assert "actual" in values
            assert 0 <= values["actual"] <= 100


def test_impossible_total_marks_raise_error(questions, config):
    config["total_marks"] = 3

    with pytest.raises(ValueError, match="Cannot generate"):
        generate_paper(questions, config)


def test_missing_subject_questions_raise_error(questions, config):
    config["subject"] = "science"

    with pytest.raises(ValueError, match="No questions"):
        generate_paper(questions, config)


def test_real_question_bank_has_no_validation_errors():
    with (BASE_DIR / "question_bank.json").open(
        encoding="utf-8"
    ) as file:
        bank = json.load(file)

    assert validate_question_bank(bank) == []
