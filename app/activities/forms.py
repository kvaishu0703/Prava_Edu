from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateTimeLocalField, DecimalField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, NumberRange


class ActivityForm(FlaskForm):
    title = StringField('Activity title', validators=[DataRequired(), Length(max=180)])
    description = TextAreaField('Description and participation details', validators=[DataRequired(), Length(max=8000)])
    category = SelectField('Category', choices=[(s, s) for s in ['NSS & outreach', 'Earn & Learn', 'Workshop', 'Internship & project', 'Career development', 'Cultural & sports']])
    department = SelectField('Department', choices=[('all', 'Both departments'), ('bca', 'BCA'), ('home-science', 'Home Science')])
    starts_at = DateTimeLocalField('Date and time (India / IST)', format='%Y-%m-%dT%H:%M', validators=[DataRequired()])
    venue = StringField('Venue', validators=[DataRequired(), Length(max=180)])
    is_active = BooleanField('Published', default=True)
    submit = SubmitField('Save activity')


class ParticipationForm(FlaskForm):
    evidence = TextAreaField('Participation summary / evidence reference', validators=[Optional(), Length(max=2500)])
    submit = SubmitField('Save participation details')


class ReviewForm(FlaskForm):
    status = SelectField('Status', choices=[(s, s) for s in ['Registered', 'Completed', 'Not attended']])
    hours = DecimalField('Verified participation hours', places=1, validators=[Optional(), NumberRange(min=0, max=999)])
    submit = SubmitField('Save review')
