"""Question bank and grading helpers for the public student test."""

import json


TEST_QUESTIONS = [
    {
        "key": "q1",
        "prompt": "PRAVA systemमध्ये मुख्य user roles किती आहेत?",
        "choices": [("a", "दोन"), ("b", "तीन"), ("c", "चार"), ("d", "पाच")],
        "correct": "b",
        "explanation": "PRAVA मध्ये Admin, Faculty आणि Student हे तीन मुख्य roles आहेत.",
    },
    {
        "key": "q2",
        "prompt": "Student स्वतःची attendance कुठे पाहू शकतो?",
        "choices": [
            ("a", "Student Dashboard मधील Attendance page"),
            ("b", "Admin Reports मध्ये"),
            ("c", "Faculty Profile मध्ये"),
            ("d", "Login page वर"),
        ],
        "correct": "a",
        "explanation": "Student sidebarमधील Attendance page वर subject-wise attendance दिसते.",
    },
    {
        "key": "q3",
        "prompt": "Study Material मिळवण्यासाठी studentने कोणता module वापरावा?",
        "choices": [
            ("a", "Notifications"),
            ("b", "Profile"),
            ("c", "Materials"),
            ("d", "Reports"),
        ],
        "correct": "c",
        "explanation": "Materials moduleमधून notes आणि इतर study files शोधता व download करता येतात.",
    },
    {
        "key": "q4",
        "prompt": "Assignmentचे उत्तर online जमा करण्यासाठी योग्य action कोणती?",
        "choices": [
            ("a", "Mark Present"),
            ("b", "Submit Assignment"),
            ("c", "Add Student"),
            ("d", "Generate Report"),
        ],
        "correct": "b",
        "explanation": "Assignments pageवरील Submit actionने student स्वतःची file upload करतो.",
    },
    {
        "key": "q5",
        "prompt": "Facultyने पाठवलेली महत्त्वाची सूचना studentला कुठे दिसते?",
        "choices": [
            ("a", "Courses"),
            ("b", "Marks"),
            ("c", "Notifications"),
            ("d", "Admin Users"),
        ],
        "correct": "c",
        "explanation": "Targeted announcements आणि notices Notifications pageवर दिसतात.",
    },
    {
        "key": "q6",
        "prompt": "PRAVA loginमध्ये password कसा store केला जातो?",
        "choices": [
            ("a", "Plain text"),
            ("b", "Password hash म्हणून"),
            ("c", "Browser titleमध्ये"),
            ("d", "CSV reportमध्ये")
        ],
        "correct": "b",
        "explanation": "Securityसाठी password databaseमध्ये secure hash म्हणून store होतो.",
    },
    {
        "key": "q7",
        "prompt": "Studentच्या marks आणि faculty feedbackसाठी कोणते page योग्य आहे?",
        "choices": [
            ("a", "Marks आणि Assignments"),
            ("b", "Login"),
            ("c", "Admin Courses"),
            ("d", "Health Check"),
        ],
        "correct": "a",
        "explanation": "Subject marks Marks pageवर आणि graded assignment feedback Assignments pageवर दिसते.",
    },
    {
        "key": "q8",
        "prompt": "PRAVA वेबसाइटचा मुख्य उद्देश कोणता आहे?",
        "choices": [
            ("a", "Online shopping"),
            ("b", "College academic work manage करणे"),
            ("c", "Video editing"),
            ("d", "Game खेळणे"),
        ],
        "correct": "b",
        "explanation": "PRAVA ही College Academic Management System आहे.",
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
                "selected_label": choice_map.get(selected, "उत्तर दिलेले नाही"),
                "correct_label": choice_map[question["correct"]],
                "is_correct": selected == question["correct"],
                "explanation": question["explanation"],
            }
        )
    return rows
