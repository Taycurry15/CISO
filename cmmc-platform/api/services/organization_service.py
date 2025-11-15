"""
Organization Service

Handles organization (tenant) management for multi-tenant support.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncpg
from uuid import uuid4

logger = logging.getLogger(__name__)


class OrganizationType(str, Enum):
    """Organization type"""
    ENTERPRISE = "Enterprise"  # Large company
    SMB = "SMB"  # Small/medium business
    CONSULTANT = "Consultant"  # Consulting firm
    C3PAO = "C3PAO"  # Third-party assessment organization


class OrganizationStatus(str, Enum):
    """Organization status"""
    ACTIVE = "Active"
    TRIAL = "Trial"
    SUSPENDED = "Suspended"
    INACTIVE = "Inactive"


@dataclass
class Organization:
    """Organization entity"""
    id: str
    name: str
    organization_type: OrganizationType
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime


class OrganizationService:
    """
    Organization Service

    Handles multi-tenant organization management
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize organization service

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    async def create_organization(
        self,
        name: str,
        organization_type: OrganizationType = OrganizationType.SMB,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        created_by: str = "system"
    ) -> str:
        """
        Create new organization

        Args:
            name: Organization name
            organization_type: Type of organization
            address: Optional address
            phone: Optional phone
            email: Optional contact email
            created_by: User creating the organization

        Returns:
            str: Organization UUID
        """
        logger.info(f"Creating organization: {name}")

        org_id = str(uuid4())
        now = datetime.utcnow()

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO organizations (
                    id, name, organization_type, status,
                    address, phone, email,
                    created_at, updated_at, created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
                org_id,
                name,
                organization_type.value,
                OrganizationStatus.TRIAL.value,  # Start as trial
                address,
                phone,
                email,
                now,
                now,
                created_by
            )

            logger.info(f"Organization {org_id} created successfully")

        return org_id

    async def get_organization(self, org_id: str) -> Optional[Dict[str, Any]]:
        """
        Get organization by ID

        Args:
            org_id: Organization UUID

        Returns:
            Organization info dict or None
        """
        async with self.db_pool.acquire() as conn:
            org = await conn.fetchrow("""
                SELECT
                    id, name, organization_type, status,
                    address, phone, email,
                    created_at, updated_at
                FROM organizations
                WHERE id = $1
            """, org_id)

            if not org:
                return None

            return dict(org)

    async def list_organizations(
        self,
        organization_type: Optional[OrganizationType] = None,
        status: Optional[OrganizationStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List organizations with optional filtering

        Args:
            organization_type: Filter by type
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of organizations
        """
        query = """
            SELECT
                id, name, organization_type, status,
                address, phone, email,
                created_at, updated_at
            FROM organizations
            WHERE 1=1
        """

        params = []
        param_count = 0

        if organization_type:
            param_count += 1
            query += f" AND organization_type = ${param_count}"
            params.append(organization_type.value)

        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status.value)

        query += f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def update_organization(
        self,
        org_id: str,
        name: Optional[str] = None,
        organization_type: Optional[OrganizationType] = None,
        status: Optional[OrganizationStatus] = None,
        address: Optional[str] = None,
        phone: Optional[str] = None,
        email: Optional[str] = None,
        updated_by: str = "system"
    ) -> bool:
        """
        Update organization

        Args:
            org_id: Organization UUID
            name: New name
            organization_type: New type
            status: New status
            address: New address
            phone: New phone
            email: New email
            updated_by: User making the update

        Returns:
            bool: Success status
        """
        updates = []
        params = []
        param_count = 0

        if name is not None:
            param_count += 1
            updates.append(f"name = ${param_count}")
            params.append(name)

        if organization_type is not None:
            param_count += 1
            updates.append(f"organization_type = ${param_count}")
            params.append(organization_type.value)

        if status is not None:
            param_count += 1
            updates.append(f"status = ${param_count}")
            params.append(status.value)

        if address is not None:
            param_count += 1
            updates.append(f"address = ${param_count}")
            params.append(address)

        if phone is not None:
            param_count += 1
            updates.append(f"phone = ${param_count}")
            params.append(phone)

        if email is not None:
            param_count += 1
            updates.append(f"email = ${param_count}")
            params.append(email)

        if not updates:
            return False

        # Add updated_at
        param_count += 1
        updates.append(f"updated_at = ${param_count}")
        params.append(datetime.utcnow())

        # Add org_id for WHERE clause
        param_count += 1
        params.append(org_id)

        query = f"""
            UPDATE organizations
            SET {', '.join(updates)}
            WHERE id = ${param_count}
        """

        async with self.db_pool.acquire() as conn:
            result = await conn.execute(query, *params)

            if result == "UPDATE 0":
                return False

            logger.info(f"Organization {org_id} updated by {updated_by}")

        return True

    async def delete_organization(
        self,
        org_id: str,
        deleted_by: str = "system"
    ) -> bool:
        """
        Delete organization (soft delete)

        Args:
            org_id: Organization UUID
            deleted_by: User performing deletion

        Returns:
            bool: Success status
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("""
                UPDATE organizations
                SET status = $1, updated_at = $2
                WHERE id = $3
            """, OrganizationStatus.INACTIVE.value, datetime.utcnow(), org_id)

            if result == "UPDATE 0":
                return False

            logger.info(f"Organization {org_id} deleted by {deleted_by}")

        return True

    async def get_organization_stats(self, org_id: str) -> Dict[str, Any]:
        """
        Get organization statistics

        Args:
            org_id: Organization UUID

        Returns:
            Dict with statistics
        """
        async with self.db_pool.acquire() as conn:
            # Get user count
            user_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM users
                WHERE organization_id = $1
                  AND status = 'Active'
            """, org_id)

            # Get assessment count
            assessment_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM assessments
                WHERE organization_id = $1
                  AND status NOT IN ('Archived')
            """, org_id)

            # Get completed assessments
            completed_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM assessments
                WHERE organization_id = $1
                  AND status = 'Completed'
            """, org_id)

            # Get evidence count
            evidence_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM evidence e
                JOIN assessments a ON e.assessment_id = a.id
                WHERE a.organization_id = $1
            """, org_id)

            return {
                'organization_id': org_id,
                'active_users': user_count,
                'total_assessments': assessment_count,
                'completed_assessments': completed_count,
                'total_evidence': evidence_count
            }
