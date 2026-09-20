# PRAVA — कॉलेज पोर्टल वापर मार्गदर्शक

अद्ययावत: 20 सप्टेंबर 2026. BCA आणि Home Science या दोन्हींसाठी वापरकर्त्याने निश्चित केलेला **2024 NEP Pattern** वापरला आहे.

## 1. प्रोजेक्ट उघडणे

स्थानिक वेबसाइट: [http://127.0.0.1:5000/](http://127.0.0.1:5000/)

प्रोजेक्ट सुरू करण्यासाठी `README.md` असलेल्या फोल्डरमधील **START-PRAVA.cmd** वर double-click करा. पहिल्या run मध्ये Python 3.11–3.13 आणि internet आवश्यक आहे. Launcher environment, database, catalogue आणि चार demo खाती तयार करतो; पुढच्या run मध्ये data जतन राहतो.

सध्याच्या संगणकावरील जुन्या shortcut साठी PowerShell मध्ये:

```powershell
cd "C:\Users\KC\OneDrive\Documents\ChatGPT\Prava"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start-local.ps1
```

सर्व्हर सुरू असेपर्यंत ही PowerShell प्रक्रिया चालू ठेवा. पोर्ट 5000 वर आधीच PRAVA सुरू असल्यास वेबसाइट थेट उघडा. सध्याची local configuration SQLite आणि स्थानिक password sign-in वापरते. Database: `Prava_Edu/instance/prava.sqlite3`. नवीन checkout साठी [README मधील setup](../README.md) वापरा.

## 2. नवीन डिझाईन आणि पानांची रचना

- पांढऱ्या पार्श्वभूमीचा **Day mode** आणि खोल निळ्या पार्श्वभूमीचा **Night mode**. Header मधील सूर्य/चंद्र बटणाने बदलता येतो. निवड browser मध्ये जतन होते आणि पुढच्या पानावरही लागू राहते.
- मुख्य रंग sapphire blue; हलके gradients, काचेप्रमाणे translucent panels, व्यवस्थित spacing आणि एकसंध forms/tables. PRAVA साठी निळा vector logo आहे.
- Home वर थोडक्यात ओळख, दोन विभाग, महत्त्वाचे दुवे आणि सार्वजनिक सूचना. सविस्तर माहिती स्वतंत्र पानांवर आहे.
- मोबाईलवर navigation संक्षिप्त होते, cards एकाखाली एक येतात आणि मोठी academic tables त्यांच्या panel मध्ये scroll होतात.

दृश्यरचनेच्या पुढील सुधारणेत Home वर **“Your college life. Beautifully connected.”** हे मोठे शीर्षक, निळ्या रंगाशी जुळवलेले campus illustration, दुहेरी border ची frame, स्वतंत्र programme cards आणि “Come with curiosity. Grow with possibility.” हा PRAVA संदेश जोडला आहे. हे चित्र कलात्मक illustration आहे. Day आणि Night दोन्हींत headings, महत्त्वाची नावे, borders आणि buttons स्पष्ट दिसण्यासाठी सुधारले आहेत; हलके hover effects reduced-motion preference पाळतात.

| पान | पत्ता | उपयोग |
| --- | --- | --- |
| Home | `/` | वेबसाइटचे सुरुवातीचे पान |
| About | `/about` | इतिहास, संस्था, Principal, PRAVA प्रोजेक्ट |
| Faculty directory | `/about/faculty` | कॉलेजने प्रकाशित केलेली व्यावसायिक माहिती |
| Academics | `/academics` | BCA / Home Science विभाग निवड |
| BCA syllabus | `/academics/bca` | FY/SY/TY आणि semester निवड |
| Home Science syllabus | `/academics/home-science` | Food Science & Nutrition / Textile Science and Designing |
| Activities | `/activities` | कार्यक्रम, नोंदणी आणि सहभाग |
| Contact | `/contact` | पत्ता, फोन, ईमेल आणि inquiry form |
| Login | `/login` | Student / Staff / Office प्रवेश |

`/courses` आणि जुना `/auth/login` प्रवेशदुवा समर्थित आहेत. मुख्य navigation नवीन स्पष्ट URLs वापरते.

## 3. प्रवेश आणि अधिकार

विद्यार्थिनीचा प्रवास: **Home → Login → Student → BCA किंवा Home Science → Login form → Dashboard**.

| खाते | Login URL | उपलब्ध काम |
| --- | --- | --- |
| BCA विद्यार्थी | `/login/student/bca` | स्वतःचे विषय, अभ्यासक्रम, हजेरी, गुण, assignments, materials आणि सहभाग |
| Home Science विद्यार्थी | `/login/student/home-science` | नोंदवलेल्या specialization व semester नुसार शैक्षणिक माहिती |
| Staff | `/login/staff` | नेमलेल्या विषयांचे वर्ग, हजेरी, गुण, assignments आणि कार्यक्रम समन्वय |
| Office | `/login/administration` | दोन्ही विभागांचे विद्यार्थी, staff, विषय, अभ्यासक्रम आणि records |
| Principal | `/login/administration` | दोन्ही विभागांची माहिती आणि reports पाहणे; शैक्षणिक नोंदी बदलण्याचा अधिकार नाही |
| System administrator | `/login/administration` | Office काम आणि Office/Principal खाते तयार करणे |

चुकीच्या विभागातून विद्यार्थी login स्वीकारला जात नाही. Staff ला दिलेल्या teaching assignments वरून उपलब्ध विद्यार्थी ठरतात. विषयाचे programme, pattern आणि semester तिन्ही जुळणे आवश्यक आहे. Inactive account ची चालू session पुढील protected request वर बंद होते.

कॉलेजच्या सार्वजनिक वेबसाइटवरील staff/Principal नावे directory मध्ये आहेत. त्या नावांवरून आपोआप login accounts तयार केलेले नाहीत. सध्याचे मूळ administrator खाते जतन केले आहे. वापरकर्त्याच्या मागणीनुसार चार स्वतंत्र local demo accounts तयार आहेत: `bca / bca123`, `home / home123`, `staff / staff123`, `office / office123`. त्यांची सविस्तर माहिती [README](../README.md) मध्ये आहे.

प्रत्येक खात्याचे योग्य नाव आणि भूमिका वर दिसते. **Back**, **Switch account** आणि **Logout** desktop/mobile वर उपलब्ध आहेत. दुसऱ्या भूमिकेचा login form उघडल्यावर आधीचे Admin खाते आपोआप उघडत नाही; नवीन credentials पडताळल्यावर session बदलते.

**Student Sign up:** `/signup` किंवा विभागाच्या login पानावरील Sign up वापरा. Request Pending स्थितीत database मध्ये साठते; Office → Student sign-ups मधून admission तपासून approve केल्यावरच student account सक्रिय होते. Staff accounts Administration तयार करते. Principal विनंत्या पाहू शकतात, पण approve/reject करू शकत नाहीत.

## 4. खरी कॉलेज माहिती

**Women's College of Home Science and BCA**

PKVM Campus, Babhaleshwar Road, Loni-413713, Dist-Ahmednagar (Maharashtra) India.

- Principal म्हणून अधिकृत पानावर प्रकाशित नाव: **Dr. Anushree Rajendra Khaire**, **I/c Principal**, M.Sc., Ph.D.
- स्थापना: 1997. Principal Desk नुसार 2016 पासून Savitribai Phule Pune University शी संलग्नता; त्यापूर्वी SNDT शी संलग्नता.
- ईमेल: `homesciencebca@pravara.in`.
- Office: `02422-273989`; Principal office: `02422-272065`.
- संस्थेची माहिती आणि कॉलेजच्या मुख्य पानावर दिलेला NAAC B++ / CGPA 2.94 उल्लेख About मध्ये स्रोताच्या संदर्भासह आहे. जुन्या Principal पानावरील 2014 मूल्यांकन आजचे म्हणून दाखवलेले नाही.
- BCA विभागातील 6 आणि Home Science मधील 5 अशा 11 प्रकाशित staff profiles जोडल्या आहेत. विभागीय पाने ऐतिहासिक असू शकतात; directory वरील नोंद सध्याची नियुक्ती असल्याची स्वतंत्र खात्री देत नाही.

स्रोत: [कॉलेज मुख्य पान](https://www.pravarahomesciencebca.in/), [Principal Desk](https://www.pravarahomesciencebca.in/PrincipalDesk.html), [Contact](https://www.pravarahomesciencebca.in/contact-us.html), [BCA](https://www.pravarahomesciencebca.in/BCA.html), [Home Science](https://www.pravarahomesciencebca.in/HomeScience.html).

Contact inquiry स्थानिक database मध्ये जाते आणि Office च्या Contact inquiries पानावर दिसते. या form वरून ईमेल आपोआप पाठवला जात नाही.

## 5. 2024 NEP अभ्यासक्रमाची अचूक स्थिती

तीन programmes, तीन curricula आणि प्रत्येक programme साठी FY/SY/TY अशी नऊ document records तयार आहेत. Catalogue मध्ये **131 विषय नोंदी** आहेत: **123 सार्वजनिक source-reviewed नोंदी** आणि **8 Office-only drafts**. Home Science चे सामायिक FY विषय दोन्ही specialization मध्ये जोडलेले असल्यामुळे हा unique subjects चा आकडा नाही.

| Programme / वर्ष | सध्या काय उपलब्ध आहे | काय पडताळणे बाकी आहे |
| --- | --- | --- |
| BCA FY | कॉलेजने लिंक केलेल्या 2024 PDF मधील विषय, codes, credits, assessment आणि अभ्यासाचा संक्षिप्त आढावा | कॉलेजची प्रत्यक्ष elective निवड |
| BCA SY | त्याच B.Sc. (Computer Applications) अभ्यासक्रमाच्या 2025–26 PDF मधील विषय व आढावा | उपलब्ध प्रत Draft आहे; अंतिम कॉलेज-मंजूर आवृत्तीशी पुष्टी |
| BCA TY | मूळ 2024 PDF मधील semester V–VI चे published structure, codes, credits आणि पर्याय | स्वतंत्र सविस्तर TY units / अंतिम सुधारित PDF |
| Home Science FY | 2024–25 SPPU common FY विषय; दोन्ही specialization साठी उपलब्ध | प्रत्यक्ष elective basket |
| Home Science SY | 2025–26 Food Science & Nutrition आणि Textile Science and Designing विषय व आढावा | PDF मधील काही minor codes/titles आणि Textile assessment विसंगती |
| Home Science TY | Year/semester निवड आणि pending document record | लागू असलेला अधिकृत 2024 NEP TY syllabus उपलब्ध झाल्यावर भरायचा |

### BCA नाव आणि दस्तऐवजाची निवड

कॉलेजच्या navigation मध्ये BCA हे नाव आहे; पण कॉलेजने 2024 साठी लिंक केलेल्या PDF वर **B.Sc. (Computer Applications), Faculty of Science and Technology** असे शीर्षक आहे. Catalogue या कॉलेज-लिंक केलेल्या अभ्यासक्रमाशी जुळवले आहे. त्याच वर्षाचे वेगळ्या B.C.A. शीर्षकाचे PDF मिळाले तरी त्यांचे codes यात मिसळलेले नाहीत. प्रत्येक वर्षाच्या verification notes मध्ये मूळ पदवी शीर्षक आणि स्रोत स्पष्ट आहेत.

### वापरलेले syllabus sources

1. [BCA म्हणून कॉलेजने लिंक केलेला FY B.Sc. (Computer Applications), 2024 PDF](http://www.pravarahomesciencebca.in/documents/STUDENT%20CORNER/Syllabus/BCA/B.%20Sc.%20%28Computer%20Applications%29_14062024.pdf).
2. [SY B.Sc. (Computer Applications), 2025–26, SPPU-authored Draft — कॉलेज mirror](https://pcccs.org.in/wp-content/uploads/2026/03/SY-B.Sc_.CA_.pdf). PDF मधील Draft स्थिती UI मध्ये नमूद आहे.
3. [FY B.Sc. Home Science, 2024 PDF — कॉलेज स्रोत](http://www.pravarahomesciencebca.in/documents/STUDENT%20CORNER/Syllabus/Home%20Science/syllabus/B.Sc.%20%28Home%20Science%29_07062024.pdf).
4. [SY B.Sc. Home Science, 2025–26 PDF — SPPU](http://collegecirculars.unipune.ac.in/sites/documents/Syllabus2025/S.Y.B.Sc.%20(Home%20Science)_25082025.pdf).

काही अधिकृत servers ची HTTPS उपलब्धता अस्थिर असल्यामुळे उपलब्ध सार्वजनिक HTTP source links वापरले आहेत. स्थानिक `research` फोल्डरमध्ये वाचलेल्या PDF प्रती, text extracts आणि पडताळणीचे page renders जतन केले आहेत.

### स्रोतांमधील विसंगती हाताळणे

- Home Science SY semester IV च्या आठ minor नोंदींमध्ये structure आणि detailed pages वरील codes/titles जुळत नाहीत. या नोंदी draft आहेत; सार्वजनिक विद्यार्थिनीच्या catalogue मध्ये दिसत नाहीत.
- Textile `TC-251-MJT` Chemistry assessment मध्ये CE 30 + EE 70 असून total 50 छापलेला आहे. Component maximum निश्चित केलेला नाही; या स्थितीत त्या नोंदीवरून teaching allocation करता येत नाही.
- BCA TY मधील छापील code विसंगती source notes मध्ये जशी आहे तशी स्पष्ट केली आहे. Programme elective जोड्या पर्याय आहेत; प्रत्येक विद्यार्थिनीला सगळे electives लागू असल्याचा दावा केलेला नाही.
- प्रत्येक subject page वर संक्षिप्त study outline आणि मूळ PDF दुवा आहे. हा आढावा पूर्ण अधिकृत PDF चा पर्याय नाही.

## 6. खरी विद्यार्थी आणि staff यादी भरणे

Office / System administrator → **Import records** (`/admin/records/import`).

1. Student किंवा Staff CSV template डाउनलोड करा.
2. कॉलेजची अधिकृत यादी वापरून UTF-8 CSV भरा. एका upload मध्ये 1–200 records आणि कमाल 1 MB स्वीकारले जाते.
3. **Validate & preview** निवडा. Duplicate username, email, enrollment/employee ID, programme, pattern आणि semester तपासले जातात.
4. Preview मधील नावे आणि विभाग तपासा. **Import these records** केल्यानंतरच खाती तयार होतात.
5. Student/Faculty editor मध्ये प्रत्येक खात्यास योग्य password द्या आणि Active करा. Import झालेली खाती सुरुवातीला inactive असतात.

Student CSV columns:

```text
full_name,username,email,enrollment_number,programme,pattern,semester,admission_year
```

Programme values: `BCA`, `BSC-FSN`, `BSC-TEXTILE`. Pattern: `2024 NEP`. Semester: `1` ते `6`. Admission year प्रत्यक्ष admission नुसार द्या.

Staff CSV columns:

```text
full_name,username,email,employee_id,department,qualification
```

Preview फक्त upload करणाऱ्या Office user ला उपलब्ध असतो आणि एका तासानंतर expire होतो. Confirm करतानाही database पुन्हा तपासला जातो; conflict आल्यास अर्धवट import होत नाही. कोणतीही खोटी enrollment number, email किंवा password यादी तयार केलेली नाही.

**Office / Principal account:** System administrator → **Office access** (`/admin/access`). Principal साठी `Principal · view both departments and reports` निवडा. Office user ला दुसरे privileged account तयार करता येत नाही. Initial password किमान 12 characters आहे.

## 7. विषय, हजेरी आणि गुणांचा वापर

1. **Curriculum catalogue** (`/admin/curriculum`) मध्ये योग्य programme, year आणि source पाहा.
2. Subjects → Add subject मध्ये verified syllabus subject निवडा. Programme, curriculum, semester, code आणि maximum त्या source शी जुळतात. प्रत्यक्ष शिक्षक निवडा आणि कॉलेजने मंजूर केलेली passing threshold द्या.
3. विद्यार्थी profile मध्ये programme + 2024 NEP + current semester अचूक असावेत. त्यानुसार विषय, materials आणि assignments दिसतात.
4. Staff login मधून नेमलेल्या वर्गाची हजेरी आणि marks भरा.
5. विद्यार्थी स्वतःची attendance/marks आणि assignments पाहू शकते; Principal reports मधून दोन्ही विभाग पाहू शकतात.

NEP-linked विषयांसाठी **Semester Exam** मध्ये source मधील Internal/External मर्यादा तपासल्या जातात. दोन्ही fields रिकामी असल्यास marks record तयार होत नाही; एकच field रिकामी ठेवून अर्धवट गुण साठवता येत नाहीत. खरे शून्य गुण असल्यास स्पष्ट `0` भरा. न भरलेले निकाल **Pending** दिसतात.

Dashboard percentage उपलब्ध marks आणि त्यांच्या एकत्रित maximum वरून काढला जातो. **NEP SGPA/CGPA/letter grades ची अधिकृत scheme निश्चित केलेली नाही; त्या गणना सक्रिय केलेल्या नाहीत.** Activity hours आपोआप शैक्षणिक credits होत नाहीत.

Teaching assignments सध्या programme + pattern + semester या वर्गाला लागू होतात. **प्रत्येक विद्यार्थिनीच्या स्वतंत्र elective/minor enrollment ची व्यवस्था अद्याप नाही.** कॉलेजची निश्चित basket मिळाल्यावर त्यानुसार विषय नेमणे आणि स्वतंत्र elective enrollment वाढवणे आवश्यक आहे. प्रकाशित पर्यायांची पूर्ण यादी थेट प्रत्येक विद्यार्थिनीचा अंतिम timetable म्हणून वापरू नका.

ज्या विषयावर वास्तविक हजेरी/गुण/materials/assignments आहेत त्याची programme/pattern/semester/source/maximum ओळख बदलण्यावर नियंत्रण आहे. यामुळे आधीच्या शैक्षणिक नोंदींचा संदर्भ टिकतो.

## 8. Activities आणि विद्यार्थिनीचा portfolio

कॉलेजच्या स्रोतांवर आधारित NSS/outreach, Earn & Learn, internships/projects, skills/workshops, career development आणि student life हे उपक्रम विभाग आहेत. [कॉलेजचे Special Features](https://www.pravarahomesciencebca.in/documents/About/Special%20Features.pdf) संदर्भ म्हणून दिले आहेत.

- Office किंवा Staff प्रत्यक्ष कार्यक्रमाचा विषय, तारीख, ठिकाण, विभाग आणि coordinator नोंदवतात.
- पात्र विभागाची विद्यार्थिनी कार्यक्रम सुरू होण्यापूर्वी register करू शकते.
- सहभागाचा evidence/reference स्वतःच्या नोंदीवर देता येतो.
- Coordinator किंवा Office पडताळणी करून completed participation आणि hours नोंदवतात. भविष्यकाळातील कार्यक्रम आत्ताच completed करता येत नाही.
- पडताळलेला सहभाग विद्यार्थिनीच्या portfolio मध्ये दिसतो; completed आणि reviewed नोंदीचे printable certificate मिळते.
- प्रमाणपत्र हे या प्रोजेक्टमधील सहभाग नोंदीचे print आहे. कॉलेजचे अधिकृत प्रमाणपत्र म्हणून वापरण्यापूर्वी कॉलेजची मान्य प्रक्रिया आवश्यक आहे.

कार्यक्रमांच्या खोट्या तारखा किंवा काल्पनिक attendance जोडलेली नाही. Office ने कार्यक्रम नोंदवल्यावर upcoming list भरते.

## 9. जतन केलेली माहिती आणि backups

ओळख पटलेल्या मूळ sample accounts, demo students/faculty, marks, attendance आणि notices काढण्यापूर्वी database backups घेतले आहेत. मूळ administrator जतन केला आहे. नंतर वापरकर्त्याच्या स्पष्ट मागणीनुसार दोन demo students, एक demo Staff आणि एक demo Administrator वेगळे तयार केले आहेत. वास्तविक हजेरी, गुण किंवा शिक्षक-विषय वाटप अद्याप भरलेले नसल्यामुळे त्या counts शून्य/Pending दिसतात.

Outer workspace मधील backups:

- `backups/20260920-170956-college-upgrade/prava.sqlite3` आणि counts.
- `backups/20260920-172955-before-seed-cleanup.sqlite3`.
- `backups/20260920-before-catalogue-source-alignment.sqlite3`.

`seed.py` हा जुन्या sample-data अभ्यासाचा script आहे; या कॉलेजच्या वास्तविक नोंदी भरताना तो वापरू नका. `flask --app run:app sync-college` catalogue setup पुन्हा चालवता येतो; विद्यमान Office edits जतन करण्याची चाचणी आहे.

## 10. पडताळणी आणि कॉलेजकडून आवश्यक पुढील माहिती

पूर्ण unittest suite: **62 tests passed**. Login व department isolation, Principal read-only access, CSV preview ownership आणि atomic import, inactive sessions, CSRF, syllabus publication, teaching allocation, marks boundaries, notification targeting आणि activity ownership/completion तपासले आहेत. Account switching, remember-cookie cleanup, demo-mode controls आणि student sign-up/approval समाविष्ट आहेत. चारही demo खात्यांचे प्रत्यक्ष browser login केले आहेत. Desktop day/night आणि mobile layout तपासले आहेत; वेगळ्या downloaded-folder simulation मध्ये launcher ने fresh environment, catalogue व खाती तयार केली. Launcher restart मध्ये database टिकतो. Bootstrap styles, icons आणि scripts repository मध्ये आहेत, त्यामुळे setup नंतर local interface साठी बाह्य CDN आवश्यक नाही; external syllabus/source links साठी internet लागतो.

उरलेल्या अचूक माहितीचा क्रम:

1. कॉलेजने अंतिम मान्य केलेला SY B.Sc. (Computer Applications) PDF आणि TY सविस्तर 2024 NEP PDF.
2. Home Science TY चा अधिकृत लागू NEP PDF; SY minor codes/assessment बाबत कॉलेजची स्पष्टता.
3. प्रत्येक batch ची AEC/VEC/OE/minor/elective निवड, passing आणि grading/SGPA/CGPA नियम.
4. खरी विद्यार्थी यादी, staff employee IDs व emails, semester enrollment आणि शिक्षक-विषय वाटप.
5. प्रत्यक्ष academic calendar आणि कॉलेजने मान्य केलेल्या activity/certificate पडताळणीची जबाबदारी.

ही माहिती मिळाल्यावर तयार असलेल्या Office workflow मधून नोंदी भरता येतात. Pending syllabus आणि grading माहिती source मिळाल्यावरच प्रकाशित/सक्रिय करायची आहे.
