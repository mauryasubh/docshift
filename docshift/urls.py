from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('allauth.urls')),
    path('', include('converter.urls')),
    path('api/', include('api.urls')),
    path('editor/', include('editor.urls')),

    # Retired features — redirect to homepage
    path('translator/', RedirectView.as_view(url='/', permanent=False)),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
