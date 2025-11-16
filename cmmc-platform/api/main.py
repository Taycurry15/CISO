# CMMC Compliance Platform - FastAPI Service
# Assessor-grade endpoints for evidence management, AI analysis, and report generation

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, UUID4
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
import hashlib
import uuid
import asyncpg
import asyncio
from pathlib import Path
import logging

# Import SPRS calculator
from sprs_calculator import (
    calculate_sprs_score,
    save_sprs_score,
    get_sprs_score_history,
    get_sprs_score_trend
)

# Import monitoring dashboard
from monitoring_dashboard import (
    get_dashboard_summary,
    get_control_compliance_overview,
    get_recent_activity,
    get_integration_status,
    get_risk_metrics,
    get_recent_alerts,
    get_evidence_statistics
)

# Import authentication
from auth import (
    TokenData,
    LoginRequest,
    CreateUserRequest,
    APIKeyRequest,
    login,
    create_user,
    create_api_key,
    get_current_user,
    get_current_admin_user,
    get_current_assessor_user
)

# Import onboarding
from onboarding import (
    OnboardingWorkflow,
    OrganizationOnboardingRequest
)

# Import customer portal
from customer_portal import (
    CustomerPortalService,
    OrganizationProfileUpdate,
    TeamMemberInvite,
    AssessmentCreateRequest,
    NotificationPreferences,
    ReportDownloadRequest
)

# Import billing
from billing import (
    BillingService,
    CreateSubscriptionRequest,
    UpdateSubscriptionRequest,
    PaymentMethodRequest
)

# Import white label
from white_label import (
    WhiteLabelService,
    BrandingConfig,
    EmailTemplateConfig,
    TerminologyCustomization
)

# Import C3PAO workflow
from c3pao_workflow import (
    C3PAOWorkflowService,
    C3PAORegistration,
    AssessmentAssignment,
    FindingReview,
    AssessmentPhaseUpdate
)

# Import assessment scheduling
from assessment_scheduling import (
    AssessmentSchedulingService,
    ScheduleEventRequest,
    UpdateEventRequest,
    AssessorAvailability,
    MilestoneRequest
)

# Initialize FastAPI
app = FastAPI(
    title="CMMC Compliance Platform API",
    version="1.0.0",
    description="Assessor-grade API for CMMC Level 1 & 2 compliance automation"
)

# Security
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    DATABASE_URL = "postgresql://user:pass@localhost:5432/cmmc_platform"
    OBJECT_STORAGE_PATH = "/var/cmmc/evidence"
    VECTOR_EMBEDDING_MODEL = "text-embedding-ada-002"  # or local model
    AI_MODEL = "gpt-4"  # or claude-3-5-sonnet
    
config = Config()

# ============================================================================
# DATABASE CONNECTION POOL
# ============================================================================

db_pool = None

async def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            config.DATABASE_URL,
            min_size=5,
            max_size=20
        )
    return db_pool

async def get_db():
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        yield conn

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class AssessmentMethod(str, Enum):
    EXAMINE = "Examine"
    INTERVIEW = "Interview"
    TEST = "Test"

class FindingStatus(str, Enum):
    MET = "Met"
    NOT_MET = "Not Met"
    PARTIALLY_MET = "Partially Met"
    NOT_APPLICABLE = "Not Applicable"
    NOT_ASSESSED = "Not Assessed"

class EvidenceType(str, Enum):
    DOCUMENT = "document"
    SCREENSHOT = "screenshot"
    LOG = "log"
    INTERVIEW_NOTES = "interview_notes"
    TEST_RESULT = "test_result"
    CONFIGURATION = "configuration"

# Request/Response Models

class DocumentIngestRequest(BaseModel):
    assessment_id: UUID4
    title: str
    document_type: str = Field(..., description="policy, procedure, ssp, manual, etc.")
    control_id: Optional[str] = None
    auto_chunk: bool = True
    auto_embed: bool = True

class DocumentChunk(BaseModel):
    id: UUID4
    chunk_text: str
    chunk_index: int
    control_id: Optional[str]
    objective_id: Optional[str]
    method: Optional[AssessmentMethod]

class DocumentIngestResponse(BaseModel):
    document_id: UUID4
    chunks_created: int
    file_hash: str
    processing_time_ms: int

class ControlAnalysisRequest(BaseModel):
    assessment_id: UUID4
    control_id: str
    objective_id: Optional[str] = None
    include_provider_inheritance: bool = True
    include_diagram_context: bool = True
    max_evidence_items: int = 10

class EvidenceReference(BaseModel):
    id: UUID4
    title: str
    evidence_type: EvidenceType
    file_hash: str
    collected_date: datetime
    confidence_contribution: float = Field(..., ge=0.0, le=100.0)

class ControlAnalysisResponse(BaseModel):
    control_id: str
    objective_id: Optional[str]
    finding_id: UUID4
    status: FindingStatus
    assessor_narrative: str
    ai_confidence_score: float
    ai_rationale: str
    evidence_used: List[EvidenceReference]
    provider_inheritance: Optional[Dict[str, Any]]
    graph_context: Optional[Dict[str, Any]]
    processing_time_ms: int

class SSPExportRequest(BaseModel):
    assessment_id: UUID4
    include_inherited_controls: bool = True
    include_diagrams: bool = True
    format: str = "docx"  # docx, pdf, json

class SSPSection(BaseModel):
    section_number: str
    title: str
    content: str
    controls_covered: List[str]

class SSPExportResponse(BaseModel):
    assessment_id: UUID4
    file_path: str
    file_hash: str
    sections_count: int
    controls_documented: int
    generation_time_ms: int

class POAMItem(BaseModel):
    poam_id: str
    control_id: str
    weakness_description: str
    risk_level: str
    remediation_plan: str
    estimated_completion_date: Optional[date]
    milestones: List[Dict[str, Any]]

class POAMExportRequest(BaseModel):
    assessment_id: UUID4
    format: str = "xlsx"  # xlsx, csv, json

class POAMExportResponse(BaseModel):
    assessment_id: UUID4
    file_path: str
    file_hash: str
    items_count: int
    generation_time_ms: int

class EvidenceUploadRequest(BaseModel):
    assessment_id: UUID4
    control_id: str
    objective_id: Optional[str]
    title: str
    description: Optional[str]
    evidence_type: EvidenceType
    method: AssessmentMethod

class EvidenceUploadResponse(BaseModel):
    evidence_id: UUID4
    file_hash: str
    file_size_bytes: int
    status: str

class ProviderInheritance(BaseModel):
    provider_name: str
    offering_name: str
    control_id: str
    responsibility: str  # Inherited, Shared, Customer
    provider_narrative: str
    customer_narrative: str
    evidence_url: Optional[str]

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def calculate_file_hash(file_content: bytes) -> str:
    """Calculate SHA-256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()

async def store_file(file_content: bytes, file_hash: str, mime_type: str) -> str:
    """Store file in object storage and return path"""
    storage_path = Path(config.OBJECT_STORAGE_PATH)
    storage_path.mkdir(parents=True, exist_ok=True)
    
    # Organize by first 2 chars of hash for better performance
    subdir = storage_path / file_hash[:2]
    subdir.mkdir(exist_ok=True)
    
    file_path = subdir / file_hash
    file_path.write_bytes(file_content)
    
    return str(file_path)

async def chunk_document(text: str, max_chunk_size: int = 1000) -> List[str]:
    """Split document into chunks for RAG"""
    # Simple chunking - in production, use more sophisticated methods
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        if current_length > max_chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

async def generate_embedding(text: str) -> List[float]:
    """Generate vector embedding for semantic search"""
    # Placeholder - integrate with OpenAI, Cohere, or local model
    # For now, return dummy embedding
    logger.warning("Using placeholder embedding - integrate with actual embedding service")
    return [0.0] * 1536  # ada-002 dimension

async def analyze_control_with_ai(
    control_id: str,
    objective_id: Optional[str],
    evidence_items: List[Dict],
    provider_inheritance: Optional[Dict],
    graph_context: Optional[Dict],
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """Use AI to analyze control compliance based on evidence"""
    
    # Get control and objective details
    control = await conn.fetchrow(
        "SELECT * FROM controls WHERE id = $1",
        control_id
    )
    
    objective = None
    if objective_id:
        objective = await conn.fetchrow(
            "SELECT * FROM assessment_objectives WHERE id = $1",
            objective_id
        )
    
    # Build context for AI
    context = {
        "control": dict(control) if control else None,
        "objective": dict(objective) if objective else None,
        "evidence_count": len(evidence_items),
        "has_provider_inheritance": provider_inheritance is not None,
        "has_diagram_context": graph_context is not None
    }
    
    # In production, call actual AI model (GPT-4, Claude, etc.)
    # For now, return mock analysis
    logger.warning("Using mock AI analysis - integrate with actual AI service")
    
    # Simple heuristic: if we have evidence, mark as Met
    if len(evidence_items) >= 2:
        status = "Met"
        confidence = 85.0
        narrative = f"The organization has demonstrated compliance with {control_id}. "
        if provider_inheritance:
            narrative += f"This control leverages {provider_inheritance['provider_name']} inheritance for {provider_inheritance['responsibility']} responsibilities. "
        narrative += f"Evidence review shows {len(evidence_items)} supporting artifacts."
    else:
        status = "Not Met"
        confidence = 60.0
        narrative = f"Insufficient evidence to demonstrate compliance with {control_id}. "
        narrative += f"Only {len(evidence_items)} evidence item(s) provided. Additional documentation required."
    
    rationale = f"Analysis based on {len(evidence_items)} evidence items, "
    if provider_inheritance:
        rationale += "provider inheritance documentation, "
    if graph_context:
        rationale += "system architecture context, "
    rationale += f"and assessment objective {objective_id or 'general'}."
    
    return {
        "status": status,
        "confidence_score": confidence,
        "narrative": narrative,
        "rationale": rationale,
        "evidence_ids": [e["id"] for e in evidence_items]
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.on_event("startup")
async def startup():
    """Initialize database pool on startup"""
    await get_db_pool()
    logger.info("Database pool initialized")

@app.on_event("shutdown")
async def shutdown():
    """Close database pool on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# ----------------------------------------------------------------------------
# DOCUMENT INGESTION
# ----------------------------------------------------------------------------

@app.post("/api/v1/ingest/document", response_model=DocumentIngestResponse)
async def ingest_document(
    file: UploadFile = File(...),
    request: DocumentIngestRequest = Depends(),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Ingest a document (PDF, DOCX, etc.), extract text, chunk it, and create embeddings.
    
    This endpoint:
    1. Stores the file with SHA-256 hash for immutability
    2. Extracts and chunks the text
    3. Tags chunks with control/objective metadata
    4. Generates vector embeddings for RAG
    """
    start_time = datetime.utcnow()
    
    # Read file content
    file_content = await file.read()
    file_hash = calculate_file_hash(file_content)
    
    # Store file
    file_path = await store_file(file_content, file_hash, file.content_type)
    
    # Insert document record
    document_id = await conn.fetchval(
        """
        INSERT INTO documents (assessment_id, title, document_type, file_path, file_hash, uploaded_by)
        VALUES ($1, $2, $3, $4, $5, $6)
        RETURNING id
        """,
        request.assessment_id,
        request.title,
        request.document_type,
        file_path,
        file_hash,
        uuid.UUID('00000000-0000-0000-0000-000000000000')  # TODO: Get from auth
    )
    
    chunks_created = 0
    
    if request.auto_chunk:
        # TODO: Actual text extraction from PDF/DOCX
        # For now, use placeholder
        text = "Placeholder text content"
        
        chunks = await chunk_document(text)
        
        for idx, chunk_text in enumerate(chunks):
            embedding = None
            if request.auto_embed:
                embedding = await generate_embedding(chunk_text)
            
            await conn.execute(
                """
                INSERT INTO document_chunks 
                (document_id, chunk_index, chunk_text, control_id, embedding)
                VALUES ($1, $2, $3, $4, $5)
                """,
                document_id,
                idx,
                chunk_text,
                request.control_id,
                embedding
            )
            chunks_created += 1
    
    end_time = datetime.utcnow()
    processing_time = int((end_time - start_time).total_seconds() * 1000)
    
    return DocumentIngestResponse(
        document_id=document_id,
        chunks_created=chunks_created,
        file_hash=file_hash,
        processing_time_ms=processing_time
    )

# ----------------------------------------------------------------------------
# CONTROL ANALYSIS
# ----------------------------------------------------------------------------

@app.post("/api/v1/analyze/{control_id}", response_model=ControlAnalysisResponse)
async def analyze_control(
    control_id: str,
    request: ControlAnalysisRequest,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Analyze a control using AI-assisted assessment.
    
    This endpoint:
    1. Retrieves all evidence for the control
    2. Fetches provider inheritance (if applicable)
    3. Gets diagram/graph context
    4. Uses RAG to find relevant documentation
    5. Generates AI-assisted finding with rationale
    6. Creates control_finding record for human review
    """
    start_time = datetime.utcnow()
    
    # Retrieve evidence for this control
    evidence_rows = await conn.fetch(
        """
        SELECT id, title, evidence_type, file_hash, collected_date, method
        FROM evidence
        WHERE assessment_id = $1 AND control_id = $2 AND status = 'approved'
        ORDER BY collected_date DESC
        LIMIT $3
        """,
        request.assessment_id,
        control_id,
        request.max_evidence_items
    )
    
    evidence_items = [dict(row) for row in evidence_rows]
    
    # Get provider inheritance if requested
    provider_inheritance = None
    if request.include_provider_inheritance:
        inheritance_row = await conn.fetchrow(
            """
            SELECT po.provider_name, po.offering_name, pci.responsibility,
                   pci.provider_narrative, pci.customer_narrative, pci.evidence_url
            FROM provider_control_inheritance pci
            JOIN provider_offerings po ON pci.provider_offering_id = po.id
            WHERE pci.control_id = $1
            LIMIT 1
            """,
            control_id
        )
        if inheritance_row:
            provider_inheritance = dict(inheritance_row)
    
    # Get diagram context if requested
    graph_context = None
    if request.include_diagram_context:
        diagram_row = await conn.fetchrow(
            """
            SELECT id, title, graph_data
            FROM system_diagrams
            WHERE assessment_id = $1 AND graph_extracted = TRUE
            ORDER BY created_at DESC
            LIMIT 1
            """,
            request.assessment_id
        )
        if diagram_row and diagram_row['graph_data']:
            graph_context = {
                "diagram_id": diagram_row['id'],
                "title": diagram_row['title'],
                "graph_summary": diagram_row['graph_data']
            }
    
    # Use AI to analyze the control
    ai_analysis = await analyze_control_with_ai(
        control_id,
        request.objective_id,
        evidence_items,
        provider_inheritance,
        graph_context,
        conn
    )
    
    # Create finding record
    finding_id = await conn.fetchval(
        """
        INSERT INTO control_findings 
        (assessment_id, control_id, objective_id, status, assessor_narrative,
         ai_generated, ai_confidence_score, ai_rationale, ai_evidence_ids)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        RETURNING id
        """,
        request.assessment_id,
        control_id,
        request.objective_id,
        ai_analysis["status"],
        ai_analysis["narrative"],
        True,
        ai_analysis["confidence_score"],
        ai_analysis["rationale"],
        ai_analysis["evidence_ids"]
    )
    
    # Build evidence references
    evidence_references = []
    for ev in evidence_items:
        evidence_references.append(EvidenceReference(
            id=ev["id"],
            title=ev["title"],
            evidence_type=EvidenceType(ev["evidence_type"]),
            file_hash=ev["file_hash"],
            collected_date=ev["collected_date"],
            confidence_contribution=ai_analysis["confidence_score"] / len(evidence_items) if evidence_items else 0
        ))
    
    end_time = datetime.utcnow()
    processing_time = int((end_time - start_time).total_seconds() * 1000)
    
    return ControlAnalysisResponse(
        control_id=control_id,
        objective_id=request.objective_id,
        finding_id=finding_id,
        status=FindingStatus(ai_analysis["status"]),
        assessor_narrative=ai_analysis["narrative"],
        ai_confidence_score=ai_analysis["confidence_score"],
        ai_rationale=ai_analysis["rationale"],
        evidence_used=evidence_references,
        provider_inheritance=provider_inheritance,
        graph_context=graph_context,
        processing_time_ms=processing_time
    )

# ----------------------------------------------------------------------------
# SSP EXPORT
# ----------------------------------------------------------------------------

@app.post("/api/v1/ssp/{assessment_id}", response_model=SSPExportResponse)
async def export_ssp(
    assessment_id: UUID4,
    request: SSPExportRequest,
    background_tasks: BackgroundTasks,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Generate System Security Plan (SSP) document.
    
    This endpoint:
    1. Gathers all control findings and evidence
    2. Includes provider inheritance documentation
    3. Adds system diagrams
    4. Generates a formatted SSP in DOCX/PDF format
    """
    start_time = datetime.utcnow()
    
    # Get assessment details
    assessment = await conn.fetchrow(
        "SELECT * FROM assessments WHERE id = $1",
        assessment_id
    )
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Get all findings for this assessment
    findings = await conn.fetch(
        """
        SELECT cf.control_id, cf.status, cf.assessor_narrative, c.title, c.requirement_text
        FROM control_findings cf
        JOIN controls c ON cf.control_id = c.id
        WHERE cf.assessment_id = $1
        ORDER BY cf.control_id
        """,
        assessment_id
    )
    
    controls_documented = len(findings)
    
    # TODO: Generate actual SSP document using python-docx or similar
    # For now, return mock response
    
    file_hash = hashlib.sha256(f"ssp_{assessment_id}".encode()).hexdigest()
    file_path = f"/var/cmmc/exports/ssp_{assessment_id}.docx"
    
    end_time = datetime.utcnow()
    processing_time = int((end_time - start_time).total_seconds() * 1000)
    
    return SSPExportResponse(
        assessment_id=assessment_id,
        file_path=file_path,
        file_hash=file_hash,
        sections_count=12,  # Standard SSP has ~12 sections
        controls_documented=controls_documented,
        generation_time_ms=processing_time
    )

# ----------------------------------------------------------------------------
# POA&M EXPORT
# ----------------------------------------------------------------------------

@app.post("/api/v1/poam/{assessment_id}", response_model=POAMExportResponse)
async def export_poam(
    assessment_id: UUID4,
    request: POAMExportRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Generate Plan of Action & Milestones (POA&M) document.
    
    This endpoint:
    1. Gathers all "Not Met" and "Partially Met" findings
    2. Formats as POA&M items with milestones
    3. Exports to Excel, CSV, or JSON
    """
    start_time = datetime.utcnow()
    
    # Get POA&M items
    poam_items = await conn.fetch(
        """
        SELECT * FROM poam_items
        WHERE assessment_id = $1
        ORDER BY risk_level DESC, poam_id
        """,
        assessment_id
    )
    
    items_count = len(poam_items)
    
    # TODO: Generate actual POA&M Excel file using openpyxl or xlsxwriter
    
    file_hash = hashlib.sha256(f"poam_{assessment_id}".encode()).hexdigest()
    file_path = f"/var/cmmc/exports/poam_{assessment_id}.xlsx"
    
    end_time = datetime.utcnow()
    processing_time = int((end_time - start_time).total_seconds() * 1000)
    
    return POAMExportResponse(
        assessment_id=assessment_id,
        file_path=file_path,
        file_hash=file_hash,
        items_count=items_count,
        generation_time_ms=processing_time
    )

# ----------------------------------------------------------------------------
# EVIDENCE UPLOAD
# ----------------------------------------------------------------------------

@app.post("/api/v1/evidence/upload", response_model=EvidenceUploadResponse)
async def upload_evidence(
    file: UploadFile = File(...),
    request: EvidenceUploadRequest = Depends(),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Upload evidence file with immutable storage and chain-of-custody tracking.
    
    This endpoint:
    1. Calculates SHA-256 hash for file integrity
    2. Stores file in object storage
    3. Creates evidence record with provenance metadata
    4. Logs access for chain-of-custody
    """
    # Read file
    file_content = await file.read()
    file_hash = calculate_file_hash(file_content)
    file_size = len(file_content)
    
    # Store file
    file_path = await store_file(file_content, file_hash, file.content_type)
    
    # Create evidence record
    evidence_id = await conn.fetchval(
        """
        INSERT INTO evidence 
        (assessment_id, control_id, objective_id, evidence_type, title, description,
         method, file_path, file_hash, file_size_bytes, mime_type, collected_by, collection_method)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, 'manual_upload')
        RETURNING id
        """,
        request.assessment_id,
        request.control_id,
        request.objective_id,
        request.evidence_type.value,
        request.title,
        request.description,
        request.method.value,
        file_path,
        file_hash,
        file_size,
        file.content_type,
        uuid.UUID('00000000-0000-0000-0000-000000000000')  # TODO: Get from auth
    )
    
    # Log access
    await conn.execute(
        """
        INSERT INTO evidence_access_log (evidence_id, user_id, action)
        VALUES ($1, $2, 'upload')
        """,
        evidence_id,
        uuid.UUID('00000000-0000-0000-0000-000000000000')  # TODO: Get from auth
    )
    
    return EvidenceUploadResponse(
        evidence_id=evidence_id,
        file_hash=file_hash,
        file_size_bytes=file_size,
        status="pending_review"
    )

# ----------------------------------------------------------------------------
# PROVIDER INHERITANCE
# ----------------------------------------------------------------------------

@app.get("/api/v1/provider-inheritance/{control_id}", response_model=List[ProviderInheritance])
async def get_provider_inheritance(
    control_id: str,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get provider inheritance information for a control.
    Useful for documenting M365, Azure, AWS responsibilities.
    """
    rows = await conn.fetch(
        """
        SELECT po.provider_name, po.offering_name, pci.control_id,
               pci.responsibility, pci.provider_narrative, pci.customer_narrative,
               pci.evidence_url
        FROM provider_control_inheritance pci
        JOIN provider_offerings po ON pci.provider_offering_id = po.id
        WHERE pci.control_id = $1
        """,
        control_id
    )
    
    return [ProviderInheritance(**dict(row)) for row in rows]

# ----------------------------------------------------------------------------
# SPRS SCORING
# ----------------------------------------------------------------------------

class SPRSScoreResponse(BaseModel):
    score: int = Field(..., ge=-203, le=110)
    total_controls: int
    met_count: int
    partially_met_count: int
    not_met_count: int
    not_assessed_count: int
    not_applicable_count: int
    family_breakdown: Dict[str, Any]
    calculation_date: str

class SPRSScoreHistoryItem(BaseModel):
    id: str
    score: int
    calculation_date: str
    details: Dict[str, Any]

class SPRSTrendResponse(BaseModel):
    current_score: Optional[int]
    previous_score: Optional[int]
    score_change: int
    improvement_rate: float
    trend: str
    calculation_date: Optional[str]
    total_calculations: int

@app.post("/api/v1/sprs/calculate/{assessment_id}", response_model=SPRSScoreResponse)
async def calculate_sprs(
    assessment_id: UUID4,
    save_to_db: bool = True,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Calculate SPRS score for an assessment.

    This endpoint:
    1. Retrieves all control findings for the assessment
    2. Calculates SPRS score based on NIST 800-171 compliance
    3. Provides breakdown by control family
    4. Optionally saves the score to the database

    SPRS Score Range: -203 to 110
    - Base score: 110
    - Met: 0 deduction
    - Partially Met: -1 point
    - Not Met (with POA&M): -1 point
    - Not Met (without POA&M): -3 points
    - Not Assessed: -1 point
    """
    score_data = await calculate_sprs_score(str(assessment_id), conn)

    if save_to_db:
        await save_sprs_score(str(assessment_id), score_data, conn)

    return SPRSScoreResponse(
        score=score_data['score'],
        total_controls=score_data['total_controls'],
        met_count=score_data['met_count'],
        partially_met_count=score_data['partially_met_count'],
        not_met_count=score_data['not_met_count'],
        not_assessed_count=score_data['not_assessed_count'],
        not_applicable_count=score_data['not_applicable_count'],
        family_breakdown=score_data['family_breakdown'],
        calculation_date=score_data['calculation_date']
    )

@app.get("/api/v1/sprs/history/{assessment_id}", response_model=List[SPRSScoreHistoryItem])
async def get_sprs_history(
    assessment_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get historical SPRS scores for an assessment.
    Useful for tracking compliance progress over time.
    """
    history = await get_sprs_score_history(str(assessment_id), conn)
    return [SPRSScoreHistoryItem(**item) for item in history]

@app.get("/api/v1/sprs/trend/{assessment_id}", response_model=SPRSTrendResponse)
async def get_sprs_trend(
    assessment_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get SPRS score trend analysis.

    Returns:
    - Current and previous scores
    - Score change (positive = improvement)
    - Improvement rate (percentage)
    - Trend direction (improving, declining, stable)
    """
    trend = await get_sprs_score_trend(str(assessment_id), conn)
    return SPRSTrendResponse(**trend)

# ----------------------------------------------------------------------------
# CONTINUOUS MONITORING DASHBOARD
# ----------------------------------------------------------------------------

@app.get("/api/v1/dashboard/summary/{organization_id}")
async def dashboard_summary(
    organization_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get dashboard summary for an organization.

    Provides high-level overview including:
    - Assessment statistics
    - SPRS score summary
    - Compliance percentage
    - Evidence counts
    - POA&M status
    - Recent alerts
    """
    return await get_dashboard_summary(str(organization_id), conn)

@app.get("/api/v1/dashboard/compliance/{assessment_id}")
async def compliance_overview(
    assessment_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get detailed control compliance overview for an assessment.

    Returns:
    - Compliance breakdown by control family
    - Top non-compliant controls
    - Compliance percentages
    """
    return await get_control_compliance_overview(str(assessment_id), conn)

@app.get("/api/v1/dashboard/activity/{organization_id}")
async def recent_activity(
    organization_id: UUID4,
    limit: int = 50,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get recent activity feed for an organization.

    Returns chronological list of recent changes including:
    - Evidence uploads
    - Finding updates
    - POA&M changes
    - Assessment progress
    """
    return await get_recent_activity(str(organization_id), conn, limit)

@app.get("/api/v1/dashboard/integrations/{organization_id}")
async def integration_status(
    organization_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get integration status for an organization.

    Returns:
    - Integration health status
    - Success rates
    - Last run times
    - Error statistics
    """
    return await get_integration_status(str(organization_id), conn)

@app.get("/api/v1/dashboard/risk/{assessment_id}")
async def risk_metrics(
    assessment_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get risk metrics for an assessment.

    Returns:
    - Overall risk score
    - Risk distribution by severity
    - Critical findings
    - Overdue POA&Ms
    """
    return await get_risk_metrics(str(assessment_id), conn)

@app.get("/api/v1/dashboard/alerts/{organization_id}")
async def alerts(
    organization_id: UUID4,
    days: int = 7,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get recent alerts for an organization.

    Returns alerts for:
    - Overdue POA&Ms
    - Integration failures
    - New non-compliant controls
    - Compliance drops
    """
    return await get_recent_alerts(str(organization_id), conn, days)

@app.get("/api/v1/dashboard/evidence/{assessment_id}")
async def evidence_statistics(
    assessment_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get evidence statistics for an assessment.

    Returns:
    - Evidence counts by type
    - Collection method breakdown
    - Status distribution
    - Recent uploads
    """
    return await get_evidence_statistics(str(assessment_id), conn)

# ----------------------------------------------------------------------------
# AUTHENTICATION & USER MANAGEMENT
# ----------------------------------------------------------------------------

@app.post("/api/v1/auth/login")
async def user_login(
    request: LoginRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    User login endpoint.

    Returns JWT access and refresh tokens.
    """
    return await login(request, conn)

@app.post("/api/v1/auth/register")
async def register_user(
    request: CreateUserRequest,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Register a new user (admin only).

    Returns user ID.
    """
    user_id = await create_user(request, conn)
    return {"user_id": user_id, "email": request.email}

@app.post("/api/v1/auth/api-keys")
async def generate_api_key(
    request: APIKeyRequest,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Generate API key for integrations (admin only).

    Returns API key (shown only once).
    """
    return await create_api_key(
        request,
        current_user.user_id,
        current_user.organization_id,
        conn
    )

@app.get("/api/v1/auth/me")
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get current authenticated user information.
    """
    return {
        "user_id": current_user.user_id,
        "email": current_user.email,
        "organization_id": current_user.organization_id,
        "role": current_user.role
    }

# ----------------------------------------------------------------------------
# ORGANIZATION ONBOARDING
# ----------------------------------------------------------------------------

@app.post("/api/v1/onboarding/start")
async def start_onboarding(
    request: OrganizationOnboardingRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Start organization onboarding workflow.

    Creates:
    - Organization
    - Admin user
    - Initial assessment
    - Integration configurations (if enabled)
    """
    workflow = OnboardingWorkflow(conn)
    return await workflow.start_onboarding(request)

@app.get("/api/v1/onboarding/{onboarding_id}/status")
async def get_onboarding_status(
    onboarding_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get onboarding workflow status.
    """
    workflow = OnboardingWorkflow(conn)
    return await workflow.get_onboarding_status(str(onboarding_id))

# ----------------------------------------------------------------------------
# CUSTOMER PORTAL
# ----------------------------------------------------------------------------

@app.get("/api/v1/portal/organization")
async def get_org_profile(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get organization profile.
    """
    portal = CustomerPortalService(conn)
    return await portal.get_organization_profile(current_user.organization_id)

@app.put("/api/v1/portal/organization")
async def update_org_profile(
    updates: OrganizationProfileUpdate,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update organization profile (admin only).
    """
    portal = CustomerPortalService(conn)
    return await portal.update_organization_profile(
        current_user.organization_id,
        updates,
        current_user.user_id
    )

@app.get("/api/v1/portal/team")
async def get_team_members(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get all team members.
    """
    portal = CustomerPortalService(conn)
    return await portal.get_team_members(current_user.organization_id)

@app.post("/api/v1/portal/team/invite")
async def invite_team_member(
    invite: TeamMemberInvite,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Invite a new team member (admin only).
    """
    portal = CustomerPortalService(conn)
    return await portal.invite_team_member(
        current_user.organization_id,
        invite,
        current_user.user_id
    )

@app.delete("/api/v1/portal/team/{user_id}")
async def remove_team_member(
    user_id: UUID4,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Remove a team member (admin only).
    """
    portal = CustomerPortalService(conn)
    await portal.remove_team_member(
        str(user_id),
        current_user.organization_id,
        current_user.user_id
    )
    return {"status": "removed", "user_id": str(user_id)}

@app.post("/api/v1/portal/assessments")
async def create_portal_assessment(
    request: AssessmentCreateRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Create a new assessment (self-service).
    """
    portal = CustomerPortalService(conn)
    return await portal.create_assessment(
        current_user.organization_id,
        request,
        current_user.user_id
    )

@app.get("/api/v1/portal/assessments")
async def get_portal_assessments(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get all assessments for organization.
    """
    portal = CustomerPortalService(conn)
    return await portal.get_assessments(current_user.organization_id)

@app.get("/api/v1/portal/preferences")
async def get_preferences(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get notification preferences.
    """
    portal = CustomerPortalService(conn)
    return await portal.get_notification_preferences(current_user.user_id)

@app.put("/api/v1/portal/preferences")
async def update_preferences(
    preferences: NotificationPreferences,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update notification preferences.
    """
    portal = CustomerPortalService(conn)
    return await portal.update_notification_preferences(
        current_user.user_id,
        preferences
    )

@app.post("/api/v1/portal/reports/generate")
async def generate_report(
    request: ReportDownloadRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Generate a report for download.
    """
    portal = CustomerPortalService(conn)
    return await portal.generate_report_download(
        request,
        current_user.organization_id
    )

@app.get("/api/v1/portal/activity")
async def get_activity(
    limit: int = 100,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get organization activity history.
    """
    portal = CustomerPortalService(conn)
    return await portal.get_activity_history(
        current_user.organization_id,
        limit
    )

# ----------------------------------------------------------------------------
# BILLING & SUBSCRIPTIONS
# ----------------------------------------------------------------------------

@app.post("/api/v1/billing/subscriptions")
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Create a new subscription (admin only).
    """
    billing = BillingService(conn)
    return await billing.create_subscription(
        current_user.organization_id,
        request
    )

@app.get("/api/v1/billing/subscription")
async def get_subscription(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get current subscription.
    """
    billing = BillingService(conn)
    return await billing.get_subscription(current_user.organization_id)

@app.put("/api/v1/billing/subscription")
async def update_subscription(
    request: UpdateSubscriptionRequest,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update subscription (upgrade/downgrade) - admin only.
    """
    billing = BillingService(conn)
    return await billing.update_subscription(
        current_user.organization_id,
        request
    )

@app.delete("/api/v1/billing/subscription")
async def cancel_subscription(
    immediate: bool = False,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Cancel subscription (admin only).
    """
    billing = BillingService(conn)
    return await billing.cancel_subscription(
        current_user.organization_id,
        immediate
    )

@app.get("/api/v1/billing/invoices")
async def get_invoices(
    limit: int = 12,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get invoices for organization.
    """
    billing = BillingService(conn)
    return await billing.get_invoices(current_user.organization_id, limit)

@app.post("/api/v1/billing/webhook")
async def stripe_webhook(
    event_type: str,
    event_data: Dict[str, Any],
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Stripe webhook endpoint.

    Handles: invoice.paid, invoice.payment_failed,
             customer.subscription.updated, customer.subscription.deleted
    """
    billing = BillingService(conn)
    success = await billing.handle_stripe_webhook(event_type, event_data)
    return {"status": "success" if success else "error"}

# ----------------------------------------------------------------------------
# WHITE-LABELING
# ----------------------------------------------------------------------------

@app.get("/api/v1/white-label/branding")
async def get_branding(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get white-label branding configuration.
    """
    white_label = WhiteLabelService(conn)
    return await white_label.get_branding(current_user.organization_id)

@app.put("/api/v1/white-label/branding")
async def update_branding(
    config: BrandingConfig,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update white-label branding (admin only, Professional/Enterprise plans).
    """
    white_label = WhiteLabelService(conn)
    return await white_label.update_branding(
        current_user.organization_id,
        config,
        current_user.user_id
    )

@app.get("/api/v1/white-label/email-templates")
async def get_email_templates(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get custom email templates.
    """
    white_label = WhiteLabelService(conn)
    return await white_label.get_email_templates(current_user.organization_id)

@app.put("/api/v1/white-label/email-templates")
async def update_email_templates(
    config: EmailTemplateConfig,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update email templates (admin only).
    """
    white_label = WhiteLabelService(conn)
    return await white_label.update_email_templates(
        current_user.organization_id,
        config,
        current_user.user_id
    )

@app.get("/api/v1/white-label/terminology")
async def get_terminology(
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get custom terminology.
    """
    white_label = WhiteLabelService(conn)
    return await white_label.get_terminology(current_user.organization_id)

@app.put("/api/v1/white-label/terminology")
async def update_terminology(
    config: TerminologyCustomization,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update custom terminology (admin only).
    """
    white_label = WhiteLabelService(conn)
    return await white_label.update_terminology(
        current_user.organization_id,
        config,
        current_user.user_id
    )

@app.get("/api/v1/white-label/custom.css")
async def get_custom_css(
    organization_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get custom CSS for white-label portal.
    """
    white_label = WhiteLabelService(conn)
    css = await white_label.get_custom_css(str(organization_id))
    return {"css": css}

# ----------------------------------------------------------------------------
# C3PAO WORKFLOW
# ----------------------------------------------------------------------------

@app.post("/api/v1/c3pao/register")
async def register_c3pao(
    registration: C3PAORegistration,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Register a new C3PAO organization.
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.register_c3pao(registration)

@app.get("/api/v1/c3pao/{c3pao_id}")
async def get_c3pao(
    c3pao_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get C3PAO organization details.
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.get_c3pao_details(str(c3pao_id))

@app.post("/api/v1/c3pao/assessments/assign")
async def assign_c3pao_assessment(
    assignment: AssessmentAssignment,
    current_user: TokenData = Depends(get_current_admin_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Assign C3PAO to assessment (admin only).
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.assign_assessment(assignment, current_user.user_id)

@app.put("/api/v1/c3pao/assessments/{c3pao_assessment_id}/phase")
async def update_assessment_phase(
    c3pao_assessment_id: UUID4,
    update: AssessmentPhaseUpdate,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update C3PAO assessment phase.
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.update_assessment_phase(
        str(c3pao_assessment_id),
        update,
        current_user.user_id
    )

@app.post("/api/v1/c3pao/findings/review")
async def review_finding(
    review: FindingReview,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Review and validate a finding (C3PAO assessors).
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.review_finding(review, current_user.user_id)

@app.get("/api/v1/c3pao/assessments/{c3pao_assessment_id}/findings")
async def get_findings_for_review(
    c3pao_assessment_id: UUID4,
    status_filter: Optional[str] = None,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get findings pending review for C3PAO assessment.
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.get_findings_for_review(
        str(c3pao_assessment_id),
        status_filter
    )

@app.post("/api/v1/c3pao/assessments/{c3pao_assessment_id}/report")
async def generate_c3pao_report(
    c3pao_assessment_id: UUID4,
    report_type: str = "final",
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Generate C3PAO assessment report.
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.generate_assessment_report(
        str(c3pao_assessment_id),
        report_type
    )

@app.post("/api/v1/c3pao/reports/{report_id}/approve")
async def approve_c3pao_report(
    report_id: UUID4,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Approve C3PAO assessment report.
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.approve_report(str(report_id), current_user.user_id)

@app.post("/api/v1/c3pao/assessments/{c3pao_assessment_id}/communicate")
async def send_client_update(
    c3pao_assessment_id: UUID4,
    subject: str,
    message: str,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Send update to client.
    """
    c3pao = C3PAOWorkflowService(conn)
    return await c3pao.send_client_update(
        str(c3pao_assessment_id),
        subject,
        message,
        current_user.user_id
    )

# ----------------------------------------------------------------------------
# ASSESSMENT SCHEDULING
# ----------------------------------------------------------------------------

@app.post("/api/v1/scheduling/events")
async def schedule_event(
    request: ScheduleEventRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Schedule an assessment event.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.schedule_event(request, current_user.user_id)

@app.get("/api/v1/scheduling/events/{event_id}")
async def get_event(
    event_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get event details.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.get_event(str(event_id))

@app.put("/api/v1/scheduling/events/{event_id}")
async def update_event(
    event_id: UUID4,
    update: UpdateEventRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Update scheduled event.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.update_event(
        str(event_id),
        update,
        current_user.user_id
    )

@app.delete("/api/v1/scheduling/events/{event_id}")
async def cancel_event(
    event_id: UUID4,
    reason: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Cancel scheduled event.
    """
    scheduler = AssessmentSchedulingService(conn)
    await scheduler.cancel_event(str(event_id), current_user.user_id, reason)
    return {"status": "canceled", "event_id": str(event_id)}

@app.get("/api/v1/scheduling/calendar/assessment/{assessment_id}")
async def get_assessment_calendar(
    assessment_id: UUID4,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get calendar view for assessment.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.get_assessment_calendar(
        str(assessment_id),
        start_date,
        end_date
    )

@app.get("/api/v1/scheduling/calendar/my")
async def get_my_calendar(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get user's personal calendar.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.get_user_calendar(
        current_user.user_id,
        start_date,
        end_date
    )

@app.post("/api/v1/scheduling/availability")
async def set_availability(
    availability: AssessorAvailability,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Set assessor availability.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.set_availability(availability)

@app.get("/api/v1/scheduling/availability/available")
async def get_available_assessors(
    date: date,
    start_time: time,
    end_time: time,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get available assessors for a time slot.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.get_available_assessors(date, start_time, end_time)

@app.post("/api/v1/scheduling/milestones")
async def create_milestone(
    request: MilestoneRequest,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Create assessment milestone.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.create_milestone(request, current_user.user_id)

@app.post("/api/v1/scheduling/milestones/{milestone_id}/complete")
async def complete_milestone(
    milestone_id: UUID4,
    current_user: TokenData = Depends(get_current_user),
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Mark milestone as complete.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.complete_milestone(
        str(milestone_id),
        current_user.user_id
    )

@app.get("/api/v1/scheduling/milestones/assessment/{assessment_id}")
async def get_milestones(
    assessment_id: UUID4,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Get all milestones for assessment.
    """
    scheduler = AssessmentSchedulingService(conn)
    return await scheduler.get_milestones(str(assessment_id))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
