"""
Report Generation API
RESTful endpoints for generating CMMC compliance reports (SSP, POA&M, etc.)
"""

import logging
from typing import Optional
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, EmailStr
import asyncpg

from services.ssp_generator import (
    SSPGenerator,
    SystemInfo,
    SSPMetadata,
    generate_ssp_for_assessment
)
from services.poam_generator import (
    POAMGenerator,
    POAMMetadata,
    generate_poam_for_assessment
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# ===========================
# Request/Response Models
# ===========================

class GenerateSSPRequest(BaseModel):
    """Request to generate SSP"""
    # System Information
    system_name: str = Field(description="Name of the information system")
    system_id: str = Field(description="Unique system identifier")
    system_type: str = Field(description="Type of system (e.g., 'Cloud-based SaaS', 'On-premise')")
    system_owner: str = Field(description="System owner name")
    system_owner_email: EmailStr = Field(description="System owner email")

    organization_name: str = Field(description="Organization name")
    organization_address: str = Field(description="Organization address")
    organization_phone: str = Field(description="Organization phone")
    organization_email: EmailStr = Field(description="Organization email")

    cmmc_level: int = Field(2, ge=1, le=3, description="CMMC level (1-3)")

    data_types: list[str] = Field(
        default=["CUI"],
        description="Types of data processed (e.g., CUI, PII)"
    )

    mission: str = Field(description="System mission/purpose")
    system_description: str = Field(description="Detailed system description")

    # Metadata
    version: str = Field(default="1.0", description="SSP version")
    prepared_by: str = Field(description="Name of person preparing SSP")
    reviewed_by: Optional[str] = Field(None, description="Name of reviewer")
    approved_by: Optional[str] = Field(None, description="Name of approver")
    classification: str = Field(default="CUI", description="Document classification")

    # Options
    include_provider_inheritance: bool = Field(
        True,
        description="Include cloud provider inheritance details"
    )
    generate_narratives: bool = Field(
        True,
        description="Use AI to generate control narratives"
    )


class GeneratePOAMRequest(BaseModel):
    """Request to generate POA&M"""
    system_name: str = Field(description="Name of the information system")
    organization: str = Field(description="Organization name")
    prepared_by: str = Field(description="Name of person preparing POA&M")
    version: str = Field(default="1.0", description="POA&M version")

    # Options
    generate_recommendations: bool = Field(
        True,
        description="Use AI to generate remediation recommendations"
    )
    auto_assign_risk: bool = Field(
        True,
        description="Automatically calculate risk levels"
    )


class ReportGenerationResponse(BaseModel):
    """Response from report generation"""
    success: bool
    message: str
    report_id: Optional[str] = None
    file_name: str
    file_size_bytes: int
    generation_time_seconds: float


class ReportListResponse(BaseModel):
    """Response listing available reports"""
    assessment_id: str
    reports: list[dict]


# ===========================
# Dependency Injection
# ===========================

async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool (to be injected)"""
    raise NotImplementedError("Database pool dependency not configured")


async def get_ssp_generator(
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> SSPGenerator:
    """Get SSP generator instance"""
    return SSPGenerator(db_pool)


async def get_poam_generator(
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> POAMGenerator:
    """Get POA&M generator instance"""
    return POAMGenerator(db_pool)


# ===========================
# API Endpoints
# ===========================

@router.post("/ssp/{assessment_id}", response_class=StreamingResponse)
async def generate_ssp(
    assessment_id: str,
    request: GenerateSSPRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Generate System Security Plan (SSP) for assessment

    Creates a comprehensive SSP document in DOCX format with:
    - System identification and description
    - Control implementation details
    - Provider inheritance information
    - Evidence references
    - AI-generated narratives

    **Parameters:**
    - assessment_id: UUID of the assessment
    - request: SSP generation parameters

    **Returns:**
    - DOCX file download

    **Example:**
    ```json
    POST /api/v1/reports/ssp/uuid
    {
      "system_name": "DoD Contract Management System",
      "system_id": "CMS-001",
      "system_type": "Cloud-based SaaS",
      "system_owner": "John Smith",
      "system_owner_email": "john.smith@example.com",
      "organization_name": "Defense Contractor Inc.",
      "organization_address": "123 Main St, Arlington, VA 22201",
      "organization_phone": "(703) 555-1234",
      "organization_email": "compliance@example.com",
      "cmmc_level": 2,
      "data_types": ["CUI", "Contract Data"],
      "mission": "Manage DoD contracts and CUI documentation",
      "system_description": "Cloud-based contract management system...",
      "prepared_by": "Jane Doe, ISSO"
    }
    ```

    **Response:**
    - Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
    - Content-Disposition: attachment; filename="SSP_{system_name}_{date}.docx"
    """
    try:
        start_time = datetime.utcnow()

        logger.info(f"Generating SSP for assessment {assessment_id}")

        # Verify assessment exists
        async with db_pool.acquire() as conn:
            assessment = await conn.fetchrow(
                "SELECT id, status FROM assessments WHERE id = $1",
                assessment_id
            )

            if not assessment:
                raise HTTPException(status_code=404, detail="Assessment not found")

        # Build system info
        system_info = SystemInfo(
            system_name=request.system_name,
            system_id=request.system_id,
            system_type=request.system_type,
            system_owner=request.system_owner,
            system_owner_email=request.system_owner_email,
            authorization_date=None,
            cmmc_level=request.cmmc_level,
            organization_name=request.organization_name,
            organization_address=request.organization_address,
            organization_phone=request.organization_phone,
            organization_email=request.organization_email,
            data_types=request.data_types,
            mission=request.mission,
            system_description=request.system_description
        )

        # Build metadata
        metadata = SSPMetadata(
            version=request.version,
            date=datetime.utcnow(),
            prepared_by=request.prepared_by,
            reviewed_by=request.reviewed_by,
            approved_by=request.approved_by,
            classification=request.classification
        )

        # Generate SSP
        ssp_generator = SSPGenerator(db_pool)
        doc_bytes = await ssp_generator.generate_ssp(
            assessment_id=assessment_id,
            system_info=system_info,
            metadata=metadata,
            include_provider_inheritance=request.include_provider_inheritance,
            generate_narratives=request.generate_narratives
        )

        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds()

        logger.info(f"SSP generated in {generation_time:.2f} seconds")

        # Return as downloadable file
        file_name = f"SSP_{request.system_name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.docx"

        return StreamingResponse(
            doc_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename={file_name}",
                "X-Generation-Time": str(generation_time)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating SSP: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate SSP: {str(e)}")


@router.post("/poam/{assessment_id}", response_class=StreamingResponse)
async def generate_poam(
    assessment_id: str,
    request: GeneratePOAMRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Generate Plan of Action & Milestones (POA&M) for assessment

    Creates a POA&M Excel workbook tracking remediation plans for
    all "Not Met" and "Partially Met" controls with:
    - Weakness descriptions
    - Risk levels (auto-calculated)
    - Remediation plans (AI-generated)
    - Milestone dates
    - Status tracking

    **Parameters:**
    - assessment_id: UUID of the assessment
    - request: POA&M generation parameters

    **Returns:**
    - Excel file download

    **Example:**
    ```json
    POST /api/v1/reports/poam/uuid
    {
      "system_name": "DoD Contract Management System",
      "organization": "Defense Contractor Inc.",
      "prepared_by": "Jane Doe, ISSO",
      "version": "1.0",
      "generate_recommendations": true,
      "auto_assign_risk": true
    }
    ```

    **Response:**
    - Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
    - Content-Disposition: attachment; filename="POAM_{system_name}_{date}.xlsx"
    """
    try:
        start_time = datetime.utcnow()

        logger.info(f"Generating POA&M for assessment {assessment_id}")

        # Verify assessment exists
        async with db_pool.acquire() as conn:
            assessment = await conn.fetchrow(
                "SELECT id, status FROM assessments WHERE id = $1",
                assessment_id
            )

            if not assessment:
                raise HTTPException(status_code=404, detail="Assessment not found")

        # Build metadata
        metadata = POAMMetadata(
            system_name=request.system_name,
            organization=request.organization,
            prepared_by=request.prepared_by,
            preparation_date=datetime.utcnow(),
            review_date=None,
            version=request.version
        )

        # Generate POA&M
        poam_generator = POAMGenerator(db_pool)
        excel_bytes = await poam_generator.generate_poam(
            assessment_id=assessment_id,
            metadata=metadata,
            generate_recommendations=request.generate_recommendations,
            auto_assign_risk=request.auto_assign_risk
        )

        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds()

        logger.info(f"POA&M generated in {generation_time:.2f} seconds")

        # Return as downloadable file
        file_name = f"POAM_{request.system_name.replace(' ', '_')}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={file_name}",
                "X-Generation-Time": str(generation_time)
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating POA&M: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate POA&M: {str(e)}")


@router.get("/assessment/{assessment_id}/summary")
async def get_assessment_summary(
    assessment_id: str,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get assessment summary for report generation

    Returns summary statistics and metadata needed for report generation.

    **Parameters:**
    - assessment_id: UUID of the assessment

    **Returns:**
    - Assessment summary with control statistics

    **Example:**
    ```json
    GET /api/v1/reports/assessment/uuid/summary
    {
      "assessment_id": "uuid",
      "total_controls": 110,
      "by_status": {
        "Met": 85,
        "Partially Met": 12,
        "Not Met": 10,
        "Not Applicable": 3
      },
      "requires_poam": 22,
      "avg_confidence": 0.82,
      "start_date": "2024-01-15",
      "end_date": null,
      "status": "In Progress"
    }
    ```
    """
    try:
        async with db_pool.acquire() as conn:
            # Get assessment info
            assessment = await conn.fetchrow("""
                SELECT
                    id,
                    organization_id,
                    scope,
                    status,
                    start_date,
                    end_date,
                    created_at
                FROM assessments
                WHERE id = $1
            """, assessment_id)

            if not assessment:
                raise HTTPException(status_code=404, detail="Assessment not found")

            # Get control statistics
            stats = await conn.fetch("""
                SELECT
                    status,
                    COUNT(*) as count,
                    AVG(ai_confidence_score) as avg_confidence
                FROM control_findings
                WHERE assessment_id = $1
                GROUP BY status
            """, assessment_id)

            by_status = {row['status']: row['count'] for row in stats}
            total_controls = sum(by_status.values())

            # Calculate average confidence
            avg_confidence = 0.0
            if stats:
                confidences = [row['avg_confidence'] for row in stats if row['avg_confidence']]
                if confidences:
                    avg_confidence = sum(confidences) / len(confidences)

            # Controls requiring POA&M
            requires_poam = by_status.get('Not Met', 0) + by_status.get('Partially Met', 0)

            return {
                "assessment_id": str(assessment['id']),
                "total_controls": total_controls,
                "by_status": by_status,
                "requires_poam": requires_poam,
                "avg_confidence": round(avg_confidence, 2),
                "start_date": assessment['start_date'].strftime("%Y-%m-%d") if assessment['start_date'] else None,
                "end_date": assessment['end_date'].strftime("%Y-%m-%d") if assessment['end_date'] else None,
                "status": assessment['status'],
                "scope": assessment['scope']
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting assessment summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get summary: {str(e)}")


@router.get("/assessment/{assessment_id}/controls")
async def get_assessment_controls(
    assessment_id: str,
    status_filter: Optional[str] = None,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get control details for assessment

    Returns detailed control information for report generation.

    **Parameters:**
    - assessment_id: UUID of the assessment
    - status_filter: Optional filter by status (Met, Not Met, Partially Met, Not Applicable)

    **Returns:**
    - List of controls with findings

    **Example:**
    ```json
    GET /api/v1/reports/assessment/uuid/controls?status_filter=Not%20Met
    [
      {
        "control_id": "AC.L2-3.1.1",
        "control_title": "Authorized Access Control",
        "domain": "AC",
        "status": "Not Met",
        "narrative": "Organization has not implemented...",
        "confidence_score": 0.75,
        "evidence_count": 2
      }
    ]
    ```
    """
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT
                    cf.control_id,
                    c.title as control_title,
                    cd.name as domain,
                    cf.status,
                    cf.assessor_narrative,
                    cf.ai_confidence_score,
                    COUNT(DISTINCT e.id) as evidence_count
                FROM control_findings cf
                JOIN controls c ON cf.control_id = c.id
                JOIN control_domains cd ON c.domain_id = cd.id
                LEFT JOIN evidence e ON e.assessment_id = cf.assessment_id AND e.control_id = cf.control_id
                WHERE cf.assessment_id = $1
            """

            params = [assessment_id]

            if status_filter:
                query += " AND cf.status = $2"
                params.append(status_filter)

            query += """
                GROUP BY cf.control_id, c.title, cd.name, cf.status, cf.assessor_narrative, cf.ai_confidence_score
                ORDER BY cd.name, cf.control_id
            """

            rows = await conn.fetch(query, *params)

            return [
                {
                    "control_id": row['control_id'],
                    "control_title": row['control_title'],
                    "domain": row['domain'],
                    "status": row['status'],
                    "narrative": row['assessor_narrative'],
                    "confidence_score": float(row['ai_confidence_score']) if row['ai_confidence_score'] else None,
                    "evidence_count": row['evidence_count']
                }
                for row in rows
            ]

    except Exception as e:
        logger.error(f"Error getting assessment controls: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get controls: {str(e)}")
