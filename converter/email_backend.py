import base64
import logging
import resend
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

logger = logging.getLogger(__name__)

class ResendEmailBackend(BaseEmailBackend):
    """
    A Django email backend that sends emails using the Resend Python SDK.
    """
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, 'RESEND_API_KEY', None)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        if not self.api_key:
            logger.error("RESEND_API_KEY is not configured in settings. Email delivery skipped.")
            if not self.fail_silently:
                raise ValueError("RESEND_API_KEY settings configuration is missing.")
            return 0

        resend.api_key = self.api_key
        sent_count = 0

        for message in email_messages:
            try:
                # Find HTML alternative if it is a multi-alternative email
                html_content = None
                if isinstance(message, EmailMultiAlternatives):
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            html_content = content
                            break

                from_email = message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', 'onboarding@resend.dev')

                # Construct Resend email payload
                payload = {
                    "from": from_email,
                    "to": message.to,
                    "subject": message.subject,
                    "text": message.body,
                }

                if html_content:
                    payload["html"] = html_content

                if message.cc:
                    payload["cc"] = message.cc
                if message.bcc:
                    payload["bcc"] = message.bcc
                if message.reply_to:
                    payload["reply_to"] = message.reply_to

                # Process attachments if present
                if message.attachments:
                    resend_attachments = []
                    for attachment in message.attachments:
                        try:
                            if isinstance(attachment, tuple):
                                filename, content, mimetype = attachment
                                if isinstance(content, str):
                                    content_bytes = content.encode('utf-8')
                                else:
                                    content_bytes = content
                                resend_attachments.append({
                                    "filename": filename,
                                    "content": list(base64.b64encode(content_bytes).decode('utf-8'))
                                })
                            else:
                                # Fallback/skip if attachment is a complex MIMEBase object
                                pass
                        except Exception as att_err:
                            logger.warning(f"Skipped attachment conversion error: {str(att_err)}")
                    if resend_attachments:
                        payload["attachments"] = resend_attachments

                # Dispatch email using Resend Python SDK
                resend.Emails.send(payload)
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send email via Resend: {str(e)}")
                if not self.fail_silently:
                    raise e

        return sent_count
