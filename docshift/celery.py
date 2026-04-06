import os
import platform
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docshift.settings')

app = Celery('docshift')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Windows fix — solo pool avoids fork() which doesn't exist on Windows
if platform.system() == 'Windows':
    app.conf.worker_pool = 'solo'