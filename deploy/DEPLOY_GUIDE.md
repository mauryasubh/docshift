# 🚀 DocShift — Render Deployment Guide

## Overview
This guide deploys DocShift to **Render.com** with:
- Django Web Service (Gunicorn)
- Celery Worker (Background tasks)
- PostgreSQL (Managed database)
- Redis (Task broker)

---

## Prerequisites

Before you start:
1. ✅ A **GitHub account** with your DocShift code pushed to a repo
2. ✅ A free **Render account** at https://render.com (sign up with GitHub)
3. ✅ Your **Stripe keys** (from your .env — you already have these)

---

## Step-by-Step Deployment

### Step 1: Push Code to GitHub

If you haven't already, create a GitHub repo and push your code:

```bash
cd C:\Users\maury\OneDrive\Desktop\docshift\docshift
git init
git add .
git commit -m "Initial commit - DocShift platform"
git remote add origin https://github.com/YOUR_USERNAME/docshift.git
git push -u origin main
```

> ⚠️ **IMPORTANT**: Make sure `.env` is in your `.gitignore`!
> Your Stripe keys and DB password should NEVER be pushed to GitHub.

---

### Step 2: Create Services on Render

Go to https://dashboard.render.com and create these 4 services:

#### 2a. PostgreSQL Database
1. Click **"New +"** → **"PostgreSQL"**
2. Name: `docshift-db`
3. Region: Choose closest to you (e.g., Oregon or Singapore)
4. Plan: **Free** (90 days) or **Starter $7/mo**
5. Click **"Create Database"**
6. Copy the **Internal Database URL** (looks like `postgres://user:pass@host:5432/dbname`)

#### 2b. Redis Instance
1. Click **"New +"** → **"Redis"**
2. Name: `docshift-redis`
3. Plan: **Free** (25MB — more than enough)
4. Click **"Create Redis"**
5. Copy the **Internal Redis URL** (looks like `redis://red-xxxx:6379`)

#### 2c. Web Service (Django)
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repo
3. Configure:
   - **Name**: `docshift-web`
   - **Region**: Same as your database
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `./deploy/build.sh`
   - **Start Command**: `gunicorn docshift.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Plan**: Free
4. Add **Environment Variables** (see Step 3 below)
5. Click **"Create Web Service"**

#### 2d. Background Worker (Celery)
1. Click **"New +"** → **"Background Worker"**
2. Connect the SAME GitHub repo
3. Configure:
   - **Name**: `docshift-worker`
   - **Branch**: `main`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `celery -A docshift worker --loglevel=info --concurrency=2`
   - **Plan**: Free
4. Add the SAME environment variables as the Web Service
5. Click **"Create Background Worker"**

---

### Step 3: Environment Variables

Add these to **BOTH** the Web Service and the Worker:

| Variable | Value |
|----------|-------|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | Generate one: `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
| `DJANGO_ALLOWED_HOSTS` | `docshift-web.onrender.com` (your Render URL) |
| `USE_POSTGRES` | `True` |
| `DATABASE_URL` | *(paste the Internal Database URL from Step 2a)* |
| `CELERY_BROKER_URL` | *(paste the Internal Redis URL from Step 2b)* |
| `STRIPE_PUBLIC_KEY` | Your Stripe publishable key |
| `STRIPE_SECRET_KEY` | Your Stripe secret key |
| `STRIPE_WEBHOOK_SECRET` | Update after setting up Stripe webhook for live domain |
| `PYTHON_VERSION` | `3.12.7` |
| `TESSERACT_CMD` | `tesseract` |

---

### Step 4: After First Deploy

Once the web service is live:

1. **Create superuser** (via Render Shell):
   ```bash
   python manage.py createsuperuser
   ```

2. **Set up Django Sites** (for allauth):
   ```bash
   python manage.py setup_site --domain docshift-web.onrender.com --name DocShift
   ```

3. **Update SITE_ID** in settings if needed (check the admin panel at `/admin/sites/site/`)

4. **Configure Stripe Webhook**:
   - Go to Stripe Dashboard → Developers → Webhooks
   - Add endpoint: `https://docshift-web.onrender.com/api/webhook/stripe/`
   - Select events: `checkout.session.completed`
   - Copy the new webhook secret and update the `STRIPE_WEBHOOK_SECRET` env var

---

## File Reference

| File | Purpose |
|------|---------|
| `deploy/build.sh` | Build script — installs deps, collects static, runs migrations |
| `deploy/render.yaml` | Infrastructure-as-code (optional one-click deploy) |
| `Procfile` | Process definitions for Render |
| `.gitignore` | Prevents secrets and local files from being pushed |
| `runtime.txt` | Specifies Python version |

---

## Troubleshooting

### "Application error" on first deploy
- Check the Render logs (Dashboard → your service → Logs)
- Most common issue: missing environment variable

### Static files not loading
- Make sure `whitenoise` is in MIDDLEWARE
- Run `python manage.py collectstatic` (the build script does this)

### Celery tasks not running
- Check the Worker service logs
- Make sure `CELERY_BROKER_URL` points to your Redis instance

### Database connection refused
- Make sure you're using the **Internal** Database URL (not External)
- Both Web Service and Worker must be in the same Render region

---

## Cost Breakdown

| Service | Free Tier | Paid Tier |
|---------|-----------|-----------|
| Web Service | ✅ Free (spins down after 15 min idle) | $7/mo (always on) |
| Background Worker | ✅ Free (spins down) | $7/mo |
| PostgreSQL | ✅ Free 90 days | $7/mo |
| Redis | ✅ Free 25MB | $10/mo |
| **Total** | **$0/month** (first 90 days) | **$31/month** |
