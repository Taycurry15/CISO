# OAuth Setup Guide

Google and Microsoft OAuth have been implemented but require credentials to function.

## Current Status

✅ **Implemented:**
- Google OAuth 2.0 endpoints
- Microsoft OAuth 2.0 endpoints
- Automatic user creation on first OAuth login
- JWT token generation and storage
- Frontend OAuth callback handling

⚠️ **Missing:** OAuth credentials (required to enable functionality)

## How to Enable Google OAuth

### 1. Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new project or select an existing one
3. Enable the **Google+ API**
4. Click **Create Credentials** → **OAuth client ID**
5. Configure the OAuth consent screen:
   - User Type: External
   - App name: SmartGnosis
   - User support email: Your email
   - Developer contact: Your email
6. Create OAuth client ID:
   - Application type: **Web application**
   - Name: SmartGnosis Web Client
   - Authorized redirect URIs:
     - `https://smartgnosis.com/api/v1/auth/google/callback`
     - `http://localhost/api/v1/auth/google/callback` (for testing)

7. Save the **Client ID** and **Client Secret**

### 2. Update Environment Variables

Edit `/home/deploy/apps/CISO/cmmc-platform/.env` and add:

```bash
# Google OAuth
GOOGLE_CLIENT_ID=your-client-id-here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret-here
GOOGLE_REDIRECT_URI=https://smartgnosis.com/api/v1/auth/google/callback

# Frontend URL
FRONTEND_URL=https://smartgnosis.com
```

### 3. Restart the API

```bash
docker compose restart api
```

### 4. Test Google OAuth

1. Visit https://smartgnosis.com
2. Click "Get Started" or "Sign In"
3. Click the "Google" button
4. You should be redirected to Google's login page
5. After logging in, you'll be redirected back to your site with authentication

## How to Enable Microsoft OAuth

### 1. Create Microsoft OAuth Credentials

1. Go to [Azure Portal - App Registrations](https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps)
2. Click **New registration**
3. Configure:
   - Name: SmartGnosis
   - Supported account types: Accounts in any organizational directory and personal Microsoft accounts
   - Redirect URI: Web → `https://smartgnosis.com/api/v1/auth/microsoft/callback`
4. Click **Register**
5. Copy the **Application (client) ID**
6. Go to **Certificates & secrets** → **New client secret**
7. Create a secret and copy the **Value** (not the Secret ID)

### 2. Configure API Permissions

1. Go to **API permissions**
2. Add permissions:
   - Microsoft Graph → Delegated permissions
   - Add: `openid`, `email`, `profile`
3. Click **Grant admin consent**

### 3. Update Environment Variables

Edit `/home/deploy/apps/CISO/cmmc-platform/.env` and add:

```bash
# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-application-id-here
MICROSOFT_CLIENT_SECRET=your-client-secret-here
MICROSOFT_REDIRECT_URI=https://smartgnosis.com/api/v1/auth/microsoft/callback

# Frontend URL
FRONTEND_URL=https://smartgnosis.com
```

### 4. Restart the API

```bash
docker compose restart api
```

## OAuth Flow

### How It Works:

1. **User clicks OAuth button** (Google/Microsoft)
   - Frontend redirects to `/api/v1/auth/google` or `/api/v1/auth/microsoft`

2. **Backend initiates OAuth flow**
   - Redirects user to Google/Microsoft login page

3. **User authenticates with provider**
   - Enters credentials on Google/Microsoft's secure page

4. **Provider redirects to callback**
   - User is sent to `/api/v1/auth/google/callback` with auth code

5. **Backend exchanges code for user info**
   - Gets user email, name, and provider ID
   - Creates user account if doesn't exist
   - Generates JWT tokens

6. **Backend redirects to frontend**
   - Sends user to `https://smartgnosis.com/?access_token=...&refresh_token=...`

7. **Frontend stores tokens**
   - JavaScript automatically stores tokens in localStorage
   - Page reloads with authenticated state

## Security Features

- ✅ State parameter validation (CSRF protection)
- ✅ HTTPS-only redirect URIs in production
- ✅ Secure token storage in localStorage
- ✅ Automatic user creation with admin role
- ✅ Session tracking in database
- ✅ Audit logging of OAuth logins

## Troubleshooting

### Error: "OAuth not configured"

Check API logs:
```bash
docker compose logs api | grep -i oauth
```

You should see:
- `Google OAuth configured` (if credentials are set)
- `Microsoft OAuth configured` (if credentials are set)

If you see warnings about missing credentials, verify your `.env` file has the correct values.

### Error: "redirect_uri_mismatch"

- Ensure the redirect URI in Google/Microsoft console exactly matches: `https://smartgnosis.com/api/v1/auth/google/callback`
- Check for trailing slashes - they must match exactly
- Verify HTTPS is being used in production

### Error: "Invalid client"

- Double-check your Client ID and Client Secret
- Make sure there are no extra spaces in the `.env` file
- Verify the credentials are from the correct Google/Microsoft project

## Testing Locally

For local testing, you can add `http://localhost/api/v1/auth/google/callback` as an authorized redirect URI in Google Cloud Console.

Update `.env`:
```bash
FRONTEND_URL=http://localhost
GOOGLE_REDIRECT_URI=http://localhost/api/v1/auth/google/callback
```

## Files Modified

- ✅ `cmmc-platform/api/oauth.py` - New OAuth implementation
- ✅ `cmmc-platform/api/main.py` - OAuth endpoints added
- ✅ `cmmc-platform/requirements.txt` - Added `authlib==1.3.0`
- ✅ `landing-page/assets/js/main.js` - OAuth callback handler
- ✅ `cmmc-platform/.env` - OAuth configuration placeholders
- ✅ Database: Added `oauth_provider` and `oauth_provider_id` columns to `users` table

## Next Steps

1. Obtain Google OAuth credentials from Google Cloud Console
2. Obtain Microsoft OAuth credentials from Azure Portal (optional)
3. Update the `.env` file with your credentials
4. Restart the API: `docker compose restart api`
5. Test OAuth login from https://smartgnosis.com

---

**Note:** OAuth will NOT work until you add the credentials to the `.env` file. The buttons will redirect but authentication will fail without valid OAuth client credentials.
