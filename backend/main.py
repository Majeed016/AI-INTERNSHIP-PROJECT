
import json
import random
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from model import PaperConfig, SwapRequest
from generator import generate_paper
from validator import validate_question_bank


BASE_DIR = Path(__file__).resolve().parent
QUESTION_BANK_PATH = BASE_DIR / "question_bank.json"
IMPORTED_BANK_PATH = BASE_DIR / "imported_questions.json"

app = FastAPI(
    title="PaperCraft API",
    description="Constraint-based Smart Question Paper Generator",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_json_file(path):
    try:
        with path.open(encoding="utf-8") as file:
            data = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Could not load {path.name}. Check the file and JSON format.",
        ) from exc

    if not isinstance(data, list):
        raise HTTPException(
            status_code=500,
            detail=f"{path.name} must contain a JSON list.",
        )

    return data


def load_question_bank():
    original = load_json_file(QUESTION_BANK_PATH)
    errors = validate_question_bank(original)

    if errors:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "The original question bank contains invalid data.",
                "errors": errors[:10],
            },
        )

    questions = list(original)
    existing_ids = {
        str(q.get("id")) for q in questions
        if isinstance(q, dict) and q.get("id") is not None
    }
    imported_count = 0

    if IMPORTED_BANK_PATH.exists():
        imported = load_json_file(IMPORTED_BANK_PATH)

        for q in imported:
            if not isinstance(q, dict):
                continue

            qid = q.get("id")
            if not isinstance(qid, str) or not qid.strip():
                continue
            if qid in existing_ids:
                continue
            if q.get("subject") not in ("maths", "science"):
                continue
            if q.get("difficulty") not in ("easy", "medium", "hard"):
                continue
            if q.get("type") not in (
                "mcq", "short_answer", "long_answer"
            ):
                continue
            if not isinstance(q.get("text"), str) or not q["text"].strip():
                continue
            if not isinstance(q.get("topic"), str) or not q["topic"].strip():
                continue

            marks = q.get("marks")
            if not isinstance(marks, int) or isinstance(marks, bool) or marks <= 0:
                continue

            if q["type"] == "mcq":
                options = q.get("options")
                if not isinstance(options, list) or len(options) < 2:
                    continue

            questions.append(q)
            existing_ids.add(qid)
            imported_count += 1

    print(f"Original questions: {len(original)}")
    print(f"Imported questions added: {imported_count}")
    print(f"Total questions available: {len(questions)}")

    return questions


def to_dict(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    raise HTTPException(status_code=400, detail="Invalid request data.")


def public_question(question):
    result = dict(question)
    result.pop("answer", None)
    return result


@app.get("/")
def home():
    return {"message": "PaperCraft API is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate-paper")
def create_paper(config: PaperConfig):
    questions = load_question_bank()

    try:
        paper = generate_paper(questions, config.model_dump())

        for section in paper.get("sections", []):
            section["questions"] = [
                public_question(q) for q in section.get("questions", [])
            ]

        return paper

    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/swap-question")
def swap_question(request: SwapRequest):
    questions = load_question_bank()
    config = to_dict(request.config)
    paper = to_dict(request.paper)

    subject = config.get("subject")
    old_id = str(request.question_id)

    old_question = None
    target_section = None

    for section in paper.get("sections", []):
        for question in section.get("questions", []):
            if str(question.get("id")) == old_id:
                old_question = question
                target_section = section
                break
        if old_question:
            break

    if old_question is None:
        raise HTTPException(status_code=404, detail="Question not found.")

    used_ids = {
        str(q.get("id"))
        for section in paper.get("sections", [])
        for q in section.get("questions", [])
        if str(q.get("id")) != old_id
    }

    candidates = [
        q for q in questions
        if str(q.get("id")) not in used_ids
        and str(q.get("id")) != old_id
        and q.get("subject") == subject
    ]

    if not candidates:
        raise HTTPException(
            status_code=422,
            detail="No unused questions are available for this subject.",
        )

    # Prefer same marks, type, difficulty and topic.
    rules = [
        lambda q: (
            q.get("marks") == old_question.get("marks")
            and q.get("type") == old_question.get("type")
            and q.get("difficulty") == old_question.get("difficulty")
            and str(q.get("topic", "")).strip().lower()
            == str(old_question.get("topic", "")).strip().lower()
        ),
        lambda q: (
            q.get("marks") == old_question.get("marks")
            and q.get("type") == old_question.get("type")
        ),
        lambda q: q.get("marks") == old_question.get("marks"),
        lambda q: True,
    ]

    replacement = None

    for rule in rules:
        matches = [q for q in candidates if rule(q)]
        if matches:
            replacement = random.choice(matches).copy()
            break

    if replacement is None:
        raise HTTPException(
            status_code=422,
            detail="No replacement question could be found.",
        )

    replacement.pop("answer", None)

    for index, question in enumerate(target_section["questions"]):
        if str(question.get("id")) == old_id:
            target_section["questions"][index] = replacement
            break

    # Recalculate the total in case replacement marks differ.
    paper["total_marks"] = sum(
        int(q.get("marks", 0))
        for section in paper.get("sections", [])
        for q in section.get("questions", [])
    )

    return paper
