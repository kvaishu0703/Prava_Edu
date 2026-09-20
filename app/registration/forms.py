from datetime import date
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, Length, Regexp, EqualTo, NumberRange, Optional


class SignupForm(FlaskForm):
    full_name = StringField('Full name', validators=[DataRequired(), Length(min=2, max=120)])
    username = StringField('Choose a username', validators=[DataRequired(), Regexp(r'^[a-zA-Z0-9_.-]{3,40}$', message='Use 3–40 letters, numbers, dots, hyphens or underscores.')])
    email = StringField('Your email', validators=[DataRequired(), Length(max=120), Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Enter a valid email address.')])
    enrollment_number = StringField('College enrollment / PRN', validators=[DataRequired(), Length(min=3, max=50), Regexp(r'^[A-Za-z0-9/-]+$', message='Use the enrollment number issued by your college.')])
    programme = SelectField('Your programme', choices=[])
    semester = SelectField('Current semester', coerce=int, choices=[(i, f'Semester {i}') for i in range(1, 7)])
    admission_year = IntegerField('Admission year', default=date.today().year, validators=[DataRequired(), NumberRange(min=2024, max=date.today().year)])
    password = PasswordField('Create password', validators=[DataRequired(), Length(min=8, max=128)])
    confirm_password = PasswordField('Confirm password', validators=[DataRequired(), EqualTo('password', message='Passwords must match.')])
    website = StringField('Leave this field empty', validators=[Optional(), Length(max=0)])
    submit = SubmitField('Submit student sign-up')


class ReviewRegistrationForm(FlaskForm):
    decision = SelectField('Decision', choices=[('Approved', 'Approve & activate student'), ('Rejected', 'Decline request')])
    note = TextAreaField('Office note', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Save decision')
