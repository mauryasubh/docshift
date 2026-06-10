import io
import fitz
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from api.models import Profile

class DeveloperDigitalSignatureApiTests(TestCase):
    def setUp(self):
        # 1. Create a test user
        self.username = "devuser"
        self.password = "devpassword123"
        self.user = User.objects.create_user(username=self.username, password=self.password, email="dev@example.com")
        
        # 2. Get and update API profile to Developer tier
        self.profile = self.user.api_profile
        self.profile.plan_tier = "Developer"
        self.profile.plan_start_date = timezone.now()
        self.profile.plan_expiry_date = timezone.now() + timedelta(days=30)
        self.profile.save()
        
        self.api_key = str(self.profile.api_key)
        self.headers = {
            "HTTP_AUTHORIZATION": f"Bearer {self.api_key}"
        }
        
        # 3. Create a dummy PDF in memory
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((100, 100), "API Signature Test Document")
        self.pdf_bytes = doc.write()
        doc.close()

    def test_missing_or_invalid_auth(self):
        # Missing Authorization header
        response = self.client.post('/api/v1/digital-sign/sign/', {})
        self.assertEqual(response.status_code, 401)
        self.assertIn("Missing or invalid Authorization", response.json()['error'])
        
        # Malformed Authorization header
        response = self.client.post('/api/v1/digital-sign/sign/', {}, HTTP_AUTHORIZATION="Bearer invalid_key_here")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Invalid API Key", response.json()['error'])

    def test_free_tier_cannot_use_api(self):
        # Set profile tier back to Free
        self.profile.plan_tier = "Free"
        self.profile.save()
        
        file_payload = io.BytesIO(self.pdf_bytes)
        file_payload.name = "test.pdf"
        
        response = self.client.post(
            '/api/v1/digital-sign/sign/', 
            {'file': file_payload}, 
            **self.headers
        )
        self.assertEqual(response.status_code, 402)
        self.assertIn("Monthly quota exceeded", response.json()['error'])

    def test_sign_pdf_successful(self):
        file_payload = io.BytesIO(self.pdf_bytes)
        file_payload.name = "original.pdf"
        
        response = self.client.post(
            '/api/v1/digital-sign/sign/',
            {
                'file': file_payload,
                'reason': 'Developer Sign Test',
                'visual_signature': 'true',
                'position': 'bottom_left',
                'stamp_style': 'card'
            },
            **self.headers
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.has_header('Content-Disposition'))
        self.assertIn('signed_original.pdf', response['Content-Disposition'])
        
        # Verify signed bytes are valid PDF
        signed_pdf_bytes = b"".join(response.streaming_content)
        self.assertIsNotNone(signed_pdf_bytes)
        self.assertNotEqual(len(signed_pdf_bytes), len(self.pdf_bytes))
        
        # Verify quota incremented
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.api_calls_used_this_month, 1)

    def test_verify_signatures_successful(self):
        # First sign the document
        from converter.signing import sign_pdf
        signed_pdf_bytes = sign_pdf(
            self.pdf_bytes,
            signer_name="Developer Agent",
            reason="Verification Unit Test",
            visual_signature=True,
            position="bottom_right"
        )
        
        # Upload signed document to verification endpoint
        file_payload = io.BytesIO(signed_pdf_bytes)
        file_payload.name = "signed.pdf"
        
        response = self.client.post(
            '/api/v1/digital-sign/verify/',
            {'file': file_payload},
            **self.headers
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['has_signatures'])
        self.assertEqual(data['status'], 'valid')
        self.assertEqual(len(data['signatures']), 1)
        self.assertEqual(data['signatures'][0]['signer_name'], 'Developer Agent')
        self.assertEqual(data['signatures'][0]['reason'], 'Verification Unit Test')
        
        # Verify quota incremented
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.api_calls_used_this_month, 1)


from unittest.mock import patch

class RazorpaySubscriptionTests(TestCase):
    def setUp(self):
        self.username = "testbuyer"
        self.password = "pass123"
        self.user = User.objects.create_user(username=self.username, password=self.password, email="buyer@example.com")
        self.client.login(username=self.username, password=self.password)

    @patch('razorpay.Client')
    def test_create_order_30_days(self, mock_client):
        # Setup mock client behavior
        mock_instance = mock_client.return_value
        mock_instance.order.create.return_value = {
            'id': 'order_123',
            'amount': 79900,
            'currency': 'INR'
        }
        
        response = self.client.get('/api/subscription/razorpay/create-order/?duration=1')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['order_id'], 'order_123')
        self.assertEqual(data['amount'], 79900)
        self.assertEqual(data['description'], 'Developer Plan (30 Days)')
        
        # Verify order notes parameters
        mock_instance.order.create.assert_called_once()
        call_args = mock_instance.order.create.call_args[1]['data']
        self.assertEqual(call_args['amount'], 79900)
        self.assertEqual(call_args['notes']['days'], 30)

    @patch('razorpay.Client')
    def test_create_order_90_days(self, mock_client):
        mock_instance = mock_client.return_value
        mock_instance.order.create.return_value = {
            'id': 'order_456',
            'amount': 149900,
            'currency': 'INR'
        }
        
        response = self.client.get('/api/subscription/razorpay/create-order/?duration=3')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['order_id'], 'order_456')
        self.assertEqual(data['amount'], 149900)
        self.assertEqual(data['description'], 'Developer Plan (90 Days)')
        
        mock_instance.order.create.assert_called_once()
        call_args = mock_instance.order.create.call_args[1]['data']
        self.assertEqual(call_args['amount'], 149900)
        self.assertEqual(call_args['notes']['days'], 90)

    @patch('razorpay.Client')
    def test_verify_and_webhook_guards(self, mock_client):
        mock_instance = mock_client.return_value
        # Mock order.fetch for verify view
        mock_instance.order.fetch.return_value = {
            'id': 'order_789',
            'notes': {'days': 30, 'user_id': self.user.id}
        }
        
        # 1. Test verification updates profile correctly
        import json
        payload = {
            'razorpay_payment_id': 'pay_789',
            'razorpay_order_id': 'order_789',
            'razorpay_signature': 'sig_789'
        }
        response = self.client.post(
            '/api/subscription/razorpay/verify/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.user.api_profile.refresh_from_db()
        self.assertEqual(self.user.api_profile.plan_tier, 'Developer')
        self.assertEqual(self.user.api_profile.razorpay_order_id, 'order_789')
        
        # Expiry date should be set to ~30 days from now
        from django.utils import timezone
        diff = self.user.api_profile.plan_expiry_date - timezone.now()
        self.assertTrue(29 <= diff.days <= 30)
        
        # Save expiry date to check against webhook race condition guard
        expiry_before_webhook = self.user.api_profile.plan_expiry_date
        
        # 2. Test webhook race condition guard: it should not modify plan_expiry_date if already active
        webhook_payload = {
            'event': 'order.paid',
            'payload': {
                'order': {
                    'entity': {
                        'id': 'order_789',
                        'notes': {
                            'user_id': self.user.id,
                            'days': 30
                        }
                    }
                }
            }
        }
        # Webhook call signature verification mock
        mock_instance.utility.verify_webhook_signature.return_value = True
        
        # Execute webhook POST
        response = self.client.post(
            '/api/subscription/razorpay/webhook/',
            data=json.dumps(webhook_payload),
            content_type='application/json',
            HTTP_X_RAZORPAY_SIGNATURE='dummy_sig'
        )
        self.assertEqual(response.status_code, 200)
        self.user.api_profile.refresh_from_db()
        
        # Expiry date should NOT have changed (exact match of timestamp)
        self.assertEqual(self.user.api_profile.plan_expiry_date, expiry_before_webhook)

    @patch('razorpay.Client')
    def test_verify_unauthorized_user_fails(self, mock_client):
        mock_instance = mock_client.return_value
        # Mock order.fetch for verify view returning a mismatching user_id
        mock_instance.order.fetch.return_value = {
            'id': 'order_999',
            'notes': {'days': 30, 'user_id': 99999}  # Mismatching user ID
        }
        
        import json
        payload = {
            'razorpay_payment_id': 'pay_999',
            'razorpay_order_id': 'order_999',
            'razorpay_signature': 'sig_999'
        }
        response = self.client.post(
            '/api/subscription/razorpay/verify/',
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Unauthorized order verification", response.json()['error'])


class StripeSubscriptionTests(TestCase):
    def setUp(self):
        self.username = "stripebuyer"
        self.password = "stripe123"
        self.user = User.objects.create_user(username=self.username, password=self.password, email="stripe@example.com")
        self.client.login(username=self.username, password=self.password)

    @patch('stripe.checkout.Session.create')
    def test_stripe_checkout_usa_usd(self, mock_create):
        with self.settings(STRIPE_SECRET_KEY='sk_live_testkey'):
            mock_create.return_value = type('Session', (object,), {'url': 'https://checkout.stripe.com/pay/session_usd'})()
            
            # Request from US
            response = self.client.get('/api/subscription/checkout/developer/?geoip_mock=US')
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.url, 'https://checkout.stripe.com/pay/session_usd')
            
            # Assert currency is usd
            mock_create.assert_called_once()
            call_args = mock_create.call_args[1]['line_items'][0]['price_data']
            self.assertEqual(call_args['currency'], 'usd')
            self.assertEqual(call_args['unit_amount'], 1900)
