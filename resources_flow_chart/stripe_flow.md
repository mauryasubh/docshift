# DocShift Subscription & Payment Flow (Stripe)

This document details the technical implementation of the DocShift subscription system, covering both the automated **Developer** tier and the managed **Corporate** sales process.

## 1. Developer Plan: Automated Checkout

The Developer plan is built on **Stripe Checkout**, ensuring that users are never asked for sensitive card data on DocShift servers directly.

### A. Sequence Diagram

```mermaid
sequenceDiagram
    participant U as User (Authenticated)
    participant DS as DocShift Django
    participant S as Stripe (PCI Compliant)

    U->>DS: Clicks "Upgrade to Developer"
    DS->>DS: Pre-Validation (Log-in, Current Plan Check)
    DS->>S: POST /v1/checkout/sessions (Include user_id in Metadata)
    S-->>DS: JSON response with checkout_url
    DS-->>U: HTTP 303 Redirect to Stripe
    U->>S: Enter CC info & Confirm
    S->>S: Process Transaction (Charge / Subscription)
    S-->>U: Success Redirect to DocShift (?subscription=success)
    S->>DS: POST Webhook (checkout.session.completed)
    DS->>DS: Validate signature (STRIPE_WEBHOOK_SECRET)
    DS->>DS: Parse event, fetch User by ID from Metadata
    DS->>DS: Set profile.plan_tier = 'Developer'
    DS->>DS: Save stripe_customer_id & stripe_subscription_id
```

### B. Implementation Details
- **Session Metadata**: We pass the `user_id` in the `metadata` field of the Stripe Session. This allows the webhook to identify the user even if the browser session is closed.
- **Webhook Security**: All webhook requests are strictly verified using the `STRIPE_WEBHOOK_SECRET` and the `HTTP_STRIPE_SIGNATURE` header.
- **Dynamic Pricing**: For the MVP, we use dynamic price creation ($19.00 USD / Month) rather than hardcoded Price IDs, allowing for easier initial deployment.


---

## 2. Corporate Plan: Lead Generation

The Corporate plan uses a high-touch sales model. Interest is captured via a contact form and stored for manual review by the sales team.

### A. Sequence Diagram

```mermaid
sequenceDiagram
    participant U as Enterprise User
    participant DS as DocShift Django (Contact View)
    participant DB as SQL Database (SalesInquiry)
    participant AD as Admin Panel

    U->>DS: Clicks "Contact Sales"
    U->>DS: Fills Name, Email, Company, Message
    DS->>DB: Save to SalesInquiry model
    DS-->>U: Redirect to Pricing (/pricing/?contact=success)
    U->>U: UI Toast: "Inquiry Received! We'll contact you."
    AD->>DB: Admin reviews inquiry
    AD->>U: Manual Sales Reachout & Enterprise Provisioning
```

### B. "Premium Feedback" Logic
To ensure a high-quality experience without complex state management, we use **URL Query Parameters**:
1.  Upon a successful POST request in `converter/views.py`, we redirect the user to `/pricing/?contact=success`.
2.  A small JavaScript listener in **[pricing.html](file:///c:/Users/maury/OneDrive/Desktop/docshift/docshift/templates/converter/pricing.html)** detects this parameter and triggers a CSS-animated banner.

---

## 3. Data Models

### Profile (`api.models.Profile`)
Extends the standard Django User to track API-specific data:
- `plan_tier`: `Free` (Default), `Developer`, or `Corporate`.
- `stripe_customer_id`: Link to the Stripe Customer object.
- `stripe_subscription_id`: Link to the active subscription for easy cancellation.

### SalesInquiry (`converter.models.SalesInquiry`)
Captures leads for the high-touch corporate flow:
- `name`, `email`, `company`, `message`.
- `processed`: Boolean to track if sales has contacted them.

---

## 4. Security Tiers

- **Hobby (Free)**: 10MB limit, no API key required for manual tool use.
- **Developer ($19)**: 50MB limit, 5,000 API calls/month, Webhook access.
- **Corporate (Custom)**: 500MB+ limit, 50,000+ API calls/month, Priority Support.
