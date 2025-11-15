"""
User Management API

RESTful API endpoints for user authentication, registration, and management.
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, Header, Query, Body
from pydantic import BaseModel, EmailStr, Field, validator
import asyncpg

from services.user_service import UserService, UserRole, UserStatus
from services.auth_service import AuthService
from services.organization_service import OrganizationService, OrganizationType, OrganizationStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["users"])


# ============================================================================
# Pydantic Models
# ============================================================================

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    organization_name: Optional[str] = Field(None, max_length=255)
    organization_type: Optional[OrganizationType] = OrganizationType.SMB
    phone: Optional[str] = Field(None, max_length=20)

    @validator('password')
    def password_strength(cls, v):
        """Validate password strength"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class LoginRequest(BaseModel):
    """User login request"""
    email: EmailStr
    password: str


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    """Change password request"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @validator('new_password')
    def password_strength(cls, v):
        """Validate password strength"""
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class UpdateUserRequest(BaseModel):
    """Update user request"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)
    job_title: Optional[str] = Field(None, max_length=100)


class CreateUserRequest(BaseModel):
    """Create user request (admin)"""
    organization_id: str
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=1, max_length=255)
    role: UserRole = UserRole.VIEWER
    phone: Optional[str] = Field(None, max_length=20)
    job_title: Optional[str] = Field(None, max_length=100)


class UpdateUserAdminRequest(BaseModel):
    """Update user request (admin)"""
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    role: Optional[UserRole] = None
    status: Optional[UserStatus] = None
    phone: Optional[str] = Field(None, max_length=20)
    job_title: Optional[str] = Field(None, max_length=100)


class CreateOrganizationRequest(BaseModel):
    """Create organization request"""
    name: str = Field(..., min_length=1, max_length=255)
    organization_type: OrganizationType = OrganizationType.SMB
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None


class UpdateOrganizationRequest(BaseModel):
    """Update organization request"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    organization_type: Optional[OrganizationType] = None
    status: Optional[OrganizationStatus] = None
    address: Optional[str] = Field(None, max_length=500)
    phone: Optional[str] = Field(None, max_length=20)
    email: Optional[EmailStr] = None


class TokenResponse(BaseModel):
    """Token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 3600


class UserResponse(BaseModel):
    """User response"""
    id: str
    organization_id: str
    email: str
    full_name: str
    role: str
    status: str
    phone: Optional[str]
    job_title: Optional[str]
    email_verified: bool
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class OrganizationResponse(BaseModel):
    """Organization response"""
    id: str
    name: str
    organization_type: str
    status: str
    address: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Dependencies
# ============================================================================

async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    # This should be injected from main app
    # For now, placeholder - will be set up in main.py
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database connection not configured"
    )


async def get_user_service(db_pool: asyncpg.Pool = Depends(get_db_pool)) -> UserService:
    """Get user service"""
    return UserService(db_pool)


async def get_auth_service() -> AuthService:
    """Get auth service"""
    # Load secret key from configuration
    from config import settings
    return AuthService(settings.jwt_secret_key)


async def get_organization_service(db_pool: asyncpg.Pool = Depends(get_db_pool)) -> OrganizationService:
    """Get organization service"""
    return OrganizationService(db_pool)


async def get_current_user(
    authorization: str = Header(...),
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """Get current authenticated user"""
    # Extract token from Authorization header
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header"
        )

    token = authorization[7:]  # Remove "Bearer " prefix

    # Verify token
    payload = auth_service.verify_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    # Get user
    user_id = payload.get('sub')
    user = await user_service.get_user(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    if user['status'] != UserStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active"
        )

    return user


async def require_role(
    required_role: UserRole,
    current_user: dict = Depends(get_current_user)
):
    """Require user to have specific role or higher"""
    user_role = UserRole(current_user['role'])

    # Role hierarchy: Admin > Assessor > Auditor > Viewer
    role_hierarchy = {
        UserRole.ADMIN: 4,
        UserRole.ASSESSOR: 3,
        UserRole.AUDITOR: 2,
        UserRole.VIEWER: 1
    }

    if role_hierarchy[user_role] < role_hierarchy[required_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {required_role.value} role or higher"
        )

    return current_user


async def require_admin(current_user: dict = Depends(get_current_user)):
    """Require admin role"""
    if current_user['role'] != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires Admin role"
        )
    return current_user


# ============================================================================
# Authentication Endpoints
# ============================================================================

@router.post("/auth/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service),
    org_service: OrganizationService = Depends(get_organization_service)
):
    """
    Register new user and organization

    Creates a new organization (if organization_name provided) and user account.
    First user is automatically assigned Admin role.

    Returns JWT access and refresh tokens.
    """
    try:
        # Create organization if name provided
        organization_id = None
        if request.organization_name:
            organization_id = await org_service.create_organization(
                name=request.organization_name,
                organization_type=request.organization_type,
                phone=request.phone,
                email=request.email,
                created_by="registration"
            )

            # First user in organization is Admin
            role = UserRole.ADMIN
        else:
            # If no organization, user must be added to existing org by admin
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization name is required for registration"
            )

        # Create user
        user_id = await user_service.create_user(
            organization_id=organization_id,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=role,
            phone=request.phone,
            created_by="registration"
        )

        # Generate tokens
        tokens = auth_service.create_token_pair(
            user_id=user_id,
            organization_id=organization_id,
            email=request.email,
            role=role.value
        )

        logger.info(f"User registered: {request.email}")

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/auth/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    user_service: UserService = Depends(get_user_service),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    User login

    Authenticates user with email and password.
    Returns JWT access and refresh tokens.
    """
    try:
        # Authenticate user
        user = await user_service.authenticate_user(
            email=request.email,
            password=request.password
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        # Check user status
        if user['status'] != UserStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Account is {user['status'].lower()}"
            )

        # Generate tokens
        tokens = auth_service.create_token_pair(
            user_id=user['id'],
            organization_id=user['organization_id'],
            email=user['email'],
            role=user['role']
        )

        logger.info(f"User logged in: {request.email}")

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(get_auth_service),
    user_service: UserService = Depends(get_user_service)
):
    """
    Refresh access token

    Uses refresh token to generate new access token.
    """
    try:
        # Verify refresh token
        payload = auth_service.verify_refresh_token(request.refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )

        # Get user to verify still active
        user_id = payload.get('sub')
        user = await user_service.get_user(user_id)

        if not user or user['status'] != UserStatus.ACTIVE.value:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is not active"
            )

        # Generate new token pair
        tokens = auth_service.create_token_pair(
            user_id=user['id'],
            organization_id=user['organization_id'],
            email=user['email'],
            role=user['role']
        )

        return TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.get("/auth/me", response_model=UserResponse)
async def get_current_user_auth(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user (auth endpoint for frontend compatibility)

    This endpoint provides the same functionality as /users/me but matches
    the frontend's expected auth endpoint pattern.
    """
    return UserResponse(**current_user)


@router.post("/auth/logout")
async def logout():
    """
    Logout (JWT stateless)

    Since JWT tokens are stateless, logout is handled client-side by
    discarding the tokens. This endpoint confirms successful logout intent.

    For enhanced security in production, consider:
    - Token blacklisting with Redis
    - Short-lived access tokens
    - Refresh token rotation
    """
    return {
        "success": True,
        "message": "Logged out successfully. Please discard your tokens."
    }


# ============================================================================
# User Profile Endpoints
# ============================================================================

@router.get("/users/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Get current user profile

    Returns the authenticated user's profile information.
    """
    return UserResponse(**current_user)


@router.put("/users/me", response_model=UserResponse)
async def update_current_user_profile(
    request: UpdateUserRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update current user profile

    Allows user to update their own profile information.
    """
    try:
        success = await user_service.update_user(
            user_id=current_user['id'],
            full_name=request.full_name,
            phone=request.phone,
            job_title=request.job_title,
            updated_by=current_user['id']
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get updated user
        updated_user = await user_service.get_user(current_user['id'])

        logger.info(f"User profile updated: {current_user['email']}")

        return UserResponse(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Profile update error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Profile update failed"
        )


@router.put("/users/me/password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Change password

    Allows user to change their own password.
    """
    try:
        success = await user_service.change_password(
            user_id=current_user['id'],
            current_password=request.current_password,
            new_password=request.new_password
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        logger.info(f"Password changed: {current_user['email']}")

        return {"message": "Password changed successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Password change error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )


@router.get("/users/me/permissions")
async def get_current_user_permissions(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get current user permissions

    Returns the authenticated user's role-based permissions.
    """
    try:
        permissions = await user_service.get_user_permissions(current_user['id'])
        return permissions

    except Exception as e:
        logger.error(f"Get permissions error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get permissions"
        )


# ============================================================================
# User Management Endpoints (Admin)
# ============================================================================

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    organization_id: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    status: Optional[UserStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    List users (Admin only)

    Returns paginated list of users with optional filtering.
    """
    try:
        # If not super admin, filter to current organization
        if organization_id is None:
            organization_id = current_user['organization_id']

        users = await user_service.list_users(
            organization_id=organization_id,
            role=role,
            status=status,
            limit=limit,
            offset=offset
        )

        return [UserResponse(**user) for user in users]

    except Exception as e:
        logger.error(f"List users error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list users"
        )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    request: CreateUserRequest,
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    Create user (Admin only)

    Creates a new user in the specified organization.
    """
    try:
        # Verify admin is creating user in their own organization
        if request.organization_id != current_user['organization_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create users in other organizations"
            )

        user_id = await user_service.create_user(
            organization_id=request.organization_id,
            email=request.email,
            password=request.password,
            full_name=request.full_name,
            role=request.role,
            phone=request.phone,
            job_title=request.job_title,
            created_by=current_user['id']
        )

        # Get created user
        user = await user_service.get_user(user_id)

        logger.info(f"User created by admin: {request.email}")

        return UserResponse(**user)

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Create user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user"
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    Get user by ID (Admin only)

    Returns detailed user information.
    """
    try:
        user = await user_service.get_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify user is in same organization
        if user['organization_id'] != current_user['organization_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access users from other organizations"
            )

        return UserResponse(**user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user"
        )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UpdateUserAdminRequest,
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    Update user (Admin only)

    Allows admin to update user profile, role, and status.
    """
    try:
        # Get user to verify organization
        user = await user_service.get_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify user is in same organization
        if user['organization_id'] != current_user['organization_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update users from other organizations"
            )

        # Update user
        success = await user_service.update_user(
            user_id=user_id,
            full_name=request.full_name,
            role=request.role,
            status=request.status,
            phone=request.phone,
            job_title=request.job_title,
            updated_by=current_user['id']
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get updated user
        updated_user = await user_service.get_user(user_id)

        logger.info(f"User updated by admin: {user['email']}")

        return UserResponse(**updated_user)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: dict = Depends(require_admin),
    user_service: UserService = Depends(get_user_service)
):
    """
    Delete user (Admin only)

    Soft deletes user by setting status to Inactive.
    """
    try:
        # Get user to verify organization
        user = await user_service.get_user(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify user is in same organization
        if user['organization_id'] != current_user['organization_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete users from other organizations"
            )

        # Prevent self-deletion
        if user_id == current_user['id']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )

        # Delete user
        success = await user_service.delete_user(
            user_id=user_id,
            deleted_by=current_user['id']
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        logger.info(f"User deleted by admin: {user['email']}")

        return {"message": "User deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete user error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user"
        )


# ============================================================================
# Organization Management Endpoints (Admin)
# ============================================================================

@router.get("/organizations", response_model=List[OrganizationResponse])
async def list_organizations(
    organization_type: Optional[OrganizationType] = Query(None),
    status: Optional[OrganizationStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(require_admin),
    org_service: OrganizationService = Depends(get_organization_service)
):
    """
    List organizations (Admin only)

    Returns paginated list of organizations with optional filtering.
    Note: Returns only current user's organization unless super admin.
    """
    try:
        organizations = await org_service.list_organizations(
            organization_type=organization_type,
            status=status,
            limit=limit,
            offset=offset
        )

        # Filter to current organization (unless super admin in future)
        organizations = [
            org for org in organizations
            if org['id'] == current_user['organization_id']
        ]

        return [OrganizationResponse(**org) for org in organizations]

    except Exception as e:
        logger.error(f"List organizations error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list organizations"
        )


@router.get("/organizations/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: str,
    current_user: dict = Depends(require_admin),
    org_service: OrganizationService = Depends(get_organization_service)
):
    """
    Get organization by ID (Admin only)

    Returns detailed organization information.
    """
    try:
        # Verify accessing own organization
        if org_id != current_user['organization_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other organizations"
            )

        org = await org_service.get_organization(org_id)

        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        return OrganizationResponse(**org)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get organization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get organization"
        )


@router.put("/organizations/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: str,
    request: UpdateOrganizationRequest,
    current_user: dict = Depends(require_admin),
    org_service: OrganizationService = Depends(get_organization_service)
):
    """
    Update organization (Admin only)

    Allows admin to update organization information.
    """
    try:
        # Verify updating own organization
        if org_id != current_user['organization_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update other organizations"
            )

        success = await org_service.update_organization(
            org_id=org_id,
            name=request.name,
            organization_type=request.organization_type,
            status=request.status,
            address=request.address,
            phone=request.phone,
            email=request.email,
            updated_by=current_user['id']
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Get updated organization
        updated_org = await org_service.get_organization(org_id)

        logger.info(f"Organization updated by admin: {org_id}")

        return OrganizationResponse(**updated_org)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update organization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update organization"
        )


@router.get("/organizations/{org_id}/stats")
async def get_organization_stats(
    org_id: str,
    current_user: dict = Depends(require_admin),
    org_service: OrganizationService = Depends(get_organization_service)
):
    """
    Get organization statistics (Admin only)

    Returns user count, assessment count, and evidence metrics.
    """
    try:
        # Verify accessing own organization
        if org_id != current_user['organization_id']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other organizations"
            )

        stats = await org_service.get_organization_stats(org_id)

        return stats

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get organization stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get organization stats"
        )
