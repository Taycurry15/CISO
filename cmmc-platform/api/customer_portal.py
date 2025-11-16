"""
Customer Portal & Self-Service
================================
Self-service portal for customers to manage their compliance journey.

Features:
- Organization profile management
- Team member management (invite, remove, role assignment)
- Assessment creation and management
- Evidence upload and management
- Report downloads (SSP, POA&M, compliance reports)
- Subscription and billing overview
- Integration configuration
- Notification preferences
- Activity history
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field
from enum import Enum
import asyncpg
import logging
import json
import secrets

logger = logging.getLogger(__name__)


class InvitationStatus(str, Enum):
    """Team invitation status."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"
    REVOKED = "revoked"


class NotificationType(str, Enum):
    """Notification types."""
    EMAIL = "email"
    WEBHOOK = "webhook"
    SLACK = "slack"
    TEAMS = "teams"


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class OrganizationProfileUpdate(BaseModel):
    """Organization profile update request."""
    name: Optional[str] = None
    duns_number: Optional[str] = None
    cage_code: Optional[str] = None
    cmmc_level: Optional[int] = Field(None, ge=1, le=3)
    target_certification_date: Optional[date] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None


class TeamMemberInvite(BaseModel):
    """Team member invitation request."""
    email: EmailStr
    full_name: str
    role: str = Field(..., pattern="^(admin|assessor|viewer)$")
    message: Optional[str] = None


class AssessmentCreateRequest(BaseModel):
    """Self-service assessment creation."""
    name: str
    cmmc_level: int = Field(..., ge=1, le=3)
    assessment_type: str = Field("self", pattern="^(self|c3pao|surveillance)$")
    target_date: Optional[date] = None
    scope_description: Optional[str] = None


class NotificationPreferences(BaseModel):
    """Notification preferences."""
    email_enabled: bool = True
    email_address: Optional[EmailStr] = None
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    slack_enabled: bool = False
    slack_webhook_url: Optional[str] = None
    teams_enabled: bool = False
    teams_webhook_url: Optional[str] = None
    alert_on_new_findings: bool = True
    alert_on_sprs_change: bool = True
    alert_on_poam_overdue: bool = True
    alert_on_integration_failure: bool = True
    weekly_summary: bool = True


class ReportDownloadRequest(BaseModel):
    """Report download request."""
    assessment_id: str
    report_type: str = Field(..., pattern="^(ssp|poam|compliance|evidence_summary)$")
    format: str = Field("pdf", pattern="^(pdf|docx|xlsx|json)$")


# =============================================================================
# CUSTOMER PORTAL SERVICE
# =============================================================================

class CustomerPortalService:
    """Customer portal service for self-service operations."""

    def __init__(self, conn: asyncpg.Connection):
        """Initialize customer portal service."""
        self.conn = conn

    # =========================================================================
    # ORGANIZATION MANAGEMENT
    # =========================================================================

    async def get_organization_profile(
        self,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get organization profile.

        Args:
            organization_id: Organization UUID

        Returns:
            Organization profile data
        """
        org = await self.conn.fetchrow(
            """
            SELECT
                id, name, duns_number, cage_code, cmmc_level,
                target_certification_date, organization_type,
                current_authorization, active, created_at
            FROM organizations
            WHERE id = $1
            """,
            organization_id
        )

        if not org:
            return None

        # Get user count
        user_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE organization_id = $1 AND active = TRUE",
            organization_id
        )

        # Get assessment count
        assessment_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM assessments WHERE organization_id = $1",
            organization_id
        )

        # Get latest SPRS score
        latest_sprs = await self.conn.fetchrow(
            """
            SELECT s.score, s.calculation_date
            FROM sprs_scores s
            JOIN assessments a ON s.assessment_id = a.id
            WHERE a.organization_id = $1
            ORDER BY s.calculation_date DESC
            LIMIT 1
            """,
            organization_id
        )

        return {
            "id": str(org['id']),
            "name": org['name'],
            "duns_number": org['duns_number'],
            "cage_code": org['cage_code'],
            "cmmc_level": org['cmmc_level'],
            "target_certification_date": org['target_certification_date'].isoformat() if org['target_certification_date'] else None,
            "organization_type": org['organization_type'],
            "current_authorization": org['current_authorization'],
            "active": org['active'],
            "created_at": org['created_at'].isoformat(),
            "metrics": {
                "users": user_count,
                "assessments": assessment_count,
                "latest_sprs_score": latest_sprs['score'] if latest_sprs else None,
                "last_score_date": latest_sprs['calculation_date'].isoformat() if latest_sprs else None
            }
        }

    async def update_organization_profile(
        self,
        organization_id: str,
        updates: OrganizationProfileUpdate,
        updated_by: str
    ) -> Dict[str, Any]:
        """
        Update organization profile.

        Args:
            organization_id: Organization UUID
            updates: Profile updates
            updated_by: User making the update

        Returns:
            Updated organization profile
        """
        # Build update query dynamically
        update_fields = []
        values = []
        param_count = 1

        if updates.name is not None:
            update_fields.append(f"name = ${param_count}")
            values.append(updates.name)
            param_count += 1

        if updates.duns_number is not None:
            update_fields.append(f"duns_number = ${param_count}")
            values.append(updates.duns_number)
            param_count += 1

        if updates.cage_code is not None:
            update_fields.append(f"cage_code = ${param_count}")
            values.append(updates.cage_code)
            param_count += 1

        if updates.cmmc_level is not None:
            update_fields.append(f"cmmc_level = ${param_count}")
            values.append(updates.cmmc_level)
            param_count += 1

        if updates.target_certification_date is not None:
            update_fields.append(f"target_certification_date = ${param_count}")
            values.append(updates.target_certification_date)
            param_count += 1

        if not update_fields:
            # No updates, return current profile
            return await self.get_organization_profile(organization_id)

        update_fields.append("updated_at = NOW()")
        values.append(organization_id)

        query = f"""
            UPDATE organizations
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id
        """

        await self.conn.execute(query, *values)

        # Log the update
        await self.conn.execute(
            """
            INSERT INTO audit_log (table_name, operation, record_id, changed_by, changed_data)
            VALUES ('organizations', 'UPDATE', $1, $2, $3)
            """,
            organization_id,
            updated_by,
            json.dumps(updates.dict(exclude_none=True))
        )

        logger.info(f"Organization profile updated: {organization_id}")

        return await self.get_organization_profile(organization_id)

    # =========================================================================
    # TEAM MANAGEMENT
    # =========================================================================

    async def get_team_members(
        self,
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all team members for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of team members
        """
        members = await self.conn.fetch(
            """
            SELECT
                id, email, full_name, role, active,
                created_at, updated_at
            FROM users
            WHERE organization_id = $1
            ORDER BY created_at ASC
            """,
            organization_id
        )

        return [
            {
                "id": str(member['id']),
                "email": member['email'],
                "full_name": member['full_name'],
                "role": member['role'],
                "active": member['active'],
                "created_at": member['created_at'].isoformat(),
                "updated_at": member['updated_at'].isoformat()
            }
            for member in members
        ]

    async def invite_team_member(
        self,
        organization_id: str,
        invite: TeamMemberInvite,
        invited_by: str
    ) -> Dict[str, Any]:
        """
        Invite a new team member.

        Args:
            organization_id: Organization UUID
            invite: Invitation details
            invited_by: User sending the invitation

        Returns:
            Invitation details
        """
        # Check if user already exists
        existing = await self.conn.fetchval(
            "SELECT id FROM users WHERE email = $1",
            invite.email.lower()
        )

        if existing:
            raise ValueError("User with this email already exists")

        # Generate invitation token
        invitation_token = secrets.token_urlsafe(32)

        # Create invitation record
        invitation_id = await self.conn.fetchval(
            """
            INSERT INTO team_invitations
            (organization_id, email, full_name, role, invitation_token,
             invited_by, message, expires_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW() + INTERVAL '7 days')
            RETURNING id
            """,
            organization_id,
            invite.email.lower(),
            invite.full_name,
            invite.role,
            invitation_token,
            invited_by,
            invite.message
        )

        logger.info(f"Team invitation created: {invitation_id} for {invite.email}")

        # In production, send invitation email here
        invitation_url = f"https://platform.example.com/accept-invitation/{invitation_token}"

        return {
            "id": str(invitation_id),
            "email": invite.email,
            "full_name": invite.full_name,
            "role": invite.role,
            "invitation_url": invitation_url,
            "expires_in_days": 7
        }

    async def remove_team_member(
        self,
        user_id: str,
        organization_id: str,
        removed_by: str
    ) -> bool:
        """
        Remove a team member (deactivate).

        Args:
            user_id: User UUID to remove
            organization_id: Organization UUID
            removed_by: User performing the removal

        Returns:
            Success status
        """
        # Verify user belongs to organization
        user_org = await self.conn.fetchval(
            "SELECT organization_id FROM users WHERE id = $1",
            user_id
        )

        if str(user_org) != organization_id:
            raise ValueError("User does not belong to this organization")

        # Deactivate user
        await self.conn.execute(
            "UPDATE users SET active = FALSE, updated_at = NOW() WHERE id = $1",
            user_id
        )

        # Log the removal
        await self.conn.execute(
            """
            INSERT INTO audit_log (table_name, operation, record_id, changed_by, changed_data)
            VALUES ('users', 'DEACTIVATE', $1, $2, $3)
            """,
            user_id,
            removed_by,
            json.dumps({"action": "team_member_removed"})
        )

        logger.info(f"Team member removed: {user_id}")

        return True

    # =========================================================================
    # SELF-SERVICE ASSESSMENTS
    # =========================================================================

    async def create_assessment(
        self,
        organization_id: str,
        request: AssessmentCreateRequest,
        created_by: str
    ) -> Dict[str, Any]:
        """
        Create a new assessment (self-service).

        Args:
            organization_id: Organization UUID
            request: Assessment creation request
            created_by: User creating the assessment

        Returns:
            Created assessment details
        """
        assessment_id = await self.conn.fetchval(
            """
            INSERT INTO assessments
            (organization_id, name, cmmc_level, assessment_type, status, scope, created_by)
            VALUES ($1, $2, $3, $4, 'planning', $5, $6)
            RETURNING id
            """,
            organization_id,
            request.name,
            request.cmmc_level,
            request.assessment_type,
            json.dumps({
                "target_date": request.target_date.isoformat() if request.target_date else None,
                "description": request.scope_description
            }),
            created_by
        )

        # Create initial control findings
        controls = await self.conn.fetch(
            """
            SELECT id FROM controls
            WHERE framework = 'NIST 800-171'
            AND level <= $1
            """,
            request.cmmc_level
        )

        for control in controls:
            await self.conn.execute(
                """
                INSERT INTO control_findings
                (assessment_id, control_id, status, assessor_narrative)
                VALUES ($1, $2, 'Not Assessed', 'Pending assessment')
                """,
                assessment_id,
                control['id']
            )

        logger.info(f"Assessment created: {assessment_id} with {len(controls)} controls")

        return {
            "id": str(assessment_id),
            "name": request.name,
            "cmmc_level": request.cmmc_level,
            "assessment_type": request.assessment_type,
            "status": "planning",
            "controls_count": len(controls)
        }

    async def get_assessments(
        self,
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all assessments for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of assessments
        """
        assessments = await self.conn.fetch(
            """
            SELECT
                a.id, a.name, a.cmmc_level, a.assessment_type, a.status,
                a.created_at, a.updated_at,
                (SELECT COUNT(*) FROM control_findings WHERE assessment_id = a.id) as total_controls,
                (SELECT COUNT(*) FROM control_findings WHERE assessment_id = a.id AND status = 'Met') as met_controls
            FROM assessments a
            WHERE a.organization_id = $1
            ORDER BY a.created_at DESC
            """,
            organization_id
        )

        return [
            {
                "id": str(assessment['id']),
                "name": assessment['name'],
                "cmmc_level": assessment['cmmc_level'],
                "assessment_type": assessment['assessment_type'],
                "status": assessment['status'],
                "created_at": assessment['created_at'].isoformat(),
                "updated_at": assessment['updated_at'].isoformat(),
                "progress": {
                    "total_controls": assessment['total_controls'],
                    "met_controls": assessment['met_controls'],
                    "completion_percentage": round((assessment['met_controls'] / assessment['total_controls'] * 100), 2) if assessment['total_controls'] > 0 else 0
                }
            }
            for assessment in assessments
        ]

    # =========================================================================
    # NOTIFICATION PREFERENCES
    # =========================================================================

    async def get_notification_preferences(
        self,
        user_id: str
    ) -> Dict[str, Any]:
        """Get user notification preferences."""
        prefs = await self.conn.fetchrow(
            "SELECT preferences FROM user_preferences WHERE user_id = $1",
            user_id
        )

        if not prefs or not prefs['preferences']:
            # Return defaults
            return NotificationPreferences().dict()

        return prefs['preferences']

    async def update_notification_preferences(
        self,
        user_id: str,
        preferences: NotificationPreferences
    ) -> Dict[str, Any]:
        """Update user notification preferences."""
        await self.conn.execute(
            """
            INSERT INTO user_preferences (user_id, preferences)
            VALUES ($1, $2)
            ON CONFLICT (user_id)
            DO UPDATE SET preferences = $2, updated_at = NOW()
            """,
            user_id,
            json.dumps(preferences.dict())
        )

        logger.info(f"Notification preferences updated for user {user_id}")

        return preferences.dict()

    # =========================================================================
    # REPORT DOWNLOADS
    # =========================================================================

    async def generate_report_download(
        self,
        request: ReportDownloadRequest,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Generate a report for download.

        Args:
            request: Report download request
            organization_id: Organization UUID

        Returns:
            Report download details
        """
        # Verify assessment belongs to organization
        assessment_org = await self.conn.fetchval(
            "SELECT organization_id FROM assessments WHERE id = $1",
            request.assessment_id
        )

        if str(assessment_org) != organization_id:
            raise ValueError("Assessment does not belong to this organization")

        # Generate report (placeholder - implement actual generation)
        report_filename = f"{request.report_type}_{request.assessment_id}.{request.format}"
        report_path = f"/var/cmmc/reports/{report_filename}"

        # Log the download
        await self.conn.execute(
            """
            INSERT INTO report_downloads
            (assessment_id, report_type, format, file_path)
            VALUES ($1, $2, $3, $4)
            """,
            request.assessment_id,
            request.report_type,
            request.format,
            report_path
        )

        logger.info(f"Report generated: {report_filename}")

        return {
            "report_type": request.report_type,
            "format": request.format,
            "filename": report_filename,
            "download_url": f"/api/v1/portal/reports/download/{report_filename}",
            "expires_in_hours": 24
        }

    # =========================================================================
    # ACTIVITY HISTORY
    # =========================================================================

    async def get_activity_history(
        self,
        organization_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get organization activity history."""
        activities = await self.conn.fetch(
            """
            SELECT
                al.id, al.table_name, al.operation,
                al.changed_at, al.changed_data,
                u.email as user_email
            FROM audit_log al
            LEFT JOIN users u ON al.changed_by = u.id
            WHERE (
                al.record_id IN (SELECT id::text FROM assessments WHERE organization_id = $1)
                OR al.changed_by IN (SELECT id FROM users WHERE organization_id = $1)
            )
            ORDER BY al.changed_at DESC
            LIMIT $2
            """,
            organization_id,
            limit
        )

        return [
            {
                "id": str(activity['id']),
                "type": activity['table_name'],
                "operation": activity['operation'],
                "timestamp": activity['changed_at'].isoformat(),
                "user": activity['user_email'] or "System",
                "details": activity['changed_data']
            }
            for activity in activities
        ]
