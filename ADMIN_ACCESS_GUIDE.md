# SmartGnosis Admin Access Guide


### Option 1: Email Login (Recommended for Testing)

1. Go to **https://smartgnosis.com**
2. Click the **"Log In"** button in the navigation
3. Enter your credentials:
4. Click **"Sign In"**
5. You'll be automatically redirected to the dashboard

### Option 2: Google OAuth

1. Go to **https://smartgnosis.com**
2. Click the **"Log In"** button
3. Click the **"Google"** button
4. Sign in with your Google account (`taycurry15@gmail.com`)
5. You'll be redirected back to the dashboard

---

## What Was Fixed

### Issues Resolved:

1. **✓ Email Login Issue**: Previously, signup/login would show "we'll be in touch" message
   - **Fixed**: Now properly authenticates and redirects to dashboard

2. **✓ Google OAuth Issue**: Previously redirected to "not found" page
   - **Fixed**: Now redirects to proper dashboard after OAuth success

3. **✓ Missing Dashboard**: No application interface existed for logged-in users
   - **Fixed**: Created a dashboard page that shows:
     - Welcome message
     - User account information
     - Role and status
     - Preview of upcoming features


---

## What You'll See After Login

The dashboard currently shows:
- Your account information (email, role, status)
- Preview cards for upcoming features:
  - CMMC Assessments
  - Evidence Collection
  - AI Analysis
  - Reports & Export
  - Continuous Monitoring
  - Provider Inheritance

**Note**: The full platform features are marked as "Coming Soon" - the dashboard serves as a placeholder while the complete application is being built.

---

## Technical Details

### Authentication Flow:
1. User submits login/signup form
2. API validates credentials and returns JWT tokens
3. Tokens stored in browser localStorage
4. User redirected to `/dashboard.html`
5. Dashboard decodes JWT to show user info
6. Authenticated users on landing page auto-redirect to dashboard

### API Endpoints Working:
- ✓ `POST /api/v1/auth/login` - Email/password authentication
- ✓ `POST /api/v1/auth/signup` - New user registration
- ✓ `GET /api/v1/auth/google` - Google OAuth initiation
- ✓ `GET /api/v1/auth/google/callback` - Google OAuth callback
- ✓ `GET /api/v1/auth/microsoft` - Microsoft OAuth initiation
- ✓ `GET /api/v1/auth/microsoft/callback` - Microsoft OAuth callback

### Database:
- PostgreSQL container: `cmmc-postgres`
- Database: `cmmc_platform`
- User sessions table: Active and working
- OAuth columns: Properly configured

---

## Testing Checklist

- [ ] Visit https://smartgnosis.com
- [ ] Click "Log In"
- [ ] Enter admin credentials
- [ ] Verify redirect to dashboard
- [ ] Verify your email and role are displayed
- [ ] Click "Logout" to test logout
- [ ] Try Google OAuth login
- [ ] Verify OAuth redirect to dashboard

---

## Next Steps

1. **Test the login** with your admin credentials
2. **Change your password** (feature to be implemented)
3. **Explore the dashboard** to see the layout
4. **Try Google OAuth** to ensure it works properly

---

## Troubleshooting

### If login doesn't work:
```bash
# Check API logs
docker logs cmmc-api

# Check nginx logs
docker logs cmmc-nginx

# Verify user in database
docker exec cmmc-postgres psql -U cmmc_admin -d cmmc_platform -c "SELECT email, role, active FROM users WHERE email = '[EMAIL]';"
```

### If OAuth fails:
- Verify Google OAuth credentials in `.env`
- Check OAuth redirect URI matches: `https://smartgnosis.com/api/v1/auth/google/callback`
- Review API logs for OAuth errors

### If dashboard doesn't load:
- Clear browser cache and localStorage
- Check browser console for JavaScript errors
- Verify dashboard.html exists in nginx container

---

## Support

If you encounter any issues:
1. Check the logs using commands above
2. Verify all containers are running: `docker ps`
3. Test API health: `curl https://smartgnosis.com/health`

---

Generated: 2025-11-16
Platform: SmartGnosis CMMC Compliance Platform
