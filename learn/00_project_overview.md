# PRAVA Project Overview

## या module चे उद्दिष्ट

PRAVA म्हणजे College Academic Management System. या system मध्ये Admin, Faculty आणि Student असे तीन roles असतील. प्रत्येक role साठी वेगळे dashboard आणि permissions असतील.

## वापरलेल्या technologies

- Flask: Python मधील web framework
- Jinja2: HTML templates मध्ये dynamic data दाखवण्यासाठी
- Bootstrap 5: responsive UI तयार करण्यासाठी
- SQLite: सुरुवातीची database choice

## महत्वाचे concepts

- Web Application: Browser मधून वापरता येणारा application
- Role-Based Access: user च्या role नुसार pages आणि actions control करणे
- Modular Structure: मोठा project छोटे modules मध्ये विभागणे

## Code flow

Phase 1 मध्ये browser request `/` route वर येते. Flask `app/core/routes.py` मधील `index()` function चालवतो आणि `app/templates/core/index.html` template render करतो.

## Practice task

README.md उघड आणि project चे नाव, roles आणि technology stack स्वतःच्या शब्दात लिहून पाहा.

## Viva प्रश्न

Q: PRAVA project चा मुख्य उद्देश काय आहे?

A: College मधील academic कामे जसे students, faculty, attendance, marks, materials, assignments आणि notifications manage करणे.
