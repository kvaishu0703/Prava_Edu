"""Forms used by Admin CRUD pages."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, DateField, DateTimeLocalField, IntegerField, PasswordField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, Regexp

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class EmptyForm(FlaskForm):
    """Small form used for POST-only actions such as deactivate."""

    submit = SubmitField("Submit")


class CourseForm(FlaskForm):
    """Validate course create and edit data."""

    name = StringField("Course Name", validators=[DataRequired(), Length(max=120)])
    code = StringField("Course Code", validators=[DataRequired(), Length(max=30)])
    duration = StringField("Duration", validators=[DataRequired(), Length(max=50)])
    total_semesters = IntegerField(
        "Total Semesters",
        validators=[DataRequired(), NumberRange(min=1, max=12)],
    )
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Course")


class FacultyForm(FlaskForm):
    """Validate faculty user and profile data."""

    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField(
        "Email",
        validators=[DataRequired(), Length(max=120), Regexp(EMAIL_PATTERN, message="Enter a valid email address.")],
    )
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=128)])
    employee_id = StringField("Employee ID", validators=[DataRequired(), Length(max=50)])
    mobile_number = StringField("Mobile Number", validators=[Optional(), Length(max=20)])
    qualification = StringField("Qualification", validators=[Optional(), Length(max=120)])
    department = StringField("Department", validators=[DataRequired(), Length(max=120)])
    joining_date = DateField("Joining Date", validators=[Optional()])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Faculty")


class StudentForm(FlaskForm):
    """Validate student user and profile data."""

    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField(
        "Email",
        validators=[DataRequired(), Length(max=120), Regexp(EMAIL_PATTERN, message="Enter a valid email address.")],
    )
    password = PasswordField("Password", validators=[Optional(), Length(min=8, max=128)])
    enrollment_number = StringField("Enrollment Number", validators=[DataRequired(), Length(max=50)])
    mobile_number = StringField("Mobile Number", validators=[Optional(), Length(max=20)])
    date_of_birth = DateField("Date of Birth", validators=[Optional()])
    gender = SelectField(
        "Gender",
        choices=[("", "Select Gender"), ("Female", "Female"), ("Male", "Male"), ("Other", "Other")],
        validators=[Optional()],
    )
    address = TextAreaField("Address", validators=[Optional(), Length(max=500)])
    course_id = SelectField("Course", coerce=int, validators=[DataRequired()])
    semester = IntegerField("Semester", validators=[DataRequired(), NumberRange(min=1, max=12)])
    admission_year = IntegerField("Admission Year", validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Student")


class SubjectForm(FlaskForm):
    """Validate subject create and edit data."""

    name = StringField("Subject Name", validators=[DataRequired(), Length(max=120)])
    code = StringField("Subject Code", validators=[DataRequired(), Length(max=30)])
    course_id = SelectField("Course", coerce=int, validators=[DataRequired()])
    semester = IntegerField("Semester", validators=[DataRequired(), NumberRange(min=1, max=12)])
    faculty_id = SelectField("Faculty", coerce=int, validators=[Optional()])
    maximum_marks = IntegerField("Maximum Marks", validators=[DataRequired(), NumberRange(min=1, max=500)])
    passing_marks = IntegerField("Passing Marks", validators=[DataRequired(), NumberRange(min=1, max=500)])
    is_active = BooleanField("Active", default=True)
    submit = SubmitField("Save Subject")


class NotificationForm(FlaskForm):
    """Validate Admin notification data."""

    title = StringField("Title", validators=[DataRequired(), Length(max=150)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=1000)])
    notification_type = SelectField("Type", validators=[DataRequired()])
    target_role = SelectField("Target Role", validators=[DataRequired()])
    target_course_id = SelectField("Target Course", coerce=int, validators=[Optional()])
    target_semester = IntegerField("Target Semester", validators=[Optional(), NumberRange(min=1, max=12)])
    expires_at = DateTimeLocalField("Expires At", format="%Y-%m-%dT%H:%M", validators=[Optional()])
    submit = SubmitField("Send Notification")
