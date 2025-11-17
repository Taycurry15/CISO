"""
OAuth 2.0 Authentication
========================
Provides OAuth authentication with Google and Microsoft.

Features:
- Google OAuth 2.0
- Microsoft OAuth 2.0
- Automatic user creation on first login
- Organization assignment
"""

from typing import Optional, Dict, Any
from datetime import datetime
import secrets
import asyncpg
import logging
import os
from urllib.parse import urlparse
from fastapi import HTTPException, status, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config

from api.auth import (
    create_access_token,
    create_refresh_token,
    hash_password,
    AuthToken,
    UserRole,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)

logger = logging.getLogger(__name__)

# OAuth Configuration
config = Config(environ=os.environ)

oauth = OAuth(config)

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost/api/v1/auth/google/callback")

# Microsoft OAuth
MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
MICROSOFT_REDIRECT_URI = os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost/api/v1/auth/microsoft/callback")

# Frontend redirect after successful OAuth
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://smartgnosis.com")

# Cookie settings helper
def set_auth_cookies(response: RedirectResponse, auth_token: AuthToken):
    """
    Set HttpOnly cookies for access/refresh tokens instead of placing them in URLs.
    """
    parsed = urlparse(FRONTEND_URL)
    cookie_domain = parsed.hostname
    secure = parsed.scheme == "https"

    response.set_cookie(
        "access_token",
        auth_token.access_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        domain=cookie_domain,
        path="/",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    if auth_token.refresh_token:
        response.set_cookie(
            "refresh_token",
            auth_token.refresh_token,
            httponly=True,
            secure=secure,
            samesite="lax",
            domain=cookie_domain,
            path="/",
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )

def oauth_state_cookie_params(request: Request) -> dict:
    """Return secure cookie parameters for OAuth state handling."""
    parsed = urlparse(str(request.url))
    return {
        "httponly": True,
        "secure": parsed.scheme == "https",
        "samesite": "lax",
        "domain": parsed.hostname,
        "path": "/",
        "max_age": 600,  # 10 minutes
    }

def generate_oauth_state() -> str:
    """Generate a random OAuth state token."""
    return secrets.token_urlsafe(32)

# Register OAuth providers
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name='google',
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    logger.info("Google OAuth configured")
else:
    logger.warning("Google OAuth not configured - missing credentials")

if MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET:
    oauth.register(
        name='microsoft',
        client_id=MICROSOFT_CLIENT_ID,
        client_secret=MICROSOFT_CLIENT_SECRET,
        server_metadata_url='https://login.microsoftonline.com/common/v2.0/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile'
        }
    )
    logger.info("Microsoft OAuth configured")
else:
    logger.warning("Microsoft OAuth not configured - missing credentials")


async def find_or_create_oauth_user(
    email: str,
    full_name: str,
    provider: str,
    provider_user_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Find existing user or create new user from OAuth login.

    Args:
        email: User email from OAuth provider
        full_name: User's full name
        provider: OAuth provider (google, microsoft)
        provider_user_id: User ID from OAuth provider
        conn: Database connection

    Returns:
        User data dictionary
    """
    # Check if user exists
    user = await conn.fetchrow(
        """
        SELECT id, email, organization_id, role, full_name, active
        FROM users
        WHERE email = $1
        """,
        email.lower()
    )

    if user:
        # User exists - verify active
        if not user['active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive"
            )

        logger.info(f"Existing user logged in via {provider}: {email}")

        return {
            "id": str(user['id']),
            "email": user['email'],
            "organization_id": str(user['organization_id']),
            "role": user['role'],
            "full_name": user['full_name']
        }

    # User doesn't exist - create new user and organization
    logger.info(f"Creating new user from {provider} OAuth: {email}")

    # Extract company domain from email for organization name
    email_domain = email.split('@')[1] if '@' in email else 'Unknown'
    company_name = f"{email_domain.split('.')[0].title()} (via {provider.title()})"

    # Create organization
    org_id = await conn.fetchval(
        """
        INSERT INTO organizations (name, active)
        VALUES ($1, TRUE)
        RETURNING id
        """,
        company_name
    )

    # Generate a random password (user won't use it since they login via OAuth)
    random_password = secrets.token_urlsafe(32)
    password_hash = hash_password(random_password)

    # Create user
    user_id = await conn.fetchval(
        """
        INSERT INTO users
        (email, password_hash, full_name, organization_id, role, active, oauth_provider, oauth_provider_id)
        VALUES ($1, $2, $3, $4, $5, TRUE, $6, $7)
        RETURNING id
        """,
        email.lower(),
        password_hash,
        full_name,
        org_id,
        UserRole.ADMIN.value,  # First user in org is admin
        provider,
        provider_user_id
    )

    logger.info(f"Created new user {email} and organization {company_name}")

    return {
        "id": str(user_id),
        "email": email.lower(),
        "organization_id": str(org_id),
        "role": UserRole.ADMIN.value,
        "full_name": full_name
    }


async def handle_oauth_callback(
    provider: str,
    user_info: Dict[str, Any],
    conn: asyncpg.Connection
) -> AuthToken:
    """
    Handle OAuth callback and generate JWT tokens.

    Args:
        provider: OAuth provider name (google, microsoft)
        user_info: User information from OAuth provider
        conn: Database connection

    Returns:
        AuthToken with access and refresh tokens
    """
    # Extract user data from provider-specific format
    if provider == 'google':
        email = user_info.get('email')
        full_name = user_info.get('name', email)
        provider_user_id = user_info.get('sub')
    elif provider == 'microsoft':
        email = user_info.get('email') or user_info.get('userPrincipalName')
        full_name = user_info.get('name', email)
        provider_user_id = user_info.get('sub') or user_info.get('id')
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}"
        )

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not provided by OAuth provider"
        )

    # Find or create user
    user = await find_or_create_oauth_user(
        email=email,
        full_name=full_name,
        provider=provider,
        provider_user_id=provider_user_id,
        conn=conn
    )

    # Generate session ID
    session_id = secrets.token_urlsafe(32)

    # Create token payload
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "org_id": user["organization_id"],
        "role": user["role"],
        "session_id": session_id
    }

    # Generate tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Store session in database
    await conn.execute(
        """
        INSERT INTO user_sessions (id, user_id, created_at, expires_at, active)
        VALUES ($1, $2, NOW(), NOW() + INTERVAL '30 days', TRUE)
        """,
        session_id,
        user["id"]
    )

    # Log login
    import json
    await conn.execute(
        """
        INSERT INTO audit_log (table_name, operation, record_id, changed_by, changed_data)
        VALUES ('users', 'oauth_login', $1, $1, $2::jsonb)
        """,
        user["id"],
        json.dumps({
            "email": user["email"],
            "provider": provider,
            "timestamp": datetime.utcnow().isoformat()
        })
    )

    logger.info(f"OAuth login successful for {email} via {provider}")

    return AuthToken(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
