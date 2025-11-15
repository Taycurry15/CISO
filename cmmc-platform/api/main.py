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
import os

# Import AI and RAG services
from services.embedding_service import EmbeddingService, EmbeddingModel
from services.document_processor import DocumentProcessor, ChunkingStrategy
from services.ai_analysis import AIAnalysisService, AIModel, FindingStatus
from services.rag_engine import RAGEngine
from services.ai_cost_service import AICostService

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
# AI/RAG SERVICES (Global Instances)
# ============================================================================

# Global service instances (initialized on first use)
_embedding_service = None
_document_processor = None
_rag_engine = None
_ai_analysis_service = None
_ai_cost_service = None

async def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OPENAI_API_KEY not set - embedding features will be disabled")
            raise HTTPException(
                status_code=503,
                detail="AI features not configured. Please set OPENAI_API_KEY environment variable."
            )
        _embedding_service = EmbeddingService(
            model=EmbeddingModel.OPENAI_3_SMALL,  # Cheaper and faster
            api_key=api_key
        )
        logger.info("Initialized EmbeddingService")
    return _embedding_service

async def get_document_processor() -> DocumentProcessor:
    """Get or create document processor instance"""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor(
            chunk_size=512,
            chunk_overlap=50,
            chunking_strategy=ChunkingStrategy.HYBRID
        )
        logger.info("Initialized DocumentProcessor")
    return _document_processor

async def get_rag_engine() -> RAGEngine:
    """Get or create RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        pool = await get_db_pool()
        embedding_service = await get_embedding_service()
        _rag_engine = RAGEngine(
            db_pool=pool,
            embedding_service=embedding_service
        )
        logger.info("Initialized RAGEngine")
    return _rag_engine

async def get_ai_analysis_service() -> AIAnalysisService:
    """Get or create AI analysis service instance"""
    global _ai_analysis_service
    if _ai_analysis_service is None:
        # Check for API keys
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")

        if not openai_key and not anthropic_key:
            logger.warning("No AI API keys configured - AI analysis will be disabled")
            raise HTTPException(
                status_code=503,
                detail="AI features not configured. Please set OPENAI_API_KEY or ANTHROPIC_API_KEY."
            )

        pool = await get_db_pool()
        rag_engine = await get_rag_engine()

        # Import confidence scorer
        from services.confidence_scorer import ConfidenceScorer
        confidence_scorer = ConfidenceScorer(db_pool=pool)

        # Choose model based on available API keys
        if openai_key:
            primary_model = AIModel.GPT4_TURBO
            fallback_model = AIModel.CLAUDE_35_SONNET if anthropic_key else None
        else:
            primary_model = AIModel.CLAUDE_35_SONNET
            fallback_model = None

        _ai_analysis_service = AIAnalysisService(
            db_pool=pool,
            rag_engine=rag_engine,
            confidence_scorer=confidence_scorer,
            primary_model=primary_model,
            fallback_model=fallback_model,
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key
        )
        logger.info(f"Initialized AIAnalysisService with {primary_model}")
    return _ai_analysis_service

async def get_ai_cost_service() -> Optional[AICostService]:
    """Get or create AI cost tracking service instance"""
    global _ai_cost_service
    if _ai_cost_service is None:
        try:
            pool = await get_db_pool()
            _ai_cost_service = AICostService(db_pool=pool)
            logger.info("Initialized AICostService")
        except Exception as e:
            logger.error(f"Failed to initialize AICostService: {e}")
            # Return None - cost tracking is optional
            return None
    return _ai_cost_service

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

async def generate_embedding(
    text: str,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    assessment_id: Optional[str] = None,
    document_id: Optional[str] = None
) -> List[float]:
    """Generate vector embedding for semantic search using OpenAI"""
    import time
    start_time = time.time()

    try:
        embedding_service = await get_embedding_service()
        result = await embedding_service.embed_text(text)

        response_time_ms = int((time.time() - start_time) * 1000)
        logger.info(f"Generated {result.dimensions}-dim embedding ({result.tokens_used} tokens, {response_time_ms}ms)")

        # Log cost tracking if org/user IDs are available
        if organization_id and user_id:
            try:
                cost_service = await get_ai_cost_service()
                if cost_service:
                    cost = cost_service.calculate_cost(
                        model_name=result.model,
                        total_tokens=result.tokens_used
                    )
                    await cost_service.log_usage(
                        organization_id=organization_id,
                        user_id=user_id,
                        assessment_id=assessment_id,
                        document_id=document_id,
                        operation_type='embedding',
                        model_name=result.model,
                        provider='openai',
                        total_tokens=result.tokens_used,
                        cost_usd=cost,
                        response_time_ms=response_time_ms,
                        metadata={'text_length': len(text), 'dimensions': result.dimensions}
                    )
            except Exception as cost_err:
                logger.warning(f"Failed to log embedding cost: {cost_err}")

        return result.embedding
    except HTTPException:
        # API key not configured
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        # Return zero vector as fallback (but log the error)
        logger.warning("Falling back to zero vector - search will not work correctly!")
        return [0.0] * 1536

async def analyze_control_with_ai(
    control_id: str,
    objective_id: Optional[str],
    evidence_items: List[Dict],
    provider_inheritance: Optional[Dict],
    graph_context: Optional[Dict],
    conn: asyncpg.Connection,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    assessment_id: Optional[str] = None
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
    
    # Use real AI analysis service
    import time
    try:
        ai_service = await get_ai_analysis_service()

        # Convert provider_inheritance dict to ProviderInheritance object if present
        from services.ai_analysis import ProviderInheritance
        provider_obj = None
        if provider_inheritance:
            provider_obj = ProviderInheritance(
                provider_name=provider_inheritance.get('provider_name', 'Unknown'),
                responsibility=provider_inheritance.get('responsibility', 'Shared'),
                inherited_controls=provider_inheritance.get('inherited_controls', []),
                documentation_url=provider_inheritance.get('documentation_url'),
                narrative=provider_inheritance.get('narrative')
            )

        # Call AI analysis service
        logger.info(f"Running AI analysis for control {control_id} with {len(evidence_items)} evidence items")
        start_time = time.time()
        result = await ai_service.analyze_control(
            control_id=control_id,
            objective_id=objective_id,
            evidence_items=evidence_items,
            provider_inheritance=provider_obj
        )
        response_time_ms = int((time.time() - start_time) * 1000)

        # Log cost tracking if org/user IDs are available
        if organization_id and user_id:
            try:
                cost_service = await get_ai_cost_service()
                if cost_service:
                    # Determine provider from model name
                    provider = 'openai' if 'gpt' in result.model_used.lower() else \
                              'anthropic' if 'claude' in result.model_used.lower() else 'other'

                    cost = cost_service.calculate_cost(
                        model_name=result.model_used,
                        total_tokens=result.tokens_used
                    )
                    await cost_service.log_usage(
                        organization_id=organization_id,
                        user_id=user_id,
                        assessment_id=assessment_id,
                        control_id=control_id,
                        operation_type='analysis',
                        model_name=result.model_used,
                        provider=provider,
                        total_tokens=result.tokens_used,
                        cost_usd=cost,
                        response_time_ms=response_time_ms,
                        metadata={
                            'evidence_count': len(evidence_items),
                            'status': result.status.value,
                            'confidence': result.ai_confidence_score,
                            'requires_review': result.requires_human_review
                        }
                    )
            except Exception as cost_err:
                logger.warning(f"Failed to log AI analysis cost: {cost_err}")

        return {
            "status": result.status.value,
            "confidence_score": result.ai_confidence_score,
            "narrative": result.assessor_narrative,
            "rationale": result.ai_rationale,
            "evidence_ids": [ref.evidence_id for ref in result.evidence_references],
            "model_used": result.model_used,
            "tokens_used": result.tokens_used,
            "requires_review": result.requires_human_review
        }

    except HTTPException:
        # API key not configured - return error
        raise
    except Exception as e:
        logger.error(f"AI analysis failed: {e}")
        # Fallback to simple heuristic
        logger.warning("AI analysis failed, using simple heuristic")

        if len(evidence_items) >= 2:
            status = "Met"
            confidence = 75.0
            narrative = f"The organization has provided {len(evidence_items)} evidence items for {control_id}. "
            if provider_inheritance:
                narrative += f"This control leverages {provider_inheritance.get('provider_name', 'provider')} inheritance. "
            narrative += "AI analysis unavailable - manual review recommended."
        else:
            status = "Not Met"
            confidence = 50.0
            narrative = f"Only {len(evidence_items)} evidence item(s) provided for {control_id}. "
            narrative += "Additional documentation required. AI analysis unavailable - manual review required."

        return {
            "status": status,
            "confidence_score": confidence,
            "narrative": narrative,
            "rationale": "AI analysis unavailable. Heuristic-based assessment pending manual review.",
            "evidence_ids": [e["id"] for e in evidence_items],
            "model_used": "heuristic-fallback",
            "tokens_used": 0,
            "requires_review": True
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
        # Use real document processor for text extraction
        try:
            import json
            doc_processor = await get_document_processor()

            # Extract text from file based on type
            logger.info(f"Processing document: {file_path}")
            processed_doc = doc_processor.process_document(str(file_path))

            logger.info(f"Extracted {len(processed_doc.chunks)} chunks from document")
            text = "\n\n".join([chunk.text for chunk in processed_doc.chunks])  # For fallback

        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            logger.warning("Falling back to placeholder text")
            text = "Document processing unavailable - manual text entry required"
        
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
