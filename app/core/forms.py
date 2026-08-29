"""Forms used by public website pages."""

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, Regexp

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class ContactForm(FlaskForm):
    """Validate public contact inquiries."""

    full_name = StringField("Full Name", validators=[DataRequired(), Length(max=120)])
    email = StringField(
        "Email",
        validators=[DataRequired(), Length(max=120), Regexp(EMAIL_PATTERN, message="Enter a valid email address.")],
    )
    phone = StringField("Phone", validators=[Optional(), Length(max=20)])
    subject = StringField("Subject", validators=[DataRequired(), Length(max=150)])
    message = TextAreaField("Message", validators=[DataRequired(), Length(max=1000)])
    submit = SubmitField("Send Message")
