"""
User Management Service

Handles user registration, authentication, and profile management.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncpg
from uuid import uuid4
import bcrypt

logger = logging.getLogger(__name__)


class UserRole(str, Enum):
    """User roles for RBAC"""
    ADMIN = "Admin"  # Full system access
    ASSESSOR = "Assessor"  # Can create/edit assessments
    AUDITOR = "Auditor"  # Read-only access to all assessments
    VIEWER = "Viewer"  # Read-only access to assigned assessments


class UserStatus(str, Enum):
    """User account status"""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    SUSPENDED = "Suspended"
    PENDING = "Pending"  # Email not verified


@dataclass
class User:
    """User entity"""
    id: str
    organization_id: str
    email: str
    full_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    email_verified: bool


class UserService:
    """
    User Management Service

    Handles user registration, authentication, and profile management
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize user service

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    async def create_user(
        self,
        organization_id: str,
        email: str,
        password: str,
        full_name: str,
        role: UserRole = UserRole.VIEWER,
        created_by: str = "system"
    ) -> str:
        """
        Create new user

        Args:
            organization_id: Organization UUID
            email: User email (must be unique)
            password: Plain text password (will be hashed)
            full_name: User's full name
            role: User role (default Viewer)
            created_by: User who created this account

        Returns:
            str: User UUID

        Raises:
            ValueError: If email already exists
        """
        logger.info(f"Creating user {email} for organization {organization_id}")

        # Validate email format
        if '@' not in email or '.' not in email:
            raise ValueError("Invalid email format")

        # Validate password strength
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters")

        user_id = str(uuid4())
        password_hash = self._hash_password(password)
        now = datetime.utcnow()

        async with self.db_pool.acquire() as conn:
            # Check if email exists
            existing = await conn.fetchval(
                "SELECT id FROM users WHERE email = $1",
                email.lower()
            )

            if existing:
                raise ValueError(f"User with email {email} already exists")

            # Create user
            await conn.execute("""
                INSERT INTO users (
                    id, organization_id, email, password_hash, full_name,
                    role, status, email_verified, created_at, updated_at, created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """,
                user_id,
                organization_id,
                email.lower(),
                password_hash,
                full_name,
                role.value,
                UserStatus.PENDING.value,  # Pending until email verified
                False,
                now,
                now,
                created_by
            )

            logger.info(f"User {user_id} created successfully")

        return user_id

    async def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate user with email and password

        Args:
            email: User email
            password: Plain text password

        Returns:
            User info dict if authenticated, None otherwise
        """
        async with self.db_pool.acquire() as conn:
            # Get user
            user = await conn.fetchrow("""
                SELECT
                    u.id, u.organization_id, u.email, u.password_hash,
                    u.full_name, u.role, u.status, u.email_verified
                FROM users u
                WHERE u.email = $1
            """, email.lower())

            if not user:
                logger.warning(f"Authentication failed: user {email} not found")
                return None

            # Verify password
            if not self._verify_password(password, user['password_hash']):
                logger.warning(f"Authentication failed: invalid password for {email}")
                return None

            # Check status
            if user['status'] != UserStatus.ACTIVE.value:
                logger.warning(f"Authentication failed: user {email} is {user['status']}")
                return None

            # Update last login
            await conn.execute("""
                UPDATE users
                SET last_login = $1, updated_at = $1
                WHERE id = $2
            """, datetime.utcnow(), user['id'])

            logger.info(f"User {email} authenticated successfully")

            return {
                'id': str(user['id']),
                'organization_id': str(user['organization_id']),
                'email': user['email'],
                'full_name': user['full_name'],
                'role': user['role'],
                'status': user['status'],
                'email_verified': user['email_verified']
            }

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user by ID

        Args:
            user_id: User UUID

        Returns:
            User info dict or None
        """
        async with self.db_pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT
                    u.id, u.organization_id, u.email, u.full_name,
                    u.role, u.status, u.email_verified,
                    u.created_at, u.updated_at, u.last_login,
                    o.name as organization_name
                FROM users u
                JOIN organizations o ON u.organization_id = o.id
                WHERE u.id = $1
            """, user_id)

            if not user:
                return None

            return dict(user)

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        async with self.db_pool.acquire() as conn:
            user = await conn.fetchrow("""
                SELECT
                    u.id, u.organization_id, u.email, u.full_name,
                    u.role, u.status, u.email_verified,
                    u.created_at, u.updated_at, u.last_login
                FROM users u
                WHERE u.email = $1
            """, email.lower())

            if not user:
                return None

            return dict(user)

    async def list_users(
        self,
        organization_id: Optional[str] = None,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List users with optional filtering

        Args:
            organization_id: Filter by organization
            role: Filter by role
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of users
        """
        query = """
            SELECT
                u.id, u.organization_id, u.email, u.full_name,
                u.role, u.status, u.email_verified,
                u.created_at, u.last_login,
                o.name as organization_name
            FROM users u
            JOIN organizations o ON u.organization_id = o.id
            WHERE 1=1
        """

        params = []
        param_count = 0

        if organization_id:
            param_count += 1
            query += f" AND u.organization_id = ${param_count}"
            params.append(organization_id)

        if role:
            param_count += 1
            query += f" AND u.role = ${param_count}"
            params.append(role.value)

        if status:
            param_count += 1
            query += f" AND u.status = ${param_count}"
            params.append(status.value)

        query += f" ORDER BY u.created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def update_user(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        role: Optional[UserRole] = None,
        status: Optional[UserStatus] = None,
        updated_by: str = "system"
    ) -> bool:
        """
        Update user profile

        Args:
            user_id: User UUID
            full_name: New full name
            role: New role
            status: New status
            updated_by: User making the update

        Returns:
            bool: Success status
        """
        updates = []
        params = []
        param_count = 0

        if full_name is not None:
            param_count += 1
            updates.append(f"full_name = ${param_count}")
            params.append(full_name)

        if role is not None:
            param_count += 1
            updates.append(f"role = ${param_count}")
            params.append(role.value)

        if status is not None:
            param_count += 1
            updates.append(f"status = ${param_count}")
            params.append(status.value)

        if not updates:
            return False

        # Add updated_at
        param_count += 1
        updates.append(f"updated_at = ${param_count}")
        params.append(datetime.utcnow())

        # Add user_id for WHERE clause
        param_count += 1
        params.append(user_id)

        query = f"""
            UPDATE users
            SET {', '.join(updates)}
            WHERE id = ${param_count}
        """

        async with self.db_pool.acquire() as conn:
            result = await conn.execute(query, *params)

            # Check if user was found and updated
            if result == "UPDATE 0":
                return False

            logger.info(f"User {user_id} updated by {updated_by}")

        return True

    async def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str
    ) -> bool:
        """
        Change user password

        Args:
            user_id: User UUID
            old_password: Current password
            new_password: New password

        Returns:
            bool: Success status

        Raises:
            ValueError: If old password is incorrect or new password is weak
        """
        # Validate new password
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters")

        async with self.db_pool.acquire() as conn:
            # Get current password hash
            user = await conn.fetchrow(
                "SELECT password_hash FROM users WHERE id = $1",
                user_id
            )

            if not user:
                return False

            # Verify old password
            if not self._verify_password(old_password, user['password_hash']):
                raise ValueError("Current password is incorrect")

            # Hash new password
            new_hash = self._hash_password(new_password)

            # Update password
            await conn.execute("""
                UPDATE users
                SET password_hash = $1, updated_at = $2
                WHERE id = $3
            """, new_hash, datetime.utcnow(), user_id)

            logger.info(f"Password changed for user {user_id}")

        return True

    async def verify_email(self, user_id: str) -> bool:
        """
        Mark user email as verified and activate account

        Args:
            user_id: User UUID

        Returns:
            bool: Success status
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE users
                SET email_verified = true,
                    status = $1,
                    updated_at = $2
                WHERE id = $3
            """, UserStatus.ACTIVE.value, datetime.utcnow(), user_id)

            if result == "UPDATE 0":
                return False

            logger.info(f"Email verified for user {user_id}")

        return True

    async def delete_user(
        self,
        user_id: str,
        deleted_by: str = "system"
    ) -> bool:
        """
        Delete user (soft delete by setting status to Inactive)

        Args:
            user_id: User UUID
            deleted_by: User performing deletion

        Returns:
            bool: Success status
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE users
                SET status = $1, updated_at = $2
                WHERE id = $3
            """, UserStatus.INACTIVE.value, datetime.utcnow(), user_id)

            if result == "UPDATE 0":
                return False

            logger.info(f"User {user_id} deleted by {deleted_by}")

        return True

    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """
        Get user permissions based on role

        Args:
            user_id: User UUID

        Returns:
            Dict with permissions
        """
        user = await self.get_user(user_id)

        if not user:
            return {'permissions': []}

        role = UserRole(user['role'])

        permissions = {
            UserRole.ADMIN: [
                'user:create', 'user:read', 'user:update', 'user:delete',
                'organization:create', 'organization:read', 'organization:update', 'organization:delete',
                'assessment:create', 'assessment:read', 'assessment:update', 'assessment:delete',
                'evidence:create', 'evidence:read', 'evidence:update', 'evidence:delete',
                'report:generate', 'dashboard:view'
            ],
            UserRole.ASSESSOR: [
                'user:read',
                'organization:read',
                'assessment:create', 'assessment:read', 'assessment:update',
                'evidence:create', 'evidence:read', 'evidence:update', 'evidence:delete',
                'report:generate', 'dashboard:view'
            ],
            UserRole.AUDITOR: [
                'user:read',
                'organization:read',
                'assessment:read',
                'evidence:read',
                'report:generate', 'dashboard:view'
            ],
            UserRole.VIEWER: [
                'organization:read',
                'assessment:read',
                'evidence:read',
                'dashboard:view'
            ]
        }

        return {
            'user_id': user_id,
            'role': role.value,
            'permissions': permissions.get(role, [])
        }
