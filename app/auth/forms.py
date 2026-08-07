"""Forms used by the authentication module."""

from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    """Validate login credentials entered by the user."""

    username_or_email = StringField(
        "Username or Email",
        validators=[DataRequired(), Length(min=3, max=120)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=6, max=128)],
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Login")


class LogoutForm(FlaskForm):
    """Provide a CSRF token for the logout action."""

    submit = SubmitField("Logout")
