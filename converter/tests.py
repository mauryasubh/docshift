import os
import io
from django.test import TestCase
from .signing import sign_pdf, verify_pdf
import fitz

class DigitalSignatureTests(TestCase):
    def test_sign_and_verify_pdf(self):
        # Create a dummy PDF in memory
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Hello ShiftDocs!")
        pdf_bytes = doc.write()
        doc.close()
        
        # Sign the PDF with a visible stamp
        signed_bytes = sign_pdf(
            pdf_bytes,
            signer_name="Test Signer",
            reason="Contract Acceptance",
            visual_signature=True,
            position="bottom_right",
            page_choice="last"
        )
        
        # Verify the signed bytes are non-empty and different
        self.assertIsNotNone(signed_bytes)
        self.assertNotEqual(len(signed_bytes), len(pdf_bytes))
        
        # Run verify_pdf on the signed bytes
        result = verify_pdf(signed_bytes)
        self.assertTrue(result['has_signatures'])
        self.assertEqual(result['status'], 'valid')
        self.assertEqual(len(result['signatures']), 1)
        self.assertEqual(result['signatures'][0]['signer_name'], 'Test Signer')
        self.assertEqual(result['signatures'][0]['reason'], 'Contract Acceptance')

    def test_separated_rate_limits(self):
        from django.test import RequestFactory
        from django.contrib.auth.models import User, AnonymousUser
        from django.contrib.sessions.middleware import SessionMiddleware
        from converter.views import _check_sign_rate_limit, _record_sign_usage
        
        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/digital-sign/')
        
        # Add session support to request
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        
        # Guest user
        request.user = AnonymousUser()
        
        from django.conf import settings
        limit_sign = getattr(settings, 'DSIGN_LIMIT_GUEST_SIGN', 5)
        limit_verify = getattr(settings, 'DSIGN_LIMIT_GUEST_VERIFY', 5)

        # Check initial limits
        allowed, remaining, _ = _check_sign_rate_limit(request, 'sign')
        self.assertTrue(allowed)
        self.assertEqual(remaining, limit_sign)
        
        # Record usage
        _record_sign_usage(request, 'sign')
        
        allowed, remaining, _ = _check_sign_rate_limit(request, 'sign')
        self.assertTrue(allowed)
        self.assertEqual(remaining, limit_sign - 1)
        
        # Verification remaining should still be limit_verify
        allowed_v, remaining_v, _ = _check_sign_rate_limit(request, 'verify')
        self.assertTrue(allowed_v)
        self.assertEqual(remaining_v, limit_verify)

    def test_sign_with_custom_stamp_styles_and_offsets(self):
        # Create a dummy PDF in memory
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "Hello ShiftDocs with custom styles!")
        pdf_bytes = doc.write()
        doc.close()

        # Test each style and some offsets
        for style in ['card', 'qr_only', 'text_only']:
            for offset in [10, 40, 80]:
                signed_bytes = sign_pdf(
                    pdf_bytes,
                    signer_name="Test Custom Signer",
                    reason="Verification",
                    visual_signature=True,
                    position="bottom_right",
                    page_choice="last",
                    stamp_style=style,
                    offset=offset
                )
                self.assertIsNotNone(signed_bytes)
                self.assertNotEqual(len(signed_bytes), len(pdf_bytes))
                
                # Verify integrity
                result = verify_pdf(signed_bytes)
                self.assertTrue(result['has_signatures'])
                self.assertEqual(result['status'], 'valid')

from unittest.mock import patch
from django.core.mail import send_mail, EmailMultiAlternatives

class ResendEmailBackendTests(TestCase):
    @patch('resend.Emails.send')
    def test_send_email_successful(self, mock_send):
        # Override the settings inside the test to force usage of our backend
        with self.settings(
            EMAIL_BACKEND='converter.email_backend.ResendEmailBackend',
            RESEND_API_KEY='test_resend_api_key_123',
            DEFAULT_FROM_EMAIL='onboarding@resend.dev'
        ):
            # 1. Simple text email
            send_mail(
                subject='Test Subject',
                message='Test Body',
                from_email='onboarding@resend.dev',
                recipient_list=['receiver@example.com'],
                fail_silently=False
            )
            
            # Verify resend.Emails.send was called with correct payload
            mock_send.assert_called_once_with({
                "from": "onboarding@resend.dev",
                "to": ["receiver@example.com"],
                "subject": "Test Subject",
                "text": "Test Body"
            })
            
    @patch('resend.Emails.send')
    def test_send_multipart_email_successful(self, mock_send):
        with self.settings(
            EMAIL_BACKEND='converter.email_backend.ResendEmailBackend',
            RESEND_API_KEY='test_resend_api_key_123',
            DEFAULT_FROM_EMAIL='onboarding@resend.dev'
        ):
            # 2. Email with HTML alternatives
            msg = EmailMultiAlternatives(
                subject='Html Subject',
                body='Text content',
                from_email='onboarding@resend.dev',
                to=['receiver2@example.com'],
                cc=['cc@example.com'],
                bcc=['bcc@example.com'],
                reply_to=['reply@example.com']
            )
            msg.attach_alternative('<p>Html content</p>', 'text/html')
            msg.send(fail_silently=False)
            
            mock_send.assert_called_once_with({
                "from": "onboarding@resend.dev",
                "to": ["receiver2@example.com"],
                "subject": "Html Subject",
                "text": "Text content",
                "html": "<p>Html content</p>",
                "cc": ["cc@example.com"],
                "bcc": ["bcc@example.com"],
                "reply_to": ["reply@example.com"]
            })
