from django.apps import AppConfig

class ConverterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'converter'

    def ready(self):
        import converter.signals  # noqa: F401
        
        # Apply Cloudflare R2 / AWS S3 task compatibility patches
        from docshift.s3_patch import apply_s3_patches
        apply_s3_patches()

        # Update Site domain dynamically on startup if SITE_DOMAIN is configured
        import os
        site_domain = os.environ.get('SITE_DOMAIN')
        if site_domain:
            try:
                from django.contrib.sites.models import Site
                from django.conf import settings
                Site.objects.update_or_create(
                    id=settings.SITE_ID,
                    defaults={'domain': site_domain, 'name': 'ShiftDocs'}
                )
            except Exception:
                # Table might not exist yet during migrations/initial setup
                pass
