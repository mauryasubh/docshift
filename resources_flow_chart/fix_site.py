import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'docshift.settings')
django.setup()

from django.contrib.sites.models import Site

# Ensure site #1 exists
site, created = Site.objects.get_or_create(
    id=1,
    defaults={'domain': '127.0.0.1:8000', 'name': 'DocShift'}
)

if not created:
    site.domain = '127.0.0.1:8000'
    site.name = 'DocShift'
    site.save()

print(f"✅ Site setup complete: ID={site.id}, Domain={site.domain}")
