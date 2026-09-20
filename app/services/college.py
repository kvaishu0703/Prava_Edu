"""College-published facts; professional profiles do not provision login accounts."""
COLLEGE_SITE = 'https://www.pravarahomesciencebca.in/'
COLLEGE = {
    'principal': 'Dr. Anushree Rajendra Khaire',
    'principal_title': 'I/c Principal',
    'principal_qualification': 'M.Sc., Ph.D.',
    'email': 'homesciencebca@pravara.in',
    'office_phone': '02422-273989',
    'principal_phone': '02422-272065',
    'established': 1997,
    'university': 'Savitribai Phule Pune University',
    'society': "Loknete Dr. Balasaheb Vikhe Patil (Padmabhushan Awardee), Pravara Rural Education Society",
    'site': COLLEGE_SITE,
}
DEPARTMENTS = {
    'bca': {'name': 'BCA', 'title': 'Bachelor of Computer Applications', 'icon': 'bi-code-slash',
            'description': 'Computer applications, programming and practical learning for a connected world.',
            'source': COLLEGE_SITE + 'BCA.html'},
    'home-science': {'name': 'Home Science', 'title': 'Home Science', 'icon': 'bi-mortarboard',
                    'description': 'Food Science & Nutrition, and Textile Science and Designing — learning for life, health and enterprise.',
                    'source': COLLEGE_SITE + 'HomeScience.html'},
}
PROGRAMMES = [
    ('BCA', 'Bachelor of Computer Applications', 'bca', 'Programming, computer applications, databases and practical software development.'),
    ('BSC-FSN', 'B.Sc. Food Science and Nutrition', 'home-science', 'Food science, nutrition and applied learning in health and community wellbeing.'),
    ('BSC-TEXTILE', 'B.Sc. Textile Science and Designing', 'home-science', 'Textiles, clothing, design and practical skills for creative enterprise.'),
]
STAFF_DIRECTORY = [
    ('bca', 'Ms. Rajshri M. Nehe', 'BCS, MCM, MCA'),
    ('bca', 'Mr. Sanjay T. Wani', 'MCM, MCA'),
    ('bca', 'Ms. Surekha K. Kale', 'MCM, MCA'),
    ('bca', 'Ms. Archana S. Ghogare', 'MCS, MCA'),
    ('bca', 'Mr. Nitin E. Kakade', 'MCS, SET'),
    ('bca', 'Mr. Mahesh S. Gaikwad', 'M.Sc. Computer Science, SET, NET, MBA'),
    ('home-science', 'Ms. Jaya B. Dabarase', 'M.Sc., B.Ed., SET'),
    ('home-science', 'Mrs. Kanchan S. Deshmukh', 'M.Sc., B.Ed., SET, Ph.D.'),
    ('home-science', 'Mrs. Rupali M. Navale', 'M.Sc., SET'),
    ('home-science', 'Mrs. Gayatri A. Gahire', 'M.Sc.'),
    ('home-science', 'Mrs. Anju R. Wighane', 'M.Sc., SET'),
]
ACTIVITY_AREAS = [
    ('NSS & outreach', 'Community participation and service through the National Service Scheme and outreach activities.', 'bi-people'),
    ('Earn & Learn', 'The college lists an Earn & Learn scheme supporting students in their educational journey.', 'bi-book'),
    ('Internships & projects', 'Industry exposure, internships and live projects connect learning with practical work.', 'bi-briefcase'),
    ('Skills & workshops', 'Technical workshops, food preservation, fashion designing and other skill programmes.', 'bi-tools'),
    ('Career development', 'Training, placement support, competitive guidance and personality development.', 'bi-compass'),
    ('Student life', 'Student council, cultural participation, sports and health awareness.', 'bi-stars'),
]


def department_for_course(course):
    if not course:
        return None
    if course.code.upper() == 'BCA':
        return 'bca'
    if course.code.upper() in {'BSC-FSN', 'BSC-TEXTILE', 'BSC-HS'}:
        return 'home-science'
    return None


def register_college_context(app):
    @app.context_processor
    def college_context():
        return {'college': COLLEGE, 'departments': DEPARTMENTS, 'department_for_course': department_for_course}
