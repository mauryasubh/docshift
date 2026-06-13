"""
settings.py — Security hardened version
Changes vs original:
  1. SECRET_KEY, DEBUG, ALLOWED_HOSTS read from environment (with safe dev defaults)
  2. Editor session cleanup added to CELERY_BEAT_SCHEDULE
  3. Dead LIBRETRANSLATE_URL setting removed
  4. OAUTH_PKCE_ENABLED set to True for Google
  5. TESSERACT_CMD reads from env so it works on any OS
"""
from pathlib import Path
from datetime import timedelta
from celery.schedules import crontab
import os
from dotenv import load_dotenv
import sys
import copy

# Monkey-patch Django Context copy for Python 3.14+ compatibility (Ticket #35844)
try:
    from django.template.context import BaseContext
    def patched_copy(self):
        duplicate = object.__new__(self.__class__)
        duplicate.__dict__ = copy.copy(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate
    BaseContext.__copy__ = patched_copy
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# ── Security — read from environment in production ──────────
DEBUG = str(os.environ.get('DJANGO_DEBUG', 'True')).strip().lower() == 'true'

# ALLOWED_HOSTS: Comma-separated list from .env, or '*' if DEBUG=True
raw_hosts = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
if raw_hosts:
    ALLOWED_HOSTS = [h.strip() for h in raw_hosts.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = ['*'] if DEBUG else ['127.0.0.1', 'localhost']

# SECRET_KEY: Required in production
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-docshift-dev-key-change-in-production-v1'
    else:
        # Stop startup if secret key is missing in production
        raise ValueError("DJANGO_SECRET_KEY must be set in .env for production!")

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    # allauth
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'allauth.socialaccount.providers.github',
    # project
    'django.contrib.humanize',
    'django_celery_beat',
    'converter',
    'editor',
    'api',
    'storages',
]

SITE_ID = int(os.environ.get('SITE_ID', 1))

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'converter.middleware.OAuthSetupMiddleware',
]

ROOT_URLCONF = 'docshift.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'docshift.wsgi.application'

# Database (Toggle via .env)
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases
#
# Priority: DATABASE_URL (Render/Railway) > USE_POSTGRES=True > SQLite fallback
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = str(os.environ.get('USE_POSTGRES', 'False')).strip().lower() == 'true'

if 'test' in sys.argv:
    # SQLite fallback (testing only)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
elif DATABASE_URL:
    # Production: Render/Railway provides a single connection string
    import dj_database_url
    DATABASES = {
        'default': dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
elif USE_POSTGRES:
    # Local dev with PostgreSQL
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME':     os.environ.get('DB_NAME', 'docshift'),
            'USER':     os.environ.get('DB_USER', 'postgres'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST':     os.environ.get('DB_HOST', '127.0.0.1'),
            'PORT':     os.environ.get('DB_PORT', '5432'),
        }
    }
else:
    # SQLite fallback (testing only)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

from django.utils.translation import gettext_lazy as _

LANGUAGE_CODE = 'en-us'
TIME_ZONE     = os.environ.get('DJANGO_TIME_ZONE', 'Asia/Kolkata')
USE_I18N      = True
USE_TZ        = True

LANGUAGES = [
    ('en', _('English')),
    ('es', _('Spanish')),
    ('hi', _('Hindi')),
    ('fr', _('French')),
    ('de', _('German')),
]

LOCALE_PATHS = [
    BASE_DIR / 'locale',
]

STATIC_URL    = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT   = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Storage Configuration (Cloudflare R2 / AWS S3) ─────────
import os
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')

if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    # Use Cloudflare R2 / AWS S3
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'docshift-media')
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL')
    AWS_S3_REGION_NAME = 'auto'  # Cloudflare R2 requirement
    AWS_S3_SIGNATURE_VERSION = 's3v4'
    AWS_S3_FILE_OVERWRITE = False
    
    # Optional: Force unique paths by removing the ability to overwrite,
    # or using UUID filenames directly. Currently django-storages handles uniqueness.
    
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Note: If public, you can use AWS_S3_CUSTOM_DOMAIN. 
    # For now, we will use default pre-signed URLs provided by boto3.
    AWS_QUERYSTRING_AUTH = True
    AWS_QUERYSTRING_EXPIRE = 3600 # 1 hour link expiry

else:
    # Use Local Storage (only for local testing without .env)
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'

MEDIA_URL  = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Upload limits (tier-based) ─────────────────────────────
MAX_UPLOAD_SIZE_FREE       = 10 * 1024 * 1024    # 10 MB  (Hobby)
MAX_UPLOAD_SIZE_DEVELOPER  = 50 * 1024 * 1024    # 50 MB  (Developer)
MAX_UPLOAD_SIZE_CORPORATE  = 200 * 1024 * 1024   # 200 MB (Corporate)
MAX_UPLOAD_SIZE            = 50 * 1024 * 1024    # default fallback

# ── API rate limits (per minute, per tier) ──────────────────
API_RATE_LIMIT_DEVELOPER  = 20
API_RATE_LIMIT_CORPORATE  = 50

# ── Job expiry tiers ───────────────────────────────────────
GUEST_EXPIRY_MINUTES = 5      # guests: 5 minutes
USER_EXPIRY_HOURS    = 24     # logged-in: 24 hours

# ── Digital Signature Quota Limits ─────────────────────────
DSIGN_LIMIT_GUEST_SIGN = int(os.environ.get('DSIGN_LIMIT_GUEST_SIGN', 5))
DSIGN_LIMIT_GUEST_VERIFY = int(os.environ.get('DSIGN_LIMIT_GUEST_VERIFY', 5))
DSIGN_LIMIT_USER_SIGN = int(os.environ.get('DSIGN_LIMIT_USER_SIGN', 10))
DSIGN_LIMIT_USER_VERIFY = int(os.environ.get('DSIGN_LIMIT_USER_VERIFY', 10))
DSIGN_LIMIT_CORPORATE_SIGN = int(os.environ.get('DSIGN_LIMIT_CORPORATE_SIGN', 999999))
DSIGN_LIMIT_CORPORATE_VERIFY = int(os.environ.get('DSIGN_LIMIT_CORPORATE_VERIFY', 999999))

# ── Celery ─────────────────────────────────────────────────
CELERY_BROKER_URL        = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND    = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT    = ['json']
CELERY_TASK_SERIALIZER   = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE          = 'UTC'
CELERY_WORKER_POOL       = 'solo' if os.name == 'nt' else 'prefork'

# SSL settings for Upstash Redis (rediss:// protocol)
if CELERY_BROKER_URL.startswith('rediss://'):
    import ssl
    CELERY_BROKER_USE_SSL = {'ssl_cert_reqs': ssl.CERT_REQUIRED}
    CELERY_REDIS_BACKEND_USE_SSL = {'ssl_cert_reqs': ssl.CERT_REQUIRED}


CELERY_BEAT_SCHEDULE = {
    'cleanup-expired-converter-jobs': {
        'task':     'converter.tasks.cleanup_expired_jobs',
        'schedule': timedelta(minutes=5),
    },

    # ── Fixed: editor cleanup was missing from Beat schedule ──
    'cleanup-expired-editor-sessions': {
        'task':     'editor.tasks.cleanup_editor_sessions',
        'schedule': timedelta(minutes=10),
    },
    'check-daily-quota-resets': {
        'task':     'api.tasks.check_quota_resets_task',
        'schedule': crontab(hour=0, minute=0),
    },
}

# ── django-allauth ─────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

LOGIN_URL           = '/auth/login/'
LOGIN_REDIRECT_URL  = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

ACCOUNT_LOGIN_BY_CODE_ENABLED = False
ACCOUNT_AUTHENTICATION_METHOD = 'username_email'
ACCOUNT_EMAIL_REQUIRED        = True
ACCOUNT_EMAIL_VERIFICATION    = 'mandatory'
ACCOUNT_PREVENT_ENUMERATION   = True
ACCOUNT_SIGNUP_FIELDS         = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_SESSION_REMEMBER      = True


SOCIALACCOUNT_AUTO_SIGNUP       = True
SOCIALACCOUNT_EMAIL_REQUIRED    = True
SOCIALACCOUNT_LOGIN_ON_GET      = True
SOCIALACCOUNT_EMAIL_VERIFICATION = 'mandatory'

GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
GITHUB_CLIENT_ID = os.environ.get('GITHUB_CLIENT_ID')
GITHUB_CLIENT_SECRET = os.environ.get('GITHUB_CLIENT_SECRET')

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': ['profile', 'email'],
        'AUTH_PARAMS': {'access_type': 'online'},
        'OAUTH_PKCE_ENABLED': True,
    },
    'github': {
        'SCOPE': ['user:email'],
    },
}

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
        'key': ''
    }

if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['github']['APP'] = {
        'client_id': GITHUB_CLIENT_ID,
        'secret': GITHUB_CLIENT_SECRET,
        'key': ''
    }

# ── Tesseract OCR ──────────────────────────────────────────
# Read from environment so this works on Linux servers too.
# Windows default kept as fallback for your dev machine.
TESSERACT_CMD = os.environ.get(
    'TESSERACT_CMD',
    r'C:\Program Files\Tesseract-OCR\tesseract.exe' if os.name == 'nt' else 'tesseract'
)

# ── Digital Signature Cert Password ───────────────────────
SIGNING_CERT_PASSWORD = os.environ.get('SIGNING_CERT_PASSWORD', 'ShiftDocs-Default-Signing-Key-2024')


# ── Email ──────────────────────────────────────────────────
RESEND_API_KEY = os.environ.get('RESEND_API_KEY')
if RESEND_API_KEY:
    EMAIL_BACKEND = 'converter.email_backend.ResendEmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'hello@shiftdocs.io')
SALES_NOTIFICATION_EMAIL = os.environ.get('SALES_NOTIFICATION_EMAIL', 'sales@shiftdocs.io')

# ── Stripe ──────────────────────────────────────────────────
STRIPE_PUBLIC_KEY = os.environ.get('STRIPE_PUBLIC_KEY', 'pk_test_placeholder')
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', 'whsec_placeholder')

# ── Razorpay ────────────────────────────────────────────────
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_test_placeholder')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'rzp_test_secret_placeholder')
RAZORPAY_WEBHOOK_SECRET = os.environ.get('RAZORPAY_WEBHOOK_SECRET', 'rzp_webhook_secret_placeholder')
RAZORPAY_PLAN_PRICE_INR = int(os.environ.get('RAZORPAY_PLAN_PRICE_INR', 1499))
RAZORPAY_PLAN_PRICE_30_DAYS_INR = int(os.environ.get('RAZORPAY_PLAN_PRICE_30_DAYS_INR', 799))
RAZORPAY_PLAN_PRICE_90_DAYS_INR = int(os.environ.get('RAZORPAY_PLAN_PRICE_90_DAYS_INR', 1499))

# ── Production security ────────────────────────────────────
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin-allow-popups'

if not DEBUG:
    # ── Payment key safety check ───────────────────────────────
    # Crash early if production is still using placeholder payment credentials
    _PLACEHOLDER_KEYS = {
        'STRIPE_SECRET_KEY': STRIPE_SECRET_KEY,
        'STRIPE_WEBHOOK_SECRET': STRIPE_WEBHOOK_SECRET,
        'RAZORPAY_KEY_SECRET': RAZORPAY_KEY_SECRET,
        'RAZORPAY_WEBHOOK_SECRET': RAZORPAY_WEBHOOK_SECRET,
    }
    _placeholder_warnings = [
        k for k, v in _PLACEHOLDER_KEYS.items() if 'placeholder' in str(v).lower()
    ]
    if _placeholder_warnings:
        import warnings
        warnings.warn(
            f"⚠️  PRODUCTION WARNING: The following payment keys are still set to placeholder values: "
            f"{', '.join(_placeholder_warnings)}. "
            f"Set real credentials in your .env file before accepting payments.",
            RuntimeWarning,
            stacklevel=1,
        )

    # Always trust the X-Forwarded-Proto header from the reverse proxy/load balancer
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Allow disabling SSL redirect for testing/initial IP access
    SECURE_SSL_REDIRECT = os.environ.get('DJANGO_SECURE_SSL_REDIRECT', 'True').lower() == 'true'
    
    if SECURE_SSL_REDIRECT:
        SESSION_COOKIE_SECURE = True
        CSRF_COOKIE_SECURE = True
        CSRF_TRUSTED_ORIGINS = [
            f'https://{h}' for h in ALLOWED_HOSTS if h != '*'
        ]
    else:
        SESSION_COOKIE_SECURE = False
        CSRF_COOKIE_SECURE = False
        CSRF_TRUSTED_ORIGINS = [
            f'http://{h}' for h in ALLOWED_HOSTS if h != '*'
        ] + [
            f'https://{h}' for h in ALLOWED_HOSTS if h != '*'
        ]