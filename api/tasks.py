import requests
from celery import shared_task
from django.utils import timezone
from datetime import timedelta

@shared_task
def send_webhook_task(url, payload):
    """
    Sends an HTTP POST webhook to a user's server when their conversion is complete.
    Fails silently if their server is offline or times out.
    """
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

@shared_task
def check_quota_resets_task():
    """
    Iterates through all user profiles and resets their monthly API usage 
    if their current 'month' has expired.
    """
    from api.models import Profile
    now = timezone.now()
    # Find active non-free profiles whose plan has expired 
    expired_profiles = Profile.objects.exclude(plan_tier='Free').filter(plan_expiry_date__lte=now)
    
    count = 0
    for profile in expired_profiles:
        profile.api_calls_used_this_month = 0
        # Push the expiry date forward by 30 days
        if profile.plan_expiry_date:
            profile.plan_expiry_date += timedelta(days=30)
        else:
            profile.plan_expiry_date = now + timedelta(days=30)
        
        profile.save(update_fields=['api_calls_used_this_month', 'plan_expiry_date'])
        count += 1
        
    return f"Reset usage for {count} profiles."
