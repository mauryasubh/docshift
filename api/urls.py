from django.urls import path
from . import views

urlpatterns = [
    path('docs/', views.api_docs, name='api_docs'),
    path('v1/convert/<str:tool_slug>/', views.api_convert, name='api_convert'),
    
    # ── Subscription & Payments ──────────────────────────────────
    path('subscription/checkout/developer/', views.checkout_developer, name='checkout_developer'),
    path('subscription/webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
]
