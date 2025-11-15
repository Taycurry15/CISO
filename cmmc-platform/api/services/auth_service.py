"""
Authentication Service

Handles JWT token generation, validation, and refresh.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import jwt
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TokenPair:
    """Access and refresh token pair"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = 3600  # 1 hour


class AuthService:
    """
    Authentication Service

    Handles JWT token generation and validation
    """

    def __init__(
        self,
        secret_key: str,
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 30
    ):
        """
        Initialize auth service

        Args:
            secret_key: Secret key for JWT signing
            algorithm: JWT algorithm (default HS256)
            access_token_expire_minutes: Access token expiration (default 60 min)
            refresh_token_expire_days: Refresh token expiration (default 30 days)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        user_id: str,
        organization_id: str,
        email: str,
        role: str,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create JWT access token

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            email: User email
            role: User role
            additional_claims: Optional additional claims

        Returns:
            str: JWT access token
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            'sub': user_id,  # Subject (user ID)
            'org_id': organization_id,
            'email': email,
            'role': role,
            'type': 'access',
            'iat': now,  # Issued at
            'exp': expires_at  # Expiration
        }

        # Add additional claims if provided
        if additional_claims:
            payload.update(additional_claims)

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Access token created for user {user_id}")

        return token

    def create_refresh_token(
        self,
        user_id: str,
        organization_id: str
    ) -> str:
        """
        Create JWT refresh token

        Args:
            user_id: User UUID
            organization_id: Organization UUID

        Returns:
            str: JWT refresh token
        """
        now = datetime.utcnow()
        expires_at = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            'sub': user_id,
            'org_id': organization_id,
            'type': 'refresh',
            'iat': now,
            'exp': expires_at
        }

        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

        logger.debug(f"Refresh token created for user {user_id}")

        return token

    def create_token_pair(
        self,
        user_id: str,
        organization_id: str,
        email: str,
        role: str
    ) -> TokenPair:
        """
        Create access and refresh token pair

        Args:
            user_id: User UUID
            organization_id: Organization UUID
            email: User email
            role: User role

        Returns:
            TokenPair with access and refresh tokens
        """
        access_token = self.create_access_token(
            user_id=user_id,
            organization_id=organization_id,
            email=email,
            role=role
        )

        refresh_token = self.create_refresh_token(
            user_id=user_id,
            organization_id=organization_id
        )

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.access_token_expire_minutes * 60  # Convert to seconds
        )

    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            logger.debug(f"Token verified for user {payload.get('sub')}")

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token verification failed: token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Token verification failed: {e}")
            return None

    def verify_access_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify access token specifically

        Args:
            token: JWT access token

        Returns:
            Decoded payload or None if invalid
        """
        payload = self.verify_token(token)

        if not payload:
            return None

        # Verify it's an access token
        if payload.get('type') != 'access':
            logger.warning("Token verification failed: not an access token")
            return None

        return payload

    def verify_refresh_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify refresh token specifically

        Args:
            token: JWT refresh token

        Returns:
            Decoded payload or None if invalid
        """
        payload = self.verify_token(token)

        if not payload:
            return None

        # Verify it's a refresh token
        if payload.get('type') != 'refresh':
            logger.warning("Token verification failed: not a refresh token")
            return None

        return payload

    def refresh_access_token(
        self,
        refresh_token: str,
        email: str,
        role: str
    ) -> Optional[str]:
        """
        Generate new access token from refresh token

        Args:
            refresh_token: Valid refresh token
            email: User email (from database)
            role: User role (from database)

        Returns:
            New access token or None if refresh token invalid
        """
        payload = self.verify_refresh_token(refresh_token)

        if not payload:
            return None

        # Create new access token
        access_token = self.create_access_token(
            user_id=payload['sub'],
            organization_id=payload['org_id'],
            email=email,
            role=role
        )

        logger.info(f"Access token refreshed for user {payload['sub']}")

        return access_token

    def extract_token_from_header(self, authorization: str) -> Optional[str]:
        """
        Extract JWT token from Authorization header

        Args:
            authorization: Authorization header value (e.g., "Bearer <token>")

        Returns:
            Token string or None if invalid format
        """
        if not authorization:
            return None

        parts = authorization.split()

        if len(parts) != 2 or parts[0].lower() != 'bearer':
            logger.warning("Invalid authorization header format")
            return None

        return parts[1]

    def get_current_user_id(self, token: str) -> Optional[str]:
        """
        Get user ID from token

        Args:
            token: JWT access token

        Returns:
            User ID or None if invalid
        """
        payload = self.verify_access_token(token)

        if not payload:
            return None

        return payload.get('sub')

    def get_current_organization_id(self, token: str) -> Optional[str]:
        """
        Get organization ID from token

        Args:
            token: JWT access token

        Returns:
            Organization ID or None if invalid
        """
        payload = self.verify_access_token(token)

        if not payload:
            return None

        return payload.get('org_id')

    def has_permission(
        self,
        token: str,
        required_permission: str
    ) -> bool:
        """
        Check if user has required permission

        Args:
            token: JWT access token
            required_permission: Permission string (e.g., "assessment:create")

        Returns:
            bool: True if user has permission
        """
        payload = self.verify_access_token(token)

        if not payload:
            return False

        role = payload.get('role')

        # Permission mappings (same as in user_service)
        permissions = {
            'Admin': [
                'user:create', 'user:read', 'user:update', 'user:delete',
                'organization:create', 'organization:read', 'organization:update', 'organization:delete',
                'assessment:create', 'assessment:read', 'assessment:update', 'assessment:delete',
                'evidence:create', 'evidence:read', 'evidence:update', 'evidence:delete',
                'report:generate', 'dashboard:view'
            ],
            'Assessor': [
                'user:read',
                'organization:read',
                'assessment:create', 'assessment:read', 'assessment:update',
                'evidence:create', 'evidence:read', 'evidence:update', 'evidence:delete',
                'report:generate', 'dashboard:view'
            ],
            'Auditor': [
                'user:read',
                'organization:read',
                'assessment:read',
                'evidence:read',
                'report:generate', 'dashboard:view'
            ],
            'Viewer': [
                'organization:read',
                'assessment:read',
                'evidence:read',
                'dashboard:view'
            ]
        }

        user_permissions = permissions.get(role, [])

        return required_permission in user_permissions
