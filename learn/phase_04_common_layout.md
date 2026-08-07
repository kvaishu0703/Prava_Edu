# Phase 4 - Common Layout and Dashboard UI

## या phase मध्ये आपण काय तयार केले?

Phase 4 मध्ये project चा common UI पाया तयार केला. Admin, Faculty आणि Student dashboard आता एकाच reusable dashboard shell मधून दिसतात. Sidebar, topbar, stats cards, tables आणि notification panels responsive केले.

## हे का आवश्यक आहे?

मोठ्या project मध्ये प्रत्येक page साठी पुन्हा-पुन्हा navbar/sidebar लिहिले तर duplicate code वाढतो. Common layout वापरल्याने design consistent राहते आणि बदल करणे सोपे होते.

## वापरलेल्या technologies

- Jinja2 Macro: repeated HTML reuse करण्यासाठी
- Bootstrap 5: responsive grid, table आणि buttons
- Bootstrap Icons: sidebar आणि cards मधील icons
- CSS Grid: dashboard layout साठी
- Flask-SQLAlchemy: dashboard stats database मधून आणण्यासाठी

## महत्वाचे concepts

- Reusable Component: एकदा तयार केलेला UI part अनेक pages मध्ये वापरणे
- Macro: Jinja मधील reusable template function
- Service Layer: route मध्ये जास्त logic न ठेवता data तयार करणारी वेगळी file
- Responsive Design: mobile आणि desktop दोन्हीवर UI नीट दिसणे

## संबंधित files

- `app/templates/base.html`: navbar, flash messages आणि common page structure
- `app/templates/components/dashboard_shell.html`: sidebar, topbar आणि stats cards reusable macro
- `app/templates/admin/dashboard.html`: Admin dashboard content
- `app/templates/faculty/dashboard.html`: Faculty dashboard content
- `app/templates/student/dashboard.html`: Student dashboard content
- `app/services/dashboard.py`: dashboard साठी database-backed stats
- `app/static/css/app.css`: dashboard आणि responsive styling

## Request flow

Admin dashboard example:

1. Browser `/admin/dashboard` request करतो.
2. `roles_required("admin")` user admin आहे का तपासतो.
3. `get_admin_dashboard_data()` database मधून counts आणि recent data आणतो.
4. `admin/dashboard.html` template render होतो.
5. Template `dashboard_shell.html` macro वापरून sidebar/topbar/stats दाखवतो.

## Database मध्ये काय होते?

Phase 4 मध्ये database write होत नाही. Dashboard pages database मधून data read करतात:

- Students count
- Faculty count
- Course count
- Attendance percentage
- Subjects
- Assignments
- Study materials
- Notifications

## Template कसा render होतो?

Dashboard template `dashboard_shell` macro `with context` import करते. त्यामुळे macro मध्ये `current_user` वापरता येतो. मग template role-specific panels दाखवते.

## Validation कुठे होते?

Phase 4 मध्ये form validation नाही. पण protected route validation `roles_required()` decorator मध्ये होते.

## Security कुठे वापरली आहे?

Dashboard pages login शिवाय उघडत नाहीत. चुकीच्या role ने page उघडल्यास user ला स्वतःच्या dashboard वर redirect केले जाते.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
python run.py
```

Browser मध्ये:

- `http://127.0.0.1:5000/auth/login`
- `http://127.0.0.1:5000/phase-summary`

## Expected output

Login केल्यावर role नुसार dashboard दिसेल:

- Admin: total students, faculty, courses, attendance, recent students
- Faculty: assigned subjects, students, assignments, pending reviews
- Student: attendance, marks, assignments, subjects, materials

## Common errors

- Dashboard blank दिसला तर `python seed.py --reset` run करून sample data तयार कर.
- `current_user is undefined` error आल्यास macro import मध्ये `with context` आहे का तपास.
- CSS load होत नसेल तर browser hard refresh कर.

## Practice task

Admin, Faculty आणि Student या तिन्ही accounts ने login करून dashboard मधील cards कसे बदलतात ते note कर.

## Viva प्रश्न

Q: Common layout का वापरतो?

A: Navbar, sidebar आणि repeated UI एकाच जागी ठेवण्यासाठी, जेणेकरून duplicate code कमी होतो आणि design consistent राहते.

Q: Service layer म्हणजे काय?

A: Route मधील business/data logic वेगळ्या helper file मध्ये ठेवणे. त्यामुळे routes छोटे आणि वाचायला सोपे राहतात.
