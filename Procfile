web: gunicorn docshift.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120
worker: celery -A docshift worker --loglevel=info --concurrency=2
beat: celery -A docshift beat --loglevel=info
