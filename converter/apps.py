from django.apps import AppConfig

class ConverterConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'converter'

    def ready(self):
        import converter.signals  # noqa: F401
