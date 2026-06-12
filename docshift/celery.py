import os
import platform
from celery import Celery
from kombu import Queue

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docshift.settings')

app = Celery('docshift')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ── Priority Queues ─────────────────────────────────────────
# 'priority' queue for Corporate tier jobs (consumed first)
# 'default'  queue for Free/Developer jobs
app.conf.task_queues = [
    Queue('default'),
    Queue('priority'),
]
app.conf.task_default_queue = 'default'

# Windows fix — solo pool avoids fork() which doesn't exist on Windows
if platform.system() == 'Windows':
    app.conf.worker_pool = 'solo'