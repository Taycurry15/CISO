"""
JWT Authentication System
=========================
Provides secure JWT-based authentication for the CMMC platform.

Features:
- JWT token generation and validation
- Password hashing with bcrypt
- Role-based access control (RBAC)
- Multi-tenant organization isolation
- API key management for integrations
- Session management
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import secrets
import asyncpg
import logging
from pydantic import BaseModel
from enum import Enum

logger = logging.getLogger(__name__)

# Security configuration
SECRET_KEY = secrets.token_urlsafe(32)  # In production, load from environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security scheme
security = HTTPBearer()


class UserRole(str, Enum):
    """User roles for RBAC."""
    ADMIN = "admin"
    ASSESSOR = "assessor"
    VIEWER = "viewer"
    INTEGRATION = "integration"


class TokenType(str, Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"


class AuthToken(BaseModel):
    """Authentication token response."""
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data."""
    user_id: str
    organization_id: str
    email: str
    role: UserRole
    token_type: TokenType


class LoginRequest(BaseModel):
    """Login request."""
    email: str
    password: str


class CreateUserRequest(BaseModel):
    """Create user request."""
    email: str
    password: str
    full_name: str
    organization_id: str
    role: UserRole = UserRole.VIEWER


class APIKeyRequest(BaseModel):
    """API key creation request."""
    name: str
    description: Optional[str] = None
    expires_days: Optional[int] = 365


# =============================================================================
# PASSWORD HASHING
# =============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to verify against

    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT TOKEN OPERATIONS
# =============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        data: Token payload data
        expires_delta: Token expiration time delta

    Returns:
        JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": TokenType.ACCESS.value
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    Create a JWT refresh token.

    Args:
        data: Token payload data

    Returns:
        JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": TokenType.REFRESH.value
    })

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> TokenData:
    """
    Decode and validate JWT token.

    Args:
        token: JWT token string

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        user_id: str = payload.get("sub")
        organization_id: str = payload.get("org_id")
        email: str = payload.get("email")
        role: str = payload.get("role")
        token_type: str = payload.get("type")

        if user_id is None or email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return TokenData(
            user_id=user_id,
            organization_id=organization_id,
            email=email,
            role=UserRole(role),
            token_type=TokenType(token_type)
        )

    except JWTError as e:
        logger.error(f"JWT decode error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# AUTHENTICATION DEPENDENCIES
# =============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    conn: asyncpg.Connection = None
) -> TokenData:
    """
    Get current authenticated user from JWT token.

    Args:
        credentials: HTTP bearer credentials
        conn: Database connection (optional)

    Returns:
        TokenData with user information

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    token_data = decode_token(token)

    # Verify token type is access token
    if token_data.token_type != TokenType.ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Optional: Verify user still exists and is active
    if conn:
        user = await conn.fetchrow(
            "SELECT id, active FROM users WHERE id = $1",
            token_data.user_id
        )

        if not user or not user['active']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User inactive or not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return token_data


async def get_current_admin_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Require admin role for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        TokenData if user is admin

    Raises:
        HTTPException: If user is not admin
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )

    return current_user


async def get_current_assessor_user(
    current_user: TokenData = Depends(get_current_user)
) -> TokenData:
    """
    Require assessor or admin role for the current user.

    Args:
        current_user: Current authenticated user

    Returns:
        TokenData if user is assessor or admin

    Raises:
        HTTPException: If user does not have required privileges
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ASSESSOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assessor privileges required"
        )

    return current_user


# =============================================================================
# USER MANAGEMENT
# =============================================================================

async def authenticate_user(
    email: str,
    password: str,
    conn: asyncpg.Connection
) -> Optional[Dict[str, Any]]:
    """
    Authenticate user with email and password.

    Args:
        email: User email
        password: User password
        conn: Database connection

    Returns:
        User data if authentication successful, None otherwise
    """
    user = await conn.fetchrow(
        """
        SELECT id, email, password_hash, organization_id, role, full_name, active
        FROM users
        WHERE email = $1
        """,
        email.lower()
    )

    if not user:
        logger.warning(f"Authentication failed: user not found - {email}")
        return None

    if not user['active']:
        logger.warning(f"Authentication failed: user inactive - {email}")
        return None

    if not verify_password(password, user['password_hash']):
        logger.warning(f"Authentication failed: invalid password - {email}")
        return None

    logger.info(f"User authenticated: {email}")

    return {
        "id": str(user['id']),
        "email": user['email'],
        "organization_id": str(user['organization_id']),
        "role": user['role'],
        "full_name": user['full_name']
    }


async def create_user(
    request: CreateUserRequest,
    conn: asyncpg.Connection
) -> str:
    """
    Create a new user.

    Args:
        request: User creation request
        conn: Database connection

    Returns:
        User UUID

    Raises:
        HTTPException: If user already exists
    """
    # Check if user already exists
    existing = await conn.fetchval(
        "SELECT id FROM users WHERE email = $1",
        request.email.lower()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )

    # Hash password
    password_hash = hash_password(request.password)

    # Create user
    user_id = await conn.fetchval(
        """
        INSERT INTO users
        (email, password_hash, full_name, organization_id, role, active)
        VALUES ($1, $2, $3, $4, $5, TRUE)
        RETURNING id
        """,
        request.email.lower(),
        password_hash,
        request.full_name,
        request.organization_id,
        request.role.value
    )

    logger.info(f"User created: {request.email}")

    return str(user_id)


async def login(
    request: LoginRequest,
    conn: asyncpg.Connection
) -> AuthToken:
    """
    Login user and generate tokens.

    Args:
        request: Login request
        conn: Database connection

    Returns:
        AuthToken with access and refresh tokens

    Raises:
        HTTPException: If authentication fails
    """
    user = await authenticate_user(request.email, request.password, conn)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token payload
    token_data = {
        "sub": user["id"],
        "email": user["email"],
        "org_id": user["organization_id"],
        "role": user["role"]
    }

    # Generate tokens
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    # Log login
    await conn.execute(
        """
        INSERT INTO audit_log (table_name, operation, record_id, changed_by, changed_data)
        VALUES ('users', 'login', $1, $1, $2)
        """,
        user["id"],
        {"email": user["email"], "timestamp": datetime.utcnow().isoformat()}
    )

    return AuthToken(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


# =============================================================================
# API KEY MANAGEMENT
# =============================================================================

async def create_api_key(
    request: APIKeyRequest,
    user_id: str,
    organization_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Create an API key for integration use.

    Args:
        request: API key creation request
        user_id: User creating the key
        organization_id: Organization ID
        conn: Database connection

    Returns:
        API key details
    """
    # Generate API key
    api_key = f"cmmc_{secrets.token_urlsafe(32)}"

    # Calculate expiration
    expires_at = datetime.utcnow() + timedelta(days=request.expires_days or 365)

    # Store API key (hashed)
    key_hash = hash_password(api_key)

    key_id = await conn.fetchval(
        """
        INSERT INTO api_keys
        (name, description, key_hash, organization_id, created_by, expires_at, active)
        VALUES ($1, $2, $3, $4, $5, $6, TRUE)
        RETURNING id
        """,
        request.name,
        request.description,
        key_hash,
        organization_id,
        user_id,
        expires_at
    )

    logger.info(f"API key created: {request.name} for organization {organization_id}")

    return {
        "id": str(key_id),
        "name": request.name,
        "api_key": api_key,  # Only returned once
        "expires_at": expires_at.isoformat()
    }


async def validate_api_key(
    api_key: str,
    conn: asyncpg.Connection
) -> Optional[Dict[str, Any]]:
    """
    Validate an API key.

    Args:
        api_key: API key to validate
        conn: Database connection

    Returns:
        API key details if valid, None otherwise
    """
    # Get all active API keys
    keys = await conn.fetch(
        """
        SELECT id, name, key_hash, organization_id, expires_at
        FROM api_keys
        WHERE active = TRUE AND expires_at > NOW()
        """
    )

    for key in keys:
        if verify_password(api_key, key['key_hash']):
            # Update last used
            await conn.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE id = $1",
                key['id']
            )

            return {
                "id": str(key['id']),
                "name": key['name'],
                "organization_id": str(key['organization_id'])
            }

    return None
