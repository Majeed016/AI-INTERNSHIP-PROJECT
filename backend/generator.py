
from math import lcm

from ortools.sat.python import cp_model


def generate_paper(questions, config):
    subject = str(config["subject"]).strip().casefold()
    total_marks = int(config["total_marks"])

    # Keep valid questions for the selected subject.
    bank = []

    for q in questions:
        if not isinstance(q, dict):
            continue

        if str(q.get("subject", "")).strip().casefold() != subject:
            continue

        if not isinstance(q.get("text"), str) or not q["text"].strip():
            continue

        marks = q.get("marks")
        if not isinstance(marks, int) or isinstance(marks, bool) or marks <= 0:
            continue

        if q.get("type") not in ("mcq", "short_answer", "long_answer"):
            continue

        if q.get("difficulty") not in ("easy", "medium", "hard"):
            continue

        if not str(q.get("topic", "")).strip():
            continue

        if q["type"] == "mcq":
            options = q.get("options")
            if not isinstance(options, list) or len(options) < 2:
                continue

        bank.append(q)

    if not bank:
        raise ValueError(
            f"No valid questions are available for subject '{subject}'."
        )

    model = cp_model.CpModel()

    selected = [
        model.NewBoolVar(f"question_{i}")
        for i in range(len(bank))
    ]

    # The generated paper must have exactly the requested marks.
    model.Add(
        sum(selected[i] * bank[i]["marks"] for i in range(len(bank)))
        == total_marks
    )

    difficulty_targets = config["difficulty"]
    type_targets = config["question_types"]
    topic_targets = {
        str(topic["name"]).strip(): topic["weight"]
        for topic in config["topics"]
    }

    groups = {
        "difficulty": difficulty_targets,
        "question_types": type_targets,
        "topics": topic_targets,
    }

    group_sizes = [len(targets) for targets in groups.values() if targets]
    scale = lcm(*group_sizes) if group_sizes else 1

    deviations = []

    for group_name, targets in groups.items():
        if not targets:
            continue

        group_weight = scale // len(targets)

        for category, percentage in targets.items():
            if group_name == "difficulty":
                matching = [
                    i for i, q in enumerate(bank)
                    if str(q.get("difficulty", "")).casefold()
                    == str(category).casefold()
                ]
                field = "difficulty"

            elif group_name == "question_types":
                matching = [
                    i for i, q in enumerate(bank)
                    if str(q.get("type", "")).casefold()
                    == str(category).casefold()
                ]
                field = "type"

            else:
                matching = [
                    i for i, q in enumerate(bank)
                    if str(q.get("topic", "")).strip().casefold()
                    == str(category).strip().casefold()
                ]
                field = "topic"

            target_marks = round(total_marks * percentage / 100)

            actual_marks = sum(
                selected[i] * bank[i]["marks"]
                for i in matching
            )

            deviation = model.NewIntVar(
                0,
                total_marks,
                f"deviation_{group_name}_{len(deviations)}",
            )

            model.Add(actual_marks - target_marks <= deviation)
            model.Add(target_marks - actual_marks <= deviation)

            deviations.append(group_weight * deviation)

    # Prefer imported questions when distribution quality is equal.
    # Imported records created by the importer include source metadata.
    imported_flags = [
        bool(q.get("source_sheet") or q.get("source_row"))
        for q in bank
    ]

    # Make distribution accuracy the priority, then prefer imported data.
    priority = len(bank) + 1

    distribution_cost = sum(deviations) * priority
    original_question_cost = sum(
        selected[i]
        for i, is_imported in enumerate(imported_flags)
        if not is_imported
    )

    model.Minimize(distribution_cost + original_question_cost)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15

    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError(
            f"Cannot generate a {total_marks}-mark paper from the valid "
            f"{subject} questions. Try a different total or add questions "
            "with suitable marks."
        )

    chosen = [
        bank[i]
        for i in range(len(bank))
        if solver.Value(selected[i]) == 1
    ]

    section_titles = {
        "mcq": "Section A - Multiple Choice Questions",
        "short_answer": "Section B - Short Answer Questions",
        "long_answer": "Section C - Long Answer Questions",
    }

    sections = []

    for question_type, title in section_titles.items():
        section_questions = []

        for question in chosen:
            if str(question.get("type", "")).casefold() != question_type:
                continue

            # Never expose answers in the question paper.
            clean_question = {
                key: value
                for key, value in question.items()
                if key != "answer"
            }

            section_questions.append(clean_question)

        if section_questions:
            sections.append({
                "title": title,
                "questions": section_questions,
            })

    def build_distribution(field, categories, requested_targets):
        result = {}

        for category in categories:
            actual_marks = sum(
                q["marks"]
                for q in chosen
                if str(q.get(field, "")).strip().casefold()
                == str(category).strip().casefold()
            )

            requested = next(
                (
                    value
                    for key, value in requested_targets.items()
                    if str(key).strip().casefold()
                    == str(category).strip().casefold()
                ),
                0,
            )

            result_key = category if field == "topic" else category.lower()

            result[result_key] = {
                "requested": requested,
                "actual": round(actual_marks / total_marks * 100, 2),
            }

        return result

    report = {
        "difficulty": build_distribution(
            "difficulty",
            ["easy", "medium", "hard"],
            difficulty_targets,
        ),
        "question_types": build_distribution(
            "type",
            ["mcq", "short_answer", "long_answer"],
            type_targets,
        ),
        "topics": build_distribution(
            "topic",
            list(topic_targets.keys()),
            topic_targets,
        ),
    }

    warnings = []

    if status != cp_model.OPTIMAL:
        warnings.append(
            "A feasible paper was found, but the solver did not prove "
            "that the distribution is optimal within the time limit."
        )

    for group_name, categories in report.items():
        for category, values in categories.items():
            if abs(values["requested"] - values["actual"]) > 0.5:
                warnings.append(
                    f"{group_name} - {category}: requested "
                    f"{values['requested']}%, actual {values['actual']}%. "
                    "The available questions may prevent an exact match."
                )

    imported_selected = sum(
        1
        for q in chosen
        if q.get("source_sheet") or q.get("source_row")
    )

    print(f"Valid questions for {subject}: {len(bank)}")
    print(f"Questions selected: {len(chosen)}")
    print(f"Imported questions selected: {imported_selected}")
    print(f"Original questions selected: {len(chosen) - imported_selected}")

    return {
        "title": f"{subject.title()} Question Paper",
        "instructions": [
            "Answer all questions.",
            "Check the marks allotted to each question.",
        ],
        "total_marks": sum(q["marks"] for q in chosen),
        "sections": sections,
        "distribution": report,
        "warnings": warnings,
    }
