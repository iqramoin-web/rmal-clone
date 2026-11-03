# RMAL Hospitality — static mirror

A 1:1 static copy of https://rmal.crackwits.com (English and Arabic), served as plain files.

- Pages live at `en/…/index.html` and `ar/…/index.html`; `/` redirects to `/en`.
- Next.js image-optimizer URLs were rewritten to the original files in `api/media/file/`.
- The contact form posts to `/api/contact`, which does not exist here, so enquiries are not sent.
