"""
AI Analysis API Endpoints
Handles AI-powered control analysis, findings management, and human review
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
import os
import asyncpg

from services.ai_analysis import (
    AIAnalysisService,
    FindingResult,
    FindingStatus,
    AIModel,
    EvidenceReference,
    ProviderInheritance
)
from services.rag_engine import RAGEngine
from services.embedding_service import EmbeddingService, EmbeddingModel
from services.confidence_scorer import ConfidenceScorer, ConfidenceBreakdown

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class AnalyzeControlRequest(BaseModel):
    """Request model for control analysis"""
    assessment_id: UUID4
    objective_id: Optional[str] = Field(None, description="Specific objective ID (e.g., 'AC.L2-3.1.1[a]')")
    include_provider_inheritance: bool = True
    top_k_evidence: int = 10
    model: AIModel = AIModel.GPT4_TURBO


class AnalyzeAssessmentRequest(BaseModel):
    """Request model for full assessment analysis"""
    control_ids: Optional[List[str]] = Field(None, description="Specific controls to analyze (None = all)")
    domain_filter: Optional[str] = Field(None, description="Filter by domain (e.g., 'AC', 'IA')")
    batch_size: int = Field(5, description="Number of controls to analyze in parallel")


class AnalyzeDomainRequest(BaseModel):
    """Request model for domain analysis"""
    assessment_id: UUID4
    batch_size: int = 5


class FindingResponse(BaseModel):
    """Response model for a finding"""
    finding_id: Optional[UUID4]
    control_id: str
    objective_id: Optional[str]
    status: str
    assessor_narrative: str
    confidence_score: float
    confidence_level: str
    ai_rationale: str
    evidence_count: int
    evidence_references: List[Dict[str, Any]]
    provider_inheritance: Optional[Dict[str, Any]]
    model_used: str
    tokens_used: int
    requires_human_review: bool
    created_at: datetime


class AnalysisJobResponse(BaseModel):
    """Response for batch analysis job"""
    job_id: UUID4
    assessment_id: UUID4
    total_controls: int
    status: str
    message: str


class UpdateFindingRequest(BaseModel):
    """Request to update/override a finding"""
    status: Optional[FindingStatus]
    assessor_narrative: Optional[str]
    override_reason: str
    reviewed_by: UUID4


class FindingStatsResponse(BaseModel):
    """Statistics for findings"""
    total_findings: int
    by_status: Dict[str, int]
    avg_confidence: float
    requires_review_count: int
    by_domain: Dict[str, int]


# ============================================================================
# DEPENDENCIES
# ============================================================================

_db_pool: Optional[asyncpg.Pool] = None
_ai_service: Optional[AIAnalysisService] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    global _db_pool
    if _db_pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL not set")
        _db_pool = await asyncpg.create_pool(database_url, min_size=5, max_size=20)
    return _db_pool


async def get_ai_service() -> AIAnalysisService:
    """Get AI analysis service instance"""
    global _ai_service
    if _ai_service is None:
        db_pool = await get_db_pool()

        # Initialize dependencies
        embedding_service = EmbeddingService(model=EmbeddingModel.OPENAI_3_LARGE)
        rag_engine = RAGEngine(
            db_pool=db_pool,
            embedding_service=embedding_service
        )
        confidence_scorer = ConfidenceScorer()

        # Initialize AI service
        _ai_service = AIAnalysisService(
            db_pool=db_pool,
            rag_engine=rag_engine,
            confidence_scorer=confidence_scorer,
            primary_model=AIModel.GPT4_TURBO,
            fallback_model=AIModel.CLAUDE_35_SONNET
        )

    return _ai_service


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/control/{control_id}", response_model=FindingResponse)
async def analyze_control(
    control_id: str,
    request: AnalyzeControlRequest,
    ai_service: AIAnalysisService = Depends(get_ai_service),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Analyze a single control using AI

    This endpoint:
    1. Retrieves relevant evidence using RAG
    2. Gets control and objective details
    3. Checks for provider inheritance
    4. Calls AI model (GPT-4 or Claude) for analysis
    5. Calculates confidence score
    6. Stores finding in database
    7. Returns structured finding

    The AI analyzes based on 800-171A assessment objectives and
    generates an assessor-grade narrative with evidence traceability.
    """
    try:
        logger.info(f"Analyzing control {control_id} for assessment {request.assessment_id}")

        # Perform AI analysis
        result = await ai_service.analyze_control(
            control_id=control_id,
            assessment_id=str(request.assessment_id),
            objective_id=request.objective_id,
            include_provider_inheritance=request.include_provider_inheritance,
            top_k_evidence=request.top_k_evidence
        )

        # Store finding in database
        finding_id = await store_finding(db_pool, request.assessment_id, result)

        # Convert to response format
        return convert_to_response(finding_id, result)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing control {control_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assessment/{assessment_id}", response_model=AnalysisJobResponse)
async def analyze_assessment(
    assessment_id: UUID4,
    request: AnalyzeAssessmentRequest,
    background_tasks: BackgroundTasks,
    ai_service: AIAnalysisService = Depends(get_ai_service),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Analyze all controls in an assessment

    This creates a background job to analyze multiple controls.
    The analysis runs asynchronously and results are stored in the database.

    You can monitor progress by checking the findings for the assessment.
    """
    try:
        # Get controls to analyze
        async with db_pool.acquire() as conn:
            query = "SELECT id FROM controls WHERE 1=1"
            params = []

            if request.domain_filter:
                query += " AND domain_id = $1"
                params.append(request.domain_filter)

            if request.control_ids:
                placeholders = ",".join(f"${i+len(params)+1}" for i in range(len(request.control_ids)))
                query += f" AND id IN ({placeholders})"
                params.extend(request.control_ids)

            controls = await conn.fetch(query, *params)

        control_ids = [c['id'] for c in controls]

        if not control_ids:
            raise HTTPException(status_code=404, detail="No controls found matching criteria")

        # Create analysis job
        job_id = await create_analysis_job(
            db_pool=db_pool,
            assessment_id=assessment_id,
            control_ids=control_ids
        )

        # Start background task
        background_tasks.add_task(
            analyze_controls_batch,
            ai_service=ai_service,
            db_pool=db_pool,
            assessment_id=assessment_id,
            control_ids=control_ids,
            job_id=job_id,
            batch_size=request.batch_size
        )

        return AnalysisJobResponse(
            job_id=job_id,
            assessment_id=assessment_id,
            total_controls=len(control_ids),
            status="running",
            message=f"Started analysis of {len(control_ids)} controls"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting assessment analysis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/domain/{domain_id}", response_model=AnalysisJobResponse)
async def analyze_domain(
    domain_id: str,
    request: AnalyzeDomainRequest,
    background_tasks: BackgroundTasks,
    ai_service: AIAnalysisService = Depends(get_ai_service),
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Analyze all controls in a domain (e.g., AC, IA, AU)

    Examples:
    - AC: Access Control (22 controls)
    - IA: Identification and Authentication (11 controls)
    - AU: Audit and Accountability (9 controls)
    """
    try:
        # Get controls in domain
        async with db_pool.acquire() as conn:
            controls = await conn.fetch("""
                SELECT id FROM controls
                WHERE domain_id = $1
                ORDER BY control_number
            """, domain_id)

        if not controls:
            raise HTTPException(status_code=404, detail=f"Domain {domain_id} not found or has no controls")

        control_ids = [c['id'] for c in controls]

        # Create analysis job
        job_id = await create_analysis_job(
            db_pool=db_pool,
            assessment_id=request.assessment_id,
            control_ids=control_ids
        )

        # Start background task
        background_tasks.add_task(
            analyze_controls_batch,
            ai_service=ai_service,
            db_pool=db_pool,
            assessment_id=request.assessment_id,
            control_ids=control_ids,
            job_id=job_id,
            batch_size=request.batch_size
        )

        return AnalysisJobResponse(
            job_id=job_id,
            assessment_id=request.assessment_id,
            total_controls=len(control_ids),
            status="running",
            message=f"Started analysis of domain {domain_id} ({len(control_ids)} controls)"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing domain {domain_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/finding/{finding_id}", response_model=FindingResponse)
async def get_finding(
    finding_id: UUID4,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get a specific finding by ID"""
    try:
        async with db_pool.acquire() as conn:
            finding = await conn.fetchrow("""
                SELECT
                    id,
                    control_id,
                    objective_id,
                    status,
                    assessor_narrative,
                    ai_confidence_score,
                    ai_rationale,
                    ai_generated,
                    reviewed_by,
                    created_at
                FROM control_findings
                WHERE id = $1
            """, finding_id)

            if not finding:
                raise HTTPException(status_code=404, detail="Finding not found")

            # Get evidence references
            evidence_refs = await conn.fetch("""
                SELECT
                    e.id as evidence_id,
                    e.title,
                    e.evidence_type,
                    d.title as document_title
                FROM evidence e
                JOIN finding_evidence fe ON e.id = fe.evidence_id
                LEFT JOIN documents d ON e.document_id = d.id
                WHERE fe.finding_id = $1
            """, finding_id)

            return FindingResponse(
                finding_id=finding['id'],
                control_id=finding['control_id'],
                objective_id=finding['objective_id'],
                status=finding['status'],
                assessor_narrative=finding['assessor_narrative'],
                confidence_score=float(finding['ai_confidence_score']),
                confidence_level=get_confidence_level_name(finding['ai_confidence_score']),
                ai_rationale=finding['ai_rationale'],
                evidence_count=len(evidence_refs),
                evidence_references=[dict(e) for e in evidence_refs],
                provider_inheritance=None,  # TODO: Fetch from database
                model_used="gpt-4-turbo",  # TODO: Store in database
                tokens_used=0,  # TODO: Store in database
                requires_human_review=finding['reviewed_by'] is None,
                created_at=finding['created_at']
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching finding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/finding/{finding_id}")
async def update_finding(
    finding_id: UUID4,
    request: UpdateFindingRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Update/override an AI-generated finding (human review)

    Allows assessors to:
    - Change the status
    - Modify the narrative
    - Add override reasoning
    - Mark as reviewed
    """
    try:
        async with db_pool.acquire() as conn:
            # Build update query dynamically
            updates = []
            params = [finding_id]
            param_count = 2

            if request.status:
                updates.append(f"status = ${param_count}")
                params.append(request.status.value)
                param_count += 1

            if request.assessor_narrative:
                updates.append(f"assessor_narrative = ${param_count}")
                params.append(request.assessor_narrative)
                param_count += 1

            updates.append(f"reviewed_by = ${param_count}")
            params.append(request.reviewed_by)
            param_count += 1

            updates.append(f"override_reason = ${param_count}")
            params.append(request.override_reason)
            param_count += 1

            updates.append("updated_at = NOW()")

            query = f"""
                UPDATE control_findings
                SET {', '.join(updates)}
                WHERE id = $1
                RETURNING id
            """

            result = await conn.fetchval(query, *params)

            if not result:
                raise HTTPException(status_code=404, detail="Finding not found")

            return {"message": "Finding updated successfully", "finding_id": result}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating finding: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/assessment/{assessment_id}/stats", response_model=FindingStatsResponse)
async def get_assessment_stats(
    assessment_id: UUID4,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """Get statistics for assessment findings"""
    try:
        async with db_pool.acquire() as conn:
            # Total findings
            total = await conn.fetchval("""
                SELECT COUNT(*) FROM control_findings WHERE assessment_id = $1
            """, assessment_id)

            # By status
            by_status_rows = await conn.fetch("""
                SELECT status, COUNT(*) as count
                FROM control_findings
                WHERE assessment_id = $1
                GROUP BY status
            """, assessment_id)
            by_status = {row['status']: row['count'] for row in by_status_rows}

            # Average confidence
            avg_conf = await conn.fetchval("""
                SELECT AVG(ai_confidence_score)
                FROM control_findings
                WHERE assessment_id = $1
            """, assessment_id) or 0.0

            # Requires review
            requires_review = await conn.fetchval("""
                SELECT COUNT(*)
                FROM control_findings
                WHERE assessment_id = $1 AND reviewed_by IS NULL
            """, assessment_id)

            # By domain
            by_domain_rows = await conn.fetch("""
                SELECT c.domain_id, COUNT(*) as count
                FROM control_findings cf
                JOIN controls c ON cf.control_id = c.id
                WHERE cf.assessment_id = $1
                GROUP BY c.domain_id
            """, assessment_id)
            by_domain = {row['domain_id']: row['count'] for row in by_domain_rows}

            return FindingStatsResponse(
                total_findings=total,
                by_status=by_status,
                avg_confidence=float(avg_conf),
                requires_review_count=requires_review,
                by_domain=by_domain
            )

    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def store_finding(
    db_pool: asyncpg.Pool,
    assessment_id: UUID4,
    result: FindingResult
) -> UUID4:
    """Store finding result in database"""
    async with db_pool.acquire() as conn:
        # Insert finding
        finding_id = await conn.fetchval("""
            INSERT INTO control_findings (
                assessment_id,
                control_id,
                objective_id,
                status,
                assessor_narrative,
                ai_confidence_score,
                ai_rationale,
                ai_generated,
                created_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING id
        """, assessment_id, result.control_id, result.objective_id,
            result.status.value, result.assessor_narrative,
            result.ai_confidence_score, result.ai_rationale,
            True, result.analysis_timestamp)

        # Link evidence
        for evidence_ref in result.evidence_references:
            await conn.execute("""
                INSERT INTO finding_evidence (finding_id, evidence_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """, finding_id, evidence_ref.evidence_id)

        logger.info(f"Stored finding {finding_id} for control {result.control_id}")
        return finding_id


def convert_to_response(finding_id: UUID4, result: FindingResult) -> FindingResponse:
    """Convert FindingResult to FindingResponse"""
    return FindingResponse(
        finding_id=finding_id,
        control_id=result.control_id,
        objective_id=result.objective_id,
        status=result.status.value,
        assessor_narrative=result.assessor_narrative,
        confidence_score=result.ai_confidence_score,
        confidence_level=get_confidence_level_name(result.ai_confidence_score),
        ai_rationale=result.ai_rationale,
        evidence_count=len(result.evidence_references),
        evidence_references=[
            {
                "evidence_id": ref.evidence_id,
                "document_title": ref.document_title,
                "relevance_score": ref.relevance_score,
                "evidence_type": ref.evidence_type
            }
            for ref in result.evidence_references
        ],
        provider_inheritance={
            "provider_name": result.provider_inheritance.provider_name,
            "responsibility": result.provider_inheritance.responsibility
        } if result.provider_inheritance else None,
        model_used=result.model_used,
        tokens_used=result.tokens_used,
        requires_human_review=result.requires_human_review,
        created_at=result.analysis_timestamp
    )


def get_confidence_level_name(score: float) -> str:
    """Get confidence level name from score"""
    if score >= 0.90:
        return "Very High"
    elif score >= 0.75:
        return "High"
    elif score >= 0.60:
        return "Medium"
    elif score >= 0.40:
        return "Low"
    else:
        return "Very Low"


async def create_analysis_job(
    db_pool: asyncpg.Pool,
    assessment_id: UUID4,
    control_ids: List[str]
) -> UUID4:
    """Create an analysis job record"""
    import uuid
    job_id = uuid.uuid4()

    # TODO: Implement job tracking table
    logger.info(f"Created analysis job {job_id} for {len(control_ids)} controls")

    return job_id


async def analyze_controls_batch(
    ai_service: AIAnalysisService,
    db_pool: asyncpg.Pool,
    assessment_id: UUID4,
    control_ids: List[str],
    job_id: UUID4,
    batch_size: int = 5
):
    """Background task to analyze multiple controls"""
    logger.info(f"Starting batch analysis job {job_id}")

    for i in range(0, len(control_ids), batch_size):
        batch = control_ids[i:i + batch_size]

        for control_id in batch:
            try:
                result = await ai_service.analyze_control(
                    control_id=control_id,
                    assessment_id=str(assessment_id)
                )

                await store_finding(db_pool, assessment_id, result)
                logger.info(f"Analyzed {control_id} ({i+1}/{len(control_ids)})")

            except Exception as e:
                logger.error(f"Error analyzing {control_id}: {e}")
                continue

    logger.info(f"Completed batch analysis job {job_id}")
