# DocShift Manual Registration & Email Verification Flow

This flowchart describes the step-by-step user signup, email verification, and login process in DocShift, using **Django-Allauth** and the custom **Resend Email Backend**.

```mermaid
graph TD
    %% Define Styles
    classDef page fill:#FF9900,stroke:#232F3E,stroke-width:2px,color:white;
    classDef process fill:#232F3E,stroke:#FF9900,stroke-width:2px,color:white;
    classDef success fill:#34d399,stroke:#10b981,stroke-width:2px,color:white;
    classDef failure fill:#ef4444,stroke:#dc2626,stroke-width:2px,color:white;

    %% Elements
    Start([👤 New User Registration]) --> Form[📝 User fills Signup Form]:::page
    Form --> Submit{User Clicks Register}
    
    %% Backend Processing
    Submit --> CreateUser[⚙️ Django creates User Account]:::process
    CreateUser --> GenToken[🔑 Generate Email Verification Token]:::process
    GenToken --> SendMail[✉️ Send Verification Email via Resend SDK]:::process
    
    %% Redirect & Verify
    SendMail --> RedirectSent[📄 Redirect to Check Inbox Page]:::page
    RedirectSent -.-> UserInbox[📬 User checks Email Inbox]
    
    UserInbox --> ClickLink{Clicks Verification Link}
    ClickLink -->|Invalid/Expired Key| LinkExpired[❌ Shows Link Expired Page]:::failure
    ClickLink -->|Valid Key| ConfirmPage[📄 Shows Confirm Email Page]:::page
    
    LinkExpired --> ResendLink[🔄 Request Resend / Return to Login]:::page
    ConfirmPage --> ClickConfirm{Clicks 'Confirm Email Address'}
    
    ClickConfirm --> SetVerified[⚙️ Marks Email as Verified]:::process
    SetVerified --> RedirectLogin[📄 Redirects to Login Page]:::page
    
    %% Login Flow
    RedirectLogin --> EnterCredentials[👤 User enters Credentials]:::page
    EnterCredentials --> VerifyLogin{Checks Verification State}
    
    VerifyLogin -->|Email Unverified| UnverifiedError[⚠️ Shows Verification Required Page]:::failure
    UnverifiedError --> ResendVerify[✉️ Resend Verification Option]:::page
    
    VerifyLogin -->|Email Verified| LoginSuccess[🎉 Access Granted]:::success
    LoginSuccess --> Dashboard[💻 User Redirected to /dashboard/]:::page
```

### 🛠️ What We Did & Core Components

We configured a complete, secure manual login and email verification flow:

1. **Mandatory Verification Settings** ([settings.py](file:///c:/Users/maury/OneDrive/Desktop/docshift/final_version_live/docshift/docshift/settings.py)):
   - Configured `ACCOUNT_EMAIL_VERIFICATION = 'mandatory'` to ensure users cannot access the dashboard or premium tools until they confirm their email.
   - Configured `SOCIALACCOUNT_EMAIL_REQUIRED = True` to guarantee that social signups (Google, GitHub) always retrieve verified emails.

2. **Custom Resend Email Backend** ([email_backend.py](file:///c:/Users/maury/OneDrive/Desktop/docshift/final_version_live/docshift/converter/email_backend.py)):
   - Created `ResendEmailBackend` to hook into Django's mailing engine.
   - Reads `RESEND_API_KEY` to send rich, multi-part HTML verification emails using the official **Resend Python SDK**.

3. **Premium User Interface Templates** ([templates/account/](file:///c:/Users/maury/OneDrive/Desktop/docshift/final_version_live/docshift/templates/account/)):
   - Created and customized the registration templates to match the sleek dark-mode design system:
     - `email_verification_sent.html`: Beautiful envelope illustration instructing the user to check their email.
     - `email_confirm.html`: Interactive page asking the user to confirm their email address or warning them if their link is expired.
     - `verified_email_required.html`: Restricts access if the user attempts to log in before verifying, offering an option to resend the verification email.
