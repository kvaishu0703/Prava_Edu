# Included project data

This snapshot is included in GitHub's **Code → Download ZIP** at the project owner's explicit request. It contains 35 active project accounts: 21 students (15 BCA, 6 Home Science), 11 staff, and 3 administration accounts. Vaishnavi Vijay Kale and Rutuja Ashok Khobare are included in TY BCA.

Run `START-PRAVA.cmd` from the extracted project folder. On the first run, the launcher verifies the snapshot and copies it to `instance/prava.sqlite3`, then restores its uploaded materials and submissions to `app/static/uploads/`. The launcher leaves an existing local database unchanged. All login details are in [PRAVA_All_Login_Details.txt](../PRAVA_All_Login_Details.txt).

The snapshot includes saved profiles, subject allocations, attendance, marks, assignments, learning materials, notifications and college activities. All bundled accounts use the existing local project mode; their published passwords are disabled when that mode is off. `-WithoutDemo` skips the snapshot when preparing an empty installation.

Profiles include owner-supplied form responses and user-requested illustrative records. Generated academic records are presentation data, not official college results. Profile illustrations are generic avatars. Official NEP grade/SGPA rules remain to be configured, so grade labels can show **Pending** even when scores and attendance are present.

`manifest.json` records the snapshot date, counts and SHA-256 checksums. The snapshot is a saved version, not live synchronization: edits made on a laptop remain in that laptop's database. Keep a backup of `instance/prava.sqlite3` and `app/static/uploads/` before changing project folders. For the latest complete project copy, stop the old server and extract the latest GitHub ZIP into a new folder.
