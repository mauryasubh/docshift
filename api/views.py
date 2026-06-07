from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from converter.models import ConversionJob
from converter.views import TOOL_CONFIG, _dispatch_task
from django.shortcuts import render
from .utils import rate_limit_api

def api_docs(request):
    """Renders the custom Developer API documentation page."""
    from converter.views import TOOL_CONFIG
    return render(request, 'api/docs.html', {
        'tool_config': TOOL_CONFIG
    })

@csrf_exempt
@rate_limit_api(requests_per_minute=20)
def api_convert(request, tool_slug):
    """
    Standardize the file conversion via an API endpoint.
    Expects method: POST
    Expects header: Authorization: Bearer <API_KEY>
    Expects form-data: file=<file>
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed. Use POST.'}, status=405)
        
    if tool_slug not in TOOL_CONFIG:
        return JsonResponse({'error': f"Unknown tool: {tool_slug}"}, status=400)
        
    if 'file' not in request.FILES:
        return JsonResponse({'error': "Missing 'file' field in multipart form-data."}, status=400)
        
    uploaded_file = request.FILES['file']
    
    # Validate basic size constraints (e.g. 100MB max)
    if uploaded_file.size > 100 * 1024 * 1024:
        return JsonResponse({'error': "File is too large. Max size is 100MB."}, status=413)

    # Save the job under the user's account
    job = ConversionJob(
        tool=tool_slug,
        input_file=uploaded_file,
        input_size=uploaded_file.size,
        original_name=uploaded_file.name,
        is_guest=False,
        user=request.api_profile.user,
    )
    job.save()
    
    # Hand off to Celery 
    _dispatch_task(tool_slug, job)
    
    # Increment quota usage since job was successfully dispatched
    request.api_profile.api_calls_used_this_month += 1
    request.api_profile.save()
    
    status_url = request.build_absolute_uri(f"/job/{job.id}/status/json/")
    
    return JsonResponse({
        'status': 'processing',
        'job_id': str(job.id),
        'status_url': status_url,
        'message': 'File queued successfully. Poll the status_url or wait for your webhook.'
    }, status=202)




# ── Subscription & Payments ──────────────────────────────────
import stripe
from django.conf import settings
from django.shortcuts import redirect
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

# Initialize stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_placeholder')

@login_required
def checkout_developer(request):
    """
    Creates a Stripe Checkout Session for the Developer plan.
    Redirects user to the hosted checkout page.
    """
    try:
        # ── Simulation Mode Check ──────────────────────────────────
        if settings.STRIPE_SECRET_KEY == 'sk_test_placeholder':
            return HttpResponse(
                "<div style='font-family:sans-serif;padding:40px;text-align:center;'>"
                "<h1 style='color:#1a73e8;'>Stripe Simulation Mode</h1>"
                "<p style='color:#5f6368;'>Please add your real <b>STRIPE_SECRET_KEY</b> to your .env file to enable live checkout.</p>"
                "<a href='/pricing/' style='color:#1a73e8;text-decoration:none;'>← Back to Pricing</a>"
                "</div>", 
                status=200
            )

        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': 'ShiftDocs Developer Plan',
                            'description': '5,000 API calls/month + Webhooks',
                        },
                        'unit_amount': 1900, # $19.00
                        'recurring': {'interval': 'month'},
                    },
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url=request.build_absolute_uri('/') + '?subscription=success',
            cancel_url=request.build_absolute_uri('/') + '?subscription=cancel',
            metadata={
                'user_id': request.user.id,
                'email': request.user.email,
                'plan': 'Developer'
            }
        )
        return redirect(checkout_session.url, code=303)
    except Exception as e:
        return HttpResponse(f"Scale error: {str(e)}", status=500)

@csrf_exempt
def stripe_webhook(request):
    """
    Stripe webhook handler to provision service after successful payment.
    Updates the user's plan_tier in the Profile model.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', 'whsec_placeholder')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return HttpResponse(status=400)

    # Handle the checkout.session.completed event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # Extract user profile from metadata
        user_id = session.get('metadata', {}).get('user_id')
        if user_id:
            try:
                from django.utils import timezone
                from datetime import timedelta
                
                user = User.objects.get(id=user_id)
                # We use 'api_profile' related_name as defined in api/models.py
                profile = user.api_profile
                profile.plan_tier = 'Developer'
                profile.stripe_customer_id = session.get('customer')
                profile.stripe_subscription_id = session.get('subscription')
                
                # Set subscription dates
                profile.plan_start_date = timezone.now()
                profile.plan_expiry_date = timezone.now() + timedelta(days=30)
                
                profile.save()
            except User.DoesNotExist:
                pass

    return HttpResponse(status=200)
