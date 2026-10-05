# PRAVA — College Academic Portal

Women's College of Home Science and BCA, Loni साठी Flask आधारित शैक्षणिक पोर्टल. Public website, BCA / Home Science student accounts, Staff tools आणि Office / Principal workspace एकत्र उपलब्ध आहेत.

## 1. डाउनलोड केल्यावर प्रोजेक्ट कसा सुरू करायचा?

1. GitHub वर **Code → Download ZIP** निवडा आणि ZIP **Extract All** करा. ZIP च्या आतून launcher चालवू नका.
2. पहिल्या वेळी **Python 3.12 (64-bit)** स्थापित करा: [Python for Windows](https://www.python.org/downloads/windows/). Installer मध्ये **Add Python to PATH** निवडा. Python 3.11 आणि 3.13 देखील समर्थित आहेत.
3. ज्या फोल्डरमध्ये हे `README.md` आहे, त्यातील **`START-PRAVA.cmd` वर double-click करा**.
4. पहिल्या run मध्ये dependencies डाउनलोड होतील, database आणि चार demo खाती तयार होतील. यासाठी internet आवश्यक आहे.
5. Setup पूर्ण झाल्यावर browser मध्ये **http://127.0.0.1:5000/** आपोआप उघडेल. Home वरून Login निवडा.

**सर्व्हरची window उघडी ठेवा.** बंद करण्यासाठी `Ctrl+C` दाबा. पुढच्या वेळी त्याच launcher वर double-click केल्यावर तुमचा जतन केलेला data वापरला जातो.

### PowerShell मधून

Project folder मध्ये right-click → **Open in Terminal** करून:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-PRAVA.ps1
```

किंवा `Start-PRAVA.ps1` वर right-click → **Run with PowerShell**. फोल्डरच्या path मध्ये spaces असले तरी launcher चालतो; त्यात कोणताही संगणक-विशिष्ट path लिहिलेला नाही.

| पर्याय | Command |
| --- | --- |
| Browser न उघडता run | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-PRAVA.ps1 -NoBrowser` |
| पोर्ट 5000 व्यस्त असल्यास | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-PRAVA.ps1 -Port 5001` |
| फक्त environment आणि database तयार करणे | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-PRAVA.ps1 -PrepareOnly` |
| Demo login बंद ठेवून local run | `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Start-PRAVA.ps1 -WithoutDemo` |

Demo setting बदलताना आधी चालू server ची window `Ctrl+C` ने बंद करा आणि इच्छित पर्यायाने launcher पुन्हा चालवा.

मुख्य UI styles, icons आणि JavaScript प्रोजेक्टमध्येच आहेत. पहिल्या यशस्वी setup नंतर local pages इंटरनेटशिवायही render होतात; अधिकृत external syllabus PDFs / college links उघडण्यासाठी internet लागतो.

macOS / Linux: Python 3.11–3.13 आणि venv support स्थापित असताना `python3 launch.py` चालवा.

## 2. चार demo Login IDs आणि Passwords

**ही सार्वजनिक, फक्त local demo साठीची खाती आहेत.** `START-PRAVA.cmd` ती तयार करतो. खरे खाते, खरे passwords किंवा database GitHub वर upload करायचे नाहीत.

| कोणासाठी | Login ID | Password | Login page | Dashboard वरील नाव |
| --- | --- | --- | --- | --- |
| BCA विद्यार्थी | `bca` | `bca123` | `/login/student/bca` | BCA Student |
| Home Science विद्यार्थी | `home` | `home123` | `/login/student/home-science` | Home Science Student |
| Staff | `staff` | `staff123` | `/login/staff` | Faculty |
| Admin / Office | `office` | `office123` | `/login/administration` | College Administration |

विद्यार्थ्यांची demo profiles पहिल्या semester च्या **2024 NEP** शी जोडलेली आहेत. Home Science demo Food Science & Nutrition programme मध्ये आहे. Office मधून Textile Science and Designing च्या विद्यार्थिनीही नोंदवता येतात.

Launcher कोणतीही काल्पनिक attendance, marks किंवा notifications भरत नाही. हे records संबंधित Office / Staff forms मधून भरायचे आहेत. पहिल्या run मध्ये Staff चे teaching assignments रिकामे असणे अपेक्षित आहे; Office ने verified catalogue मधून विषय आणि शिक्षक नेमल्यानंतर Staff ला तो वर्ग दिसतो.

Setup पुन्हा केल्यावर आधीची खाती, passwords, enrollment किंवा शैक्षणिक records reset होत नाहीत. Demo password स्वतः बदलला असल्यास नवीन password वापरा. वरील username आधीपासून एखाद्या वास्तविक खात्याचा असेल तर setup conflict दाखवतो आणि त्या खात्यावर लिहीत नाही. या संगणकावरील मूळ administrator खाते जतन केले आहे; चार demo accounts वेगळे आहेत.

## 3. Login, Back आणि Logout flow

- **Home → Login → Student → BCA / Home Science → Login form → त्या विद्यार्थिनीचा dashboard.**
- **Home → Login → Staff → Staff dashboard.**
- **Home → Login → Office / Administration → Admin dashboard.**
- प्रत्येक पानावर योग्य **Back to Home / Back to programmes / Back to dashboard / Back to list** दुवा असतो. तो ठराविक अंतर्गत पानावर जातो.
- Login झाल्यावर वर खात्याचे नाव, भूमिका आणि स्पष्ट **Logout** दिसते. Mobile वरही उपलब्ध आहे.
- **Switch** मधून दुसरी भूमिका निवडा. त्या form मध्ये दुसऱ्या खात्याचा ID/password भरल्यावरच खाते बदलते. आधीचे Admin खाते विद्यार्थ्याच्या form वरून आपोआप उघडत नाही.
- चुकीच्या विभागाच्या form मधून विद्यार्थी login स्वीकारला जात नाही. चुकीचा password दिल्यास जुने खाते बदलत नाही.
- Logout ही CSRF-protected POST action आहे; logout झाल्यावर Home उघडते.
- एका browser profile मधील tabs session share करतात. चार स्वतंत्र भूमिका एकाचवेळी पाहायच्या असल्यास वेगवेगळे browser profiles / private windows वापरा; सामान्य वापरासाठी Switch account पुरेसे आहे.

## 4. विद्यार्थ्यांसाठी Sign up

मुख्य header मध्ये **Home, Academics, Contact आणि Login** आहेत. **Login** वर क्लिक केल्यावर त्याखाली **Student, Staff आणि Office / Administration** dropdown दिसतो. Student निवडून BCA किंवा Home Science उघडा; **Sign up** पर्याय programme आणि student login pages वर आहे:

- सर्व programmes: `/signup`
- BCA: `/signup/bca`
- Home Science: `/signup/home-science`

विद्यार्थिनी पूर्ण नाव, स्वतःचा email, username, कॉलेजने दिलेला enrollment / PRN, programme, current semester, admission year आणि password भरते. वास्तविक Sign-up password किमान **8 characters** असतो. Demo passwords ही फक्त local demonstration ची स्वतंत्र सोय आहे.

### Office पडताळणी

1. Sign-up request database मध्ये **Pending** स्थितीत साठते. Password ची hash साठते; plain password साठत नाही.
2. Office / Admin → **Student sign-ups** (`/admin/registrations`).
3. Admission record सोबत नाव, enrollment, programme आणि semester पडताळा.
4. **Approve & activate student** केल्यावरच student account आणि academic profile एकत्र तयार होतात.
5. विद्यार्थिनीने Sign up वेळी दिलेल्या ID/password ने योग्य programme मधून login करायचा.

Duplicate enrollment / username / email रोखले जातात. Review आधी दुसरे conflicting account तयार झाले असेल तर approval अर्धवट save होत नाही. Rejected request पुन्हा approve करता येत नाही; दुरुस्त नोंदणीबाबत Office ने मदत करावी. Principal requests पाहू शकतात, पण approve / reject करू शकत नाहीत. विद्यार्थी किंवा Staff स्वतःला Admin बनवू शकत नाहीत.

**Approval email आपोआप पाठवला जात नाही.** सध्या विद्यार्थिनीने Office कडून status विचारायचा आहे. हे sign-up workflow स्थानिक password authentication वापरते आणि प्रकाशित local-auth installation वरही काम करते. Optional Supabase Auth वापरणार असल्यास त्याचे identity provisioning आधी जोडणे आवश्यक आहे; त्या configuration मध्ये हे Sign up बंद राहते. `STUDENT_SIGNUP_ENABLED=false` केल्यास public registration बंद करता येते.

Staff आणि Office खात्यांना सार्वजनिक Sign up नाही. Staff ची credentials Administration देते. Administrator → **Office & Principal access** मधून इतर Office / Principal खाती तयार करता येतात.

## 5. डेटा कुठे साठतो? पुन्हा सुरू केल्यावर टिकतो का?

| फाईल / फोल्डर | उपयोग |
| --- | --- |
| `instance/prava.sqlite3` | Local users, academic profiles, sign-up requests, marks, attendance, inquiries आणि activity records |
| `instance/.local-secret` | या installation ची random session secret; launcher ती पुन्हा वापरतो |
| `instance/backups/` | Schema बदलण्यापूर्वी launcher घेतलेले SQLite backups |
| `app/static/uploads/` | Uploaded materials, assignments आणि profile files |
| `.venv/` | Project च्या स्वतंत्र Python dependencies |
| `app/data/nep_2024.json` | स्रोत तपासून भरलेला curriculum catalogue |

सर्व्हर बंद केला किंवा संगणक restart केला तरी त्याच project folder मधील database टिकतो. नवीन ZIP वेगळ्या फोल्डरमध्ये extract केल्यास तो **नवीन installation** असतो: त्यात चार demo खाती आणि catalogue पुन्हा तयार होतात. जुना data हवा असल्यास server बंद करून जुनी `instance` आणि `uploads` folders सुरक्षितपणे जतन करा आणि नवीन installation मध्ये migrate करा. जुना database overwrite करण्यापूर्वी backup ठेवा.

`.gitignore` मध्ये database, local secret, backups, uploads, `.env`, logs आणि `.venv` वगळले आहेत. GitHub मध्ये **code + reproducible setup** जाईल; तुमचे खाजगी records जाणार नाहीत.

## 6. पहिल्या presentation साठी वापराचा क्रम

1. Day / Night toggle आणि Home, About, Academics, Contact दाखवा.
2. `bca` ने login → नाव, BCA programme, syllabus, marks / attendance pages आणि Back दाखवा.
3. Logout / Switch → `home` ने login → Home Science programme व syllabus दाखवा.
4. `staff` ने login → Staff dashboard, subjects, materials आणि assignments navigation दाखवा.
5. `office` ने login → दोन्ही विभाग, विद्यार्थी / Staff व्यवस्थापन, curriculum, student sign-ups आणि reports दाखवा.
6. खरी Office यादी उपलब्ध असल्यास **Import college records** मधून CSV template डाउनलोड करा, यादी भरा, **Validate & preview**, नंतर confirm करा. Import झालेली खाती सुरुवातीला inactive असतात; password ठरवून activate करा.
7. विद्यार्थी profile मध्ये programme + pattern + semester ठेवा. Subjects मध्ये verified catalogue item व शिक्षक नेमा; त्यानंतर Staff हजेरी / गुण भरू शकतात.

## 7. Public आणि workspace pages

| विभाग | URLs |
| --- | --- |
| Public | `/`, `/about`, `/contact`, `/academics`, `/activities` |
| Published faculty directory | `/about/faculty` |
| BCA / Home Science syllabus | `/academics/bca`, `/academics/home-science` |
| Login / Sign up | `/login`, `/login/student`, `/login/staff`, `/login/administration`, `/signup` |
| Student | `/student/dashboard`, `/student/subjects`, `/student/syllabus`, `/student/attendance`, `/student/marks`, `/student/materials`, `/student/assignments` |
| Staff | `/faculty/dashboard`, `/faculty/subjects`, `/faculty/students`, `/faculty/attendance`, `/faculty/marks`, `/faculty/materials`, `/faculty/assignments` |
| Office | `/admin/dashboard`, `/admin/students`, `/admin/faculty`, `/admin/subjects`, `/admin/curriculum`, `/admin/records/import`, `/admin/registrations`, `/admin/access`, `/admin/reports` |

Header मध्ये ठळक PRAVA wordmark, वाचायला स्पष्ट Academic Portal subtitle, active navigation आणि Day/Night toggle आहेत. पहिल्या भेटीत **Night mode हा default** आहे; वापरकर्त्याने Day/Night बदलल्यास ती निवड जतन राहते. Home वर Academic Information, BCA / Home Science programmes, college resources आणि notices आहेत. सार्वजनिक पाने, dashboard आणि Reports मध्ये स्पष्ट शीर्षके आणि दोन्ही modes मध्ये वाचनीय cards आहेत. मुख्य मजकूर, navigation आणि form controls साधारण 16px, तर table records 15px आहेत; मोबाइलवर मोठे tables त्यांच्या panelमध्ये आडवे scroll होतात. अपडेटनंतर जुना font size दिसल्यास `Ctrl+F5` वापरा. स्थानिक presentation खात्यांवर वरील programme / role नावे दिसतात; Office ने भरलेली खरी नावे कायम राहतात.

## 8. 2024 NEP अभ्यासक्रम — उपलब्धता

BCA आणि Home Science साठी 2024 NEP निश्चित आहे. **131 catalogue records: 123 सार्वजनिक source-reviewed नोंदी + 8 drafts**. सामायिक Home Science FY नोंदी दोन्ही specialization मध्ये असल्यामुळे हा unique subjects चा आकडा नाही.

- FY आणि SY content संबंधित source PDF वर आधारित आहे. BCA SY ची उपलब्ध प्रत Draft असल्याची नोंद आहे.
- कॉलेज BCA म्हणून लिंक करते त्या 2024 PDF चे शीर्षक **B.Sc. (Computer Applications)** आहे; catalogue त्याच source शी जुळवला आहे.
- BCA TY चे प्रकाशित structure उपलब्ध आहे; सविस्तर units / अंतिम PDF पडताळणे बाकी आहे.
- Home Science TY चा लागू अधिकृत 2024 NEP PDF अजून आवश्यक आहे.
- काही Home Science SY minor codes / assessment विसंगती notes मध्ये आहेत; आठ नोंदी सार्वजनिक केलेल्या नाहीत.
- प्रत्येक विद्यार्थिनीच्या स्वतंत्र elective निवडी आणि अधिकृत NEP SGPA/CGPA/grade scheme अजून जोडायची आहे. न भरलेले marks Pending दिसतात.

संपूर्ण source provenance आणि academic workflow: [सविस्तर मराठी मार्गदर्शक](docs/college-portal-guide.md).

## 9. Developer setup आणि चाचण्या

Launcher आवश्यक commands आपोआप चालवतो. स्वतंत्रपणे वापरायचे असल्यास environment तयार केल्यानंतर:

```powershell
$env:FLASK_ENV = 'development'
$env:SUPABASE_AUTH_ENABLED = 'false'
$env:PRAVA_DEMO_MODE = 'true'
.\.venv\Scripts\python.exe -m flask --app run:app upgrade-db
.\.venv\Scripts\python.exe -m flask --app run:app sync-college
.\.venv\Scripts\python.exe -m flask --app run:app setup-demo
```

Tests (isolated in-memory database):

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py" -v
```

चाचण्यांत role / department isolation, account switching, remember-cookie cleanup, Sign up / Office approval, duplicate conflicts, CSRF, Principal permissions, CSV imports, curriculum, marks limits आणि activities तपासल्या आहेत. `seed.py` हा जुन्या sample-data अभ्यासाचा script आहे; या setup मध्ये वापरायचा नाही.

## 10. पुढे website publish करताना

- Local launcher `127.0.0.1` वर demonstration साठी आहे. Production साठी [deployment guide](docs/deployment_guide.md) वापरा.
- `FLASK_ENV=production`, `PRAVA_DEMO_MODE=false`, मजबूत private `SECRET_KEY` आणि persistent `DATABASE_URL` सेट करा. Production मध्ये demo mode सुरू असल्यास application startup थांबतो. Demo accounts चा login बंद राहतो.
- First real administrator साठी private `BOOTSTRAP_ADMIN_EMAIL` आणि `BOOTSTRAP_ADMIN_PASSWORD` environment मध्ये सेट करून `flask --app wsgi:app bootstrap-admin` वापरा. ही खरी credentials README मध्ये लिहू नका.
- Startup मध्ये `upgrade-db`, `sync-college`, `bootstrap-admin`, मग Gunicorn वापरा. `render.yaml` मध्ये ही क्रमवारी आहे.
- Staff accounts वास्तविक administrator तयार करेल. Student Sign up Office approval नंतर सक्रिय होईल.
- Database आणि uploads साठी persistent storage आणि backup ठेवा. Repository download मध्ये live data समाविष्ट नसतो.
- प्रकाशित college service वर admission verification, account recovery आणि approval email प्रक्रिया कॉलेजच्या नियमांप्रमाणे पूर्ण करा.

## 11. अडचणी आल्यास

| संदेश / अडचण | काय करायचे |
| --- | --- |
| Python सापडत नाही / version error | Python 3.12 install करा; launcher Python 3.12, 3.11, नंतर 3.13 शोधतो. |
| पहिल्या setup मध्ये pip / download error | Internet तपासा आणि `START-PRAVA.cmd` पुन्हा चालवा. यशस्वी setup नंतर dependencies प्रत्येक वेळी डाउनलोड होत नाहीत. |
| Port 5000 in use | जुनी server window बंद करा किंवा `-Port 5001` वापरा. त्याच installation चा server असेल तर launcher त्याचा Home उघडतो. |
| Demo login बंद | Local presentation साठी default launcher वापरा; `-WithoutDemo` दिल्यास demo access बंद असतो. |
| Login करताना चुकीचे खाते दिसते | वरचे नाव पाहा, Switch निवडा आणि इच्छित form मध्ये योग्य ID/password भरा. |
| Sign up केले पण login होत नाही | Office ने enrollment verify करून request Approve केली आहे का तपासा. |
| Demo ID conflict | वास्तविक खाते overwrite करू नका; Office सोबत username तपासा किंवा नवीन रिकाम्या project copy मध्ये demo सुरू करा. |
| Data रिकामा दिसतो | कोणत्या extracted folder चा launcher चालू आहे ते तपासा; प्रत्येक installation चा स्वतःचा `instance/prava.sqlite3` आहे. |

## 12. अद्ययावत Project Report

**५ ऑक्टोबर २०२६ — तीन स्वतंत्र आवृत्त्या, प्रत्येकी ४५ पाने.** पहिली चार पाने संबंधित विद्यार्थिनीच्या नावाने आहेत. प्रत्येक आवृत्तीत नमुन्याप्रमाणे cover, title page, Project Submission आणि Certificate आहेत; पहिल्या सहा पानांना बॉर्डर, काळ्या Bold headings आणि योग्य signature spaces आहेत. Declaration, Acknowledgement आणि पुढील group-project report तिन्ही आवृत्त्यांत समान आहेत.

| प्रिंट कोणासाठी | PDF — वाचन / छपाई | Word — संपादन |
| --- | --- | --- |
| वैष्णवी विजय काळे — Roll No. 28 | [Vaishnavi PDF](docs/report/PRAVA_Report_Vaishnavi_Kale.pdf) | [Vaishnavi DOCX](docs/report/PRAVA_Report_Vaishnavi_Kale.docx) |
| ऋतुजा अशोक खोबरे — Roll No. 30 | [Rutuja PDF](docs/report/PRAVA_Report_Rutuja_Khobare.pdf) | [Rutuja DOCX](docs/report/PRAVA_Report_Rutuja_Khobare.docx) |
| दोघींची एकत्र प्रत | [Group PDF](docs/report/PRAVA_Report_Group.pdf) | [Group DOCX](docs/report/PRAVA_Report_Group.docx) |

Data Dictionary ५ पानांत संक्षिप्त केली आहे. Use Case Diagram, validation examples, १९ अद्ययावत website screenshots आणि ६३ यशस्वी automated tests यांच्या तपशीलांचा समावेश आहे. PDF मधील fonts embedded असून मजकूर selectable आहे.

ZIP extract केल्यावर सर्व सहा फाईल्स `docs/report/` मध्ये मिळतील. प्रिंटसाठी **A4 → Actual Size / 100%** निवडा. फक्त सुरुवातीची चार पाने प्रिंट करायची असल्यास **Pages: 1–4** द्या. [रिपोर्ट आणि प्रिंट सूचना](docs/report/README.md).

रिपोर्टमधील screenshot data हा local presentation installation चा आहे; नवीन ZIP मध्ये तुमच्या जुन्या installationचा database आपोआप येत नाही. तो जतन करण्याची पद्धत वरच्या **डेटा कुठे साठतो?** विभागात दिली आहे; प्रत्यक्ष विद्यार्थ्यांचे records Office ने पडताळून भरायचे आहेत.

## 13. Student आणि Staff माहिती संकलन

विद्यार्थिनी आणि Staff साठी स्वतंत्र **English Google Forms** आहेत:

- Student: https://docs.google.com/forms/d/e/1FAIpQLSdTkcm-zC-qoU6q_wrG1IIvGTcXLF1mDZZgxEkDKGI-D_dQQQ/viewform
- Staff: https://docs.google.com/forms/d/e/1FAIpQLSdF3HYT-MY2DA7vY7L_zlFs2n-J276xHjpXvAsx73iLQGRktQ/viewform

Responses मालकाच्या linked Google Sheets मध्ये साठतात. Forms मध्ये password विचारलेला नाही. माहिती PRAVA database मध्ये आपोआप येत नाही: Office ने अधिकृत नोंदींशी पडताळून **Import college records** मधील Student / Staff CSV template मध्ये आवश्यक माहिती भरावी, preview तपासावा आणि import करावा. नवीन imported खात्यांचे स्वतंत्र password व activation Office पूर्ण करते.

इतर दस्तऐवज: [College guide](docs/college-portal-guide.md), [मूळ redesign आराखडा](docs/college-redesign-plan.md), [तांत्रिक report outline](docs/final_project_report.md), [Viva guide](docs/viva_guide.md).
