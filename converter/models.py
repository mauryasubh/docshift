import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.conf import settings


class UserProfile(models.Model):
    user            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar_url      = models.URLField(blank=True, default='')
    bio             = models.CharField(max_length=200, blank=True, default='')
    total_converted = models.PositiveIntegerField(default=0)
    created_at      = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Profile({self.user.username})"

    @property
    def display_name(self):
        return self.user.get_full_name() or self.user.username

    @property
    def initials(self):
        name = self.display_name
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[-1][0]).upper()
        return name[:2].upper()

    def total_size_bytes(self):
        return self.user.conversion_jobs.aggregate(
            t=models.Sum('input_size'))['t'] or 0


class ConversionJob(models.Model):
    TOOL_CHOICES = [
        ('merge_pdf',        'Merge PDFs'),
        ('compress_pdf',     'Compress PDF'),
        ('split_pdf',        'Split PDF'),
        ('pdf_to_images',    'PDF to Images'),
        ('docx_to_pdf',      'DOCX to PDF'),
        ('txt_to_pdf',       'TXT to PDF'),
        ('img_to_pdf',       'Image to PDF'),
        ('jpg_to_png',       'JPG to PNG'),
        ('png_to_jpg',       'PNG to JPG'),
        ('resize_image',     'Resize Image'),
        ('pdf_to_word',      'PDF to Word'),
        ('any_to_pdf',       'Any to PDF'),
        # Round 1
        ('password_protect', 'Password Protect PDF'),
        ('unlock_pdf',       'Unlock PDF'),
        ('rotate_pdf',       'Rotate PDF'),
        ('watermark_pdf',    'Watermark PDF'),
        ('add_page_numbers', 'Add Page Numbers'),
        # Round 2
        ('pdf_to_excel',     'PDF to Excel'),
        ('excel_to_pdf',     'Excel to PDF'),
        ('pptx_to_pdf',      'PowerPoint to PDF'),
        ('pdf_to_pptx',      'PDF to PowerPoint'),
        ('html_to_pdf',      'HTML to PDF'),
        ('ocr_pdf',          'OCR Searchable PDF'),
        ('extract_text',     'Extract Text'),
        ('extract_images',   'Extract Images'),
    ]
    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('processing', 'Processing'),
        ('done',       'Done'),
        ('failed',     'Failed'),
    ]

    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user          = models.ForeignKey(User, on_delete=models.SET_NULL,
                                      null=True, blank=True, related_name='conversion_jobs')
    tool          = models.CharField(max_length=50, choices=TOOL_CHOICES)
    status        = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    input_file    = models.FileField(upload_to='uploads/', blank=True, null=True)
    output_file   = models.FileField(upload_to='outputs/', blank=True, null=True)
    original_name = models.CharField(max_length=255, blank=True, default='')
    input_size    = models.BigIntegerField(default=0)
    output_size   = models.BigIntegerField(default=0)
    error_message = models.TextField(blank=True, null=True)
    is_guest      = models.BooleanField(default=True)
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
        return f"{self.get_tool_display()} [{self.status}] {who} {self.id}"

    @property
    def compression_ratio(self):
        if self.input_size and self.output_size and self.input_size > 0:
            return round((1 - self.output_size / self.input_size) * 100, 1)
        return None

    @property
    def tool_display(self):
        return dict(self.TOOL_CHOICES).get(self.tool, self.tool)

    @property
    def output_ext(self):
        """Extension of the output file (e.g. 'pdf', 'xlsx', 'zip')."""
        from pathlib import Path
        if self.output_file and self.output_file.name:
            return Path(self.output_file.name).suffix.lstrip('.').lower()
        # Fallback: derive from tool slug
        ext_map = {
            'compress_pdf':     'pdf',
            'merge_pdf':        'pdf',
            'split_pdf':        'zip',
            'pdf_to_images':    'zip',
            'pdf_to_word':      'docx',
            'docx_to_pdf':      'pdf',
            'txt_to_pdf':       'pdf',
            'img_to_pdf':       'pdf',
            'any_to_pdf':       'pdf',
            'jpg_to_png':       'png',
            'png_to_jpg':       'jpg',
            'resize_image':     'pdf',
            'password_protect': 'pdf',
            'unlock_pdf':       'pdf',
            'rotate_pdf':       'pdf',
            'watermark_pdf':    'pdf',
            'add_page_numbers': 'pdf',
            'pdf_to_excel':     'xlsx',
            'excel_to_pdf':     'pdf',
            'pptx_to_pdf':      'pdf',
            'pdf_to_pptx':      'pptx',
            'html_to_pdf':      'pdf',
            'ocr_pdf':          'pdf',
            'extract_text':     'txt',
            'extract_images':   'zip',
        }
        return ext_map.get(self.tool, 'pdf')

    @property
    def display_name(self):
        return self.original_name or (
            self.input_file.name.split('/')[-1] if self.input_file else '—')

    def seconds_until_expiry(self):
        if not self.expires_at:
            return 0
        delta = (self.expires_at - timezone.now()).total_seconds()
        return max(0, int(delta))

from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=ConversionJob)
def trigger_webhook_on_completion(sender, instance, created, **kwargs):
    if created or not instance.user:
        return
        
    if instance.status in ['done', 'failed']:
        try:
            profile = getattr(instance.user, 'api_profile', None)
            if profile and profile.webhook_url:
                from api.tasks import send_webhook_task
                
                download_url = None
                if instance.status == 'done' and instance.output_file:
                    download_url = f"/job/{instance.id}/download/"
                
                payload = {
                    'job_id': str(instance.id),
                    'tool': instance.tool,
                    'status': instance.status,
                    'error': instance.error_message,
                    'download_url': download_url
                }
                
                send_webhook_task.delay(profile.webhook_url, payload)
        except Exception:
            pass

class SalesInquiry(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    company = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Inquiry from {self.name} ({self.company or 'No Company'})"