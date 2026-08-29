"""Forms used by Faculty pages."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from datetime import date

from wtforms import DateField, DateTimeLocalField, IntegerField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class FacultyProfileForm(FlaskForm):
    """Validate faculty profile updates."""

    profile_image = FileField("Profile Photo")
    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField(
        "Email",
        validators=[DataRequired(), Length(max=120), Regexp(EMAIL_PATTERN, message="Enter a valid email address.")],
    )
    mobile_number = StringField("Mobile Number", validators=[Optional(), Length(max=20)])
    qualification = StringField("Qualification", validators=[Optional(), Length(max=120)])
    department = StringField("Department", validators=[DataRequired(), Length(max=120)])
    joining_date = DateField("Joining Date", validators=[Optional()])
    submit = SubmitField("Save Profile")


class AttendanceSelectionForm(FlaskForm):
    """Select subject and date before marking attendance."""

    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    attendance_date = DateField("Date", default=date.today, validators=[DataRequired()])
    submit = SubmitField("Load Students")


class MarksSelectionForm(FlaskForm):
    """Select subject and exam before entering marks."""

    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    exam_type = SelectField(
        "Exam Type",
        choices=[
            ("Internal Test", "Internal Test"),
            ("Semester Exam", "Semester Exam"),
            ("Practical", "Practical"),
            ("Assignment", "Assignment"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Load Students")


class MarksRowForm(FlaskForm):
    """Optional future single-row marks form."""

    internal_marks = IntegerField("Internal Marks", validators=[DataRequired(), NumberRange(min=0, max=100)])
    external_marks = IntegerField("External Marks", validators=[DataRequired(), NumberRange(min=0, max=400)])
    remarks = StringField("Remarks", validators=[Optional(), Length(max=255)])
    submit = SubmitField("Save Marks")


class MaterialUploadForm(FlaskForm):
    """Validate study material upload data."""

    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=500)])
    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    file = FileField(
        "Material File",
    )
    submit = SubmitField("Upload Material")


class MaterialActionForm(FlaskForm):
    """Small form used for POST-only material actions."""

    submit = SubmitField("Submit")


class AssignmentForm(FlaskForm):
    """Validate assignment creation data."""

    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    description = TextAreaField("Description", validators=[Optional(), Length(max=1000)])
    subject_id = SelectField("Subject", coerce=int, validators=[DataRequired()])
    due_date = DateTimeLocalField("Due Date and Time", format="%Y-%m-%dT%H:%M", validators=[DataRequired()])
    maximum_marks = IntegerField("Maximum Marks", default=100, validators=[DataRequired(), NumberRange(min=1, max=500)])
    attachment = FileField("Attachment")
    submit = SubmitField("Save Assignment")


class AssignmentActionForm(FlaskForm):
    """Small form used for POST-only assignment actions."""

    submit = SubmitField("Submit")


class SubmissionGradeForm(FlaskForm):
    """Validate marks and feedback for a submitted assignment."""

    marks_obtained = IntegerField("Marks Obtained", validators=[DataRequired(), NumberRange(min=0, max=500)])
    faculty_feedback = TextAreaField("Feedback", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Save Grade")


class FacultyNotificationForm(FlaskForm):
    """Validate Faculty notification data."""

    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=1000)])
    notification_type = SelectField("Type", validators=[DataRequired()])
    subject_id = SelectField("Target Subject", coerce=int, validators=[DataRequired()])
    expires_at = DateTimeLocalField("Expires At", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    submit = SubmitField("Send Notification")


class NotificationActionForm(FlaskForm):
    """Small form used for notification read/deactivate actions."""

    submit = SubmitField("Submit")
