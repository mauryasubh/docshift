# DocShift — Complete Setup & Feature Guide

## What is DocShift?

DocShift is a full-stack document processing web app built with Django + Celery + Redis.
It has three stages, all running locally on your machine.

| Stage | Feature | Status |
|---|---|---|
| Stage 1 | Document Converter (12 tools) | ✅ Production |
| Stage 2 | PDF Editor | ✅ Beta |
| Stage 3 | Document Translator (FR ↔ EN) | ✅ Beta |

---

## Tech Stack

- **Backend**: Django 4.2 + Celery 5 + Redis
- **Auth**: django-allauth (email, Google, GitHub OAuth)
- **PDF**: PyMuPDF (fitz), ReportLab, python-docx
- **Translation**: argostranslate (offline, no internet needed)
- **Frontend**: Tailwind CSS, HTMX, dark/light mode

---

## Prerequisites

Install these before anything else:

1. **Python 3.10+** — https://www.python.org/downloads/
2. **Redis for Windows** — download `redis-server.exe` and place it in your project folder
3. **Git** (optional) — https://git-scm.com

---

## First-Time Installation

### Step 1 — Create virtual environment

```powershell
cd C:\path\to\docshift\docshift
python -m venv venv
.\venv\Scripts\activate
```

### Step 2 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 3 — Run migrations

```powershell
python manage.py migrate
```

### Step 4 — Create admin account

```powershell
python manage.py createsuperuser
```

### Step 5 — Collect static files

```powershell
python manage.py collectstatic --noinput
```

---

## Installing Stage 3 — Translator

### Copy translator app files

```powershell
xcopy /E /I docshift_stage3_final\translator translator
xcopy /E /I docshift_stage3_final\templates\translator templates\translator
copy docshift_stage3_final\base.html templates\base.html
python manage.py migrate translator
```

### Install translation models (offline)

You need to download two `.argosmodel` files manually from:
https://www.argosopentech.com/argospm/index/

Download:
- `translate-fr_en-1.9.argosmodel`
- `translate-en_fr-1.9.argosmodel`

Then install them (note: filenames use underscores `_` not dots `.`):

```powershell
python -c "import argostranslate.package; argostranslate.package.install_from_path(r'C:\path\to\translate-fr_en-1_9.argosmodel')"
python -c "import argostranslate.package; argostranslate.package.install_from_path(r'C:\path\to\translate-en_fr-1_9.argosmodel')"
```

Verify they installed:

```powershell
python -c "from argostranslate import translate; print([l.code for l in translate.get_installed_languages()])"
# Should print: ['fr', 'en']
```

---

## Running the App (Every Time)

Open **4 separate PowerShell terminals**, all with venv activated:

```powershell
# Activate venv in each terminal first:
.\venv\Scripts\activate
```

| Terminal | Command |
|---|---|
| 1 — Redis | `redis-server.exe` |
| 2 — Django | `python manage.py runserver` |
| 3 — Celery Worker | `celery -A docshift worker --loglevel=info --pool=solo` |
| 4 — Celery Beat | `celery -A docshift beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler` |

Then open: **http://127.0.0.1:8000**

> **Note:** `--pool=solo` is required on Windows. The standard prefork pool
> uses Unix fork() which doesn't exist on Windows.

---

## OAuth Setup (Google + GitHub Login)

### Step 1 — Fix Site domain

1. Go to http://127.0.0.1:8000/admin
2. Click **Sites → Sites → example.com**
3. Change domain to: `127.0.0.1:8000`
4. Change display name to: `DocShift`
5. Save

### Step 2 — Add GitHub OAuth App

1. Go to https://github.com/settings/developers → **New OAuth App**
2. Fill in:
   - Homepage URL: `http://127.0.0.1:8000`
   - Callback URL: `http://127.0.0.1:8000/auth/github/login/callback/`
3. Copy your **Client ID** and **Client Secret**
4. In Django admin → **Social Accounts → Social Applications → Add**:
   - Provider: `GitHub`
   - Client ID: *(your GitHub client ID)*
   - Secret: *(your GitHub secret)*
   - Move `127.0.0.1:8000` to Chosen sites → Save

### Step 3 — Add Google OAuth App

1. Go to https://console.cloud.google.com
2. APIs & Services → Credentials → **Create OAuth 2.0 Client ID**
3. Authorised redirect URI: `http://127.0.0.1:8000/auth/google/login/callback/`
4. Copy your **Client ID** and **Client Secret**
5. In Django admin → **Social Accounts → Social Applications → Add**:
   - Provider: `Google`
   - Client ID: *(your Google client ID)*
   - Secret: *(your Google secret)*
   - Move `127.0.0.1:8000` to Chosen sites → Save

Test at: http://127.0.0.1:8000/auth/login/

---

## Stage 1 — Document Converter

**URL:** http://127.0.0.1:8000

### Available Tools

| Tool | Input → Output |
|---|---|
| Compress PDF | `.pdf` → smaller `.pdf` |
| Merge PDFs | multiple `.pdf` → single `.pdf` |
| Split PDF | `.pdf` → `.zip` of pages |
| PDF to Images | `.pdf` → `.zip` of PNGs |
| PDF to Word | `.pdf` → `.docx` |
| DOCX to PDF | `.docx` → `.pdf` |
| TXT to PDF | `.txt` → `.pdf` |
| Image to PDF | `.jpg/.png/…` → `.pdf` |
| JPG to PNG | `.jpg` → `.png` |
| PNG to JPG | `.png` → `.jpg` |
| Resize Image | any image → resized image |
| Any to PDF | auto-detects → `.pdf` |

### How it works
- Upload file → Celery task created → live status polling → download when done
- Guest files expire in **5 minutes**
- Logged-in user files expire in **24 hours**
- Max upload size: **50 MB**

---

## Stage 2 — PDF Editor (Beta)

**URL:** http://127.0.0.1:8000/editor/

### Features
- Upload any PDF → pages rendered as images
- Click any text block → edit text in right panel
- Change font size, bold/italic, colour
- Replace or remove images
- Highlight / Add Text annotation modes
- Save & download edited PDF

### How it works
- PDF pages are rendered as PNG images via PyMuPDF
- Text blocks are extracted with position data (x, y, w, h)
- JS overlays invisible click targets over each block
- On save: PyMuPDF redacts original text, inserts new text at same position
- Text box auto-expands to fit new content

### Limitations (Beta)
- No real-time text reflow (longer text may overflow visually)
- Scanned PDFs require Tesseract OCR installed separately
- Complex multi-column layouts may have imperfect block detection

---

## Stage 3 — Document Translator (Beta)

**URL:** http://127.0.0.1:8000/translator/

### Features
- Upload `.docx` file
- Select source language (or Auto-detect) and target language
- Download translated `.docx` with formatting preserved
- Bold, italic, headings, tables all translated correctly
- Works 100% offline — no internet required

### Supported Languages
French ↔ English (more languages can be added by installing additional `.argosmodel` files)

### How it works
- Uses **argostranslate** Python library directly (no server needed)
- Translation runs inside the Celery worker — fully offline
- `StanzaSentencizer` is patched out to prevent GitHub download attempts
- Sentence splitting uses regex instead

### Limitations (Beta)
- Only `.docx` files supported (PDF translation coming later)
- Translation quality is open-source level — good for most documents
- Very long documents may take 1–2 minutes to translate

---

## Settings Reference (docshift/settings.py)

| Setting | Default | Description |
|---|---|---|
| `DEBUG` | `True` | Set to `False` in production |
| `MAX_UPLOAD_SIZE` | 50MB | Max file upload size |
| `GUEST_EXPIRY_MINUTES` | 5 | Guest file expiry |
| `USER_EXPIRY_HOURS` | 24 | Logged-in user file expiry |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Redis connection |
| `CELERY_WORKER_POOL` | `solo` | Required for Windows |
| `LIBRETRANSLATE_URL` | `http://127.0.0.1:5000` | Legacy — not used |

---

## Dashboard

| User type | History stored | File expiry |
|---|---|---|
| Guest | Session only (browser) | 5 minutes |
| Logged-in | Database (persistent) | 24 hours |

When a guest logs in, their session jobs are automatically migrated to their account.

---

## Project Structure

```
docshift/
├── manage.py
├── requirements.txt
├── redis-server.exe          ← Redis for Windows
├── docshift/
│   ├── settings.py
│   ├── urls.py
│   └── celery.py
├── converter/                ← Stage 1: 12 conversion tools
├── editor/                   ← Stage 2: PDF editor
├── translator/               ← Stage 3: document translator
│   └── utils.py              ← argostranslate with StanzaSentencizer patch
├── templates/
│   ├── base.html             ← navbar, dark/light mode, all nav pills
│   ├── index.html            ← landing page
│   ├── dashboard.html        ← conversion history
│   ├── editor/
│   └── translator/
└── media/
    ├── uploads/
    ├── outputs/
    ├── editor/
    └── translator/
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `No module named 'cryptography'` | `pip install cryptography>=41.0` |
| Celery worker crashes on Windows | Make sure `--pool=solo` flag is used |
| Blank white page on editor | Template error — check `templates/editor/editor.html` is the latest version |
| `getaddrinfo failed` in translator | Translation uses argostranslate offline — internet not needed, ignore this |
| `StanzaSentencizer() takes no arguments` | Replace `translator/utils.py` with latest version |
| `Model 'fr' not installed` | Install both `.argosmodel` files (see Stage 3 setup above) |
| Redis connection refused | Start `redis-server.exe` in Terminal 1 first |
| OAuth `DoesNotExist` error | Set Site domain to `127.0.0.1:8000` in Django admin |
