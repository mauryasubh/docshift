from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('allauth.urls')),
    path('', include('converter.urls')),
    path('api/', include('api.urls')),
    path('editor/', include('editor.urls')),
    path('translator/', include('translator.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
