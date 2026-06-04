<p align="center">
  <strong>🔷 DocShift</strong><br>
  <em>All-in-one document conversion, editing & processing platform</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Django-4.2-green?style=flat-square&logo=django" alt="Django">
  <img src="https://img.shields.io/badge/Celery-5.x-green?style=flat-square" alt="Celery">
  <img src="https://img.shields.io/badge/Redis-Queue-red?style=flat-square&logo=redis" alt="Redis">
  <img src="https://img.shields.io/badge/License-Private-lightgrey?style=flat-square" alt="License">
</p>

---

## ✨ Features

### 📄 PDF Tools (14 tools)
Compress, Merge, Split, PDF to Images, PDF to Word, PDF to Excel, PDF to PowerPoint, Extract Text, Extract Images, OCR (Searchable PDF), Password Protect, Unlock, Rotate (live preview), Watermark, Page Numbers, Edit Metadata, Flatten, Grayscale, Crop

### 📁 Office Conversion
DOCX → PDF, Excel → PDF, PowerPoint → PDF, TXT → PDF, HTML → PDF

### 🖼️ Image Tools
Image → PDF, JPG → PNG, PNG → JPG, Resize Image

### ✏️ PDF Editor
Interactive browser-based PDF editor with annotation, text editing, and save support

### 🔌 Developer API
REST API with Bearer token authentication, webhook support, and Stripe-based subscription billing

### 🔐 Authentication
Google & GitHub OAuth (via django-allauth), email/password signup, user dashboard with history, analytics charts, CSV export

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 4.2, Python 3.12 |
| Task Queue | Celery 5.x + Redis |
| PDF Engine | PyMuPDF (fitz), ReportLab, pdfplumber |
| OCR | Tesseract via pytesseract |
| Office | python-docx, openpyxl, python-pptx |
| Storage | Local filesystem or Cloudflare R2 / AWS S3 (via django-storages) |
| Auth | django-allauth (Google, GitHub OAuth) |
| Payments | Stripe Checkout + Webhooks |
| Static Files | WhiteNoise |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Deployment | Gunicorn, Docker, Railway / Render ready |

---

## 🚀 Local Setup

### Prerequisites

- **Python 3.12+** — [Download](https://www.python.org/downloads/)
- **Redis** — [Download](https://redis.io/download) (required for Celery task queue)
- **Tesseract OCR** *(optional, for OCR tool)* — [Download](https://github.com/tesseract-ocr/tesseract)
- **PostgreSQL** *(optional, SQLite works for dev)* — [Download](https://www.postgresql.org/download/)
- **Git** — [Download](https://git-scm.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/mauryasubh/docshift.git
cd docshift
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note (Windows):** If `pytesseract` fails, make sure [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) is installed and added to your PATH, or set `TESSERACT_CMD` in your `.env`.

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# ── Core Django ──────────────────────────────────────────
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DJANGO_SECRET_KEY=your-secret-key-here

# ── Database ─────────────────────────────────────────────
# Option A: SQLite (default, no config needed)
# USE_POSTGRES=False

# Option B: PostgreSQL
# USE_POSTGRES=True
# DB_NAME=docshift
# DB_USER=postgres
# DB_PASSWORD=your_password
# DB_HOST=127.0.0.1
# DB_PORT=5432

# ── Celery (Redis) ───────────────────────────────────────
# CELERY_BROKER_URL=redis://localhost:6379/0

# ── Storage (optional — for cloud file storage) ─────────
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_STORAGE_BUCKET_NAME=docshift-media
# AWS_S3_ENDPOINT_URL=https://your-r2-endpoint

# ── Payments (optional — Stripe) ────────────────────────
# STRIPE_PUBLIC_KEY=pk_test_...
# STRIPE_SECRET_KEY=sk_test_...
# STRIPE_WEBHOOK_SECRET=whsec_...

# ── OCR (optional — Windows default shown) ──────────────
# TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 5. Run Database Migrations

```bash
python manage.py migrate
```

### 6. Collect Static Files

```bash
python manage.py collectstatic --noinput
```

### 7. Start Redis

Make sure Redis is running on `localhost:6379`:

```bash
# Windows (if using Memurai or Redis for Windows)
redis-server

# macOS (Homebrew)
brew services start redis

# Linux
sudo systemctl start redis
```

### 8. Start the Celery Worker

Open a **new terminal** (with venv activated):

```bash
# Windows
celery -A docshift worker --loglevel=info --pool=solo

# macOS / Linux
celery -A docshift worker --loglevel=info
```

### 9. (Optional) Start Celery Beat

For scheduled tasks like job cleanup, open another terminal:

```bash
celery -A docshift beat --loglevel=info
```

### 10. Start the Dev Server

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000/** 🎉

---

## 📂 Project Structure

```
docshift/
├── converter/          # Core conversion tools (14+ PDF, office, image tools)
│   ├── models.py       # ConversionJob model
│   ├── views.py        # Upload, dashboard, job status views
│   ├── tasks.py        # Celery tasks for all conversions
│   ├── forms.py        # Upload forms with validation
│   └── utils.py        # File validation, helpers
├── editor/             # PDF Editor app
│   ├── views.py        # Editor session management
│   └── tasks.py        # PDF analysis & save tasks
├── api/                # Developer REST API + Stripe billing
│   ├── views.py        # API endpoints, Stripe checkout/webhooks
│   ├── models.py       # API Profile, keys, quotas
│   └── utils.py        # Rate limiting, auth middleware
├── docshift/           # Django project config
│   ├── settings.py     # All settings (env-driven)
│   ├── urls.py         # Root URL routing
│   ├── celery.py       # Celery app init
│   └── wsgi.py         # WSGI entry point
├── templates/          # HTML templates
│   ├── base.html       # Base layout with navbar
│   ├── index.html      # Landing page
│   ├── dashboard.html  # User dashboard
│   └── ...
├── static/css/         # Stylesheets
├── media/              # User uploads (gitignored)
├── requirements.txt    # Python dependencies
├── Procfile            # Process config (Render/Railway)
├── Dockerfile          # Docker build
├── runtime.txt         # Python version (3.12.7)
└── .env                # Environment variables (gitignored)
```

---

## 🌐 Production Deployment

### Environment Variables (Required)

```env
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<strong-random-key>
DJANGO_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgres://user:pass@host:5432/dbname
CELERY_BROKER_URL=redis://your-redis-host:6379/0
```

### Procfile (Render / Railway)

```
web: gunicorn docshift.wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120
worker: celery -A docshift worker --loglevel=info --concurrency=2
beat: celery -A docshift beat --loglevel=info
```

### Docker

```bash
docker build -t docshift .
docker run -p 8000:8000 --env-file .env docshift
```

### Security Notes

When `DEBUG=False`, the app automatically enables:
- HTTPS redirect (`SECURE_SSL_REDIRECT`)
- Secure cookies (`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`)
- CSRF trusted origins from `ALLOWED_HOSTS`

---

## 🧪 Quick Checks

```bash
# Validate Django configuration
python manage.py check

# Run migrations check
python manage.py showmigrations

# Test static file collection
python manage.py collectstatic --noinput --dry-run
```

---

## 👤 Author

**Subhash Maurya** — Designed & Built  
[GitHub](https://github.com/mauryasubh)
