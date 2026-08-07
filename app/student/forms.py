"""Forms used by Student pages."""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import DateField, SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

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
