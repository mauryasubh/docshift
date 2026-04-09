from django.apps import AppConfig

class ConverterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'converter'

    def ready(self):
        import converter.signals  # noqa: F401
        
        # Apply Cloudflare R2 / AWS S3 task compatibility patches
        from docshift.s3_patch import apply_s3_patches
        apply_s3_patches()
