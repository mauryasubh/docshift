# ============================================================
#  DocShift — Windows PowerShell Setup & Start Script
#  Run this from your project root (where manage.py lives)
#  Usage:
#    First time:  .\setup.ps1 -Setup
#    Every time:  .\setup.ps1
# ============================================================

param(
    [switch]$Setup   # Pass -Setup for first-time installation
)

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

Write-Host ""
Write-Host "  ____             ____  _     _  __ _   " -ForegroundColor Cyan
Write-Host "  |  _ \  ___  ___|  _ \| |__ (_)/ _| |_ " -ForegroundColor Cyan
Write-Host "  | | | |/ _ \/ __| |_) | '_ \| | |_| __|" -ForegroundColor Cyan
Write-Host "  | |_| | (_) \__ \  __/| | | | |  _| |_ " -ForegroundColor Cyan
Write-Host "  |____/ \___/|___/_|   |_| |_|_|_|  \__|" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Django + Celery + Redis — Document Processing" -ForegroundColor Gray
Write-Host "  ───────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""

# ── Activate virtualenv ───────────────────────────────────────
if (Test-Path ".\venv\Scripts\Activate.ps1") {
    Write-Host "[ ] Activating virtual environment..." -ForegroundColor Yellow
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "[+] venv activated" -ForegroundColor Green
} else {
    Write-Host "[!] No venv found. Creating one..." -ForegroundColor Yellow
    python -m venv venv
    & ".\venv\Scripts\Activate.ps1"
    Write-Host "[+] venv created and activated" -ForegroundColor Green
}

# ── First-time setup ──────────────────────────────────────────
if ($Setup) {
    Write-Host ""
    Write-Host "=== FIRST-TIME SETUP ===" -ForegroundColor Cyan
    Write-Host ""

    Write-Host "[ ] Installing Python dependencies..." -ForegroundColor Yellow
    pip install -r requirements.txt --quiet
    Write-Host "[+] Dependencies installed" -ForegroundColor Green

    Write-Host "[ ] Running database migrations..." -ForegroundColor Yellow
    python manage.py migrate
    Write-Host "[+] Migrations done" -ForegroundColor Green

    Write-Host "[ ] Collecting static files..." -ForegroundColor Yellow
    python manage.py collectstatic --noinput 2>$null
    Write-Host "[+] Static files collected" -ForegroundColor Green

    Write-Host ""
    Write-Host "[ ] Creating admin superuser..." -ForegroundColor Yellow
    Write-Host "    (Enter your desired admin username, email and password)" -ForegroundColor Gray
    python manage.py createsuperuser

    Write-Host ""
    Write-Host "=== SETUP COMPLETE ===" -ForegroundColor Green
    Write-Host ""
    Write-Host "  Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Install argostranslate models for Stage 3 translator" -ForegroundColor White
    Write-Host "     python -c `"import argostranslate.package; argostranslate.package.install_from_path(r'C:\path\to\translate-fr_en-1_9.argosmodel')`"" -ForegroundColor Gray
    Write-Host "     python -c `"import argostranslate.package; argostranslate.package.install_from_path(r'C:\path\to\translate-en_fr-1_9.argosmodel')`"" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. Configure OAuth in Django admin (see GUIDE.md)" -ForegroundColor White
    Write-Host ""
    Write-Host "  3. Run the app: .\setup.ps1" -ForegroundColor White
    Write-Host ""
    exit 0
}

# ── Check Redis ───────────────────────────────────────────────
Write-Host "[ ] Checking Redis..." -ForegroundColor Yellow
try {
    $ping = redis-cli ping 2>$null
    if ($ping -eq "PONG") {
        Write-Host "[+] Redis is running" -ForegroundColor Green
    } else {
        throw "not running"
    }
} catch {
    Write-Host "[!] Redis not running. Starting redis-server.exe..." -ForegroundColor Yellow
    if (Test-Path ".\redis-server.exe") {
        Start-Process -FilePath ".\redis-server.exe" -WindowStyle Minimized
        Start-Sleep -Seconds 2
        Write-Host "[+] Redis started" -ForegroundColor Green
    } else {
        Write-Host "[X] redis-server.exe not found in project root." -ForegroundColor Red
        Write-Host "    Download from: https://github.com/microsoftarchive/redis/releases" -ForegroundColor Gray
        Write-Host "    Place redis-server.exe in: $ProjectRoot" -ForegroundColor Gray
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# ── Apply migrations ──────────────────────────────────────────
Write-Host "[ ] Applying migrations..." -ForegroundColor Yellow
python manage.py migrate --run-syncdb -q
Write-Host "[+] Migrations applied" -ForegroundColor Green

# ── Start Celery Worker in new window ────────────────────────
Write-Host "[ ] Starting Celery worker..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "cd '$ProjectRoot'; .\venv\Scripts\Activate.ps1; Write-Host 'CELERY WORKER' -ForegroundColor Cyan; celery -A docshift worker --loglevel=info --pool=solo" `
    -WindowStyle Normal
Write-Host "[+] Celery worker started (new window)" -ForegroundColor Green

Start-Sleep -Seconds 2

# ── Start Celery Beat in new window ──────────────────────────
Write-Host "[ ] Starting Celery beat..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList `
    "-NoExit", "-Command", `
    "cd '$ProjectRoot'; .\venv\Scripts\Activate.ps1; Write-Host 'CELERY BEAT' -ForegroundColor Magenta; celery -A docshift beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler" `
    -WindowStyle Normal
Write-Host "[+] Celery beat started (new window)" -ForegroundColor Green

Start-Sleep -Seconds 1

# ── Start Django ──────────────────────────────────────────────
Write-Host ""
Write-Host "  ──────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Web app:   http://127.0.0.1:8000" -ForegroundColor Cyan
Write-Host "  Admin:     http://127.0.0.1:8000/admin" -ForegroundColor Cyan
Write-Host "  Editor:    http://127.0.0.1:8000/editor/" -ForegroundColor Cyan
Write-Host "  Translator:http://127.0.0.1:8000/translator/" -ForegroundColor Cyan
Write-Host "  ──────────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Press Ctrl+C to stop Django server" -ForegroundColor Gray
Write-Host ""

python manage.py runserver
