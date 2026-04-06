# Stripe Configuration Guide for DocShift

This guide outlines the steps required to move from the current **Simulation Mode** to a live **Stripe** payment system for your Developer tier.

## 1. Obtain API Keys
1.  Log in to your [Stripe Dashboard](https://dashboard.stripe.com/).
2.  Navigate to **Developers** > **API Keys**.
3.  Copy your **Publishable key** (`pk_test_...`) and **Secret key** (`sk_test_...`).
4.  Add them to your `.env` file:
    ```bash
    STRIPE_PUBLIC_KEY=pk_test_your_key_here
    STRIPE_SECRET_KEY=sk_test_your_key_here
    ```

## 2. Configure Webhooks (Crucial for Upgrades)
Webhooks allow Stripe to tell your server when a payment is successful so that the user's plan can be upgraded automatically.

### For Local Development:
1.  Download and install the [Stripe CLI](https://stripe.com/docs/stripe-cli).
2.  Run `stripe login` in your terminal.
3.  Start forwarding events to your local server:
    ```bash
    stripe listen --forward-to localhost:8000/api/subscription/webhook/stripe/
    ```
4.  Copy the **Webhook Signing Secret** (`whsec_...`) provided by the CLI.
5.  Add it to your `.env` file:
    ```bash
    STRIPE_WEBHOOK_SECRET=whsec_your_cli_secret_here
    ```

### For Production:
1.  Go to **Developers** > **Webhooks** in the Stripe Dashboard.
2.  Add an endpoint: `https://your-domain.com/api/subscription/webhook/stripe/`.
3.  Select the event: `checkout.session.completed`.
4.  Copy the **Signing Secret** and update your production environment variables.

## 3. Product & Pricing (Optional for Dynamic Setup)
The current implementation uses **Dynamic Price Creation**, meaning it creates a $19/mo subscription on the fly. 

> [!TIP]
> **Best Practice**: For better reporting in Stripe, you should create a **Product** named "Developer Plan" with a **Recurring Price** of $19/mo in the Stripe Dashboard, then use that `price_id` (e.g., `price_1Pabc...`) in the `api/views.py` file.

## 4. Verification Flow
1.  **Click Upgrade**: User clicks "Upgrade to Developer" on your site.
2.  **Redirect**: They are sent to a Stripe-hosted checkout page.
3.  **Payment**: User enters test card data (Stripe's 4242...4242).
4.  **Callback**: Stripe sends a `checkout.session.completed` event to your webhook.
5.  **Provisioning**: Your server receives the event, finds the `user_id` in the metadata, and sets `plan_tier = 'Developer'`.

## Summary Checklist
- [ ] Stripe Account active
- [ ] `.env` updated with `STRIPE_PUBLIC_KEY`
- [ ] `.env` updated with `STRIPE_SECRET_KEY`
- [ ] `STRIPE_WEBHOOK_SECRET` configured for local or production
- [ ] Stripe CLI installed (for local testing)
