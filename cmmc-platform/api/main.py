# CMMC Compliance Platform - FastAPI Service
# Assessor-grade endpoints for evidence management, AI analysis, and report generation

from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, BackgroundTasks, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from enum import Enum
from uuid import UUID
import hashlib
import uuid
import asyncpg
from pathlib import Path
import logging
import os
from contextlib import asynccontextmanager

# Import AI/RAG services
from api.services import (
    create_embedding_service,
    create_ai_analyzer,
    RAGService,
    EmbeddingService,
    AIAnalyzer
)

# Import SPRS calculator
from api.sprs_calculator import (
    calculate_sprs_score,
    save_sprs_score,
    get_sprs_score_history,
    get_sprs_score_trend
)

# Import monitoring dashboard
from api.monitoring_dashboard import (
    get_dashboard_summary,
    get_control_compliance_overview,
    get_recent_activity,
    get_integration_status,
    get_risk_metrics,
    get_recent_alerts,
    get_evidence_statistics
)

# Import authentication
from api.auth import (
    login,
    create_user,
    LoginRequest,
    CreateUserRequest,
    AuthToken,
    UserRole
)

# Import OAuth
from api.oauth import oauth, handle_oauth_callback, FRONTEND_URL

# Note: FastAPI app initialization will be updated after lifespan is defined
# Placeholder for now - will be moved after lifespan definition

# Security
security = HTTPBearer()

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/cmmc_platform")
    OBJECT_STORAGE_PATH = os.getenv("OBJECT_STORAGE_PATH", "/var/cmmc/evidence")

    # AI Configuration
    AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")  # openai or anthropic
    AI_MODEL = os.getenv("AI_MODEL", "gpt-4-turbo-preview")
    AI_API_KEY = os.getenv("AI_API_KEY", "")

    # Embedding Configuration
    EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "openai")  # openai or sentence_transformers
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")  # Use AI_API_KEY if not set

config = Config()

# Global service instances
embedding_service: Optional[EmbeddingService] = None
rag_service: Optional[RAGService] = None
ai_analyzer: Optional[AIAnalyzer] = None

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
    assessment_id: UUID
    title: str
    document_type: str = Field(..., description="policy, procedure, ssp, manual, etc.")
    control_id: Optional[str] = None
    auto_chunk: bool = True
    auto_embed: bool = True

class DocumentChunk(BaseModel):
    id: UUID
    chunk_text: str
    chunk_index: int
    control_id: Optional[str]
    objective_id: Optional[str]
    method: Optional[AssessmentMethod]

class DocumentIngestResponse(BaseModel):
    document_id: UUID
    chunks_created: int
    file_hash: str
    processing_time_ms: int

class ControlAnalysisRequest(BaseModel):
    assessment_id: UUID
    control_id: str
    objective_id: Optional[str] = None
    include_provider_inheritance: bool = True
    include_diagram_context: bool = True
    max_evidence_items: int = 10

class EvidenceReference(BaseModel):
    id: UUID
    title: str
    evidence_type: EvidenceType
    file_hash: str
    collected_date: datetime
    confidence_contribution: float = Field(..., ge=0.0, le=100.0)

class ControlAnalysisResponse(BaseModel):
    control_id: str
    objective_id: Optional[str]
    finding_id: UUID
    status: FindingStatus
    assessor_narrative: str
    ai_confidence_score: float
    ai_rationale: str
    evidence_used: List[EvidenceReference]
    provider_inheritance: Optional[Dict[str, Any]]
    graph_context: Optional[Dict[str, Any]]
    processing_time_ms: int

class SSPExportRequest(BaseModel):
    assessment_id: UUID
    include_inherited_controls: bool = True
    include_diagrams: bool = True
    format: str = "docx"  # docx, pdf, json

class SSPSection(BaseModel):
    section_number: str
    title: str
    content: str
    controls_covered: List[str]

class SSPExportResponse(BaseModel):
    assessment_id: UUID
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
    assessment_id: UUID
    format: str = "xlsx"  # xlsx, csv, json

class POAMExportResponse(BaseModel):
    assessment_id: UUID
    file_path: str
    file_hash: str
    items_count: int
    generation_time_ms: int

class EvidenceUploadRequest(BaseModel):
    assessment_id: UUID
    control_id: str
    objective_id: Optional[str]
    title: str
    description: Optional[str]
    evidence_type: EvidenceType
    method: AssessmentMethod

class EvidenceUploadResponse(BaseModel):
    evidence_id: UUID
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
    if not embedding_service:
        logger.warning("Embedding service not available, using zero vector")
        return [0.0] * 1536

    try:
        return await embedding_service.generate_embedding(text)
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}")
        return [0.0] * 1536

async def analyze_control_with_ai(
    control_id: str,
    objective_id: Optional[str],
    evidence_items: List[Dict],
    provider_inheritance: Optional[Dict],
    graph_context: Optional[Dict],
    conn: asyncpg.Connection,
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

    if not control:
        raise ValueError(f"Control {control_id} not found")

    # Use AI analyzer if available
    if ai_analyzer and assessment_id:
        try:
            # Prepare control data
            control_data = {
                'id': control['id'],
                'title': control['title'],
                'requirement_text': control['requirement_text'],
                'objective_id': objective_id,
                'objective_text': objective['determination_statement'] if objective else None,
                'method': objective['method'] if objective else None
            }

            # Call AI analyzer
            analysis = await ai_analyzer.analyze_control(
                control_data=control_data,
                evidence_items=evidence_items,
                assessment_id=assessment_id,
                include_rag=True,
                provider_inheritance=provider_inheritance,
                graph_context=graph_context
            )

            # Map AI response to expected format
            return {
                "status": analysis.get('determination', 'Not Assessed'),
                "confidence_score": analysis.get('confidence_score', 0.0),
                "narrative": analysis.get('assessor_narrative', ''),
                "rationale": analysis.get('rationale', ''),
                "evidence_ids": [e.get("id") for e in evidence_items if e.get("id")],
                "key_findings": analysis.get('key_findings', []),
                "gaps_identified": analysis.get('gaps_identified', []),
                "recommendations": analysis.get('recommendations', [])
            }

        except Exception as e:
            logger.error(f"AI analysis failed: {e}")
            # Fall through to fallback logic

    # Fallback: simple heuristic if AI unavailable
    logger.warning("Using fallback heuristic analysis (AI service unavailable)")

    if len(evidence_items) >= 2:
        status = "Met"
        confidence = 75.0
        narrative = f"The organization has demonstrated compliance with {control_id}. "
        if provider_inheritance:
            narrative += f"This control leverages {provider_inheritance['provider_name']} inheritance for {provider_inheritance['responsibility']} responsibilities. "
        narrative += f"Evidence review shows {len(evidence_items)} supporting artifacts."
    else:
        status = "Not Met"
        confidence = 50.0
        narrative = f"Insufficient evidence to demonstrate compliance with {control_id}. "
        narrative += f"Only {len(evidence_items)} evidence item(s) provided. Additional documentation required."

    rationale = f"Heuristic analysis based on {len(evidence_items)} evidence items. "
    rationale += "Note: AI-assisted analysis unavailable."

    return {
        "status": status,
        "confidence_score": confidence,
        "narrative": narrative,
        "rationale": rationale,
        "evidence_ids": [e.get("id") for e in evidence_items if e.get("id")]
    }

# ============================================================================
# API ENDPOINTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown"""
    global embedding_service, rag_service, ai_analyzer, db_pool

    # Startup
    try:
        # Initialize database pool
        await get_db_pool()
        logger.info("Database pool initialized")

        # Initialize embedding service
        try:
            embedding_api_key = config.EMBEDDING_API_KEY or config.AI_API_KEY
            embedding_service = create_embedding_service(
                provider=config.EMBEDDING_PROVIDER,
                api_key=embedding_api_key,
                model_name=config.EMBEDDING_MODEL
            )
            logger.info(f"Embedding service initialized: {config.EMBEDDING_PROVIDER}/{config.EMBEDDING_MODEL}")
        except Exception as e:
            logger.warning(f"Failed to initialize embedding service: {e}")
            embedding_service = None

        # Initialize RAG service
        try:
            if embedding_service:
                pool = await get_db_pool()
                rag_service = RAGService(
                    embedding_service=embedding_service,
                    db_pool=pool
                )
                logger.info("RAG service initialized")
            else:
                logger.warning("RAG service not initialized (embedding service unavailable)")
        except Exception as e:
            logger.warning(f"Failed to initialize RAG service: {e}")
            rag_service = None

        # Initialize AI analyzer
        try:
            ai_analyzer = create_ai_analyzer(
                provider=config.AI_PROVIDER,
                api_key=config.AI_API_KEY,
                model_name=config.AI_MODEL,
                rag_service=rag_service
            )
            logger.info(f"AI analyzer initialized: {config.AI_PROVIDER}/{config.AI_MODEL}")
        except Exception as e:
            logger.warning(f"Failed to initialize AI analyzer: {e}")
            ai_analyzer = None
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise

    yield

    # Shutdown
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

# Initialize FastAPI with lifespan
app = FastAPI(
    title="CMMC Compliance Platform API",
    version="1.0.0",
    description="Assessor-grade API for CMMC Level 1 & 2 compliance automation",
    lifespan=lifespan
)

# ============================================================================
# SECURITY MIDDLEWARE - OWASP API Security Top 10
# ============================================================================

from starlette.middleware.cors import CORSMiddleware
from api.security_middleware import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    InputValidationMiddleware,
    AuditLoggingMiddleware,
    get_cors_config
)

# Add security middleware (order matters - first added = outermost layer)

# 1. Audit logging (outermost - logs everything)
app.add_middleware(AuditLoggingMiddleware)

# 2. Security headers
app.add_middleware(SecurityHeadersMiddleware)

# 3. CORS (must be before rate limiting to handle preflight requests)
cors_config = get_cors_config()
app.add_middleware(CORSMiddleware, **cors_config)

# 4. Rate limiting (prevent abuse)
app.add_middleware(RateLimitMiddleware)

# 5. Input validation (innermost - validates all inputs before processing)
app.add_middleware(InputValidationMiddleware)

logger.info("Security middleware initialized with OWASP API Security protections")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# ----------------------------------------------------------------------------
# AUTHENTICATION ENDPOINTS
# ----------------------------------------------------------------------------

@app.post("/api/v1/auth/login", response_model=AuthToken)
async def login_endpoint(
    request: LoginRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Authenticate user and generate JWT tokens.

    Returns:
    - access_token: JWT token for API authentication (60 min expiry)
    - refresh_token: Token to refresh access token (30 day expiry)
    - expires_in: Seconds until access token expires
    """
    return await login(request, conn)

class SignupRequest(BaseModel):
    """Signup request for new users."""
    email: str
    password: str
    firstName: str
    lastName: str
    company: str

@app.post("/api/v1/auth/signup", response_model=Dict[str, str])
async def signup_endpoint(
    request: SignupRequest,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Create a new user account with organization.

    This endpoint:
    1. Creates a new organization for the company
    2. Creates a user account as the admin of that organization
    3. Returns the user ID and success message
    """
    try:
        # First, create the organization
        org_id = await conn.fetchval(
            """
            INSERT INTO organizations (name, active)
            VALUES ($1, TRUE)
            RETURNING id
            """,
            request.company
        )

        # Create the user as an admin of the organization
        full_name = f"{request.firstName} {request.lastName}"
        user_request = CreateUserRequest(
            email=request.email,
            password=request.password,
            full_name=full_name,
            organization_id=str(org_id),
            role=UserRole.ADMIN
        )

        user_id = await create_user(user_request, conn)

        logger.info(f"New signup: {request.email} for organization {request.company}")

        return {
            "user_id": user_id,
            "organization_id": str(org_id),
            "message": "Account created successfully"
        }

    except Exception as e:
        logger.error(f"Signup error: {str(e)}")
        if "already exists" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account"
        )

# ----------------------------------------------------------------------------
# OAUTH ENDPOINTS
# ----------------------------------------------------------------------------

@app.get("/api/v1/auth/google")
async def google_login(request: Request):
    """
    Initiate Google OAuth login flow.

    Redirects user to Google login page.
    """
    redirect_uri = request.url_for('google_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)

@app.get("/api/v1/auth/google/callback")
async def google_callback(
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Handle Google OAuth callback.

    Processes OAuth response, creates/finds user, generates JWT tokens,
    and redirects to frontend with tokens.
    """
    try:
        # Get OAuth token from Google
        token = await oauth.google.authorize_access_token(request)

        # Get user info from Google
        user_info = token.get('userinfo')
        if not user_info:
            # Fetch user info if not in token
            resp = await oauth.google.get('https://www.googleapis.com/oauth2/v3/userinfo', token=token)
            user_info = resp.json()

        # Handle OAuth callback and generate tokens
        auth_token = await handle_oauth_callback('google', user_info, conn)

        # Redirect to frontend with tokens in URL params (will be moved to localStorage by frontend)
        redirect_url = f"{FRONTEND_URL}/?access_token={auth_token.access_token}&refresh_token={auth_token.refresh_token}&auth_success=true"

        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"Google OAuth error: {str(e)}")
        # Redirect to frontend with error
        return RedirectResponse(url=f"{FRONTEND_URL}/?auth_error={str(e)}")

@app.get("/api/v1/auth/microsoft")
async def microsoft_login(request: Request):
    """
    Initiate Microsoft OAuth login flow.

    Redirects user to Microsoft login page.
    """
    redirect_uri = request.url_for('microsoft_callback')
    return await oauth.microsoft.authorize_redirect(request, redirect_uri)

@app.get("/api/v1/auth/microsoft/callback")
async def microsoft_callback(
    request: Request,
    conn: asyncpg.Connection = Depends(get_db)
):
    """
    Handle Microsoft OAuth callback.

    Processes OAuth response, creates/finds user, generates JWT tokens,
    and redirects to frontend with tokens.
    """
    try:
        # Get OAuth token from Microsoft
        token = await oauth.microsoft.authorize_access_token(request)

        # Get user info from Microsoft
        resp = await oauth.microsoft.get('https://graph.microsoft.com/v1.0/me', token=token)
        user_info = resp.json()

        # Handle OAuth callback and generate tokens
        auth_token = await handle_oauth_callback('microsoft', user_info, conn)

        # Redirect to frontend with tokens in URL params
        redirect_url = f"{FRONTEND_URL}/?access_token={auth_token.access_token}&refresh_token={auth_token.refresh_token}&auth_success=true"

        return RedirectResponse(url=redirect_url)

    except Exception as e:
        logger.error(f"Microsoft OAuth error: {str(e)}")
        # Redirect to frontend with error
        return RedirectResponse(url=f"{FRONTEND_URL}/?auth_error={str(e)}")

@app.get("/health/ai")
async def ai_health_check():
    """Health check for AI/RAG services"""
    health_status = {
        "timestamp": datetime.utcnow().isoformat(),
        "services": {}
    }

    # Check embedding service
    if embedding_service:
        try:
            embed_health = await embedding_service.healthcheck()
            health_status["services"]["embedding"] = embed_health
        except Exception as e:
            health_status["services"]["embedding"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        health_status["services"]["embedding"] = {
            "status": "not_initialized"
        }

    # Check RAG service
    if rag_service:
        try:
            rag_health = await rag_service.healthcheck()
            health_status["services"]["rag"] = rag_health
        except Exception as e:
            health_status["services"]["rag"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        health_status["services"]["rag"] = {
            "status": "not_initialized"
        }

    # Check AI analyzer
    if ai_analyzer:
        try:
            ai_health = await ai_analyzer.healthcheck()
            health_status["services"]["ai_analyzer"] = ai_health
        except Exception as e:
            health_status["services"]["ai_analyzer"] = {
                "status": "error",
                "error": str(e)
            }
    else:
        health_status["services"]["ai_analyzer"] = {
            "status": "not_initialized"
        }

    # Overall status
    all_healthy = all(
        svc.get("status") == "healthy"
        for svc in health_status["services"].values()
        if isinstance(svc, dict)
    )
    health_status["overall_status"] = "healthy" if all_healthy else "degraded"

    return health_status

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
        # For now, use placeholder text
        text = "Placeholder text content - implement PDF/DOCX extraction"

        # Use RAG service for chunking and embedding if available
        if rag_service and request.auto_embed:
            try:
                chunks_created = await rag_service.chunk_and_embed_document(
                    document_id=str(document_id),
                    text=text,
                    control_id=request.control_id,
                    doc_type=request.document_type
                )
            except Exception as e:
                logger.error(f"RAG service chunking failed: {e}")
                # Fallback to simple chunking
                chunks = await chunk_document(text)
                for idx, chunk_text in enumerate(chunks):
                    embedding = await generate_embedding(chunk_text) if request.auto_embed else None
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
        else:
            # Fallback to simple chunking
            chunks = await chunk_document(text)
            for idx, chunk_text in enumerate(chunks):
                embedding = await generate_embedding(chunk_text) if request.auto_embed else None
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
        conn,
        assessment_id=str(request.assessment_id)
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
    assessment_id: UUID,
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
    assessment_id: UUID,
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
    assessment_id: UUID,
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
    assessment_id: UUID,
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
    assessment_id: UUID,
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
    organization_id: UUID,
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
    assessment_id: UUID,
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
    organization_id: UUID,
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
    organization_id: UUID,
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
    assessment_id: UUID,
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
    organization_id: UUID,
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
    assessment_id: UUID,
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
