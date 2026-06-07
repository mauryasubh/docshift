"""
Signals:
  1. Auto-create UserProfile on new User
  2. On social login: pull avatar from provider
  3. On login: migrate guest session jobs to the authenticated user
"""
from django.db.models.signals import post_save
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.contrib.auth.models import User


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        from converter.models import UserProfile
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    from converter.models import UserProfile
    UserProfile.objects.get_or_create(user=instance)


@receiver(user_logged_in)
def migrate_guest_jobs(sender, request, user, **kwargs):
    """Transfer session-tracked guest jobs to the logged-in user."""
    from converter.models import ConversionJob
    from django.utils import timezone
    from datetime import timedelta
    from django.conf import settings

    session_ids = request.session.get('dashboard_jobs', [])
    if not session_ids:
        return

    hours = getattr(settings, 'USER_EXPIRY_HOURS', 24)
    new_expiry = timezone.now() + timedelta(hours=hours)

    migrated = 0
    for jid in session_ids:
        try:
            job = ConversionJob.objects.get(id=jid, user__isnull=True)
            job.user = user
            job.is_guest = False
            job.expires_at = new_expiry   # extend expiry to 24h
            job.save(update_fields=['user', 'is_guest', 'expires_at'])
            migrated += 1
        except ConversionJob.DoesNotExist:
            pass

    # Clear session list — dashboard now uses DB query
    request.session['dashboard_jobs'] = []


@receiver(user_logged_in)
def pull_social_avatar(sender, request, user, **kwargs):
    """Pull avatar URL from social account on every login."""
    try:
        from allauth.socialaccount.models import SocialAccount
        social = SocialAccount.objects.filter(user=user).first()
        if not social:
            return
        profile = user.profile
        avatar = ''
        if social.provider == 'google':
            avatar = social.extra_data.get('picture', '')
        elif social.provider == 'github':
            avatar = social.extra_data.get('avatar_url', '')
        if avatar and avatar != profile.avatar_url:
            profile.avatar_url = avatar
            profile.save(update_fields=['avatar_url'])
    except Exception:
        pass

# ── Clean up files from storage (Local / AWS S3 / Cloudflare R2) when models are deleted ──
from django.db.models.signals import pre_delete
from django.core.files.storage import default_storage

@receiver(pre_delete, sender='converter.ConversionJob')
def cleanup_conversion_job_files(sender, instance, **kwargs):
    # 1. Delete uploaded and converted files from storage
    for f in [instance.input_file, instance.output_file]:
        if f:
            try:
                f.delete(save=False)
            except Exception:
                pass
                
    # 2. Delete rotate previews thumbnails from storage
    try:
        for i in range(1000):
            path = f"rotate_previews/{instance.id}/page_{i}.jpg"
            if default_storage.exists(path):
                default_storage.delete(path)
            else:
                break
    except Exception:
        pass

@receiver(pre_delete, sender='editor.EditorSession')
def cleanup_editor_session_files(sender, instance, **kwargs):
    # 1. Delete original and result files from storage
    for f in [instance.original_file, instance.result_file]:
        if f:
            try:
                f.delete(save=False)
            except Exception:
                pass
                
    # 2. Delete rendered page images from storage
    try:
        for i in range(1, instance.page_count + 1):
            path = f"editor_pages/{instance.id}/page_{i}.png"
            if default_storage.exists(path):
                default_storage.delete(path)
    except Exception:
        pass
        
    # 3. Clean up local directories if they exist (dev mode fallback)
    try:
        import shutil
        if instance.pages_dir.exists():
            shutil.rmtree(str(instance.pages_dir))
    except Exception:
        pass
