import time
from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
from api.models import Profile

def rate_limit_api(requests_per_minute=20):
    """
    1) Validates Authorization: Bearer <Key>
    2) Checks Redis to ensure speed limit isn't exceeded
    3) Checks Database to ensure monthly quota isn't exceeded
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return JsonResponse({'error': 'Missing or invalid Authorization: Bearer token'}, status=401)
            
            api_key = auth_header.split(' ')[1]
            try:
                # UUIDs can raise ValueError if malformed
                profile = Profile.objects.get(api_key=api_key)
            except (Profile.DoesNotExist, ValueError):
                return JsonResponse({'error': 'Invalid API Key'}, status=401)
            
            # --- Redis Speed Limiter ---
            cache_key = f"rate_limit_{api_key}"
            current_count = cache.get(cache_key, 0)
            
            if current_count >= requests_per_minute:
                return JsonResponse({'error': f'Too Many Requests. Limit is {requests_per_minute} per minute.'}, status=429)
                
            cache.set(cache_key, current_count + 1, timeout=60)
            
            # --- DB Quota Limiter ---
            if not profile.can_make_api_call():
                return JsonResponse({
                    'error': 'Monthly quota exceeded. Upgrade your plan.', 
                    'tier': profile.plan_tier,
                    'used': profile.api_calls_used_this_month
                }, status=402)
                
            # Attach profile so inner view can increment usage after success
            request.api_profile = profile
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
