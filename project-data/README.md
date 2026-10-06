# Included project data

The GitHub **Code → Download ZIP** snapshot contains **174 local project accounts: 160 students (80 BCA, 80 Home Science), 11 faculty and 3 administration accounts**. Vaishnavi Vijay Kale and Rutuja Ashok Khobare remain in TY BCA. The bundled database contains no working password hashes, and the repository contains no usable login handout.

Run `START-PRAVA.cmd` from a newly extracted project folder. The launcher verifies the snapshot, restores the database and uploaded files, and generates a separate random password for every account in that installation. It saves the private login list as:

- `instance/PRAVA_Local_Login_Details.txt`
- `instance/PRAVA_Local_Login_Details.csv`

Open the text file to find an account by name, or open the CSV in Excel. These files are ignored by Git and belong only to that installation. Each new installation has different passwords. Do not use a login PDF or handout from another computer for the new installation.

An existing `instance/prava.sqlite3` is preserved: the launcher does not replace its records or reset its passwords. Restarting an installation preserves its current credentials. Password changes made later through the portal do not rewrite an earlier handout; an administrator can reset an individual account when needed. Previously issued private PDFs remain private and apply only to their original installation and unchanged passwords.

The snapshot includes profiles, subject allocations, timetable, attendance, marks, assignments, learning materials, notifications, activities and saved academic-year history. Bundled accounts use local project mode. `-WithoutDemo` skips snapshot restoration for an empty installation and disables bundled-account login.

Profiles include owner-supplied form responses and user-requested illustrative records. Generated academic records are presentation data, not official college results. Profile illustrations are generic avatars. Official NEP grade/SGPA rules remain to be configured, so grade labels can show **Pending** even when scores and attendance are present.

`manifest.json` records the snapshot date, counts and SHA-256 checksums. The snapshot is a saved version, not live synchronization: edits on a laptop remain in its own database. Before changing folders, keep a private backup of `instance/prava.sqlite3`, `app/static/uploads/` and the local login files. Preserve the old folder, stop its server, and extract the latest ZIP into a new folder to see the latest bundled project data. Never add the private login files, session secrets, import handouts or credential encryption key to the public repository.
