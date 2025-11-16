# ComplianceFlow API Integration Guide

This guide explains how to integrate the ComplianceFlow landing page with your backend authentication API.

## Table of Contents

- [Authentication Flow](#authentication-flow)
- [API Endpoints](#api-endpoints)
- [Request/Response Formats](#requestresponse-formats)
- [Error Handling](#error-handling)
- [Security Considerations](#security-considerations)
- [Testing](#testing)

## Authentication Flow

### Login Flow

```
1. User fills login form (email + password)
2. Frontend validates inputs
3. POST /api/v1/auth/login
4. Backend validates credentials
5. Backend returns JWT token + user data
6. Frontend stores token (httpOnly cookie or localStorage)
7. Redirect to dashboard
```

### Signup Flow

```
1. User fills signup form (name, company, email, password)
2. Frontend validates inputs + password strength
3. POST /api/v1/auth/signup
4. Backend creates user account
5. Backend sends verification email (optional)
6. Backend returns JWT token + user data
7. Frontend stores token
8. Redirect to onboarding
```

### OAuth Flow (Google/Microsoft)

```
1. User clicks social auth button
2. Redirect to /api/v1/auth/oauth/{provider}
3. Backend redirects to OAuth provider
4. User authorizes
5. Provider redirects back with code
6. Backend exchanges code for token
7. Backend creates/updates user
8. Backend returns JWT token
9. Redirect to dashboard
```

## API Endpoints

### POST /api/v1/auth/login

**Request:**
```json
{
  "email": "user@company.com",
  "password": "SecurePassword123!",
  "remember": false
}
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_1234567890",
      "email": "user@company.com",
      "firstName": "John",
      "lastName": "Doe",
      "company": "Acme Defense Corp",
      "role": "admin",
      "emailVerified": true,
      "createdAt": "2025-01-15T10:30:00Z"
    },
    "token": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "expiresIn": 3600,
      "tokenType": "Bearer"
    }
  },
  "message": "Login successful"
}
```

**Error Response (401):**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": null
  }
}
```

**Error Response (429 - Rate Limited):**
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many login attempts. Please try again in 15 minutes.",
    "details": {
      "retryAfter": 900
    }
  }
}
```

### POST /api/v1/auth/signup

**Request:**
```json
{
  "firstName": "John",
  "lastName": "Doe",
  "company": "Acme Defense Corp",
  "email": "john.doe@acme.com",
  "password": "SecurePassword123!",
  "terms": true
}
```

**Success Response (201):**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "usr_1234567890",
      "email": "john.doe@acme.com",
      "firstName": "John",
      "lastName": "Doe",
      "company": "Acme Defense Corp",
      "role": "user",
      "emailVerified": false,
      "createdAt": "2025-01-16T14:20:00Z"
    },
    "token": {
      "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "expiresIn": 3600,
      "tokenType": "Bearer"
    }
  },
  "message": "Account created successfully. Please verify your email."
}
```

**Error Response (400):**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "email": "Email already exists",
      "password": "Password must be at least 8 characters"
    }
  }
}
```

### POST /api/v1/auth/forgot-password

**Request:**
```json
{
  "email": "user@company.com"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Password reset link sent to your email",
  "data": {
    "resetTokenExpiry": "2025-01-16T16:00:00Z"
  }
}
```

### POST /api/v1/auth/reset-password

**Request:**
```json
{
  "token": "reset_token_here",
  "password": "NewSecurePassword123!",
  "confirmPassword": "NewSecurePassword123!"
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Password reset successful"
}
```

### GET /api/v1/auth/oauth/{provider}

**Supported Providers:** `google`, `microsoft`

**Query Parameters:**
- `redirect_uri` (optional): Where to redirect after auth

**Response:**
Redirects to OAuth provider

### GET /api/v1/auth/oauth/{provider}/callback

**Query Parameters:**
- `code`: Authorization code from provider
- `state`: CSRF token

**Response:**
Redirects to frontend with token in URL or cookie

### POST /api/v1/auth/refresh

**Request:**
```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "success": true,
  "data": {
    "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expiresIn": 3600
  }
}
```

### POST /api/v1/auth/logout

**Headers:**
```
Authorization: Bearer {accessToken}
```

**Request:**
```json
{
  "refreshToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `EMAIL_EXISTS` | 400 | Email already registered |
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `TOKEN_EXPIRED` | 401 | JWT token expired |
| `TOKEN_INVALID` | 401 | JWT token invalid |
| `EMAIL_NOT_VERIFIED` | 403 | Email verification required |
| `ACCOUNT_DISABLED` | 403 | Account has been disabled |
| `INTERNAL_ERROR` | 500 | Server error |

## Security Considerations

### Password Requirements

Enforce these on the backend:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- No common passwords (check against breach databases)

### Rate Limiting

Implement rate limiting for authentication endpoints:
- **Login**: 5 attempts per 15 minutes per IP
- **Signup**: 3 attempts per hour per IP
- **Password Reset**: 3 attempts per hour per email

### CSRF Protection

For session-based auth:
1. Generate CSRF token on page load
2. Include in all state-changing requests
3. Validate on backend

### Token Security

**JWT Storage:**
- **Recommended**: httpOnly cookies (prevents XSS)
- **Alternative**: localStorage with XSS protection

**Token Expiry:**
- Access Token: 1 hour
- Refresh Token: 7 days
- Implement token rotation

### OAuth Security

- Validate `state` parameter (CSRF protection)
- Use PKCE for additional security
- Verify OAuth callback origin
- Store OAuth tokens securely

## Frontend Integration

### Update main.js

Replace demo mode with actual API calls:

```javascript
// Remove "|| true" from login/signup handlers
if (response.ok) { // Remove || true
    // Success handling
}

// Update API URLs
const response = await fetch(`${config.api.baseUrl}${config.api.endpoints.login}`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': getCsrfToken(),
    },
    body: JSON.stringify({ email, password }),
    credentials: 'include', // Include cookies
});
```

### Token Storage

```javascript
// Store token after successful login
function storeAuthToken(token) {
    // Option 1: httpOnly cookie (backend sets this)
    // No frontend code needed

    // Option 2: localStorage
    localStorage.setItem('cf_access_token', token.accessToken);
    localStorage.setItem('cf_refresh_token', token.refreshToken);

    // Option 3: sessionStorage (expires when tab closes)
    sessionStorage.setItem('cf_access_token', token.accessToken);
}

// Get token for API requests
function getAuthToken() {
    return localStorage.getItem('cf_access_token');
}

// Clear token on logout
function clearAuthToken() {
    localStorage.removeItem('cf_access_token');
    localStorage.removeItem('cf_refresh_token');
}
```

### Authenticated Requests

```javascript
async function makeAuthenticatedRequest(url, options = {}) {
    const token = getAuthToken();

    const response = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
        credentials: 'include',
    });

    // Handle token expiry
    if (response.status === 401) {
        // Try to refresh token
        const refreshed = await refreshAuthToken();
        if (refreshed) {
            // Retry request
            return makeAuthenticatedRequest(url, options);
        } else {
            // Redirect to login
            window.location.href = '/';
        }
    }

    return response;
}
```

### Token Refresh

```javascript
async function refreshAuthToken() {
    const refreshToken = localStorage.getItem('cf_refresh_token');
    if (!refreshToken) return false;

    try {
        const response = await fetch(`${config.api.baseUrl}${config.api.endpoints.refresh}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refreshToken }),
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('cf_access_token', data.data.accessToken);
            return true;
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
    }

    return false;
}
```

## Testing

### Manual Testing Checklist

- [ ] Login with valid credentials
- [ ] Login with invalid email
- [ ] Login with invalid password
- [ ] Login rate limiting (5 failed attempts)
- [ ] Signup with all fields
- [ ] Signup with existing email
- [ ] Signup with weak password
- [ ] Signup rate limiting
- [ ] Google OAuth flow
- [ ] Microsoft OAuth flow
- [ ] Forgot password flow
- [ ] Token refresh on expiry
- [ ] Logout functionality
- [ ] CSRF protection
- [ ] XSS protection

### Automated Testing

Create API integration tests:

```javascript
describe('Authentication API', () => {
    test('POST /api/v1/auth/login - success', async () => {
        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: 'test@example.com',
                password: 'TestPassword123!'
            }),
        });

        expect(response.status).toBe(200);
        const data = await response.json();
        expect(data.success).toBe(true);
        expect(data.data.token.accessToken).toBeDefined();
    });

    test('POST /api/v1/auth/login - invalid credentials', async () => {
        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                email: 'test@example.com',
                password: 'WrongPassword'
            }),
        });

        expect(response.status).toBe(401);
        const data = await response.json();
        expect(data.success).toBe(false);
        expect(data.error.code).toBe('INVALID_CREDENTIALS');
    });
});
```

## Production Checklist

Before deploying to production:

- [ ] Update API base URL in config
- [ ] Set all environment variables
- [ ] Enable HTTPS for all endpoints
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable CSRF protection
- [ ] Configure secure cookie settings
- [ ] Set up error tracking (Sentry)
- [ ] Test OAuth flows in production
- [ ] Set up monitoring and alerts
- [ ] Configure CDN for static assets
- [ ] Enable request logging
- [ ] Set up backup authentication method

## Support

For API integration support:
- **Documentation**: https://docs.complianceflow.app/api
- **Support**: support@complianceflow.app
- **Status**: https://status.complianceflow.app
