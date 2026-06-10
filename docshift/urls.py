from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.http import JsonResponse, HttpResponse

def health_check(request):
    return JsonResponse({'status': 'ok'})

def robots_txt(request):
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /auth/",
        "Disallow: /dashboard/",
        "Disallow: /job/",
        "Disallow: /editor/session/",
        "Disallow: /api/v1/",
        "Allow: /",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('health/', health_check, name='health_check'),

    path('admin/', admin.site.urls),
    path('auth/', include('allauth.urls')),
    path('', include('converter.urls')),
    path('api/', include('api.urls')),
    path('editor/', include('editor.urls')),

    # Retired features — redirect to homepage
    path('translator/', RedirectView.as_view(url='/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
