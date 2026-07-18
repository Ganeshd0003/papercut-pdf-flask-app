# PaperCut PDF — Flask PDF Toolkit

A production-ready, original Flask web app offering 16 PDF/image tools
(merge, split, compress, rotate, watermark, page numbers, protect/unlock,
organize, delete/extract pages, PDF↔JPG, PDF↔Word, OCR), with user
accounts, processing history, an admin panel, and automatic file cleanup.

This is an independent implementation with its own branding/UI/code —
it does not copy iLovePDF's code, assets, or branding.

## 1. Requirements

- Python 3.11+
- **Poppler** (for `pdf2image`, used indirectly by some workflows)
  - macOS: `brew install poppler`
  - Ubuntu/Debian: `sudo apt install poppler-utils`
- **Tesseract OCR** (for the OCR tool)
  - macOS: `brew install tesseract`
  - Ubuntu/Debian: `sudo apt install tesseract-ocr`
- **LibreOffice** (for Word → PDF conversion on Linux servers; Windows/Mac
  use `docx2pdf` + MS Word instead)
  - Ubuntu/Debian: `sudo apt install libreoffice`
- **qpdf** is bundled via `pikepdf`, no separate install needed.

## 2. Setup

```bash
cd pdf_app
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# edit .env and set a real SECRET_KEY

python app.py
```

The app will be live at `http://localhost:5000`. SQLite is used by
default (`app.db` is created automatically on first run).

## 3. Create an admin user

```bash
# 1. Register a normal account at /auth/register in the browser
# 2. Then promote it from the CLI:
flask make-admin you@example.com
```

Admin panel lives at `/admin` once you're logged in as an admin.

## 4. Switching to PostgreSQL

Just change `DATABASE_URL` in `.env`, e.g.:

```
DATABASE_URL=postgresql://user:password@localhost:5432/papercut
```

Install `psycopg2-binary` and rerun the app — SQLAlchemy handles the rest.

## 5. Production notes

- Run behind Gunicorn + a reverse proxy (Nginx):
  `gunicorn -w 4 -b 0.0.0.0:8000 "app:create_app()"`
- Set `FLASK_ENV=production` in `.env`.
- Put a real secret key in `SECRET_KEY` — never use the default.
- The in-process cleanup thread works for a single worker; for
  multi-worker/multi-server deployments, move `cleanup_expired_files()`
  into a cron job or Celery beat task instead (see `utils.py`).
- Swap `RATELIMIT_STORAGE_URI` to Redis (`redis://...`) for multi-worker
  rate limiting — `memory://` only works per-process.

## 6. Project structure

```
pdf_app/
├── app.py              # App factory, CLI commands, error handlers, cleanup thread
├── config.py            # Environment-based configuration
├── extensions.py         # db, login_manager, csrf, limiter, migrate
├── models.py             # User, ProcessingJob
├── forms.py              # All Flask-WTF forms (CSRF-protected)
├── utils.py               # Filename safety, MIME sniffing, page-range parsing, cleanup job
├── requirements.txt
├── routes/
│   ├── main.py           # Homepage, pricing, FAQ
│   ├── auth.py            # Register/login/logout (rate-limited)
│   ├── tools.py            # All 16 tool endpoints + download
│   ├── dashboard.py         # User profile, history, subscription
│   └── admin.py              # Admin dashboard, users, files, analytics, settings
├── services/
│   ├── pdf_service.py     # Actual PDF/image manipulation (PyMuPDF, pikepdf, Pillow, reportlab)
│   └── file_service.py     # Upload validation + ProcessingJob bookkeeping
├── templates/              # Bootstrap 5 templates, dark/light mode, all pages
├── static/
│   ├── css/style.css        # Theme, cards, dropzone, animations
│   └── js/
│       ├── main.js           # Dark/light toggle
│       └── tool-upload.js     # Drag & drop, AJAX submit, progress bar, page reorder
├── uploads/                 # Temp uploaded files (auto-cleaned)
└── processed/                # Temp output files (auto-cleaned)
```

## 7. Security features implemented

- CSRF protection on every form and AJAX POST (Flask-WTF)
- Rate limiting per route (Flask-Limiter)
- File size cap (`MAX_CONTENT_LENGTH`, default 100MB)
- Real MIME-signature sniffing, not just extension trust
- `secure_filename()` + UUID prefixing (prevents collisions/traversal)
- Passwords hashed with Werkzeug's `generate_password_hash`
- Automatic deletion of uploaded/processed files after a configurable
  retention window (default 60 minutes), via a background sweep

## 8. Known limitations to be aware of

- Word→PDF on Linux requires LibreOffice installed on the server (there's
  no pure-Python equivalent of MS Word's renderer).
- OCR requires the Tesseract binary — the Python package only binds to it.
- The in-process cleanup thread is fine for one worker; use a real
  scheduler in multi-worker production deployments.
- Subscription/billing is stubbed (`dashboard/subscription.html`) —
  wire in Stripe/Paddle yourself for real payments.
