# Authentication

## या module चे उद्दिष्ट

Phase 3 मध्ये आपण login आणि logout system तयार केली. आता user username/email आणि password वापरून login करू शकतो. Login नंतर user च्या role नुसार dashboard उघडते.

## वापरलेल्या technologies

- Flask-Login: user session manage करण्यासाठी
- Flask-WTF: secure forms आणि CSRF token साठी
- WTForms: form fields आणि validation साठी
- Werkzeug Password Hashing: password verify करण्यासाठी
- SQLAlchemy: `users` table मधून user शोधण्यासाठी

## महत्वाचे concepts

- Authentication: user खरा आहे का हे तपासणे
- Session: login झाल्यावर browser आणि server मध्ये user ची ओळख ठेवणे
- Password Hash: password database मध्ये direct न ठेवता secure hash ठेवणे
- CSRF Protection: fake form submit attacks कमी करण्यासाठी token वापरणे
- Flash Message: success/error message browser मध्ये दाखवणे

## संबंधित files

- `app/extensions.py`: `login_manager` तयार केला.
- `app/__init__.py`: `login_manager.init_app(app)` आणि auth blueprint register केला.
- `app/auth/forms.py`: `LoginForm` तयार केला.
- `app/auth/routes.py`: `/auth/login` आणि `/auth/logout` routes.
- `app/templates/auth/login.html`: login page UI.
- `app/templates/base.html`: login/logout link आणि flash messages.

## Code कुठून सुरू होतो?

Browser मध्ये `/auth/login` उघडल्यावर `app/auth/routes.py` मधील `login()` function execute होते. GET request असेल तर login form दिसतो. POST request असेल तर form validate होतो आणि database मधून user शोधला जातो.

## Login request flow

1. User login form भरतो.
2. Flask-WTF form validate करतो.
3. Username किंवा email वापरून `User` record शोधला जातो.
4. `user.check_password()` password hash verify करतो.
5. User inactive असेल तर login block होते.
6. Password बरोबर असेल तर `login_user()` session सुरू करतो.
7. User role नुसार dashboard ला redirect होतो.

## Database मध्ये काय बदल होतो?

- Successful login नंतर `users.last_login` update होते.
- `activity_logs` table मध्ये login success, login failure किंवा logout entry save होते.

## Template कसा render होतो?

`login()` route `auth/login.html` template render करतो. हा template `base.html` extend करतो. `base.html` मध्ये flash messages आणि navbar common ठेवले आहेत.

## Validation कुठे होते?

`app/auth/forms.py` मध्ये `LoginForm` मध्ये `DataRequired` आणि `Length` validators वापरले आहेत.

## Security कुठे वापरली आहे?

- Password direct compare नाही केला; hash verify केला.
- CSRF token form मध्ये आहे.
- Inactive user login block केला.
- Failed login activity log मध्ये नोंदवला.
- Sensitive technical traceback user ला दाखवत नाही.

## Run commands

```powershell
cd D:\parava\prava-college-system
.\.venv\Scripts\Activate.ps1
python seed.py --reset
python run.py
```

Browser मध्ये:

- `http://127.0.0.1:5000/auth/login`

## Demo accounts

- Admin: `admin / Admin@123`
- Faculty: `faculty / Faculty@123`
- Student: `student / Student@123`

## Expected output

Login केल्यावर:

- Admin user `/admin/dashboard` वर जाईल.
- Faculty user `/faculty/dashboard` वर जाईल.
- Student user `/student/dashboard` वर जाईल.

## Common errors

- `Invalid username/email or password`: username/password पुन्हा तपास.
- `CSRF token missing`: page refresh करून form पुन्हा submit कर.
- `No such table: users`: `python seed.py --reset` run कर.

## Practice task

`student / Student@123` ने login करून manually `/admin/dashboard` URL उघडण्याचा प्रयत्न कर. तुला access denied message दिसायला हवा आणि student dashboard वर redirect व्हायला हवे.

## Viva प्रश्न

Q: Password hash का वापरतो?

A: Database leak झाली तरी original password direct दिसू नये म्हणून.

Q: Flask-Login काय करते?

A: Login user ची session manage करते आणि `current_user` वापरून current logged-in user मिळवून देते.
