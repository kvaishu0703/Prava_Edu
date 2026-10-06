"""Forms for administrative registers and class teacher assignments."""
from flask_wtf import FlaskForm
from wtforms import DateField, HiddenField, IntegerField, SelectField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class StaffRegisterForm(FlaskForm):
    attendance_date = DateField("Attendance date", validators=[DataRequired()])
    register_version = HiddenField(validators=[DataRequired(message="Reload the staff register before saving.")])
    correction_reason = TextAreaField("Reason for correction", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save staff attendance")


class ClassTeacherForm(FlaskForm):
    curriculum_id = SelectField("Programme and curriculum", coerce=int, validators=[DataRequired()])
    semester = IntegerField("Semester", validators=[DataRequired(), NumberRange(min=1, max=12)])
    academic_year = IntegerField("Academic year starts", validators=[DataRequired(), NumberRange(min=2000, max=2100)])
    faculty_id = SelectField("Class teacher", coerce=int, validators=[DataRequired()])
    submit = SubmitField("Assign class teacher")


class CampusActionForm(FlaskForm):
    submit = SubmitField("Remove assignment")
