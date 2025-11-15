"""
Assessment Management Service

Manages CMMC assessment lifecycle from creation through completion,
including scoping, status tracking, and progress monitoring.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncpg
from uuid import UUID, uuid4

logger = logging.getLogger(__name__)


class AssessmentStatus(str, Enum):
    """Assessment lifecycle status"""
    DRAFT = "Draft"
    SCOPING = "Scoping"
    IN_PROGRESS = "In Progress"
    REVIEW = "Review"
    COMPLETED = "Completed"
    ARCHIVED = "Archived"


class AssessmentType(str, Enum):
    """Type of assessment"""
    INITIAL = "Initial Assessment"
    ANNUAL = "Annual Assessment"
    REMEDIATION = "Remediation Assessment"
    SURVEILLANCE = "Surveillance Assessment"


@dataclass
class AssessmentScope:
    """Assessment scope definition"""
    cmmc_level: int  # 1, 2, or 3
    domains: List[str]  # Specific domains or ["ALL"]
    cloud_providers: List[str]  # M365, Azure, AWS, etc.
    system_boundary: str
    exclusions: Optional[str] = None
    include_inherited: bool = True


@dataclass
class AssessmentProgress:
    """Assessment progress metrics"""
    total_controls: int
    controls_analyzed: int
    controls_met: int
    controls_not_met: int
    controls_partial: int
    controls_na: int
    evidence_collected: int
    completion_percentage: float
    avg_confidence_score: float


@dataclass
class Assessment:
    """Assessment entity"""
    id: str
    organization_id: str
    assessment_type: AssessmentType
    status: AssessmentStatus
    scope: AssessmentScope
    start_date: Optional[datetime]
    target_end_date: Optional[datetime]
    end_date: Optional[datetime]
    lead_assessor: Optional[str]
    team_members: List[str]
    created_at: datetime
    updated_at: datetime
    created_by: str


class AssessmentService:
    """
    Assessment Management Service

    Handles assessment creation, lifecycle management, and progress tracking
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize assessment service

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    async def create_assessment(
        self,
        organization_id: str,
        assessment_type: AssessmentType,
        scope: AssessmentScope,
        lead_assessor: Optional[str] = None,
        team_members: Optional[List[str]] = None,
        target_end_date: Optional[datetime] = None,
        created_by: str = "system"
    ) -> str:
        """
        Create new assessment

        Args:
            organization_id: Organization UUID
            assessment_type: Type of assessment
            scope: Assessment scope configuration
            lead_assessor: Lead assessor name
            team_members: List of team member names
            target_end_date: Target completion date
            created_by: User who created assessment

        Returns:
            str: Assessment UUID
        """
        logger.info(f"Creating {assessment_type.value} for organization {organization_id}")

        assessment_id = str(uuid4())
        now = datetime.utcnow()

        async with self.db_pool.acquire() as conn:
            # Create assessment record
            await conn.execute("""
                INSERT INTO assessments (
                    id, organization_id, assessment_type, status,
                    scope, start_date, target_end_date, end_date,
                    lead_assessor, team_members, created_at, updated_at, created_by
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            """,
                assessment_id,
                organization_id,
                assessment_type.value,
                AssessmentStatus.DRAFT.value,
                self._serialize_scope(scope),
                None,  # start_date - set when moved to In Progress
                target_end_date,
                None,  # end_date - set when completed
                lead_assessor,
                team_members or [],
                now,
                now,
                created_by
            )

            # Initialize control findings based on scope
            await self._initialize_control_findings(conn, assessment_id, scope)

            logger.info(f"Assessment {assessment_id} created successfully")

        return assessment_id

    async def _initialize_control_findings(
        self,
        conn: asyncpg.Connection,
        assessment_id: str,
        scope: AssessmentScope
    ):
        """Initialize control findings for scoped controls"""

        # Build query to get controls based on scope
        query = """
            SELECT c.id
            FROM controls c
            JOIN control_domains cd ON c.domain_id = cd.id
            WHERE c.cmmc_level <= $1
        """

        params = [scope.cmmc_level]

        # Filter by domains if not ALL
        if scope.domains and scope.domains != ["ALL"]:
            query += " AND cd.name = ANY($2)"
            params.append(scope.domains)

        controls = await conn.fetch(query, *params)

        # Create control_findings entries
        for control in controls:
            await conn.execute("""
                INSERT INTO control_findings (
                    id, assessment_id, control_id, status,
                    assessor_narrative, ai_confidence_score,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (assessment_id, control_id) DO NOTHING
            """,
                str(uuid4()),
                assessment_id,
                control['id'],
                "Not Assessed",  # Initial status
                None,
                None,
                datetime.utcnow(),
                datetime.utcnow()
            )

        logger.info(f"Initialized {len(controls)} control findings for assessment {assessment_id}")

    def _serialize_scope(self, scope: AssessmentScope) -> str:
        """Serialize scope to JSON string"""
        import json
        return json.dumps({
            'cmmc_level': scope.cmmc_level,
            'domains': scope.domains,
            'cloud_providers': scope.cloud_providers,
            'system_boundary': scope.system_boundary,
            'exclusions': scope.exclusions,
            'include_inherited': scope.include_inherited
        })

    def _deserialize_scope(self, scope_json: str) -> AssessmentScope:
        """Deserialize scope from JSON string"""
        import json
        data = json.loads(scope_json) if isinstance(scope_json, str) else scope_json
        return AssessmentScope(**data)

    async def update_status(
        self,
        assessment_id: str,
        new_status: AssessmentStatus,
        updated_by: str = "system"
    ) -> bool:
        """
        Update assessment status

        Args:
            assessment_id: Assessment UUID
            new_status: New status
            updated_by: User making the update

        Returns:
            bool: Success status
        """
        logger.info(f"Updating assessment {assessment_id} status to {new_status.value}")

        now = datetime.utcnow()

        async with self.db_pool.acquire() as conn:
            # Get current status
            current = await conn.fetchrow(
                "SELECT status, start_date FROM assessments WHERE id = $1",
                assessment_id
            )

            if not current:
                raise ValueError(f"Assessment {assessment_id} not found")

            # Set start_date when moving to In Progress
            start_date = current['start_date']
            if new_status == AssessmentStatus.IN_PROGRESS and not start_date:
                start_date = now

            # Set end_date when completing
            end_date = None
            if new_status == AssessmentStatus.COMPLETED:
                end_date = now

            # Update status
            await conn.execute("""
                UPDATE assessments
                SET status = $1,
                    start_date = $2,
                    end_date = $3,
                    updated_at = $4
                WHERE id = $5
            """,
                new_status.value,
                start_date,
                end_date,
                now,
                assessment_id
            )

            logger.info(f"Assessment {assessment_id} status updated to {new_status.value}")

        return True

    async def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get assessment details

        Args:
            assessment_id: Assessment UUID

        Returns:
            Assessment details or None
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    a.*,
                    o.name as organization_name
                FROM assessments a
                JOIN organizations o ON a.organization_id = o.id
                WHERE a.id = $1
            """, assessment_id)

            if not row:
                return None

            return dict(row)

    async def get_assessment_progress(
        self,
        assessment_id: str
    ) -> AssessmentProgress:
        """
        Get assessment progress metrics

        Args:
            assessment_id: Assessment UUID

        Returns:
            AssessmentProgress with metrics
        """
        async with self.db_pool.acquire() as conn:
            # Get control statistics
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_controls,
                    COUNT(*) FILTER (WHERE status != 'Not Assessed') as controls_analyzed,
                    COUNT(*) FILTER (WHERE status = 'Met') as controls_met,
                    COUNT(*) FILTER (WHERE status = 'Not Met') as controls_not_met,
                    COUNT(*) FILTER (WHERE status = 'Partially Met') as controls_partial,
                    COUNT(*) FILTER (WHERE status = 'Not Applicable') as controls_na,
                    AVG(ai_confidence_score) FILTER (WHERE ai_confidence_score IS NOT NULL) as avg_confidence
                FROM control_findings
                WHERE assessment_id = $1
            """, assessment_id)

            # Get evidence count
            evidence_count = await conn.fetchval("""
                SELECT COUNT(DISTINCT e.id)
                FROM evidence e
                WHERE e.assessment_id = $1
            """, assessment_id)

            total = stats['total_controls']
            analyzed = stats['controls_analyzed']

            completion_pct = (analyzed / total * 100) if total > 0 else 0

            return AssessmentProgress(
                total_controls=total,
                controls_analyzed=analyzed,
                controls_met=stats['controls_met'],
                controls_not_met=stats['controls_not_met'],
                controls_partial=stats['controls_partial'],
                controls_na=stats['controls_na'],
                evidence_collected=evidence_count,
                completion_percentage=round(completion_pct, 1),
                avg_confidence_score=round(float(stats['avg_confidence'] or 0), 2)
            )

    async def list_assessments(
        self,
        organization_id: Optional[str] = None,
        status: Optional[AssessmentStatus] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List assessments with optional filtering

        Args:
            organization_id: Filter by organization
            status: Filter by status
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of assessments
        """
        query = """
            SELECT
                a.*,
                o.name as organization_name
            FROM assessments a
            JOIN organizations o ON a.organization_id = o.id
            WHERE 1=1
        """

        params = []
        param_count = 0

        if organization_id:
            param_count += 1
            query += f" AND a.organization_id = ${param_count}"
            params.append(organization_id)

        if status:
            param_count += 1
            query += f" AND a.status = ${param_count}"
            params.append(status.value)

        query += f" ORDER BY a.created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def update_scope(
        self,
        assessment_id: str,
        scope: AssessmentScope,
        updated_by: str = "system"
    ) -> bool:
        """
        Update assessment scope

        Args:
            assessment_id: Assessment UUID
            scope: New scope configuration
            updated_by: User making the update

        Returns:
            bool: Success status
        """
        logger.info(f"Updating assessment {assessment_id} scope")

        async with self.db_pool.acquire() as conn:
            # Check current status
            current = await conn.fetchrow(
                "SELECT status FROM assessments WHERE id = $1",
                assessment_id
            )

            if not current:
                raise ValueError(f"Assessment {assessment_id} not found")

            # Only allow scope changes in Draft or Scoping status
            if current['status'] not in [AssessmentStatus.DRAFT.value, AssessmentStatus.SCOPING.value]:
                raise ValueError(f"Cannot change scope in {current['status']} status")

            # Update scope
            await conn.execute("""
                UPDATE assessments
                SET scope = $1,
                    updated_at = $2
                WHERE id = $3
            """,
                self._serialize_scope(scope),
                datetime.utcnow(),
                assessment_id
            )

            # Reinitialize control findings
            await self._initialize_control_findings(conn, assessment_id, scope)

            logger.info(f"Assessment {assessment_id} scope updated")

        return True

    async def assign_team(
        self,
        assessment_id: str,
        lead_assessor: Optional[str] = None,
        team_members: Optional[List[str]] = None,
        updated_by: str = "system"
    ) -> bool:
        """
        Assign assessment team

        Args:
            assessment_id: Assessment UUID
            lead_assessor: Lead assessor name
            team_members: List of team member names
            updated_by: User making the update

        Returns:
            bool: Success status
        """
        logger.info(f"Assigning team to assessment {assessment_id}")

        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                UPDATE assessments
                SET lead_assessor = COALESCE($1, lead_assessor),
                    team_members = COALESCE($2, team_members),
                    updated_at = $3
                WHERE id = $4
            """,
                lead_assessor,
                team_members,
                datetime.utcnow(),
                assessment_id
            )

        return True

    async def delete_assessment(
        self,
        assessment_id: str,
        deleted_by: str = "system"
    ) -> bool:
        """
        Delete assessment (soft delete by archiving)

        Args:
            assessment_id: Assessment UUID
            deleted_by: User deleting the assessment

        Returns:
            bool: Success status
        """
        logger.info(f"Deleting assessment {assessment_id}")

        async with self.db_pool.acquire() as conn:
            # Archive instead of delete
            await conn.execute("""
                UPDATE assessments
                SET status = $1,
                    updated_at = $2
                WHERE id = $3
            """,
                AssessmentStatus.ARCHIVED.value,
                datetime.utcnow(),
                assessment_id
            )

        return True

    async def get_assessment_summary(
        self,
        assessment_id: str
    ) -> Dict[str, Any]:
        """
        Get comprehensive assessment summary

        Args:
            assessment_id: Assessment UUID

        Returns:
            Dictionary with assessment details and metrics
        """
        # Get basic info
        assessment = await self.get_assessment(assessment_id)

        if not assessment:
            raise ValueError(f"Assessment {assessment_id} not found")

        # Get progress
        progress = await self.get_assessment_progress(assessment_id)

        # Get scope
        scope = self._deserialize_scope(assessment['scope'])

        return {
            'assessment': {
                'id': str(assessment['id']),
                'organization_name': assessment['organization_name'],
                'assessment_type': assessment['assessment_type'],
                'status': assessment['status'],
                'start_date': assessment['start_date'].isoformat() if assessment['start_date'] else None,
                'target_end_date': assessment['target_end_date'].isoformat() if assessment['target_end_date'] else None,
                'end_date': assessment['end_date'].isoformat() if assessment['end_date'] else None,
                'lead_assessor': assessment['lead_assessor'],
                'team_members': assessment['team_members'],
                'created_at': assessment['created_at'].isoformat()
            },
            'scope': {
                'cmmc_level': scope.cmmc_level,
                'domains': scope.domains,
                'cloud_providers': scope.cloud_providers,
                'system_boundary': scope.system_boundary,
                'include_inherited': scope.include_inherited
            },
            'progress': {
                'total_controls': progress.total_controls,
                'controls_analyzed': progress.controls_analyzed,
                'controls_met': progress.controls_met,
                'controls_not_met': progress.controls_not_met,
                'controls_partial': progress.controls_partial,
                'controls_na': progress.controls_na,
                'evidence_collected': progress.evidence_collected,
                'completion_percentage': progress.completion_percentage,
                'avg_confidence_score': progress.avg_confidence_score
            }
        }
