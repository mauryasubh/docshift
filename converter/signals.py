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
