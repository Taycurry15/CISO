"""
Authentication & Authorization Middleware

Provides RBAC middleware for protecting API routes with role and permission checks.
"""

import logging
from typing import Optional, List, Callable
from functools import wraps

from fastapi import Header, HTTPException, status, Depends
import asyncpg

from services.user_service import UserService, UserRole, UserStatus
from services.auth_service import AuthService

logger = logging.getLogger(__name__)


# ============================================================================
# Auth Context
# ============================================================================

class AuthContext:
    """
    Authentication context for current request

    Contains authenticated user information and helper methods for
    permission checking.
    """

    def __init__(self, user: dict, token_payload: dict):
        self.user = user
        self.token_payload = token_payload

        # Quick access properties
        self.user_id = user['id']
        self.organization_id = user['organization_id']
        self.email = user['email']
        self.role = UserRole(user['role'])
        self.status = UserStatus(user['status'])

    def has_role(self, *roles: UserRole) -> bool:
        """Check if user has any of the specified roles"""
        return self.role in roles

    def has_permission(self, permission: str) -> bool:
        """
        Check if user has specific permission

        Permission format: "resource:action"
        Examples: "assessment:create", "evidence:delete"
        """
        # Admin has all permissions
        if self.role == UserRole.ADMIN:
            return True

        # Parse permission
        if ':' not in permission:
            return False

        resource, action = permission.split(':', 1)

        # Role-based permissions
        role_permissions = {
            UserRole.ASSESSOR: {
                'assessment': ['read', 'create', 'update'],
                'evidence': ['read', 'create', 'update', 'delete'],
                'control': ['read', 'update'],
                'report': ['read', 'create'],
                'user': ['read'],
                'organization': ['read']
            },
            UserRole.AUDITOR: {
                'assessment': ['read'],
                'evidence': ['read'],
                'control': ['read'],
                'report': ['read', 'create'],
                'user': ['read'],
                'organization': ['read']
            },
            UserRole.VIEWER: {
                'assessment': ['read'],
                'evidence': ['read'],
                'control': ['read'],
                'report': ['read'],
                'user': ['read'],
                'organization': ['read']
            }
        }

        permissions = role_permissions.get(self.role, {})
        allowed_actions = permissions.get(resource, [])

        return action in allowed_actions

    def require_permission(self, permission: str):
        """Raise exception if user lacks permission"""
        if not self.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}"
            )

    def is_same_organization(self, org_id: str) -> bool:
        """Check if resource belongs to user's organization"""
        return self.organization_id == org_id

    def require_same_organization(self, org_id: str):
        """Raise exception if resource is from different organization"""
        if not self.is_same_organization(org_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access resources from other organizations"
            )


# ============================================================================
# Dependencies
# ============================================================================

async def get_db_pool() -> asyncpg.Pool:
    """
    Get database connection pool

    This should be injected from main app.
    Override this dependency in main.py with actual pool.
    """
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database connection not configured"
    )


async def get_auth_service() -> AuthService:
    """
    Get auth service

    Override this dependency in main.py with proper configuration.
    """
    # Secret key should come from environment
    import os
    secret_key = os.getenv('JWT_SECRET_KEY', 'your-secret-key-here')
    return AuthService(secret_key)


async def get_user_service(db_pool: asyncpg.Pool = Depends(get_db_pool)) -> UserService:
    """Get user service"""
    return UserService(db_pool)


async def get_auth_context(
    authorization: str = Header(...),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
) -> AuthContext:
    """
    Get authentication context for current request

    Verifies JWT token and returns authenticated user context.
    Raises 401 if token is invalid or user is not active.
    """
    # Extract token from Authorization header
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected 'Bearer <token>'"
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    # Verify token
    payload = auth_service.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    # Get user from database
    user_id = payload.get('sub')
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    user = await user_service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # Check user status
    if user['status'] != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"User account is {user['status'].lower()}"
        )

    # Return auth context
    return AuthContext(user, payload)


async def get_optional_auth_context(
    authorization: Optional[str] = Header(None),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
) -> Optional[AuthContext]:
    """
    Get optional authentication context

    Returns None if no authorization header provided.
    Useful for endpoints that have different behavior for authenticated users.
    """
    if not authorization:
        return None

    try:
        return await get_auth_context(
            authorization=authorization,
            auth_service=auth_service,
            user_service=user_service
        )
    except HTTPException:
        return None


# ============================================================================
# Role-Based Access Control
# ============================================================================

def require_role(*allowed_roles: UserRole):
    """
    Dependency factory for requiring specific role(s)

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(
            auth: AuthContext = Depends(require_role(UserRole.ADMIN))
        ):
            ...

    Args:
        allowed_roles: One or more UserRole values that are allowed

    Returns:
        Dependency function that returns AuthContext
    """
    async def check_role(
        auth_context: AuthContext = Depends(get_auth_context)
    ) -> AuthContext:
        """Check if user has required role"""
        if not auth_context.has_role(*allowed_roles):
            role_names = ", ".join(r.value for r in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these roles: {role_names}"
            )
        return auth_context

    return check_role


def require_permission(*permissions: str):
    """
    Dependency factory for requiring specific permission(s)

    Usage:
        @router.post("/assessments")
        async def create_assessment(
            auth: AuthContext = Depends(require_permission("assessment:create"))
        ):
            ...

    Args:
        permissions: One or more permission strings (format: "resource:action")

    Returns:
        Dependency function that returns AuthContext
    """
    async def check_permission(
        auth_context: AuthContext = Depends(get_auth_context)
    ) -> AuthContext:
        """Check if user has required permission"""
        # User needs at least one of the specified permissions
        has_any = any(auth_context.has_permission(p) for p in permissions)

        if not has_any:
            perms_str = ", ".join(permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of these permissions: {perms_str}"
            )

        return auth_context

    return check_permission


# ============================================================================
# Convenience Dependencies
# ============================================================================

# Require admin role
require_admin = require_role(UserRole.ADMIN)

# Require assessor or admin role
require_assessor = require_role(UserRole.ASSESSOR, UserRole.ADMIN)

# Require auditor, assessor, or admin role
require_auditor = require_role(UserRole.AUDITOR, UserRole.ASSESSOR, UserRole.ADMIN)

# Any authenticated user
require_auth = Depends(get_auth_context)


# ============================================================================
# Organization Isolation
# ============================================================================

class OrganizationIsolation:
    """
    Middleware for multi-tenant organization isolation

    Ensures users can only access resources from their own organization.
    """

    def __init__(self, allow_cross_org_admin: bool = False):
        """
        Initialize organization isolation middleware

        Args:
            allow_cross_org_admin: If True, admins can access other organizations
        """
        self.allow_cross_org_admin = allow_cross_org_admin

    async def __call__(
        self,
        resource_org_id: str,
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        Verify resource belongs to user's organization

        Args:
            resource_org_id: Organization ID of the resource being accessed
            auth_context: Current authentication context

        Raises:
            HTTPException: If user tries to access resource from different org
        """
        # Admin can access cross-org if configured
        if self.allow_cross_org_admin and auth_context.role == UserRole.ADMIN:
            return

        # Verify same organization
        if resource_org_id != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access resources from other organizations"
            )


# ============================================================================
# Rate Limiting (Placeholder)
# ============================================================================

class RateLimiter:
    """
    Rate limiting middleware (placeholder)

    In production, implement with Redis for distributed rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000
    ):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour

    async def __call__(
        self,
        auth_context: AuthContext = Depends(get_auth_context)
    ):
        """
        Check rate limits for user

        TODO: Implement with Redis
        """
        # Placeholder - implement with Redis in production
        pass


# ============================================================================
# API Key Authentication (Future)
# ============================================================================

async def verify_api_key(
    x_api_key: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    Verify API key authentication

    For programmatic access to the API.
    TODO: Implement API key management system.
    """
    if not x_api_key:
        return None

    # TODO: Implement API key verification
    # - Look up API key in database
    # - Verify not expired
    # - Return associated organization/permissions

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="API key authentication not yet implemented"
    )


# ============================================================================
# Audit Logging
# ============================================================================

class AuditLogger:
    """
    Audit logging middleware

    Logs all authenticated requests for security auditing.
    """

    def __init__(self, log_body: bool = False):
        """
        Initialize audit logger

        Args:
            log_body: If True, log request/response bodies (may contain sensitive data)
        """
        self.log_body = log_body

    async def log_request(
        self,
        auth_context: AuthContext,
        method: str,
        path: str,
        ip_address: str,
        body: Optional[dict] = None
    ):
        """
        Log authenticated request

        Args:
            auth_context: Current authentication context
            method: HTTP method
            path: Request path
            ip_address: Client IP address
            body: Optional request body
        """
        log_entry = {
            'user_id': auth_context.user_id,
            'organization_id': auth_context.organization_id,
            'email': auth_context.email,
            'role': auth_context.role.value,
            'method': method,
            'path': path,
            'ip_address': ip_address,
            'timestamp': 'utcnow'  # TODO: Add actual timestamp
        }

        if self.log_body and body:
            log_entry['body'] = body

        # TODO: Store in audit log table
        logger.info(f"API Request: {log_entry}")


# ============================================================================
# Helper Functions
# ============================================================================

def get_role_hierarchy_level(role: UserRole) -> int:
    """
    Get numeric level for role hierarchy

    Higher number = more permissions
    """
    hierarchy = {
        UserRole.VIEWER: 1,
        UserRole.AUDITOR: 2,
        UserRole.ASSESSOR: 3,
        UserRole.ADMIN: 4
    }
    return hierarchy.get(role, 0)


def role_has_higher_privilege(role1: UserRole, role2: UserRole) -> bool:
    """Check if role1 has higher or equal privilege than role2"""
    return get_role_hierarchy_level(role1) >= get_role_hierarchy_level(role2)
