import os
import sys
import traceback

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docshift.settings")

try:
    import django
    django.setup()
    print("SUCCESS")
except Exception as e:
    with open("error.txt", "w") as f:
        traceback.print_exc(file=f)
