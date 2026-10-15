# PaperCraft — Smart Question Paper Generator

PaperCraft is a web-based tool that helps teachers generate Maths and Science question papers based on their requirements. Teachers can configure total marks, difficulty mix, topic weightage, and question-type mix. The application generates a structured question paper and displays a breakdown of the requested versus actual distributions.

## Features

- Generate Maths and Science question papers.
- Configure total marks.
- Set easy, medium, and hard difficulty percentages.
- Configure topic weightage.
- Set the distribution of MCQs, short-answer questions, and long-answer questions.
- Generate papers using constraint-based optimization.
- Display the actual distribution alongside requested targets.
- Show warnings when the available questions prevent exact distribution matching.
- Regenerate a paper using the same configuration.
- Replace individual questions when suitable alternatives are available.
- Print or export the question paper using the browser's print functionality.

## Technology Stack

- **Frontend:** HTML, CSS, JavaScript
- **Backend:** Python, FastAPI
- **Optimization:** Google OR-Tools CP-SAT
- **Question bank:** JSON
- **API:** REST endpoints

## How It Works

1. The teacher selects Maths or Science and enters the required total marks.
2. The teacher specifies difficulty percentages, topic weights, and question-type percentages.
3. The frontend sends the configuration to the FastAPI backend.
4. The backend loads the question bank and filters questions for the selected subject.
5. The CP-SAT solver selects questions while enforcing the exact total-marks constraint.
6. The solver minimizes the mismatch between the requested and actual difficulty, question-type, and topic distributions.
7. The backend returns the selected questions and distribution report.
8. The frontend displays the paper, allowing the teacher to review, regenerate, replace questions, and print it.

## Optimization Approach and Why

PaperCraft uses **constraint programming and optimization**, rather than random selection or a generative AI model, to choose questions.

Each question is represented by a Boolean decision variable: selected or not selected.

The primary hard constraint is:

- The sum of the marks of the selected questions must equal the requested total marks.

The optimization objective minimizes deviations between requested and actual marks allocated to difficulty levels, question types, and configured topics.

This approach is suitable because the problem has explicit numerical constraints and measurable objectives. A solver can evaluate combinations of questions systematically and return a feasible selection when one exists.

AI-assisted development tools were used during implementation and debugging. The question-selection algorithm itself uses OR-Tools and does not require an AI model at runtime.

## Handling Incompatible Constraints

Sometimes the question bank does not contain enough suitable questions to satisfy every requested percentage exactly. For example, a requested difficulty mix may be impossible because the available questions have fixed marks and difficulty classifications.

PaperCraft treats the total-marks requirement as a hard constraint and distribution percentages as optimization targets.

- If a feasible selection exists, the solver attempts to minimize distribution mismatches.
- If the exact requested percentages are impossible, the application can show the requested and actual distributions.
- If no feasible selection can achieve the required total marks, the backend returns an error asking the teacher to adjust the configuration or expand the question bank.

This prevents the application from silently treating an incorrect total as a valid paper.

## Limitations

- The generator depends on the quality, variety, and classification of the available question bank.
- Exact distribution percentages may not be possible for every configuration.
- Question marks and available combinations limit which total marks can be achieved.
- Replacement behavior depends on the availability of suitable unused questions and must be tested against the final implementation.
- Imported questions may require validation to ensure their subjects, topics, marks, and answers are accurate.
- The current project uses JSON files instead of a database.
- Generated questions and answers should be reviewed before use in a real examination.

## What I Would Improve With More Time

- Expand and verify the question bank across more topics and difficulty levels.
- Improve question replacement so it preserves total marks and the paper's constraints.
- Add automated tests for total marks, distributions, regeneration, replacement, and infeasible configurations.
- Improve dataset validation and error reporting.
- Add grade-level and curriculum filters.
- Deploy the application so teachers can access it online.
- Add persistent storage and user accounts if the application needs to support multiple teachers.

## What I Am Proud Of

I am proud of using constraint-based optimization to address a practical problem in question-paper creation. The system treats total marks as a hard requirement and makes distribution mismatches visible rather than relying on random question selection.

## What Still Needs Improvement

The main weakness is that distribution accuracy depends on the available question bank, and suitable replacements may not always exist. The dataset and replacement logic need further validation and testing to make the application more reliable.
