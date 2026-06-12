from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from converter.models import ConversionJob
from converter.views import TOOL_CONFIG, _dispatch_task
from django.shortcuts import render
from .utils import rate_limit_api
from .tier_utils import get_max_upload_size_for_profile

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
    
    # Validate size constraints based on user's tier
    max_size = get_max_upload_size_for_profile(request.api_profile)
    if uploaded_file.size > max_size:
        return JsonResponse({'error': f'File is too large. Max size is {max_size // (1024*1024)}MB for your plan.'}, status=413)

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


@csrf_exempt
@rate_limit_api(requests_per_minute=20)
def api_digital_sign(request):
    """
    Sign a PDF document with a Level 2 digital signature.
    Expects method: POST
    Expects header: Authorization: Bearer <API_KEY>
    Expects form-data: 
      - file: PDF file to sign
      - reason: (optional) reason string
      - visual_signature: (optional) "true"/"false" (defaults to true)
      - position: (optional) "bottom_right"/"bottom_left"/"top_right"/"top_left"/"center" (defaults to bottom_right)
      - stamp_style: (optional) "card"/"minimal"/"badge" (defaults to card)
      - page_choice: (optional) "last"/"first" (defaults to last)
      - offset: (optional) integer margin offset (defaults to 10)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed. Use POST.'}, status=405)
        
    if 'file' not in request.FILES:
        return JsonResponse({'error': "Missing 'file' field in multipart form-data."}, status=400)
        
    uploaded_file = request.FILES['file']
    if not uploaded_file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'Only PDF files can be digitally signed.'}, status=400)
        
    # Validate size constraints based on user's tier
    max_size = get_max_upload_size_for_profile(request.api_profile)
    if uploaded_file.size > max_size:
        return JsonResponse({'error': f'File is too large. Max size is {max_size // (1024*1024)}MB for your plan.'}, status=413)

    # Read bytes
    try:
        input_bytes = uploaded_file.read()
    except Exception as e:
        return JsonResponse({'error': f"Failed to read file: {str(e)}"}, status=400)

    # Get optional params
    reason = request.POST.get('reason', 'Document Signing')
    visual_signature = request.POST.get('visual_signature', 'true').strip().lower() == 'true'
    position = request.POST.get('position', 'bottom_right')
    page_choice = request.POST.get('page_choice', 'last')
    stamp_style = request.POST.get('stamp_style', 'card')
    
    try:
        offset = int(request.POST.get('offset', 10))
    except (ValueError, TypeError):
        offset = 10

    # Execute signing synchronously
    from converter.signing import sign_pdf
    try:
        signed_bytes = sign_pdf(
            input_bytes,
            signer_name=request.api_profile.user.get_full_name() or request.api_profile.user.username,
            reason=reason,
            visual_signature=visual_signature,
            position=position,
            page_choice=page_choice,
            stamp_style=stamp_style,
            offset=offset
        )
    except Exception as e:
        return JsonResponse({'error': f"Signing failed: {str(e)}"}, status=500)

    # Increment quota usage
    request.api_profile.api_calls_used_this_month += 1
    request.api_profile.save()

    # Return signed file
    import io
    from django.http import FileResponse
    response = FileResponse(
        io.BytesIO(signed_bytes),
        as_attachment=True,
        filename=f"signed_{uploaded_file.name}",
        content_type='application/pdf'
    )
    return response


@csrf_exempt
@rate_limit_api(requests_per_minute=20)
def api_digital_verify(request):
    """
    Verify all digital signatures in a PDF.
    Expects method: POST
    Expects header: Authorization: Bearer <API_KEY>
    Expects form-data:
      - file: PDF file to verify
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed. Use POST.'}, status=405)
        
    if 'file' not in request.FILES:
        return JsonResponse({'error': "Missing 'file' field in multipart form-data."}, status=400)
        
    uploaded_file = request.FILES['file']
    if not uploaded_file.name.lower().endswith('.pdf'):
        return JsonResponse({'error': 'Only PDF files can be verified.'}, status=400)
        
    # Validate size constraints based on user's tier
    max_size = get_max_upload_size_for_profile(request.api_profile)
    if uploaded_file.size > max_size:
        return JsonResponse({'error': f'File is too large. Max size is {max_size // (1024*1024)}MB for your plan.'}, status=413)

    # Read bytes
    try:
        input_bytes = uploaded_file.read()
    except Exception as e:
        return JsonResponse({'error': f"Failed to read file: {str(e)}"}, status=400)

    # Execute verification synchronously
    from converter.signing import verify_pdf
    try:
        result = verify_pdf(input_bytes)
    except Exception as e:
        return JsonResponse({'error': f"Verification failed: {str(e)}"}, status=500)

    # Increment quota usage
    request.api_profile.api_calls_used_this_month += 1
    request.api_profile.save()

    return JsonResponse(result)







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
                profile.last_quota_reset = timezone.now()
                
                profile.save()

                # Send confirmation email
                from converter.email_utils import send_plan_confirmation_email
                send_plan_confirmation_email(user, 'Developer', plan_expiry_date=profile.plan_expiry_date)
            except User.DoesNotExist:
                pass

    return HttpResponse(status=200)


# ── Razorpay Payment Views ───────────────────────────────────
import razorpay
import json
from django.utils import timezone
from datetime import timedelta

@login_required
def razorpay_create_order(request):
    """
    Creates a Razorpay Order for the Developer plan (One-Time purchase, 30 or 90 days).
    """
    try:
        # Simulation Mode Check
        if settings.RAZORPAY_KEY_SECRET == 'rzp_test_secret_placeholder':
            return JsonResponse({
                "error": "Razorpay Simulation Mode. Please configure real credentials in your .env file."
            }, status=400)

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Get requested duration (default to 3 months / 90 days)
        duration_param = request.GET.get('duration', '3')
        if duration_param == '1':
            price_inr = getattr(settings, 'RAZORPAY_PLAN_PRICE_30_DAYS_INR', 799)
            days = 30
            desc = "Developer Plan (30 Days)"
        else:
            price_inr = getattr(settings, 'RAZORPAY_PLAN_PRICE_90_DAYS_INR', 1499)
            days = 90
            desc = "Developer Plan (90 Days)"
        
        amount_in_paisa = price_inr * 100
        
        data = {
            "amount": amount_in_paisa,
            "currency": "INR",
            "receipt": f"rcpt_{request.user.id}_{int(timezone.now().timestamp())}",
            "notes": {
                "user_id": request.user.id,
                "email": request.user.email,
                "plan": "Developer",
                "days": days
            }
        }
        
        order = client.order.create(data=data)
        
        # Save order ID to the profile for reference
        profile = request.user.api_profile
        profile.razorpay_order_id = order['id']
        profile.save(update_fields=['razorpay_order_id'])
        
        return JsonResponse({
            "key_id": settings.RAZORPAY_KEY_ID,
            "amount": order['amount'],
            "currency": order['currency'],
            "order_id": order['id'],
            "name": "ShiftDocs",
            "description": desc,
            "prefill": {
                "name": request.user.username,
                "email": request.user.email
            }
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


@login_required
@csrf_exempt
def razorpay_verify(request):
    """
    Verifies the Razorpay payment signature and updates user plan to Developer.
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Method not allowed. Use POST."}, status=405)
        
    try:
        data = json.loads(request.body)
        payment_id = data.get('razorpay_payment_id')
        order_id = data.get('razorpay_order_id')
        signature = data.get('razorpay_signature')
        
        if not all([payment_id, order_id, signature]):
            return JsonResponse({"error": "Missing signature verification details."}, status=400)
            
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Check signature verification
        params_dict = {
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        }
        
        client.utility.verify_payment_signature(params_dict)
        
        # Fetch order from Razorpay to read verified notes including plan duration days
        days = 90
        try:
            order = client.order.fetch(order_id)
            notes = order.get('notes', {})
            days = int(notes.get('days', 90))
            
            # Security verification: Ensure order belongs to current user
            order_user_id = notes.get('user_id')
            if order_user_id and int(order_user_id) != request.user.id:
                return JsonResponse({"error": "Unauthorized order verification."}, status=403)
        except Exception:
            pass  # Fallback to default if order fetch fails
        
        # Upgrade User Profile
        profile = request.user.api_profile
        profile.plan_tier = 'Developer'
        profile.razorpay_order_id = order_id
        profile.razorpay_payment_id = payment_id
        
        # Only update plan validity and reset usage if not already active
        if not profile.plan_expiry_date or profile.plan_expiry_date < timezone.now():
            profile.plan_start_date = timezone.now()
            profile.plan_expiry_date = timezone.now() + timedelta(days=days)
            profile.last_quota_reset = timezone.now()
            profile.api_calls_used_this_month = 0
            
        profile.save()

        # Send confirmation email
        from converter.email_utils import send_plan_confirmation_email
        send_plan_confirmation_email(request.user, 'Developer', plan_expiry_date=profile.plan_expiry_date)
        
        return JsonResponse({
            "status": "success",
            "message": "Plan successfully upgraded to Developer!"
        })
    except Exception as e:
        return JsonResponse({"error": f"Verification failed: {str(e)}"}, status=400)


@csrf_exempt
def razorpay_webhook(request):
    """
    Webhook handler for async Razorpay payment capture events.
    """
    if request.method != 'POST':
        return HttpResponse(status=405)
        
    webhook_secret = getattr(settings, 'RAZORPAY_WEBHOOK_SECRET', '')
    sig = request.headers.get('X-Razorpay-Signature')
    
    if not sig:
        return HttpResponse(status=400)
        
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    
    try:
        # Verify the raw request payload with the signature and secret
        client.utility.verify_webhook_signature(request.body, sig, webhook_secret)
        
        payload = json.loads(request.body)
        event = payload.get('event')
        
        if event == 'order.paid':
            order_entity = payload['payload']['order']['entity']
            order_id = order_entity['id']
            notes = order_entity.get('notes', {})
            user_id = notes.get('user_id')
            days = int(notes.get('days', 90))  # Default fallback
            
            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    profile = user.api_profile
                    
                    profile.plan_tier = 'Developer'
                    profile.razorpay_order_id = order_id
                    
                    # Only update plan validity and reset usage if not already active
                    if not profile.plan_expiry_date or profile.plan_expiry_date < timezone.now():
                        profile.plan_start_date = timezone.now()
                        profile.plan_expiry_date = timezone.now() + timedelta(days=days)
                        profile.last_quota_reset = timezone.now()
                        profile.api_calls_used_this_month = 0
                    
                    profile.save()

                    # Send confirmation email
                    from converter.email_utils import send_plan_confirmation_email
                    send_plan_confirmation_email(user, 'Developer', plan_expiry_date=profile.plan_expiry_date)
                except User.DoesNotExist:
                    pass
                    
        return HttpResponse(status=200)
    except Exception:
        # Invalid signature or error processing
        return HttpResponse(status=400)
