from django.shortcuts import render
from django.contrib.sites.models import Site


class OAuthSetupMiddleware:
    """
    Catch allauth DoesNotExist errors (unconfigured OAuth apps)
    and show a friendly setup page instead of a 500 error.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        path = request.path
        # Only intercept on /auth/<provider>/login/ paths
        if '/auth/' in path and '/login/' in path:
            from django.core.exceptions import ObjectDoesNotExist
            if isinstance(exception, ObjectDoesNotExist):
                provider = 'google' if 'google' in path else 'github' if 'github' in path else 'unknown'
                return render(request, 'oauth_setup_error.html', {
                    'provider': provider,
                    'provider_title': provider.title(),
                }, status=200)
        return None
