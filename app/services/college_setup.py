"""Idempotent import of public programme identities and syllabus references."""
from datetime import date
import json
from pathlib import Path
from app.extensions import db
from app.models import Course, Curriculum, SyllabusDocument, CurriculumSubject
from app.services.college import PROGRAMMES, COLLEGE_SITE

BCA_FY = 'https://collegecirculars.unipune.ac.in/sites/documents/Syllabus2024/B.C.A._14062024.pdf'
HS_FY = COLLEGE_SITE + 'documents/STUDENT%20CORNER/Syllabus/Home%20Science/syllabus/B.Sc.%20%28Home%20Science%29_07062024.pdf'
HS_SY = 'https://collegecirculars.unipune.ac.in/sites/documents/Syllabus2025/S.Y.B.Sc.%20(Home%20Science)_25082025.pdf'


def sync_college():
    for code, name, department, description in PROGRAMMES:
        course = Course.query.filter_by(code=code).first()
        if course is None:
            course = Course(code=code, name=name, duration='3 Years', total_semesters=6, description=description)
            db.session.add(course)
        db.session.flush()
        curriculum = Curriculum.query.filter_by(course_id=course.id, pattern='2024 NEP').first()
        if curriculum is None:
            curriculum = Curriculum(course=course, pattern='2024 NEP', effective_year=2024)
            db.session.add(curriculum)
            db.session.flush()
        for year in (1, 2, 3):
            if SyllabusDocument.query.filter_by(curriculum_id=curriculum.id, year=year).first():
                continue
            source = BCA_FY if code == 'BCA' and year == 1 else HS_FY if department == 'home-science' and year == 1 else HS_SY if department == 'home-science' and year == 2 else None
            db.session.add(SyllabusDocument(
                curriculum=curriculum, year=year, title=f'{code} · {("FY", "SY", "TY")[year-1]} · 2024 NEP syllabus',
                source_url=source, status='reference' if source else 'pending',
                checked_at=date(2026, 9, 20) if source else None,
                notes=('An official source reference was located. Full subject, credit and assessment details are awaiting document verification.' if source else 'The applicable official university document is awaiting verification.')))
    data = json.loads((Path(__file__).resolve().parents[1] / 'data' / 'nep_2024.json').read_text(encoding='utf-8'))
    curricula = {code: Curriculum.query.join(Curriculum.course).filter(Course.code == code, Curriculum.pattern == '2024 NEP').one() for code, *_ in PROGRAMMES}
    for row in data['documents']:
        document = SyllabusDocument.query.filter_by(curriculum_id=curricula[row['programme']].id, year=row['year']).one()
        # Upgrade only untouched setup notes; preserve later office edits.
        if (document.notes or '').startswith(('An official source reference was located.', 'The applicable official university document')):
            for field in ('status', 'source_url', 'notes'):
                setattr(document, field, row[field])
            document.checked_at = date.fromisoformat(data['checked_at'])
    for row in data['subjects']:
        values = dict(row)
        curriculum = curricula[values.pop('programme')]
        if not CurriculumSubject.query.filter_by(curriculum_id=curriculum.id, semester=values['semester'], code=values['code']).first():
            db.session.add(CurriculumSubject(curriculum=curriculum, **values))
    db.session.commit()
