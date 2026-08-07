# Folder Structure

## या module चे उद्दिष्ट

Project मोठा झाल्यावर code गोंधळात जाऊ नये म्हणून files आणि folders व्यवस्थित ठेवणे.

## महत्वाचे folders

- `app/`: main Flask application
- `app/core/`: public routes जसे home आणि health
- `app/auth/`: login/logout पुढे इथे येईल
- `app/admin/`: admin module पुढे इथे येईल
- `app/faculty/`: faculty module पुढे इथे येईल
- `app/student/`: student module पुढे इथे येईल
- `app/templates/`: HTML templates
- `app/static/`: CSS, JavaScript, images, uploads
- `learn/`: Marathi learning notes
- `docs/`: college submission documents
- `tests/`: automated tests

## Request flow

Browser request Flask app कडे येते. Route function execute होते. तो function template render करतो आणि HTML browser ला परत पाठवतो.

## Practice task

`app/templates/core/index.html` मध्ये welcome page आहे हे शोधून पाहा.
