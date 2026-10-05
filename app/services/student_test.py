"""Question bank and grading helpers for the student test."""

import json


TEST_QUESTIONS = [
    {
        "key": "q1",
        "prompt": "How many main user roles are available in PRAVA?",
        "choices": [("a", "Two"), ("b", "Three"), ("c", "Four"), ("d", "Five")],
        "correct": "b",
        "explanation": "PRAVA has three main user roles: Admin, Faculty and Student.",
    },
    {
        "key": "q2",
        "prompt": "Where can a student view her attendance?",
        "choices": [
            ("a", "The Attendance page in the student workspace"),
            ("b", "Admin Reports"),
            ("c", "The Faculty Profile page"),
            ("d", "The Login page"),
        ],
        "correct": "a",
        "explanation": "The My attendance page shows attendance records for each subject.",
    },
    {
        "key": "q3",
        "prompt": "Which module should a student use to access study resources?",
        "choices": [
            ("a", "Notifications"),
            ("b", "Profile"),
            ("c", "Materials"),
            ("d", "Reports"),
        ],
        "correct": "c",
        "explanation": "The Study materials module lets students find and download notes and learning files.",
    },
    {
        "key": "q4",
        "prompt": "Which action allows a student to upload assignment work?",
        "choices": [
            ("a", "Mark Present"),
            ("b", "Submit Assignment"),
            ("c", "Add Student"),
            ("d", "Generate Report"),
        ],
        "correct": "b",
        "explanation": "Submit Assignment lets a student upload her work for an assigned task.",
    },
    {
        "key": "q5",
        "prompt": "Where can a student find announcements from her teachers?",
        "choices": [
            ("a", "Courses"),
            ("b", "Marks"),
            ("c", "Notifications"),
            ("d", "Admin Users"),
        ],
        "correct": "c",
        "explanation": "The Notifications page shows announcements and notices intended for the student.",
    },
    {
        "key": "q6",
        "prompt": "How does PRAVA store a login password?",
        "choices": [
            ("a", "Plain text"),
            ("b", "As a password hash"),
            ("c", "In the browser title"),
            ("d", "In a CSV report")
        ],
        "correct": "b",
        "explanation": "PRAVA stores a secure password hash in the database.",
    },
    {
        "key": "q7",
        "prompt": "Which pages show a student's marks and assignment feedback?",
        "choices": [
            ("a", "Marks and Assignments"),
            ("b", "Login"),
            ("c", "Admin Courses"),
            ("d", "Health Check"),
        ],
        "correct": "a",
        "explanation": "The Marks page shows subject scores. The Assignments page shows feedback on graded work.",
    },
    {
        "key": "q8",
        "prompt": "What is the main purpose of PRAVA?",
        "choices": [
            ("a", "Online shopping"),
            ("b", "Managing college academic work"),
            ("c", "Video editing"),
            ("d", "Playing games"),
        ],
        "correct": "b",
        "explanation": "PRAVA is a College Academic Management System.",
    },
]


def grade_answers(form_data) -> tuple[dict[str, str], int]:
    """Copy submitted answers and calculate the trusted server-side score."""
    answers = {question["key"]: form_data.get(question["key"], "") for question in TEST_QUESTIONS}
    score = sum(answers[question["key"]] == question["correct"] for question in TEST_QUESTIONS)
    return answers, score


def serialize_answers(answers: dict[str, str]) -> str:
    """Serialize answers for portable SQLite/PostgreSQL storage."""
    return json.dumps(answers, separators=(",", ":"))


def response_result_rows(response) -> list[dict]:
    """Build display rows containing selected and correct answer labels."""
    try:
        answers = json.loads(response.answers_json)
    except (TypeError, json.JSONDecodeError):
        answers = {}

    rows = []
    for number, question in enumerate(TEST_QUESTIONS, start=1):
        choice_map = dict(question["choices"])
        selected = answers.get(question["key"], "")
        rows.append(
            {
                "number": number,
                "prompt": question["prompt"],
                "selected_label": choice_map.get(selected, "Not answered"),
                "correct_label": choice_map[question["correct"]],
                "is_correct": selected == question["correct"],
                "explanation": question["explanation"],
            }
        )
    return rows
