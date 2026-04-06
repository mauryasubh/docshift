import uuid
from pathlib import Path
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class TranslationJob(models.Model):

    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('done',       'Done'),
        ('failed',     'Failed'),
    ]

    LANG_CHOICES = [
        ('auto', 'Auto-detect'),
        ('en',   'English'),
        ('fr',   'French'),
        ('es',   'Spanish'),
        ('de',   'German'),
        ('it',   'Italian'),
        ('pt',   'Portuguese'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='translation_jobs')
    is_guest      = models.BooleanField(default=True)
    original_file = models.FileField(upload_to='translator/originals/')
    result_file   = models.FileField(upload_to='translator/results/', blank=True, null=True)
    original_name = models.CharField(max_length=255, blank=True, default='')
    original_size = models.BigIntegerField(default=0)
    result_size   = models.BigIntegerField(default=0)
    source_lang   = models.CharField(max_length=10, choices=LANG_CHOICES, default='auto')
    target_lang   = models.CharField(max_length=10, choices=LANG_CHOICES, default='en')
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    char_count    = models.IntegerField(default=0)
    created_at    = models.DateTimeField(auto_now_add=True)
    expires_at    = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.expires_at:
            if self.is_guest:
                minutes = getattr(settings, 'GUEST_EXPIRY_MINUTES', 5)
                self.expires_at = timezone.now() + timedelta(minutes=minutes)
            else:
                hours = getattr(settings, 'USER_EXPIRY_HOURS', 24)
                self.expires_at = timezone.now() + timedelta(hours=hours)
        super().save(*args, **kwargs)

    def __str__(self):
        who = self.user.username if self.user else 'guest'
        return f"TranslationJob [{self.status}] {who} {self.source_lang}→{self.target_lang} {self.original_name}"

    @property
    def display_name(self):
        return self.original_name or (
            Path(self.original_file.name).name if self.original_file else '—')

    @property
    def lang_pair(self):
        src = dict(self.LANG_CHOICES).get(self.source_lang, self.source_lang)
        tgt = dict(self.LANG_CHOICES).get(self.target_lang, self.target_lang)
        return f"{src} → {tgt}"

    def seconds_until_expiry(self):
        if not self.expires_at:
            return 0
        delta = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(delta))

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=TranslationJob)
def trigger_webhook_on_completion(sender, instance, created, **kwargs):
    if created or not instance.user:
        return
        
    if instance.status in ['done', 'failed']:
        try:
            profile = getattr(instance.user, 'api_profile', None)
            if profile and profile.webhook_url:
                from api.tasks import send_webhook_task
                
                download_url = None
                if instance.status == 'done' and instance.result_file:
                    download_url = f"/translator/job/{instance.id}/download/"
                
                payload = {
                    'job_id': str(instance.id),
                    'module': 'translator',
                    'source_lang': instance.source_lang,
                    'target_lang': instance.target_lang,
                    'status': instance.status,
                    'error': instance.error_message,
                    'download_url': download_url
                }
                
                send_webhook_task.delay(profile.webhook_url, payload)
        except Exception:
            pass
