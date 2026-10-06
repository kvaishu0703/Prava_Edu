"""Import all database models so SQLAlchemy can create every table."""

from app.models.assignment import Assignment
from app.models.attendance import Attendance
from app.models.contact import ContactInquiry
from app.models.course import Course
from app.models.faculty import Faculty
from app.models.marks import Marks
from app.models.material import StudyMaterial
from app.models.notification import ActivityLog, Notification, NotificationRead
from app.models.student import Student
from app.models.student_test import StudentTestResponse
from app.models.subject import Subject
from app.models.submission import Submission
from app.models.user import User
from app.models.curriculum import Curriculum, CurriculumSubject, SyllabusDocument
from app.models.campus_activity import CampusActivity, ActivityParticipation
from app.models.record_import import RecordImport
from app.models.registration import StudentRegistration
from app.models.timetable import TimetableSlot

__all__ = [
    "ActivityLog",
    "TimetableSlot",
    "StudentRegistration",
    "Curriculum", "CurriculumSubject", "SyllabusDocument",
    "CampusActivity", "ActivityParticipation", "RecordImport",
    "Assignment",
    "Attendance",
    "ContactInquiry",
    "Course",
    "Faculty",
    "Marks",
    "Notification",
    "NotificationRead",
    "Student",
    "StudentTestResponse",
    "StudyMaterial",
    "Subject",
    "Submission",
    "User",
]
