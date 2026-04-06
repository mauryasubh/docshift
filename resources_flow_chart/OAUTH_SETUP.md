# OAuth Setup Guide — Google & GitHub

After running `./start.sh`, visit http://127.0.0.1:8000/admin  
Log in with your admin account, then follow the steps below.

---

## Step 1 — Set your Site domain

1. Go to **Sites → Sites** in the admin
2. Click the default site (example.com)
3. Set **Domain name**: `127.0.0.1:8000`
4. Set **Display name**: `DocShift`
5. Save

---

## Step 2 — GitHub OAuth

### Create the GitHub OAuth App:
1. Go to https://github.com/settings/developers
2. Click **New OAuth App**
3. Fill in:
   - **Application name**: `DocShift`
   - **Homepage URL**: `http://127.0.0.1:8000`
   - **Authorization callback URL**: `http://127.0.0.1:8000/auth/github/login/callback/`
4. Click **Register application**
5. Copy the **Client ID**
6. Click **Generate a new client secret** and copy it

### Add to Django admin:
1. Go to **Social Accounts → Social applications**
2. Click **Add Social Application**
3. Fill in:
   - **Provider**: `GitHub`
   - **Name**: `GitHub`
   - **Client id**: *(paste your Client ID)*
   - **Secret key**: *(paste your Client Secret)*
   - **Sites**: move `127.0.0.1:8000` to Chosen sites
4. Save

---

## Step 3 — Google OAuth

### Create the Google OAuth App:
1. Go to https://console.cloud.google.com
2. Create a project (or select existing)
3. Go to **APIs & Services → Credentials**
4. Click **Create Credentials → OAuth 2.0 Client IDs**
5. Set **Application type**: Web application
6. Add **Authorised redirect URI**:
   `http://127.0.0.1:8000/auth/google/login/callback/`
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

### Add to Django admin:
1. Go to **Social Accounts → Social applications**
2. Click **Add Social Application**
3. Fill in:
   - **Provider**: `Google`
   - **Name**: `Google`
   - **Client id**: *(paste your Client ID)*
   - **Secret key**: *(paste your Client Secret)*
   - **Sites**: move `127.0.0.1:8000` to Chosen sites
4. Save

---

## Done!

Visit http://127.0.0.1:8000/auth/login — you'll see the Google and GitHub buttons working.

### For production (real domain):
- Replace all `127.0.0.1:8000` with your actual domain
- Set `DEBUG = False` in settings.py
- Set a strong `SECRET_KEY`
- Add your domain to `ALLOWED_HOSTS`
