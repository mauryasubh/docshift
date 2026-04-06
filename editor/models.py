import uuid
from pathlib import Path
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class EditorSession(models.Model):

    STATUS_CHOICES = [
        ('analysing', 'Analysing'),
        ('ready',     'Ready'),
        ('saving',    'Saving'),
        ('saved',     'Saved'),
        ('failed',    'Failed'),
    ]

    PDF_TYPE_CHOICES = [
        ('unknown',   'Unknown'),
        ('generated', 'Generated'),
        ('scanned',   'Scanned'),
        ('mixed',     'Mixed'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(
                        User, on_delete=models.SET_NULL,
                        null=True, blank=True, related_name='editor_sessions'
                    )
    is_guest      = models.BooleanField(default=True)

    original_file = models.FileField(upload_to='editor/originals/')
    original_name = models.CharField(max_length=255, blank=True, default='')
    original_size = models.BigIntegerField(default=0)

    pdf_type      = models.CharField(max_length=20, choices=PDF_TYPE_CHOICES, default='unknown')
    page_count    = models.IntegerField(default=0)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='analysing')
    error_message = models.TextField(blank=True, null=True)

    blocks_json   = models.JSONField(default=list)
    images_json   = models.JSONField(default=list)

    result_file   = models.FileField(upload_to='editor/results/', blank=True, null=True)
    result_size   = models.BigIntegerField(default=0)

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
        return f"EditorSession [{self.status}] {who} — {self.original_name} ({self.id})"

    @property
    def display_name(self):
        return self.original_name or (
            Path(self.original_file.name).name if self.original_file else '—'
        )

    @property
    def pages_dir(self):
        return Path(settings.MEDIA_ROOT) / 'editor' / 'pages' / str(self.id)

    @property
    def pages_url_prefix(self):
        return f"{settings.MEDIA_URL}editor/pages/{self.id}/"

    def page_image_url(self, page_number):
        return f"{self.pages_url_prefix}page_{page_number}.png"

    def seconds_until_expiry(self):
        if not self.expires_at:
            return 0
        delta = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(delta))
