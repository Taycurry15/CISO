"""
Assessment Workflow API
RESTful endpoints for managing CMMC assessments and evidence
"""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncpg

from services.assessment_service import (
    AssessmentService,
    AssessmentStatus,
    AssessmentType,
    AssessmentScope
)
from services.evidence_service import (
    EvidenceService,
    EvidenceType,
    AssessmentMethod,
    EvidenceMetadata
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assessments", tags=["assessments"])


# ===========================
# Request/Response Models
# ===========================

class CreateAssessmentRequest(BaseModel):
    """Request to create assessment"""
    organization_id: str = Field(description="Organization UUID")
    assessment_type: AssessmentType = Field(AssessmentType.INITIAL, description="Assessment type")

    # Scope
    cmmc_level: int = Field(2, ge=1, le=3, description="CMMC level (1-3)")
    domains: List[str] = Field(["ALL"], description="Domains to assess or ['ALL']")
    cloud_providers: List[str] = Field([], description="Cloud providers used (e.g., M365, Azure, AWS)")
    system_boundary: str = Field(description="System boundary description")
    exclusions: Optional[str] = Field(None, description="Scope exclusions")
    include_inherited: bool = Field(True, description="Include provider-inherited controls")

    # Team
    lead_assessor: Optional[str] = Field(None, description="Lead assessor name")
    team_members: List[str] = Field([], description="Team member names")

    # Timeline
    target_end_date: Optional[datetime] = Field(None, description="Target completion date")


class UpdateAssessmentStatusRequest(BaseModel):
    """Request to update assessment status"""
    status: AssessmentStatus = Field(description="New status")


class UpdateAssessmentScopeRequest(BaseModel):
    """Request to update assessment scope"""
    cmmc_level: Optional[int] = Field(None, ge=1, le=3)
    domains: Optional[List[str]] = None
    cloud_providers: Optional[List[str]] = None
    system_boundary: Optional[str] = None
    exclusions: Optional[str] = None
    include_inherited: Optional[bool] = None


class AssignTeamRequest(BaseModel):
    """Request to assign assessment team"""
    lead_assessor: Optional[str] = None
    team_members: Optional[List[str]] = None


class UploadEvidenceRequest(BaseModel):
    """Request to upload evidence"""
    title: str
    description: Optional[str] = None
    evidence_type: EvidenceType
    assessment_methods: List[AssessmentMethod]
    tags: List[str] = []
    link_to_controls: List[str] = []
    collected_by: str


class LinkEvidenceRequest(BaseModel):
    """Request to link evidence to control"""
    control_id: str


class AssessmentResponse(BaseModel):
    """Assessment response"""
    id: str
    organization_id: str
    organization_name: str
    assessment_type: str
    status: str
    start_date: Optional[str]
    target_end_date: Optional[str]
    end_date: Optional[str]
    lead_assessor: Optional[str]
    team_members: List[str]
    created_at: str


class AssessmentSummaryResponse(BaseModel):
    """Assessment summary response"""
    assessment: dict
    scope: dict
    progress: dict


# ===========================
# Dependency Injection
# ===========================

async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool (to be injected)"""
    raise NotImplementedError("Database pool dependency not configured")


async def get_assessment_service(
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> AssessmentService:
    """Get assessment service instance"""
    return AssessmentService(db_pool)


async def get_evidence_service(
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> EvidenceService:
    """Get evidence service instance"""
    return EvidenceService(db_pool)


# ===========================
# Assessment Endpoints
# ===========================

@router.post("", response_model=AssessmentResponse)
async def create_assessment(
    request: CreateAssessmentRequest,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    Create new CMMC assessment

    Creates a new assessment with defined scope, team, and timeline.
    Automatically initializes control findings for all in-scope controls.

    **Example:**
    ```json
    POST /api/v1/assessments
    {
      "organization_id": "uuid",
      "assessment_type": "Initial Assessment",
      "cmmc_level": 2,
      "domains": ["ALL"],
      "cloud_providers": ["Microsoft 365 GCC High", "Azure Government"],
      "system_boundary": "Cloud-based contract management system hosted in Azure Government",
      "exclusions": "Physical security controls handled by cloud provider",
      "include_inherited": true,
      "lead_assessor": "Jane Doe",
      "team_members": ["John Smith", "Bob Wilson"],
      "target_end_date": "2024-03-31T00:00:00Z"
    }
    ```
    """
    try:
        # Build scope
        scope = AssessmentScope(
            cmmc_level=request.cmmc_level,
            domains=request.domains,
            cloud_providers=request.cloud_providers,
            system_boundary=request.system_boundary,
            exclusions=request.exclusions,
            include_inherited=request.include_inherited
        )

        # Create assessment
        assessment_id = await service.create_assessment(
            organization_id=request.organization_id,
            assessment_type=request.assessment_type,
            scope=scope,
            lead_assessor=request.lead_assessor,
            team_members=request.team_members,
            target_end_date=request.target_end_date,
            created_by="api_user"  # Would come from auth context
        )

        # Get created assessment
        assessment = await service.get_assessment(assessment_id)

        return AssessmentResponse(
            id=str(assessment['id']),
            organization_id=str(assessment['organization_id']),
            organization_name=assessment['organization_name'],
            assessment_type=assessment['assessment_type'],
            status=assessment['status'],
            start_date=assessment['start_date'].isoformat() if assessment['start_date'] else None,
            target_end_date=assessment['target_end_date'].isoformat() if assessment['target_end_date'] else None,
            end_date=assessment['end_date'].isoformat() if assessment['end_date'] else None,
            lead_assessor=assessment['lead_assessor'],
            team_members=assessment['team_members'] or [],
            created_at=assessment['created_at'].isoformat()
        )

    except Exception as e:
        logger.error(f"Error creating assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create assessment: {str(e)}")


@router.get("", response_model=List[AssessmentResponse])
async def list_assessments(
    organization_id: Optional[str] = None,
    status: Optional[AssessmentStatus] = None,
    limit: int = 50,
    offset: int = 0,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    List assessments with optional filtering

    **Parameters:**
    - organization_id: Filter by organization
    - status: Filter by status (Draft, Scoping, In Progress, Review, Completed, Archived)
    - limit: Maximum results (default 50)
    - offset: Pagination offset (default 0)

    **Example:**
    ```
    GET /api/v1/assessments?status=In%20Progress&limit=10
    ```
    """
    try:
        assessments = await service.list_assessments(
            organization_id=organization_id,
            status=status,
            limit=limit,
            offset=offset
        )

        return [
            AssessmentResponse(
                id=str(a['id']),
                organization_id=str(a['organization_id']),
                organization_name=a['organization_name'],
                assessment_type=a['assessment_type'],
                status=a['status'],
                start_date=a['start_date'].isoformat() if a['start_date'] else None,
                target_end_date=a['target_end_date'].isoformat() if a['target_end_date'] else None,
                end_date=a['end_date'].isoformat() if a['end_date'] else None,
                lead_assessor=a['lead_assessor'],
                team_members=a['team_members'] or [],
                created_at=a['created_at'].isoformat()
            )
            for a in assessments
        ]

    except Exception as e:
        logger.error(f"Error listing assessments: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list assessments: {str(e)}")


@router.get("/{assessment_id}", response_model=AssessmentSummaryResponse)
async def get_assessment(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    Get assessment details and summary

    Returns comprehensive assessment information including:
    - Basic info (type, status, dates, team)
    - Scope configuration
    - Progress metrics (controls analyzed, completion %, confidence)

    **Example:**
    ```
    GET /api/v1/assessments/uuid
    {
      "assessment": {
        "id": "uuid",
        "organization_name": "Defense Contractor Inc.",
        "assessment_type": "Initial Assessment",
        "status": "In Progress",
        "start_date": "2024-01-15T00:00:00Z",
        "lead_assessor": "Jane Doe",
        "team_members": ["John Smith", "Bob Wilson"]
      },
      "scope": {
        "cmmc_level": 2,
        "domains": ["ALL"],
        "cloud_providers": ["Microsoft 365 GCC High"],
        "system_boundary": "Cloud-based contract management...",
        "include_inherited": true
      },
      "progress": {
        "total_controls": 110,
        "controls_analyzed": 85,
        "controls_met": 70,
        "controls_not_met": 10,
        "controls_partial": 5,
        "controls_na": 0,
        "evidence_collected": 142,
        "completion_percentage": 77.3,
        "avg_confidence_score": 0.82
      }
    }
    ```
    """
    try:
        summary = await service.get_assessment_summary(assessment_id)
        return AssessmentSummaryResponse(**summary)

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get assessment: {str(e)}")


@router.put("/{assessment_id}/status")
async def update_assessment_status(
    assessment_id: str,
    request: UpdateAssessmentStatusRequest,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    Update assessment status

    Valid status transitions:
    - Draft → Scoping → In Progress → Review → Completed
    - Any status → Archived (soft delete)

    **Example:**
    ```json
    PUT /api/v1/assessments/uuid/status
    {
      "status": "In Progress"
    }
    ```
    """
    try:
        await service.update_status(
            assessment_id=assessment_id,
            new_status=request.status,
            updated_by="api_user"
        )

        return {"success": True, "message": f"Status updated to {request.status.value}"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


@router.put("/{assessment_id}/scope")
async def update_assessment_scope(
    assessment_id: str,
    request: UpdateAssessmentScopeRequest,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    Update assessment scope

    Note: Scope can only be changed in Draft or Scoping status.
    Changing scope will reinitialize control findings.

    **Example:**
    ```json
    PUT /api/v1/assessments/uuid/scope
    {
      "cmmc_level": 2,
      "domains": ["AC", "IA", "SC"],
      "cloud_providers": ["Azure Government"],
      "system_boundary": "Updated boundary description",
      "include_inherited": true
    }
    ```
    """
    try:
        # Get current assessment to merge scope
        assessment = await service.get_assessment(assessment_id)
        if not assessment:
            raise HTTPException(status_code=404, detail="Assessment not found")

        # Parse current scope
        import json
        current_scope = json.loads(assessment['scope']) if isinstance(assessment['scope'], str) else assessment['scope']

        # Merge updates
        updated_scope = AssessmentScope(
            cmmc_level=request.cmmc_level or current_scope['cmmc_level'],
            domains=request.domains or current_scope['domains'],
            cloud_providers=request.cloud_providers if request.cloud_providers is not None else current_scope['cloud_providers'],
            system_boundary=request.system_boundary or current_scope['system_boundary'],
            exclusions=request.exclusions if request.exclusions is not None else current_scope.get('exclusions'),
            include_inherited=request.include_inherited if request.include_inherited is not None else current_scope['include_inherited']
        )

        await service.update_scope(
            assessment_id=assessment_id,
            scope=updated_scope,
            updated_by="api_user"
        )

        return {"success": True, "message": "Scope updated successfully"}

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating scope: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update scope: {str(e)}")


@router.put("/{assessment_id}/team")
async def assign_assessment_team(
    assessment_id: str,
    request: AssignTeamRequest,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    Assign assessment team

    **Example:**
    ```json
    PUT /api/v1/assessments/uuid/team
    {
      "lead_assessor": "Jane Doe, C3PAO",
      "team_members": ["John Smith", "Bob Wilson", "Alice Johnson"]
    }
    ```
    """
    try:
        await service.assign_team(
            assessment_id=assessment_id,
            lead_assessor=request.lead_assessor,
            team_members=request.team_members,
            updated_by="api_user"
        )

        return {"success": True, "message": "Team assigned successfully"}

    except Exception as e:
        logger.error(f"Error assigning team: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to assign team: {str(e)}")


@router.delete("/{assessment_id}")
async def delete_assessment(
    assessment_id: str,
    service: AssessmentService = Depends(get_assessment_service)
):
    """
    Delete assessment (soft delete by archiving)

    **Example:**
    ```
    DELETE /api/v1/assessments/uuid
    ```
    """
    try:
        await service.delete_assessment(
            assessment_id=assessment_id,
            deleted_by="api_user"
        )

        return {"success": True, "message": "Assessment archived successfully"}

    except Exception as e:
        logger.error(f"Error deleting assessment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete assessment: {str(e)}")


# ===========================
# Evidence Endpoints
# ===========================

@router.post("/{assessment_id}/evidence")
async def upload_evidence(
    assessment_id: str,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    evidence_type: EvidenceType = Form(...),
    assessment_methods: str = Form(...),  # JSON string
    tags: str = Form("[]"),  # JSON string
    link_to_controls: str = Form("[]"),  # JSON string
    collected_by: str = Form(...),
    service: EvidenceService = Depends(get_evidence_service)
):
    """
    Upload evidence file

    **Form Data:**
    - file: Evidence file
    - title: Evidence title
    - description: Evidence description
    - evidence_type: Type (Document, Screenshot, Configuration, etc.)
    - assessment_methods: JSON array of methods ["Examine", "Interview", "Test"]
    - tags: JSON array of tags
    - link_to_controls: JSON array of control IDs to link
    - collected_by: Person who collected evidence

    **Example:**
    ```
    POST /api/v1/assessments/uuid/evidence
    Form Data:
      file: access_control_policy.pdf
      title: "Access Control Policy"
      evidence_type: "Policy"
      assessment_methods: ["Examine"]
      tags: ["access-control", "policy"]
      link_to_controls: ["AC.L2-3.1.1", "AC.L2-3.1.2"]
      collected_by: "Jane Doe"
    ```
    """
    try:
        import json

        # Parse JSON fields
        methods = [AssessmentMethod(m) for m in json.loads(assessment_methods)]
        tags_list = json.loads(tags)
        controls = json.loads(link_to_controls)

        # Build metadata
        metadata = EvidenceMetadata(
            title=title,
            description=description,
            evidence_type=evidence_type,
            assessment_methods=methods,
            tags=tags_list,
            collection_date=datetime.utcnow(),
            collected_by=collected_by
        )

        # Upload evidence
        evidence_id = await service.upload_evidence(
            assessment_id=assessment_id,
            file_data=file.file,
            file_name=file.filename,
            metadata=metadata,
            link_to_controls=controls
        )

        return {
            "success": True,
            "evidence_id": evidence_id,
            "message": f"Evidence '{title}' uploaded successfully"
        }

    except Exception as e:
        logger.error(f"Error uploading evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to upload evidence: {str(e)}")


@router.get("/{assessment_id}/evidence")
async def list_evidence(
    assessment_id: str,
    evidence_type: Optional[EvidenceType] = None,
    control_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    service: EvidenceService = Depends(get_evidence_service)
):
    """
    List evidence for assessment

    **Parameters:**
    - evidence_type: Filter by type
    - control_id: Filter by linked control
    - limit: Maximum results
    - offset: Pagination offset

    **Example:**
    ```
    GET /api/v1/assessments/uuid/evidence?control_id=AC.L2-3.1.1
    ```
    """
    try:
        evidence = await service.list_evidence(
            assessment_id=assessment_id,
            evidence_type=evidence_type,
            control_id=control_id,
            limit=limit,
            offset=offset
        )

        return evidence

    except Exception as e:
        logger.error(f"Error listing evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list evidence: {str(e)}")


@router.get("/{assessment_id}/evidence/statistics")
async def get_evidence_statistics(
    assessment_id: str,
    service: EvidenceService = Depends(get_evidence_service)
):
    """
    Get evidence statistics for assessment

    **Example:**
    ```
    GET /api/v1/assessments/uuid/evidence/statistics
    {
      "total_evidence": 142,
      "evidence_types": 6,
      "total_size_bytes": 52428800,
      "controls_with_evidence": 95,
      "by_type": {
        "Document": 45,
        "Screenshot": 38,
        "Configuration": 25,
        "Log": 20,
        "Policy": 10,
        "Diagram": 4
      },
      "by_method": {
        "Examine": 85,
        "Interview": 32,
        "Test": 25
      }
    }
    ```
    """
    try:
        stats = await service.get_evidence_statistics(assessment_id)
        return stats

    except Exception as e:
        logger.error(f"Error getting evidence statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")


@router.post("/{assessment_id}/evidence/{evidence_id}/link")
async def link_evidence_to_control(
    assessment_id: str,
    evidence_id: str,
    request: LinkEvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service)
):
    """
    Link evidence to a control

    **Example:**
    ```json
    POST /api/v1/assessments/uuid/evidence/uuid/link
    {
      "control_id": "AC.L2-3.1.1"
    }
    ```
    """
    try:
        await service.link_evidence_to_control(
            evidence_id=evidence_id,
            control_id=request.control_id,
            assessment_id=assessment_id
        )

        return {"success": True, "message": f"Evidence linked to {request.control_id}"}

    except Exception as e:
        logger.error(f"Error linking evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to link evidence: {str(e)}")


@router.delete("/{assessment_id}/evidence/{evidence_id}/link/{control_id}")
async def unlink_evidence_from_control(
    assessment_id: str,
    evidence_id: str,
    control_id: str,
    service: EvidenceService = Depends(get_evidence_service)
):
    """
    Unlink evidence from a control

    **Example:**
    ```
    DELETE /api/v1/assessments/uuid/evidence/uuid/link/AC.L2-3.1.1
    ```
    """
    try:
        await service.unlink_evidence_from_control(
            evidence_id=evidence_id,
            control_id=control_id
        )

        return {"success": True, "message": f"Evidence unlinked from {control_id}"}

    except Exception as e:
        logger.error(f"Error unlinking evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to unlink evidence: {str(e)}")


@router.delete("/{assessment_id}/evidence/{evidence_id}")
async def delete_evidence(
    assessment_id: str,
    evidence_id: str,
    delete_file: bool = True,
    service: EvidenceService = Depends(get_evidence_service)
):
    """
    Delete evidence

    **Parameters:**
    - delete_file: Also delete the file from storage (default true)

    **Example:**
    ```
    DELETE /api/v1/assessments/uuid/evidence/uuid?delete_file=true
    ```
    """
    try:
        await service.delete_evidence(
            evidence_id=evidence_id,
            delete_file=delete_file
        )

        return {"success": True, "message": "Evidence deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting evidence: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to delete evidence: {str(e)}")
