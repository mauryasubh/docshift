import os
import tempfile
from django.conf import settings
from django.db.models.fields.files import FieldFile
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.files import File

def apply_s3_patches():
    """
    Applies patches to Django's file handling to transparently support S3 in tasks
    that were originally written assuming local disk access.
    """
    if getattr(settings, 'DEFAULT_FILE_STORAGE', '').endswith('FileSystemStorage'):
        return  # No patch needed for local development

    # 1. Patch FieldFile.path to automatically download from S3 to a temporary file
    _original_path = FieldFile.path.fget

    def _get_path(self):
        try:
            return _original_path(self)
        except NotImplementedError:
            # Storage does not support absolute paths (like S3).
            # Download file to a temporary location and cache the path.
            if not getattr(self, '_custom_temp_path', None):
                self.file.seek(0)
                ext = os.path.splitext(self.name)[1]
                tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
                tmp.write(self.read())
                tmp.close()
                self._custom_temp_path = tmp.name
            return self._custom_temp_path

    FieldFile.path = property(_get_path)

    # 2. Hook into models to detect local files assigned to S3-backed FileFields
    from converter.models import ConversionJob
    from translator.models import TranslationJob

    def handle_s3_upload(instance, field_name):
        field = getattr(instance, field_name)
        if field and isinstance(field.name, str):
            # In Celery tasks, we assign: job.output_file = 'outputs/some_id.pdf'
            # The task generated the file locally at MEDIA_ROOT / 'outputs/some_id.pdf'
            rel_path = field.name
            abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
            
            # If the file physically exists on the local worker disk, we need to upload it!
            if os.path.exists(abs_path):
                with open(abs_path, 'rb') as f:
                    # This uploads the file to S3
                    field.save(rel_path, File(f), save=False)
                
                # Clean up the local temp file after uploading to S3
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    @receiver(pre_save, sender=ConversionJob)
    def pre_save_conversion_job(sender, instance, **kwargs):
        handle_s3_upload(instance, 'output_file')

    @receiver(pre_save, sender=TranslationJob)
    def pre_save_translation_job(sender, instance, **kwargs):
        handle_s3_upload(instance, 'result_file')
