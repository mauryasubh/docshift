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
    Checks all non-Free profiles and downgrades them if they have expired.
    """
    from api.models import Profile
    now = timezone.now()
    # Find active non-free profiles whose plan has expired 
    expired_profiles = Profile.objects.exclude(plan_tier='Free').filter(plan_expiry_date__lte=now)
    
    count = 0
    for profile in expired_profiles:
        profile.plan_tier = 'Free'
        profile.plan_start_date = None
        profile.plan_expiry_date = None
        profile.last_quota_reset = None
        profile.api_calls_used_this_month = 0
        profile.stripe_subscription_id = None
        profile.razorpay_subscription_id = None
        profile.razorpay_order_id = None
        profile.razorpay_payment_id = None
        profile.save()
        count += 1
        
    return f"Downgraded {count} expired profiles."
