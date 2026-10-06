# Student accounts, imports and retained academic records

Updated for the 6 October 2026 local project snapshot.

## Included accounts

The snapshot contains **160 students, 11 faculty and 3 administration accounts: 174 accounts altogether**. These totals describe a fresh installation of the bundled snapshot; additions, removal and restoration in an existing installation change its current roster.

| Programme | First Year | Second Year | Third Year | Total |
| --- | ---: | ---: | ---: | ---: |
| BCA | 25 | 27 | 28 | 80 |
| Home Science — Food Science and Nutrition (`BSC-FSN`) | 13 | 14 | 14 | 41 |
| Home Science — Textiles (`BSC-TEXTILE`) | 12 | 13 | 14 | 39 |
| **Home Science combined** | **25** | **27** | **28** | **80** |
| **All students** | **50** | **54** | **56** | **160** |

Vaishnavi Vijay Kale and Rutuja Ashok Khobare remain in the BCA cohort. The supplied profiles and owner-requested generated project records are retained separately by their record source. Generated contact details, attendance, assessment marks, coursework and previous-year summaries are presentation data, not verified college records or official results. Unconfirmed NEP grading requirements remain marked pending verification.

The public snapshot contains no usable passwords or working password hashes. On the first launch in a new folder, `START-PRAVA.cmd` assigns a separate random password to every account and writes the private files `instance/PRAVA_Local_Login_Details.txt` and `instance/PRAVA_Local_Login_Details.csv`. Use the handout created by that installation; a different installation receives different passwords. These files are ignored by Git. Keep a private backup and share each person only their own login details.

An existing local database and its passwords remain unchanged. The previously supplied private login PDF remains valid only for the original installation, while its passwords are unchanged; it does not describe a fresh ZIP installation. Password changes made later through the website do not rewrite an earlier handout. Newly imported accounts use the separate private one-time download described below.

## Principal and administration workspace

Sign in through **Login → Office / Administration**, then open **Students**. The Principal can create and edit student accounts, set login IDs/passwords, import rosters, and remove or restore selected students. Creating Office / Principal access accounts remains restricted to the main Administrator. Public sign-up requests retain their separate Office approval workflow.

To add one student:

1. Select **Add student**.
2. Enter the student's name, login username, email, enrollment number, programme, curriculum, semester and admission year.
3. Add profile details, gender and practical batch where known. Match programme and curriculum so that the correct subjects, timetable and teaching roster are connected.
4. Set a password of at least eight characters and enable **Active** when the account is ready for login.
5. Select the record source and save. Share that student's login details directly with them.

Use **Edit** to correct the profile or login ID. A blank password field preserves the existing password; entering a new password replaces it. Existing usernames, emails and enrollment numbers cannot be reused for another account, including when the original account is removed. Student creation always creates the student role.

If another officer changes or removes the account while an Edit form is open, the older form is rejected and its entered profile values remain visible. Copy any draft values you need, select **reload the latest student record**, review the saved changes and enter a new password again if required. Saving an old form cannot overwrite newer profile or login changes.

## Directory filters and source labels

The directory offers name/login ID/email/enrollment search and programme, year, gender, account status and record source filters. Year groups the two corresponding semesters. **Current students** includes active and inactive accounts that have not been removed. **Active login** and **Inactive login** narrow these states; **Removed students** lists retained accounts awaiting possible restoration.

| Record source | Meaning |
| --- | --- |
| Provided | Information entered from a student or college record |
| Imported | Information created through a registration/roster import |
| Generated project record | Information created for the local project presentation |

Source labels are visible in administration tools. They are independent of the local-account authentication flag; a bundled account is not automatically classified as generated. Verify the source before removing a group.

## Remove selected students and restore them

1. Apply filters and select the required rows. **Select generated records** selects generated, currently unremoved records in the visible list.
2. Click **Remove selected**. The confirmation popup lists every selected name and enrollment number and shows the account count.
3. Check those names, enter an optional reason, tick the confirmation checkbox, then confirm. One request can contain up to 500 students.
4. The selected accounts are removed from current class rosters and cannot log in. Existing sessions are denied on their next protected-page request.

This operation retains the Student and User records, passwords, attendance, marks, submissions, activity participation and saved academic-year history. It records the removal time and reason and writes an audit entry identifying the acting account. No related academic rows are deleted.

To restore, select **Account status → Removed students → Apply filters**. Select the accounts or use the row's **Restore** button, then confirm the names in the popup. Restoration enables login and returns the student to the matching active teaching rosters. Existing login IDs and passwords remain valid. Removal and restoration audit entries remain available after restoration. Editing a removed profile cannot silently enable its login; use Restore explicitly.

Mixed selections of removed and current students are not accepted for the same action. Invalid IDs, changed removal state or a mismatched selection count cause the whole request to fail without a partial update. An ordinary inactive account can instead be activated through Edit; inactivity and removal are separate states.

## Import an Excel or CSV roster

Open **Import college records**, available to Principal, Office and main Administrator.

1. Download the **Student Excel template** or **Staff Excel template**. UTF-8 CSV templates are also available.
2. Fill the **Roster** sheet, one person per row. Preserve the template's column names and order. Each upload supports 1–200 records and a maximum file size of 1 MB.
3. Enter names and valid email addresses. Username and enrollment/employee ID can be left blank to generate unique IDs, or enter the existing college IDs. Generated values are shown in the preview before saving.
4. For students, choose `BCA`, `BSC-FSN` or `BSC-TEXTILE`, use the matching curriculum pattern such as `2024 NEP`, and enter semester and admission year. Use `YYYY-MM-DD` for dates and text cells for mobile numbers.
5. Upload the file and select **Validate & preview**. Resolve the reported row errors, including duplicate usernames, emails or IDs. An existing removed account still owns its IDs; restore it rather than creating a duplicate.
6. Check every row, then select **Create accounts and generate passwords**. The entire batch is validated again before committing. Confirmed accounts are immediately active and receive individual random passwords.
7. Download the private CSV login handout **once within one hour of creation**. It contains the person's name, programme/department, college ID, login ID, password and correct login page. Open it in Excel and share only each person's own row.

If you leave the download page, return to **Import college records → Login handouts awaiting download** within that hour. The handout is accessible only to its creating account, is encrypted while temporarily stored and is removed from the server after successful download. Expiry does not disable the imported accounts. For a lost password, use the account editor to set a replacement; the original password cannot be recovered from its hash.

Student template columns:

`full_name`, `username`, `email`, `enrollment_number`, `programme`, `pattern`, `semester`, `admission_year`, `mobile_number`, `gender`, `date_of_birth`, `address`, `practical_batch`.

Staff template columns:

`full_name`, `username`, `email`, `employee_id`, `department`, `qualification`, `mobile_number`, `gender`, `joining_date`.

Contact/profile fields are optional. Fill formula results as values; Excel formulas, errors, macros and external workbook links are rejected. Importing staff creates accounts and profiles; allocate their subjects or class-teacher responsibilities separately. Importing students connects them to the selected programme/semester, while teachers subsequently enter their actual attendance and marks.

The account/password import flow uses local authentication. When optional Supabase Auth is enabled, external identities must be provisioned through that deployment's matching workflow; this local automatic-password import is unavailable. Google Forms responses are not automatically imported: verify the responses, then map them into the PRAVA template.

## Academic history and local copies

Current-year records and saved previous-year summaries remain associated with the same student ID after removal and restoration. Administration and the current class teacher can review the full academic record; other assigned faculty remain scoped to their subjects. Retaining these records supports historical review and prevents loss when a presentation account is removed from current lists.

Students use **Academic history** in their sidebar to choose an available academic year. Administration and teachers open the student record, then **View academic year history**. Generated historical summaries explicitly retain their source; they are not a claim that teachers entered those events at the historical date. Current attendance entry audit times reflect the actual save/update time, separate from the lecture's scheduled date/time.

The launcher preserves an existing `instance/prava.sqlite3` and its saved accounts. It does not overwrite it with a newer GitHub snapshot. To inspect the updated bundled cohort, extract the latest ZIP into a new folder and run that folder's launcher. Keep the old folder and its uploads when preserving local work. Different laptops have independent databases; importing, removing or editing on one laptop does not automatically update the other.

## Quick verification

- Sign in as Principal and confirm Students shows the expected programme/year counts for the current installation.
- Add a student, sign in with the saved credentials, and check the linked programme/semester.
- Remove one selected account after checking the popup; verify it leaves the teaching roster and cannot log in.
- Open Removed students, restore that account, and verify its previous marks and attendance remain.
- Import a small roster preview, confirm it once, download the private handout, and check a created account's login and programme.

The regression tests cover role scope, profile and password editing, source filtering, confirmation, atomic removal/restore, retained marks/attendance, teaching rosters, session blocking and CSRF. See [README setup instructions](../README.md) for running the complete isolated test suite.
