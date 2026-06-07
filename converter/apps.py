from django.apps import AppConfig

class ConverterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'converter'

    def ready(self):
        import converter.signals  # noqa: F401
        
        # Apply Cloudflare R2 / AWS S3 task compatibility patches
        from docshift.s3_patch import apply_s3_patches
        apply_s3_patches()

        # Update Site domain dynamically on startup (guarantees Site ID exists to prevent 500 errors)
        import os
        from django.conf import settings
        
        site_domain = os.environ.get('SITE_DOMAIN')
        if not site_domain:
            site_domain = 'shiftdocs.io' if not settings.DEBUG else '127.0.0.1:8000'
            
        try:
            from django.contrib.sites.models import Site
            Site.objects.update_or_create(
                id=settings.SITE_ID,
                defaults={'domain': site_domain, 'name': 'ShiftDocs'}
            )
        except Exception:
            # Table might not exist yet during migrations/initial setup
            pass
