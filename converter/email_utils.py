import logging
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

def send_plan_confirmation_email(user, plan_tier, plan_expiry_date=None, days=None):
    """
    Sends a confirmation email to the user when they subscribe/upgrade to Developer or Corporate plans.
    """
    if not user.email:
        logger.warning(f"User {user.username} has no email address. Skipping confirmation email.")
        return False

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@shiftdocs.io')
    
    # Format date
    expiry_str = "N/A"
    if plan_expiry_date:
        # If timezone aware, convert to local or just format nicely
        expiry_str = plan_expiry_date.strftime("%B %d, %Y")
    elif days:
        expiry_str = f"{days} days"

    subject = ""
    body = ""

    if plan_tier == 'Developer':
        subject = "Your ShiftDocs Developer Plan is Active!"
        body = f"""Hi {user.username},

Thank you for upgrading to the ShiftDocs Developer Plan!

Your plan is now active with the following benefits:
- 5,000 API calls / month
- 50MB Max Upload File Size
- Webhook Integrations
- Access to developer API docs and tools

Your subscription is valid until {expiry_str}.
You can view your API key and track your usage directly on your dashboard:
https://shiftdocs.io/dashboard/

If you have any questions or need support, reply to this email or contact support@shiftdocs.io.

Happy converting!
The ShiftDocs Team
https://shiftdocs.io/
"""
    elif plan_tier == 'Corporate':
        subject = "Welcome to ShiftDocs Corporate Tier!"
        body = f"""Hi {user.username},

Your ShiftDocs Corporate Plan is now active!

Welcome to our premium corporate tier. Here is a summary of your features:
- 50,000+ API calls / month
- 200MB Max Upload File Size
- Priority Processing Queue (Corporate files processed first)
- Digital Signature API (Sign & Verify)
- Dedicated Success Support

Your plan is valid until {expiry_str}.
Access your API key, configure webhooks, and start building at:
https://shiftdocs.io/dashboard/

If you need anything or want to schedule an onboarding call, reach out to your Dedicated Success Manager.

Best regards,
The ShiftDocs Team
https://shiftdocs.io/
"""
    else:
        # Ignore free or other tiers for confirmation emails
        return False

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=[user.email],
            fail_silently=True
        )
        logger.info(f"Confirmation email sent to {user.email} for plan {plan_tier}.")
        return True
    except Exception as e:
        logger.error(f"Failed to send confirmation email to {user.email}: {str(e)}")
        return False


def send_sales_inquiry_emails(name, email, company, message):
    """
    1. Sends an alert email to the ShiftDocs sales team (SALES_NOTIFICATION_EMAIL).
    2. Sends a polite auto-acknowledgement email to the user who submitted the form.
    """
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@shiftdocs.io')
    sales_email = getattr(settings, 'SALES_NOTIFICATION_EMAIL', 'sales@shiftdocs.io')
    
    # 1. Alert to Sales Team
    sales_subject = f"[Sales Lead] New Corporate Plan Inquiry - {company or name}"
    sales_body = f"""Hi Team,

A new Corporate Plan Inquiry has been submitted on ShiftDocs.

Details:
- Name: {name}
- Email: {email}
- Company: {company or "Not specified"}

Message:
{message}

---
You can view and manage all sales inquiries in the Django Admin:
https://shiftdocs.io/admin/converter/salesinquiry/
"""

    # 2. Acknowledgement to User
    user_subject = "We've received your ShiftDocs Sales inquiry"
    user_body = f"""Hi {name},

Thank you for your interest in the ShiftDocs Corporate Plan!

We have received your request and our sales team is reviewing it. A dedicated success manager will get back to you at this email address ({email}) within 24 hours to discuss custom pricing, integration needs, and feature requirements.

In the meantime, you can explore our API documentation here:
https://shiftdocs.io/api/docs/

Summary of details submitted:
- Company: {company or "Not specified"}
- Message: {message}

Best regards,
The ShiftDocs Team
https://shiftdocs.io/
"""

    # Send to sales team
    try:
        send_mail(
            subject=sales_subject,
            message=sales_body,
            from_email=from_email,
            recipient_list=[sales_email],
            fail_silently=True
        )
        logger.info(f"Sales alert email sent to {sales_email}.")
    except Exception as e:
        logger.error(f"Failed to send sales alert email to {sales_email}: {str(e)}")

    # Send to user
    try:
        send_mail(
            subject=user_subject,
            message=user_body,
            from_email=from_email,
            recipient_list=[email],
            fail_silently=True
        )
        logger.info(f"Sales acknowledgement email sent to {email}.")
    except Exception as e:
        logger.error(f"Failed to send sales acknowledgement email to {email}: {str(e)}")
