"""
Multi-Tenant Onboarding Workflow
=================================
Automated onboarding process for new organizations and users.

Features:
- Organization registration
- Initial assessment creation
- User provisioning
- Integration setup
- Configuration templates
- Welcome emails and documentation
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field
from enum import Enum
import asyncpg
import logging
import json

logger = logging.getLogger(__name__)


class CMMCLevel(int, Enum):
    """CMMC certification levels."""
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3


class OrganizationType(str, Enum):
    """Organization type classification."""
    PRIME_CONTRACTOR = "prime_contractor"
    SUBCONTRACTOR = "subcontractor"
    OSC = "osc"  # Other Service Contractor
    SUPPLIER = "supplier"


class OnboardingStatus(str, Enum):
    """Onboarding workflow status."""
    INITIATED = "initiated"
    ORG_CREATED = "org_created"
    USERS_CREATED = "users_created"
    ASSESSMENT_CREATED = "assessment_created"
    INTEGRATIONS_CONFIGURED = "integrations_configured"
    COMPLETED = "completed"
    FAILED = "failed"


class OrganizationOnboardingRequest(BaseModel):
    """Organization onboarding request."""
    # Organization details
    organization_name: str = Field(..., min_length=1, max_length=255)
    duns_number: Optional[str] = Field(None, max_length=13)
    cage_code: Optional[str] = Field(None, max_length=5)
    organization_type: OrganizationType

    # Compliance details
    cmmc_level: CMMCLevel
    target_certification_date: Optional[date] = None
    current_authorization: Optional[str] = None  # FedRAMP, StateRAMP, etc.

    # Primary contact
    admin_email: EmailStr
    admin_name: str
    admin_password: str

    # Additional settings
    enable_integrations: bool = False
    integration_configs: Optional[Dict[str, Any]] = None
    custom_controls: Optional[List[str]] = None


class OnboardingResponse(BaseModel):
    """Onboarding workflow response."""
    onboarding_id: str
    organization_id: str
    status: OnboardingStatus
    created_at: str
    steps_completed: List[str]
    next_steps: List[str]
    admin_user_id: Optional[str] = None
    assessment_id: Optional[str] = None
    access_url: Optional[str] = None


class OnboardingWorkflow:
    """
    Multi-tenant onboarding workflow manager.

    Orchestrates the complete onboarding process for new organizations.
    """

    def __init__(self, conn: asyncpg.Connection):
        """
        Initialize onboarding workflow.

        Args:
            conn: Database connection
        """
        self.conn = conn

    async def start_onboarding(
        self,
        request: OrganizationOnboardingRequest
    ) -> OnboardingResponse:
        """
        Start the onboarding workflow.

        Args:
            request: Onboarding request details

        Returns:
            OnboardingResponse with workflow status
        """
        logger.info(f"Starting onboarding for organization: {request.organization_name}")

        # Create onboarding record
        onboarding_id = await self.conn.fetchval(
            """
            INSERT INTO onboarding_workflows
            (organization_name, status, request_data)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            request.organization_name,
            OnboardingStatus.INITIATED.value,
            json.dumps(request.dict())
        )

        steps_completed = []

        try:
            # Step 1: Create organization
            org_id = await self._create_organization(request)
            steps_completed.append("organization_created")

            await self._update_onboarding_status(
                onboarding_id,
                OnboardingStatus.ORG_CREATED,
                {"organization_id": str(org_id)}
            )

            # Step 2: Create admin user
            admin_user_id = await self._create_admin_user(request, org_id)
            steps_completed.append("admin_user_created")

            await self._update_onboarding_status(
                onboarding_id,
                OnboardingStatus.USERS_CREATED,
                {"admin_user_id": str(admin_user_id)}
            )

            # Step 3: Create initial assessment
            assessment_id = await self._create_initial_assessment(request, org_id)
            steps_completed.append("assessment_created")

            await self._update_onboarding_status(
                onboarding_id,
                OnboardingStatus.ASSESSMENT_CREATED,
                {"assessment_id": str(assessment_id)}
            )

            # Step 4: Configure integrations (if enabled)
            if request.enable_integrations and request.integration_configs:
                await self._configure_integrations(org_id, request.integration_configs)
                steps_completed.append("integrations_configured")

                await self._update_onboarding_status(
                    onboarding_id,
                    OnboardingStatus.INTEGRATIONS_CONFIGURED,
                    {}
                )

            # Step 5: Complete onboarding
            await self._update_onboarding_status(
                onboarding_id,
                OnboardingStatus.COMPLETED,
                {
                    "completed_at": datetime.utcnow().isoformat(),
                    "steps_completed": steps_completed
                }
            )

            logger.info(f"Onboarding completed for organization: {request.organization_name}")

            return OnboardingResponse(
                onboarding_id=str(onboarding_id),
                organization_id=str(org_id),
                status=OnboardingStatus.COMPLETED,
                created_at=datetime.utcnow().isoformat(),
                steps_completed=steps_completed,
                next_steps=[
                    "Log in with admin credentials",
                    "Upload initial evidence documents",
                    "Configure additional users",
                    "Schedule assessment kickoff"
                ],
                admin_user_id=str(admin_user_id),
                assessment_id=str(assessment_id),
                access_url=f"https://platform.example.com/org/{org_id}"
            )

        except Exception as e:
            logger.error(f"Onboarding failed: {str(e)}")

            await self._update_onboarding_status(
                onboarding_id,
                OnboardingStatus.FAILED,
                {"error": str(e)}
            )

            raise

    async def _create_organization(
        self,
        request: OrganizationOnboardingRequest
    ) -> str:
        """Create organization record."""
        org_id = await self.conn.fetchval(
            """
            INSERT INTO organizations
            (name, duns_number, cage_code, cmmc_level, target_certification_date,
             organization_type, current_authorization, active)
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE)
            RETURNING id
            """,
            request.organization_name,
            request.duns_number,
            request.cage_code,
            request.cmmc_level.value,
            request.target_certification_date,
            request.organization_type.value,
            request.current_authorization
        )

        logger.info(f"Organization created: {org_id}")
        return org_id

    async def _create_admin_user(
        self,
        request: OrganizationOnboardingRequest,
        org_id: str
    ) -> str:
        """Create admin user for the organization."""
        from auth import hash_password

        password_hash = hash_password(request.admin_password)

        user_id = await self.conn.fetchval(
            """
            INSERT INTO users
            (email, password_hash, full_name, organization_id, role, active)
            VALUES ($1, $2, $3, $4, 'admin', TRUE)
            RETURNING id
            """,
            request.admin_email.lower(),
            password_hash,
            request.admin_name,
            org_id
        )

        logger.info(f"Admin user created: {user_id} for org {org_id}")
        return user_id

    async def _create_initial_assessment(
        self,
        request: OrganizationOnboardingRequest,
        org_id: str
    ) -> str:
        """Create initial CMMC assessment."""
        # Generate assessment name
        assessment_name = f"CMMC Level {request.cmmc_level.value} Assessment - {datetime.utcnow().year}"

        assessment_id = await self.conn.fetchval(
            """
            INSERT INTO assessments
            (organization_id, name, cmmc_level, assessment_type, status, scope)
            VALUES ($1, $2, $3, 'self', 'planning', $4)
            RETURNING id
            """,
            org_id,
            assessment_name,
            request.cmmc_level.value,
            json.dumps({
                "description": "Initial self-assessment",
                "target_date": request.target_certification_date.isoformat() if request.target_certification_date else None,
                "created_during_onboarding": True
            })
        )

        # Create initial control findings (all as "Not Assessed")
        controls = await self.conn.fetch(
            """
            SELECT id FROM controls
            WHERE framework = 'NIST 800-171'
            AND ($1 = 1 OR level <= $1)
            """,
            request.cmmc_level.value
        )

        for control in controls:
            await self.conn.execute(
                """
                INSERT INTO control_findings
                (assessment_id, control_id, status, assessor_narrative)
                VALUES ($1, $2, 'Not Assessed', 'Pending initial assessment')
                """,
                assessment_id,
                control['id']
            )

        logger.info(f"Assessment created: {assessment_id} with {len(controls)} controls")
        return assessment_id

    async def _configure_integrations(
        self,
        org_id: str,
        integration_configs: Dict[str, Any]
    ) -> None:
        """Configure integrations for the organization."""
        # Store integration credentials (encrypted in production)
        for integration_type, config in integration_configs.items():
            await self.conn.execute(
                """
                INSERT INTO integration_credentials
                (organization_id, integration_type, credentials, active)
                VALUES ($1, $2, $3, TRUE)
                """,
                org_id,
                integration_type,
                json.dumps(config)
            )

        logger.info(f"Integrations configured for org {org_id}: {list(integration_configs.keys())}")

    async def _update_onboarding_status(
        self,
        onboarding_id: str,
        status: OnboardingStatus,
        metadata: Dict[str, Any]
    ) -> None:
        """Update onboarding workflow status."""
        await self.conn.execute(
            """
            UPDATE onboarding_workflows
            SET status = $1,
                metadata = COALESCE(metadata, '{}'::jsonb) || $2::jsonb,
                updated_at = NOW()
            WHERE id = $3
            """,
            status.value,
            json.dumps(metadata),
            onboarding_id
        )

    async def get_onboarding_status(
        self,
        onboarding_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get onboarding workflow status.

        Args:
            onboarding_id: Onboarding workflow ID

        Returns:
            Onboarding status details
        """
        workflow = await self.conn.fetchrow(
            """
            SELECT id, organization_name, status, metadata, created_at, updated_at
            FROM onboarding_workflows
            WHERE id = $1
            """,
            onboarding_id
        )

        if not workflow:
            return None

        return {
            "onboarding_id": str(workflow['id']),
            "organization_name": workflow['organization_name'],
            "status": workflow['status'],
            "metadata": workflow['metadata'],
            "created_at": workflow['created_at'].isoformat(),
            "updated_at": workflow['updated_at'].isoformat()
        }


# =============================================================================
# ORGANIZATION TEMPLATES
# =============================================================================

class OrganizationTemplate:
    """Predefined organization templates for common scenarios."""

    @staticmethod
    def defense_prime_contractor(
        name: str,
        duns: str,
        cage: str,
        admin_email: str,
        admin_name: str,
        admin_password: str
    ) -> OrganizationOnboardingRequest:
        """Template for defense prime contractors."""
        return OrganizationOnboardingRequest(
            organization_name=name,
            duns_number=duns,
            cage_code=cage,
            organization_type=OrganizationType.PRIME_CONTRACTOR,
            cmmc_level=CMMCLevel.LEVEL_2,
            target_certification_date=date.today().replace(year=date.today().year + 1),
            admin_email=admin_email,
            admin_name=admin_name,
            admin_password=admin_password,
            enable_integrations=True,
            integration_configs={
                "nessus": {"enabled": True},
                "splunk": {"enabled": True}
            }
        )

    @staticmethod
    def subcontractor(
        name: str,
        admin_email: str,
        admin_name: str,
        admin_password: str,
        cmmc_level: CMMCLevel = CMMCLevel.LEVEL_1
    ) -> OrganizationOnboardingRequest:
        """Template for subcontractors."""
        return OrganizationOnboardingRequest(
            organization_name=name,
            organization_type=OrganizationType.SUBCONTRACTOR,
            cmmc_level=cmmc_level,
            admin_email=admin_email,
            admin_name=admin_name,
            admin_password=admin_password,
            enable_integrations=False
        )

    @staticmethod
    def cloud_service_provider(
        name: str,
        admin_email: str,
        admin_name: str,
        admin_password: str
    ) -> OrganizationOnboardingRequest:
        """Template for cloud service providers."""
        return OrganizationOnboardingRequest(
            organization_name=name,
            organization_type=OrganizationType.OSC,
            cmmc_level=CMMCLevel.LEVEL_2,
            current_authorization="FedRAMP Moderate",
            admin_email=admin_email,
            admin_name=admin_name,
            admin_password=admin_password,
            enable_integrations=True,
            integration_configs={
                "azure": {"enabled": True},
                "aws": {"enabled": True},
                "m365": {"enabled": True}
            }
        )
