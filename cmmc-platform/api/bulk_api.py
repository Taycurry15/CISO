"""
Bulk Operations API

RESTful API endpoints for batch processing operations:
- Bulk control status updates
- Bulk evidence upload (ZIP files)
- Excel import/export for control findings
- Mass control assignments
- Batch AI analysis requests

Designed for high-volume operations with progress tracking.
"""

import logging
from typing import List, Optional
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncpg

from services.bulk_service import BulkService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/bulk", tags=["bulk-operations"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ControlUpdate(BaseModel):
    """Single control update"""
    control_id: str = Field(..., description="Control ID (e.g., AC.L2-3.1.1)")
    status: str = Field(..., description="Control status")
    implementation_status: Optional[str] = Field(None, description="Implementation status")
    implementation_narrative: Optional[str] = Field(None, description="Implementation narrative")
    test_results: Optional[str] = Field(None, description="Test results")
    findings: Optional[str] = Field(None, description="Findings")
    recommendations: Optional[str] = Field(None, description="Recommendations")
    risk_level: Optional[str] = Field(None, description="Risk level")
    residual_risk: Optional[str] = Field(None, description="Residual risk")


class BulkControlUpdateRequest(BaseModel):
    """Bulk control update request"""
    assessment_id: str = Field(..., description="Assessment ID")
    updates: List[ControlUpdate] = Field(..., description="List of control updates")


class MassAssignmentRequest(BaseModel):
    """Mass assignment request"""
    assessment_id: str = Field(..., description="Assessment ID")
    control_ids: List[str] = Field(..., description="Control IDs to assign")
    assigned_to: str = Field(..., description="User ID to assign to")


class BulkOperationResponse(BaseModel):
    """Bulk operation response"""
    operation: str
    total: int
    success: int
    failed: int
    errors: List[dict]
    status: str


class BulkEvidenceUploadResponse(BulkOperationResponse):
    """Bulk evidence upload response"""
    uploaded_files: List[dict]


# ============================================================================
# Dependencies
# ============================================================================

async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    # This should be injected from main app
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Database connection not configured"
    )


async def get_bulk_service(db_pool: asyncpg.Pool = Depends(get_db_pool)) -> BulkService:
    """Get bulk service instance"""
    return BulkService(db_pool)


async def get_current_user_id():
    """
    Get current authenticated user ID

    TODO: Replace with actual auth middleware
    """
    # Placeholder - should come from JWT token
    return "user-123"


# ============================================================================
# Bulk Control Update Endpoints
# ============================================================================

@router.post("/controls/update", response_model=BulkOperationResponse)
async def bulk_update_controls(
    request: BulkControlUpdateRequest,
    user_id: str = Depends(get_current_user_id),
    service: BulkService = Depends(get_bulk_service)
):
    """
    Update multiple control findings at once

    Allows batch updates of control status, narratives, findings, etc.
    Useful for bulk edits after assessments or when applying templates.

    **Time Savings:** 2-5 hours for 50+ controls

    **Request Body:**
    ```json
    {
        "assessment_id": "uuid",
        "updates": [
            {
                "control_id": "AC.L2-3.1.1",
                "status": "Met",
                "implementation_narrative": "Access control implemented",
                "risk_level": "Low"
            },
            {
                "control_id": "AC.L2-3.1.2",
                "status": "Partially Met",
                "findings": "Some gaps identified"
            }
        ]
    }
    ```

    **Response:**
    ```json
    {
        "operation": "control_update",
        "total": 2,
        "success": 2,
        "failed": 0,
        "errors": [],
        "status": "completed"
    }
    ```
    """
    try:
        updates = [update.dict(exclude_none=True) for update in request.updates]

        result = await service.bulk_update_control_status(
            assessment_id=request.assessment_id,
            updates=updates,
            updated_by=user_id
        )

        logger.info(
            f"Bulk control update: {result['success']}/{result['total']} "
            f"successful for assessment {request.assessment_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Bulk control update failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk update failed: {str(e)}"
        )


# ============================================================================
# Bulk Evidence Upload Endpoints
# ============================================================================

@router.post("/evidence/upload-zip", response_model=BulkEvidenceUploadResponse)
async def bulk_upload_evidence_zip(
    assessment_id: str = Query(..., description="Assessment ID"),
    organization_id: str = Query(..., description="Organization ID"),
    evidence_type: str = Query(..., description="Evidence type"),
    control_ids: Optional[str] = Query(None, description="Comma-separated control IDs"),
    zip_file: UploadFile = File(..., description="ZIP file with evidence"),
    user_id: str = Depends(get_current_user_id),
    service: BulkService = Depends(get_bulk_service)
):
    """
    Upload multiple evidence files from a ZIP archive

    Automatically extracts and processes all files in the ZIP.
    Optionally links all evidence to specified controls.

    **Time Savings:** 1-2 hours for 20+ files

    **Query Parameters:**
    - `assessment_id`: Assessment UUID
    - `organization_id`: Organization UUID
    - `evidence_type`: Policy, Procedure, Configuration, Screenshot, Log, etc.
    - `control_ids`: Optional comma-separated control IDs (e.g., "AC.L2-3.1.1,AC.L2-3.1.2")

    **File Upload:**
    - Upload a ZIP file containing evidence documents
    - Supported formats: PDF, DOCX, XLSX, PNG, JPG, TXT, etc.
    - Maximum file size: 100MB per ZIP

    **Response:**
    ```json
    {
        "operation": "evidence_upload",
        "total": 15,
        "success": 15,
        "failed": 0,
        "errors": [],
        "uploaded_files": [
            {
                "id": "uuid",
                "file_name": "access_control_policy.pdf",
                "file_size": 245678,
                "file_path": "/var/cmmc/evidence/org/assessment/uuid_file.pdf"
            }
        ],
        "status": "completed"
    }
    ```
    """
    try:
        # Validate ZIP file
        if not zip_file.filename.endswith('.zip'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be a ZIP archive"
            )

        # Parse control IDs
        control_id_list = None
        if control_ids:
            control_id_list = [cid.strip() for cid in control_ids.split(',')]

        # Read ZIP file
        zip_content = await zip_file.read()
        zip_stream = BytesIO(zip_content)

        # Process upload
        result = await service.bulk_upload_evidence_zip(
            assessment_id=assessment_id,
            organization_id=organization_id,
            zip_file=zip_stream,
            evidence_type=evidence_type,
            control_ids=control_id_list,
            uploaded_by=user_id
        )

        logger.info(
            f"Bulk evidence upload: {result['success']}/{result['total']} "
            f"files uploaded for assessment {assessment_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Bulk evidence upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bulk upload failed: {str(e)}"
        )


# ============================================================================
# Excel Import/Export Endpoints
# ============================================================================

@router.get("/controls/export-excel")
async def export_controls_to_excel(
    assessment_id: str = Query(..., description="Assessment ID"),
    service: BulkService = Depends(get_bulk_service)
):
    """
    Export control findings to Excel workbook

    Generates a formatted Excel file with all control findings.
    Useful for offline review, collaboration, and reporting.

    **Time Savings:** 30 minutes vs manual data entry

    **Query Parameters:**
    - `assessment_id`: Assessment UUID

    **Response:**
    - Excel file download (.xlsx)
    - Includes all control findings with:
      - Control ID, Domain, Title
      - Status, Implementation Status
      - Narratives, Findings, Recommendations
      - Risk Level, Assignment
      - Assessment method completion
      - AI confidence score
      - Last updated timestamp

    **Excel Format:**
    - Sheet 1: Control Findings (with color-coded headers)
    - Sheet 2: Metadata (assessment info and export date)
    - Frozen header row for easy scrolling
    - Optimized column widths
    """
    try:
        excel_file = await service.export_findings_to_excel(assessment_id)

        logger.info(f"Excel export generated for assessment {assessment_id}")

        return StreamingResponse(
            excel_file,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=assessment_{assessment_id}_findings.xlsx"
            }
        )

    except Exception as e:
        logger.error(f"Excel export failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Excel export failed: {str(e)}"
        )


@router.post("/controls/import-excel", response_model=BulkOperationResponse)
async def import_controls_from_excel(
    assessment_id: str = Query(..., description="Assessment ID"),
    excel_file: UploadFile = File(..., description="Excel file with control findings"),
    user_id: str = Depends(get_current_user_id),
    service: BulkService = Depends(get_bulk_service)
):
    """
    Import control findings from Excel workbook

    Batch import control findings from an Excel file.
    Useful for bulk updates from external sources or templates.

    **Time Savings:** 3-5 hours for 100+ controls

    **Query Parameters:**
    - `assessment_id`: Assessment UUID

    **File Upload:**
    - Upload Excel file (.xlsx)
    - Must match export format:
      - Column A: Control ID (required)
      - Column D: Status (required)
      - Column E: Implementation Status
      - Column F: Implementation Narrative
      - Column G: Test Results
      - Column H: Findings
      - Column I: Recommendations
      - Column J: Risk Level

    **Response:**
    ```json
    {
        "operation": "excel_import",
        "total": 110,
        "success": 108,
        "failed": 2,
        "errors": [
            {
                "row": 5,
                "error": "Invalid control ID"
            }
        ],
        "status": "partial"
    }
    ```
    """
    try:
        # Validate Excel file
        if not excel_file.filename.endswith(('.xlsx', '.xls')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File must be an Excel workbook (.xlsx or .xls)"
            )

        # Read Excel file
        excel_content = await excel_file.read()
        excel_stream = BytesIO(excel_content)

        # Process import
        result = await service.import_findings_from_excel(
            assessment_id=assessment_id,
            excel_file=excel_stream,
            updated_by=user_id
        )

        logger.info(
            f"Excel import: {result['success']}/{result['total']} "
            f"controls imported for assessment {assessment_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Excel import failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Excel import failed: {str(e)}"
        )


# ============================================================================
# Mass Assignment Endpoints
# ============================================================================

@router.post("/controls/assign", response_model=BulkOperationResponse)
async def mass_assign_controls(
    request: MassAssignmentRequest,
    user_id: str = Depends(get_current_user_id),
    service: BulkService = Depends(get_bulk_service)
):
    """
    Assign multiple controls to a user

    Batch assignment of controls to assessors or reviewers.
    Useful for workload distribution and team coordination.

    **Time Savings:** 15-30 minutes for 50+ controls

    **Request Body:**
    ```json
    {
        "assessment_id": "uuid",
        "control_ids": [
            "AC.L2-3.1.1",
            "AC.L2-3.1.2",
            "AC.L2-3.1.3"
        ],
        "assigned_to": "user-uuid"
    }
    ```

    **Response:**
    ```json
    {
        "operation": "mass_assignment",
        "total": 3,
        "success": 3,
        "failed": 0,
        "errors": [],
        "status": "completed"
    }
    ```
    """
    try:
        result = await service.mass_assign_controls(
            assessment_id=request.assessment_id,
            control_ids=request.control_ids,
            assigned_to=request.assigned_to,
            updated_by=user_id
        )

        logger.info(
            f"Mass assignment: {result['success']}/{result['total']} "
            f"controls assigned for assessment {request.assessment_id}"
        )

        return result

    except Exception as e:
        logger.error(f"Mass assignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Mass assignment failed: {str(e)}"
        )


# ============================================================================
# Convenience Endpoints
# ============================================================================

@router.post("/controls/assign-by-domain", response_model=BulkOperationResponse)
async def assign_controls_by_domain(
    assessment_id: str = Query(..., description="Assessment ID"),
    domain: str = Query(..., description="Domain (AC, AT, AU, etc.)"),
    assigned_to: str = Query(..., description="User ID to assign to"),
    user_id: str = Depends(get_current_user_id),
    service: BulkService = Depends(get_bulk_service)
):
    """
    Assign all controls in a domain to a user

    Convenience endpoint for domain-based assignments.

    **Time Savings:** 5-10 minutes

    **Query Parameters:**
    - `assessment_id`: Assessment UUID
    - `domain`: Domain code (AC, AT, AU, CA, CM, IA, IR, MA, MP, PE, PS, RA, SA, SC, SI)
    - `assigned_to`: User UUID

    **Example:**
    ```
    POST /bulk/controls/assign-by-domain?assessment_id=uuid&domain=AC&assigned_to=user-uuid
    ```
    """
    try:
        # Get all control IDs for domain
        async with service.db_pool.acquire() as conn:
            control_rows = await conn.fetch("""
                SELECT id FROM cmmc_controls
                WHERE domain = $1 AND level = 2
                ORDER BY id
            """, domain.upper())

        control_ids = [row['id'] for row in control_rows]

        if not control_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No controls found for domain {domain}"
            )

        # Assign controls
        result = await service.mass_assign_controls(
            assessment_id=assessment_id,
            control_ids=control_ids,
            assigned_to=assigned_to,
            updated_by=user_id
        )

        logger.info(
            f"Domain assignment: {result['success']}/{result['total']} "
            f"{domain} controls assigned for assessment {assessment_id}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Domain assignment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Domain assignment failed: {str(e)}"
        )


@router.post("/controls/mark-na-by-domain", response_model=BulkOperationResponse)
async def mark_domain_not_applicable(
    assessment_id: str = Query(..., description="Assessment ID"),
    domain: str = Query(..., description="Domain (AC, AT, AU, etc.)"),
    user_id: str = Depends(get_current_user_id),
    service: BulkService = Depends(get_bulk_service)
):
    """
    Mark all controls in a domain as Not Applicable

    Convenience endpoint for excluding entire domains from scope.

    **Time Savings:** 5-10 minutes

    **Query Parameters:**
    - `assessment_id`: Assessment UUID
    - `domain`: Domain code to mark as N/A

    **Example:**
    ```
    POST /bulk/controls/mark-na-by-domain?assessment_id=uuid&domain=PE
    ```
    """
    try:
        # Get all control IDs for domain
        async with service.db_pool.acquire() as conn:
            control_rows = await conn.fetch("""
                SELECT id FROM cmmc_controls
                WHERE domain = $1 AND level = 2
                ORDER BY id
            """, domain.upper())

        control_ids = [row['id'] for row in control_rows]

        if not control_ids:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No controls found for domain {domain}"
            )

        # Create updates
        updates = [
            {
                'control_id': control_id,
                'status': 'Not Applicable',
                'implementation_narrative': f'{domain} domain not in scope'
            }
            for control_id in control_ids
        ]

        # Bulk update
        result = await service.bulk_update_control_status(
            assessment_id=assessment_id,
            updates=updates,
            updated_by=user_id
        )

        logger.info(
            f"Domain N/A marking: {result['success']}/{result['total']} "
            f"{domain} controls marked N/A for assessment {assessment_id}"
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Domain N/A marking failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Domain N/A marking failed: {str(e)}"
        )
