"""Forms used by Student pages."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import DateField, RadioField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, Regexp

from app.services.student_test import TEST_QUESTIONS

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class StudentProfileForm(FlaskForm):
    """Validate student profile updates."""

    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField(
        "Email",
        validators=[DataRequired(), Length(max=120), Regexp(EMAIL_PATTERN, message="Enter a valid email address.")],
    )
    mobile_number = StringField("Mobile Number", validators=[Optional(), Length(max=20)])
    date_of_birth = DateField("Date of Birth", validators=[Optional()])
    gender = SelectField(
        "Gender",
        choices=[("", "Select Gender"), ("Female", "Female"), ("Male", "Male"), ("Other", "Other")],
        validators=[Optional()],
    )
    address = TextAreaField("Address", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save Profile")


class AssignmentSubmissionForm(FlaskForm):
    """Validate student assignment submission upload."""

    file = FileField("Submission File")
    submit = SubmitField("Submit Assignment")


class NotificationActionForm(FlaskForm):
    """Small form used for notification read actions."""

    submit = SubmitField("Submit")


class StudentTestForm(FlaskForm):
    """Validate the public student website test and feedback form."""

    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField(
        "Email Address",
        validators=[DataRequired(), Length(max=120), Regexp(EMAIL_PATTERN, message="Enter a valid email address.")],
    )
    college_name = StringField("College Name", validators=[Optional(), Length(max=160)])
    course_year = StringField("Course and Year", validators=[DataRequired(), Length(max=80)])

    q1 = RadioField(choices=TEST_QUESTIONS[0]["choices"], validators=[InputRequired()])
    q2 = RadioField(choices=TEST_QUESTIONS[1]["choices"], validators=[InputRequired()])
    q3 = RadioField(choices=TEST_QUESTIONS[2]["choices"], validators=[InputRequired()])
    q4 = RadioField(choices=TEST_QUESTIONS[3]["choices"], validators=[InputRequired()])
    q5 = RadioField(choices=TEST_QUESTIONS[4]["choices"], validators=[InputRequired()])
    q6 = RadioField(choices=TEST_QUESTIONS[5]["choices"], validators=[InputRequired()])
    q7 = RadioField(choices=TEST_QUESTIONS[6]["choices"], validators=[InputRequired()])
    q8 = RadioField(choices=TEST_QUESTIONS[7]["choices"], validators=[InputRequired()])

    website_rating = SelectField(
        "Website Experience",
        coerce=int,
        choices=[(0, "Select rating"), (5, "Excellent"), (4, "Very Good"), (3, "Good"), (2, "Average"), (1, "Needs Improvement")],
        validators=[NumberRange(min=1, max=5, message="Please select a website rating.")],
    )
    feedback = TextAreaField("Feedback or Suggestion", validators=[Optional(), Length(max=1000)])
    submit = SubmitField("Submit Test")
