# PRAVA profile avatars

Student, staff and administrator profiles display an uploaded photo when one is saved. Otherwise they use the recorded gender to select an illustrated avatar. Unspecified/Other gender uses the PRAVA mark. Names are never used to infer gender. These illustrations do not represent real people.

Edit Profile accepts JPG, PNG, GIF and WEBP photos. Student gender remains on the student record; staff and administrator gender is stored on the user record. Existing photos remain unchanged when gender changes. Run the usual launcher to back up and upgrade an existing local database.

Assets were generated using the built-in image generation tool on 5 October 2026, then copied into the project:

- `app/static/img/profile-female.png`
- `app/static/img/profile-male.png`

Female avatar prompt:

> Create a single square professional profile avatar for a college academic portal: a generic Indian adult woman with neatly tied-back dark hair, wearing a plain navy professional collared top, centered front-facing head-and-shoulders portrait. Refined soft 3D illustration, simplified non-identifying face, friendly neutral expression, light blue and lavender studio background. Crisp clean silhouette, generous space around head, suitable for both female students and female staff. No lettering, logo, watermark, border, or graduation cap. Clearly an illustrative avatar, not a photo of a real person.

Short-haired avatar prompt (the generated result is used for Male):

> Create one square profile avatar asset for a professional college academic portal. A refined non-photorealistic 3D head-and-shoulders human avatar with deliberately simplified, non-identifying, gender-neutral features, a plain navy collared top, centered and front-facing. Elegant soft blue and lavender studio background, subtle ambient light, crisp silhouette, uncluttered composition, generous space around the head. Suitable for students, staff and administrators as an illustrative placeholder until they upload their own photo. No lettering, no logos, no watermark, no border, no graduation cap. This is a generic avatar, not a portrait of a real person.
