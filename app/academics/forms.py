from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, IntegerField, DecimalField, TextAreaField, BooleanField, SubmitField
from wtforms.validators import DataRequired, InputRequired, Length, NumberRange, Optional, URL


class DocumentForm(FlaskForm):
    title = StringField('Document title', validators=[DataRequired(), Length(max=180)])
    source_url = StringField('Official source URL', validators=[Optional(), URL(), Length(max=1000)])
    status = SelectField('Verification', choices=[('pending', 'Applicable document awaiting verification'), ('reference', 'Source located — contents awaiting review'), ('structure', 'Published structure only — detailed units pending'), ('verified', 'Source reviewed — see verification notes')])
    notes = TextAreaField('Verification notes / applicable academic year', validators=[DataRequired(), Length(max=2500)])
    submit = SubmitField('Save document')

    def validate(self, extra_validators=None):
        valid = super().validate(extra_validators=extra_validators)
        if self.status.data != 'pending' and not (self.source_url.data or '').strip():
            self.source_url.errors.append('Add the source URL before marking this document as located or reviewed.')
            return False
        return valid


class CurriculumSubjectForm(FlaskForm):
    semester = SelectField('Semester', coerce=int, choices=[(i, f'Semester {i}') for i in range(1, 7)])
    code = StringField('Official subject code', validators=[DataRequired(), Length(max=60)])
    name = StringField('Subject title', validators=[DataRequired(), Length(max=180)])
    category = SelectField('NEP category', choices=[(s, s) for s in ['Major', 'Minor', 'Programme Elective', 'Open Elective', 'VSC', 'VSEC', 'SEC', 'AEC', 'VEC', 'IKS', 'CC', 'Field Project', 'Community Engagement', 'Internship', 'Research Project']])
    credits = DecimalField('Credits', places=1, validators=[InputRequired(), NumberRange(min=0, max=30)])
    internal_max = IntegerField('Internal maximum (if applicable)', validators=[Optional(), NumberRange(min=0, max=1000)])
    external_max = IntegerField('External maximum (if applicable)', validators=[Optional(), NumberRange(min=0, max=1000)])
    practical_max = IntegerField('Practical maximum (if separate)', validators=[Optional(), NumberRange(min=0, max=1000)])
    units = TextAreaField('Units, outcomes and references', validators=[DataRequired(), Length(max=30000)])
    source_url = StringField('Official syllabus URL', validators=[DataRequired(), URL(), Length(max=1000)])
    is_verified = BooleanField('Publish this source-reviewed subject; describe unresolved details in the notes')
    submit = SubmitField('Save subject')
