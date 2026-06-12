"""
tier_utils.py — Single source of truth for tier-based limits.

Every view should call these helpers instead of reading settings constants
directly. This keeps tier logic centralized and easy to update.
"""
from django.conf import settings


def get_max_upload_size(user) -> int:
    """
    Return max upload size in bytes based on user's plan tier.
    
    - Guest / Free:    10 MB
    - Developer:       50 MB
    - Corporate:      200 MB
    """
    if not user or not user.is_authenticated:
        return getattr(settings, 'MAX_UPLOAD_SIZE_FREE', 10 * 1024 * 1024)

    try:
        tier = user.api_profile.plan_tier
    except Exception:
        return getattr(settings, 'MAX_UPLOAD_SIZE_FREE', 10 * 1024 * 1024)

    tier_map = {
        'Corporate': getattr(settings, 'MAX_UPLOAD_SIZE_CORPORATE', 200 * 1024 * 1024),
        'Developer': getattr(settings, 'MAX_UPLOAD_SIZE_DEVELOPER', 50 * 1024 * 1024),
        'Free':      getattr(settings, 'MAX_UPLOAD_SIZE_FREE', 10 * 1024 * 1024),
    }
    return tier_map.get(tier, getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024))


def get_max_upload_size_for_profile(profile) -> int:
    """
    Same as get_max_upload_size but takes an api.models.Profile directly.
    Used in API views where request.api_profile is available.
    """
    tier = getattr(profile, 'plan_tier', 'Free')
    tier_map = {
        'Corporate': getattr(settings, 'MAX_UPLOAD_SIZE_CORPORATE', 200 * 1024 * 1024),
        'Developer': getattr(settings, 'MAX_UPLOAD_SIZE_DEVELOPER', 50 * 1024 * 1024),
        'Free':      getattr(settings, 'MAX_UPLOAD_SIZE_FREE', 10 * 1024 * 1024),
    }
    return tier_map.get(tier, getattr(settings, 'MAX_UPLOAD_SIZE', 50 * 1024 * 1024))


def get_api_rate_limit(profile) -> int:
    """Return requests-per-minute for the user's tier."""
    tier = getattr(profile, 'plan_tier', 'Free')
    if tier == 'Corporate':
        return getattr(settings, 'API_RATE_LIMIT_CORPORATE', 50)
    return getattr(settings, 'API_RATE_LIMIT_DEVELOPER', 20)


def get_dsign_limits(user) -> dict:
    """
    Return digital signature daily limits based on user's tier.
    Returns dict with keys: sign_limit, verify_limit
    """
    if not user or not user.is_authenticated:
        return {
            'sign_limit': getattr(settings, 'DSIGN_LIMIT_GUEST_SIGN', 5),
            'verify_limit': getattr(settings, 'DSIGN_LIMIT_GUEST_VERIFY', 5),
        }

    try:
        tier = user.api_profile.plan_tier
    except Exception:
        tier = 'Free'

    if tier == 'Corporate':
        return {
            'sign_limit': getattr(settings, 'DSIGN_LIMIT_CORPORATE_SIGN', 999999),
            'verify_limit': getattr(settings, 'DSIGN_LIMIT_CORPORATE_VERIFY', 999999),
        }
    else:
        return {
            'sign_limit': getattr(settings, 'DSIGN_LIMIT_USER_SIGN', 10),
            'verify_limit': getattr(settings, 'DSIGN_LIMIT_USER_VERIFY', 10),
        }


def get_max_upload_size_display(user) -> str:
    """Return a human-readable string like '50MB' for the user's tier limit."""
    size = get_max_upload_size(user)
    return f"{size // (1024 * 1024)}MB"
