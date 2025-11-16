"""
C3PAO Workflow Support
======================
Support for CMMC Third-Party Assessment Organizations (C3PAOs).

Features:
- C3PAO organization management
- Assessor assignment
- Assessment scheduling and coordination
- Evidence review workflow
- Finding validation
- Report approval workflow
- Client communication
- Assessment lifecycle management
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
from pydantic import BaseModel, EmailStr
from enum import Enum
import asyncpg
import logging
import json

logger = logging.getLogger(__name__)


class AssessmentPhase(str, Enum):
    """C3PAO assessment phases."""
    SCOPING = "scoping"
    PLANNING = "planning"
    EVIDENCE_REVIEW = "evidence_review"
    ONSITE_ASSESSMENT = "onsite_assessment"
    FINDING_VALIDATION = "finding_validation"
    REPORT_WRITING = "report_writing"
    REPORT_REVIEW = "report_review"
    FINAL_APPROVAL = "final_approval"
    COMPLETED = "completed"


class FindingValidationStatus(str, Enum):
    """Finding validation status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_CLARIFICATION = "needs_clarification"


class C3PAORole(str, Enum):
    """C3PAO team roles."""
    LEAD_ASSESSOR = "lead_assessor"
    ASSESSOR = "assessor"
    TECHNICAL_EXPERT = "technical_expert"
    QUALITY_REVIEWER = "quality_reviewer"


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class C3PAORegistration(BaseModel):
    """C3PAO organization registration."""
    organization_name: str
    certification_number: str
    accreditation_body: str = "CMMC-AB"
    contact_email: EmailStr
    contact_phone: str
    lead_assessor_name: str
    lead_assessor_email: EmailStr


class AssessmentAssignment(BaseModel):
    """Assign C3PAO to client assessment."""
    client_organization_id: str
    assessment_id: str
    c3pao_organization_id: str
    lead_assessor_id: str
    planned_start_date: date
    planned_end_date: date
    scope_notes: Optional[str] = None


class FindingReview(BaseModel):
    """C3PAO finding review."""
    finding_id: str
    validation_status: FindingValidationStatus
    assessor_comments: str
    evidence_sufficiency: bool
    remediation_required: bool


class AssessmentPhaseUpdate(BaseModel):
    """Update assessment phase."""
    phase: AssessmentPhase
    notes: Optional[str] = None


# =============================================================================
# C3PAO WORKFLOW SERVICE
# =============================================================================

class C3PAOWorkflowService:
    """C3PAO workflow management service."""

    def __init__(self, conn: asyncpg.Connection):
        """Initialize C3PAO workflow service."""
        self.conn = conn

    # =========================================================================
    # C3PAO ORGANIZATION MANAGEMENT
    # =========================================================================

    async def register_c3pao(
        self,
        registration: C3PAORegistration
    ) -> Dict[str, Any]:
        """
        Register a new C3PAO organization.

        Args:
            registration: C3PAO registration details

        Returns:
            C3PAO organization details
        """
        # Create C3PAO organization
        c3pao_id = await self.conn.fetchval(
            """
            INSERT INTO c3pao_organizations
            (name, certification_number, accreditation_body,
             contact_email, contact_phone, status)
            VALUES ($1, $2, $3, $4, $5, 'active')
            RETURNING id
            """,
            registration.organization_name,
            registration.certification_number,
            registration.accreditation_body,
            registration.contact_email,
            registration.contact_phone
        )

        # Create lead assessor user
        from auth import hash_password
        temp_password = hash_password("TempPassword123!")  # Would send reset email

        lead_assessor_id = await self.conn.fetchval(
            """
            INSERT INTO c3pao_assessors
            (c3pao_organization_id, email, full_name, role, active)
            VALUES ($1, $2, $3, $4, TRUE)
            RETURNING id
            """,
            c3pao_id,
            registration.lead_assessor_email,
            registration.lead_assessor_name,
            C3PAORole.LEAD_ASSESSOR.value
        )

        logger.info(f"C3PAO registered: {c3pao_id}")

        return {
            "c3pao_id": str(c3pao_id),
            "organization_name": registration.organization_name,
            "certification_number": registration.certification_number,
            "lead_assessor_id": str(lead_assessor_id),
            "status": "active"
        }

    async def get_c3pao_details(
        self,
        c3pao_id: str
    ) -> Dict[str, Any]:
        """Get C3PAO organization details."""
        c3pao = await self.conn.fetchrow(
            """
            SELECT
                id, name, certification_number, accreditation_body,
                contact_email, contact_phone, status, created_at
            FROM c3pao_organizations
            WHERE id = $1
            """,
            c3pao_id
        )

        if not c3pao:
            return None

        # Get assessor count
        assessor_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM c3pao_assessors WHERE c3pao_organization_id = $1 AND active = TRUE",
            c3pao_id
        )

        # Get active assessments
        active_assessments = await self.conn.fetchval(
            """
            SELECT COUNT(*)
            FROM c3pao_assessments
            WHERE c3pao_organization_id = $1
            AND status NOT IN ('completed', 'canceled')
            """,
            c3pao_id
        )

        return {
            "id": str(c3pao['id']),
            "name": c3pao['name'],
            "certification_number": c3pao['certification_number'],
            "accreditation_body": c3pao['accreditation_body'],
            "contact_email": c3pao['contact_email'],
            "contact_phone": c3pao['contact_phone'],
            "status": c3pao['status'],
            "created_at": c3pao['created_at'].isoformat(),
            "metrics": {
                "assessors": assessor_count,
                "active_assessments": active_assessments
            }
        }

    # =========================================================================
    # ASSESSMENT ASSIGNMENT & MANAGEMENT
    # =========================================================================

    async def assign_assessment(
        self,
        assignment: AssessmentAssignment,
        assigned_by: str
    ) -> Dict[str, Any]:
        """
        Assign C3PAO to client assessment.

        Args:
            assignment: Assessment assignment details
            assigned_by: User making the assignment

        Returns:
            Assignment details
        """
        # Verify assessment exists and is eligible for C3PAO
        assessment = await self.conn.fetchrow(
            """
            SELECT id, name, assessment_type
            FROM assessments
            WHERE id = $1 AND organization_id = $2
            """,
            assignment.assessment_id,
            assignment.client_organization_id
        )

        if not assessment:
            raise ValueError("Assessment not found or does not belong to organization")

        if assessment['assessment_type'] != 'c3pao':
            raise ValueError("Assessment type must be 'c3pao' for C3PAO assignment")

        # Create C3PAO assessment record
        c3pao_assessment_id = await self.conn.fetchval(
            """
            INSERT INTO c3pao_assessments
            (assessment_id, client_organization_id, c3pao_organization_id,
             lead_assessor_id, planned_start_date, planned_end_date,
             current_phase, status, scope_notes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'assigned', $8)
            RETURNING id
            """,
            assignment.assessment_id,
            assignment.client_organization_id,
            assignment.c3pao_organization_id,
            assignment.lead_assessor_id,
            assignment.planned_start_date,
            assignment.planned_end_date,
            AssessmentPhase.SCOPING.value,
            assignment.scope_notes
        )

        # Update assessment status
        await self.conn.execute(
            "UPDATE assessments SET status = 'in_progress' WHERE id = $1",
            assignment.assessment_id
        )

        # Create initial milestone timeline
        await self._create_assessment_milestones(
            c3pao_assessment_id,
            assignment.planned_start_date,
            assignment.planned_end_date
        )

        logger.info(f"C3PAO assessment assigned: {c3pao_assessment_id}")

        return {
            "c3pao_assessment_id": str(c3pao_assessment_id),
            "assessment_id": assignment.assessment_id,
            "c3pao_organization_id": assignment.c3pao_organization_id,
            "lead_assessor_id": assignment.lead_assessor_id,
            "current_phase": AssessmentPhase.SCOPING.value,
            "status": "assigned"
        }

    async def _create_assessment_milestones(
        self,
        c3pao_assessment_id: str,
        start_date: date,
        end_date: date
    ):
        """Create assessment phase milestones."""
        total_days = (end_date - start_date).days

        milestones = [
            ("Scoping Complete", start_date + timedelta(days=int(total_days * 0.1))),
            ("Planning Complete", start_date + timedelta(days=int(total_days * 0.2))),
            ("Evidence Review Complete", start_date + timedelta(days=int(total_days * 0.5))),
            ("Onsite Assessment Complete", start_date + timedelta(days=int(total_days * 0.7))),
            ("Finding Validation Complete", start_date + timedelta(days=int(total_days * 0.8))),
            ("Report Writing Complete", start_date + timedelta(days=int(total_days * 0.9))),
            ("Final Report Approval", end_date)
        ]

        for milestone_name, target_date in milestones:
            await self.conn.execute(
                """
                INSERT INTO c3pao_milestones
                (c3pao_assessment_id, milestone_name, target_date, status)
                VALUES ($1, $2, $3, 'pending')
                """,
                c3pao_assessment_id,
                milestone_name,
                target_date
            )

    async def update_assessment_phase(
        self,
        c3pao_assessment_id: str,
        update: AssessmentPhaseUpdate,
        updated_by: str
    ) -> Dict[str, Any]:
        """Update assessment phase."""
        await self.conn.execute(
            """
            UPDATE c3pao_assessments
            SET current_phase = $1, updated_at = NOW()
            WHERE id = $2
            """,
            update.phase.value,
            c3pao_assessment_id
        )

        # Log phase transition
        await self.conn.execute(
            """
            INSERT INTO c3pao_phase_history
            (c3pao_assessment_id, phase, entered_by, notes)
            VALUES ($1, $2, $3, $4)
            """,
            c3pao_assessment_id,
            update.phase.value,
            updated_by,
            update.notes
        )

        logger.info(f"Assessment phase updated to {update.phase.value}: {c3pao_assessment_id}")

        return {
            "c3pao_assessment_id": c3pao_assessment_id,
            "current_phase": update.phase.value,
            "updated_at": datetime.utcnow().isoformat()
        }

    # =========================================================================
    # FINDING REVIEW & VALIDATION
    # =========================================================================

    async def review_finding(
        self,
        review: FindingReview,
        assessor_id: str
    ) -> Dict[str, Any]:
        """
        Review and validate a finding.

        Args:
            review: Finding review details
            assessor_id: Assessor performing the review

        Returns:
            Review result
        """
        # Create finding review record
        review_id = await self.conn.fetchval(
            """
            INSERT INTO c3pao_finding_reviews
            (finding_id, assessor_id, validation_status,
             assessor_comments, evidence_sufficiency, remediation_required)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING id
            """,
            review.finding_id,
            assessor_id,
            review.validation_status.value,
            review.assessor_comments,
            review.evidence_sufficiency,
            review.remediation_required
        )

        # Update finding if approved
        if review.validation_status == FindingValidationStatus.APPROVED:
            await self.conn.execute(
                """
                UPDATE control_findings
                SET human_reviewed = TRUE, reviewer_id = $1, reviewed_date = NOW()
                WHERE id = $2
                """,
                assessor_id,
                review.finding_id
            )

        logger.info(f"Finding reviewed: {review.finding_id} - {review.validation_status.value}")

        return {
            "review_id": str(review_id),
            "finding_id": review.finding_id,
            "validation_status": review.validation_status.value,
            "evidence_sufficiency": review.evidence_sufficiency,
            "remediation_required": review.remediation_required
        }

    async def get_findings_for_review(
        self,
        c3pao_assessment_id: str,
        status_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get findings pending review."""
        query = """
            SELECT
                cf.id, cf.control_id, cf.status, cf.assessor_narrative,
                cf.ai_confidence_score, cf.human_reviewed,
                c.title as control_title,
                (SELECT COUNT(*) FROM evidence WHERE control_id = cf.control_id AND assessment_id = cf.assessment_id) as evidence_count
            FROM control_findings cf
            JOIN controls c ON cf.control_id = c.id
            JOIN c3pao_assessments ca ON cf.assessment_id = ca.assessment_id
            WHERE ca.id = $1
        """

        if status_filter:
            query += f" AND cf.status = '{status_filter}'"

        query += " ORDER BY cf.updated_at DESC"

        findings = await self.conn.fetch(query, c3pao_assessment_id)

        return [
            {
                "id": str(finding['id']),
                "control_id": finding['control_id'],
                "control_title": finding['control_title'],
                "status": finding['status'],
                "narrative": finding['assessor_narrative'],
                "ai_confidence": finding['ai_confidence_score'],
                "human_reviewed": finding['human_reviewed'],
                "evidence_count": finding['evidence_count']
            }
            for finding in findings
        ]

    # =========================================================================
    # REPORT WORKFLOW
    # =========================================================================

    async def generate_assessment_report(
        self,
        c3pao_assessment_id: str,
        report_type: str = "final"
    ) -> Dict[str, Any]:
        """
        Generate C3PAO assessment report.

        Args:
            c3pao_assessment_id: C3PAO assessment UUID
            report_type: Report type (draft, final)

        Returns:
            Report generation details
        """
        # Get assessment details
        assessment = await self.conn.fetchrow(
            """
            SELECT
                ca.id, ca.assessment_id, ca.client_organization_id,
                ca.c3pao_organization_id, ca.current_phase,
                a.name as assessment_name, a.cmmc_level,
                o.name as client_name
            FROM c3pao_assessments ca
            JOIN assessments a ON ca.assessment_id = a.id
            JOIN organizations o ON ca.client_organization_id = o.id
            WHERE ca.id = $1
            """,
            c3pao_assessment_id
        )

        if not assessment:
            raise ValueError("C3PAO assessment not found")

        # Generate report (placeholder)
        report_filename = f"c3pao_report_{c3pao_assessment_id}_{report_type}.pdf"

        # Create report record
        report_id = await self.conn.fetchval(
            """
            INSERT INTO c3pao_reports
            (c3pao_assessment_id, report_type, filename, status)
            VALUES ($1, $2, $3, 'draft')
            RETURNING id
            """,
            c3pao_assessment_id,
            report_type,
            report_filename
        )

        logger.info(f"C3PAO report generated: {report_id}")

        return {
            "report_id": str(report_id),
            "c3pao_assessment_id": c3pao_assessment_id,
            "report_type": report_type,
            "filename": report_filename,
            "status": "draft"
        }

    async def approve_report(
        self,
        report_id: str,
        approved_by: str
    ) -> Dict[str, Any]:
        """Approve C3PAO assessment report."""
        await self.conn.execute(
            """
            UPDATE c3pao_reports
            SET status = 'approved', approved_by = $1, approved_at = NOW()
            WHERE id = $2
            """,
            approved_by,
            report_id
        )

        logger.info(f"C3PAO report approved: {report_id}")

        return {
            "report_id": report_id,
            "status": "approved",
            "approved_at": datetime.utcnow().isoformat()
        }

    # =========================================================================
    # CLIENT COMMUNICATION
    # =========================================================================

    async def send_client_update(
        self,
        c3pao_assessment_id: str,
        subject: str,
        message: str,
        sent_by: str
    ) -> Dict[str, Any]:
        """Send update to client."""
        communication_id = await self.conn.fetchval(
            """
            INSERT INTO c3pao_communications
            (c3pao_assessment_id, subject, message, sent_by, sent_at)
            VALUES ($1, $2, $3, $4, NOW())
            RETURNING id
            """,
            c3pao_assessment_id,
            subject,
            message,
            sent_by
        )

        # In production, send actual email

        logger.info(f"Client update sent: {communication_id}")

        return {
            "communication_id": str(communication_id),
            "subject": subject,
            "sent_at": datetime.utcnow().isoformat()
        }
