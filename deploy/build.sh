#!/usr/bin/env bash
# deploy/build.sh — Render build script for DocShift
# This runs during every deploy on Render.

set -o errexit  # Exit on error

echo "=== Installing Python dependencies ==="
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Installing Tesseract OCR ==="
apt-get update && apt-get install -y tesseract-ocr || echo "Tesseract install skipped (may already exist)"

echo "=== Collecting static files ==="
python manage.py collectstatic --noinput

echo "=== Running database migrations ==="
python manage.py migrate --noinput

echo "=== Creating Superuser (if not exists) ==="
python manage.py createsuperuser --noinput || echo "Superuser already exists or variables missing."

echo "=== Build complete ==="
