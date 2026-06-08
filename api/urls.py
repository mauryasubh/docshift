from django.urls import path
from . import views

urlpatterns = [
    path('docs/', views.api_docs, name='api_docs'),
    path('v1/convert/<str:tool_slug>/', views.api_convert, name='api_convert'),
    
    # ── Subscription & Payments ──────────────────────────────────
    path('subscription/checkout/developer/', views.checkout_developer, name='checkout_developer'),
    path('subscription/webhook/stripe/', views.stripe_webhook, name='stripe_webhook'),
    path('subscription/razorpay/create-order/', views.razorpay_create_order, name='razorpay_create_order'),
    path('subscription/razorpay/verify/', views.razorpay_verify, name='razorpay_verify'),
    path('subscription/razorpay/webhook/', views.razorpay_webhook, name='razorpay_webhook'),
]
