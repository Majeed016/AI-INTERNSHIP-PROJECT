import json

from validator import validate_question_bank, get_bank_summary

with open("question_bank.json", encoding="utf-8") as file:
    questions = json.load(file)

errors = validate_question_bank(questions)

if errors:
    print("Question bank errors:")
    for error in errors:
        print("-", error)
else:
    print("Question bank is valid!")

print(get_bank_summary(questions))