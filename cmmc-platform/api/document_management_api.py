"""
Document Management API for RAG System
Handles document upload, processing, embedding, and querying
"""

import os
import uuid
import asyncio
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Any
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from database import database, get_database, Database
from services.document_processor import DocumentProcessor, ChunkingStrategy
from services.embedding_service import EmbeddingService, EmbeddingModel
from services.rag_engine import RAGEngine, SimilarityMetric, ReRankingStrategy
from middleware.auth_middleware import get_auth_context, AuthContext

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================

class DocumentUploadResponse(BaseModel):
    """Response after document upload"""
    document_id: str
    filename: str
    file_size: int
    status: str = "uploaded"
    message: str


class DocumentProcessRequest(BaseModel):
    """Request to process uploaded document"""
    document_id: str
    chunk_size: int = Field(default=512, ge=100, le=2000)
    chunk_overlap: int = Field(default=50, ge=0, le=500)
    chunking_strategy: str = Field(default="hybrid")
    auto_embed: bool = Field(default=True)


class DocumentProcessResponse(BaseModel):
    """Response after document processing"""
    document_id: str
    total_chunks: int
    status: str
    processing_time_seconds: float


class DocumentListItem(BaseModel):
    """Document list item"""
    id: str
    filename: str
    title: Optional[str]
    file_type: str
    file_size: int
    total_chunks: int
    embedded_chunks: int
    processing_status: str
    uploaded_at: datetime
    processed_at: Optional[datetime]


class RAGQueryRequest(BaseModel):
    """RAG query request"""
    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=20)
    rerank_top_k: int = Field(default=10, ge=1, le=50)
    control_id: Optional[str] = None
    objective_id: Optional[str] = None
    assessment_id: Optional[str] = None
    include_context: bool = Field(default=True)


class RAGChunkResult(BaseModel):
    """Single RAG search result chunk"""
    chunk_id: str
    document_id: str
    document_title: Optional[str]
    chunk_text: str
    chunk_index: int
    similarity_score: float
    control_id: Optional[str] = None


class RAGQueryResponse(BaseModel):
    """RAG query response"""
    query: str
    results: List[RAGChunkResult]
    total_results: int
    context: Optional[str] = None


class DocumentStatsResponse(BaseModel):
    """Document statistics"""
    total_documents: int
    total_chunks: int
    embedded_chunks: int
    embedding_coverage: float
    storage_size_mb: float
    documents_by_type: List[Dict[str, Any]]


# =============================================================================
# Dependencies
# =============================================================================

async def get_db():
    """Get database connection (uses global database instance)"""
    return database


async def get_document_processor():
    """Get document processor instance"""
    return DocumentProcessor(
        chunk_size=512,
        chunk_overlap=50,
        chunking_strategy=ChunkingStrategy.HYBRID
    )


async def get_embedding_service():
    """Get embedding service instance"""
    return EmbeddingService(model=EmbeddingModel.OPENAI_3_SMALL)


async def get_rag_engine(db: Database = Depends(get_db)):
    """Get RAG engine instance"""
    embedding_service = await get_embedding_service()
    return RAGEngine(
        db_pool=db.get_pool(),
        embedding_service=embedding_service,
        similarity_metric=SimilarityMetric.COSINE,
        reranking_strategy=ReRankingStrategy.MMR
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = None,
    organization_id: Optional[str] = None,
    assessment_id: Optional[str] = None,
    auth_context: AuthContext = Depends(get_auth_context),
    db: Database = Depends(get_db)
):
    """
    Upload a document for RAG processing

    Accepts PDF, DOCX, TXT files
    """
    # Validate file type
    allowed_extensions = {'.pdf', '.docx', '.doc', '.txt', '.md'}
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        # Create upload directory if it doesn't exist
        upload_dir = Path("/var/cmmc/documents")
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        document_id = str(uuid.uuid4())
        filename = f"{document_id}{file_ext}"
        file_path = upload_dir / filename

        # Save file
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = file_path.stat().st_size

        # Store document metadata in database
        pool = db.get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO documents (
                    id, filename, title, file_path, file_type, file_size,
                    organization_id, assessment_id, uploaded_by, uploaded_at,
                    processing_status
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            """, document_id, file.filename, title or file.filename,
                str(file_path), file_ext[1:], file_size,
                organization_id, assessment_id, auth_context.user_id,
                datetime.utcnow(), 'uploaded'
            )

        logger.info(f"Document uploaded: {document_id} ({file.filename})")

        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            file_size=file_size,
            status="uploaded",
            message="Document uploaded successfully. Ready for processing."
        )

    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        # Clean up file if it was created
        if file_path and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_document_background(
    document_id: str,
    chunk_size: int,
    chunk_overlap: int,
    chunking_strategy: str,
    auto_embed: bool,
    db: Database
):
    """Background task to process document"""
    start_time = datetime.utcnow()

    try:
        # Get document from database
        pool = db.get_pool()
        async with pool.acquire() as conn:
            doc = await conn.fetchrow(
                "SELECT * FROM documents WHERE id = $1", document_id
            )

            if not doc:
                logger.error(f"Document not found: {document_id}")
                return

            # Update status to processing
            await conn.execute(
                "UPDATE documents SET processing_status = $1 WHERE id = $2",
                'processing', document_id
            )

        # Process document
        processor = DocumentProcessor(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunking_strategy=ChunkingStrategy(chunking_strategy)
        )

        processed_doc = processor.process_document(
            file_path=doc['file_path'],
            title=doc['title']
        )

        # Store chunks in database
        async with pool.acquire() as conn:
            for chunk in processed_doc.chunks:
                chunk_id = str(uuid.uuid4())
                await conn.execute("""
                    INSERT INTO document_chunks (
                        id, document_id, chunk_index, chunk_text,
                        start_char, end_char, token_count, created_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """, chunk_id, document_id, chunk.chunk_index, chunk.text,
                    chunk.start_char, chunk.end_char, chunk.token_count,
                    datetime.utcnow()
                )

            # Update document status
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            await conn.execute("""
                UPDATE documents
                SET processing_status = $1,
                    total_chunks = $2,
                    processed_at = $3,
                    processing_time_seconds = $4
                WHERE id = $5
            """, 'processed', len(processed_doc.chunks), datetime.utcnow(),
                processing_time, document_id
            )

        # Auto-embed if requested
        if auto_embed:
            embedding_service = EmbeddingService(model=EmbeddingModel.OPENAI_3_SMALL)

            async with pool.acquire() as conn:
                chunks = await conn.fetch(
                    "SELECT id, chunk_text FROM document_chunks WHERE document_id = $1",
                    document_id
                )

                for chunk in chunks:
                    try:
                        embedding_result = await embedding_service.embed_text(chunk['chunk_text'])
                        await conn.execute(
                            "UPDATE document_chunks SET embedding = $1 WHERE id = $2",
                            embedding_result.embedding, chunk['id']
                        )
                    except Exception as e:
                        logger.error(f"Error embedding chunk {chunk['id']}: {e}")

                # Update status
                await conn.execute(
                    "UPDATE documents SET processing_status = $1 WHERE id = $2",
                    'embedded', document_id
                )

        logger.info(f"Document processed: {document_id} ({len(processed_doc.chunks)} chunks)")

    except Exception as e:
        logger.error(f"Error processing document {document_id}: {e}")

        # Update status to failed
        async with db.get_pool().acquire() as conn:
            await conn.execute(
                "UPDATE documents SET processing_status = $1, error_message = $2 WHERE id = $3",
                'failed', str(e), document_id
            )


@router.post("/documents/process", response_model=DocumentProcessResponse)
async def process_document(
    request: DocumentProcessRequest,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db),
    auth_context: AuthContext = Depends(get_auth_context)
):
    """
    Process an uploaded document: extract text, chunk, and optionally embed

    Processing happens in the background
    """
    # Verify document exists
    pool = db.get_pool()
    async with pool.acquire() as conn:
        doc = await conn.fetchrow(
            "SELECT * FROM documents WHERE id = $1", request.document_id
        )

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        if doc['processing_status'] not in ['uploaded', 'failed']:
            raise HTTPException(
                status_code=400,
                detail=f"Document is already being processed (status: {doc['processing_status']})"
            )

    # Queue background processing
    background_tasks.add_task(
        process_document_background,
        document_id=request.document_id,
        chunk_size=request.chunk_size,
        chunk_overlap=request.chunk_overlap,
        chunking_strategy=request.chunking_strategy,
        auto_embed=request.auto_embed,
        db=db
    )

    return DocumentProcessResponse(
        document_id=request.document_id,
        total_chunks=0,  # Will be updated when processing completes
        status="processing",
        processing_time_seconds=0.0
    )


@router.get("/documents", response_model=List[DocumentListItem])
async def list_documents(
    organization_id: Optional[str] = Query(None),
    assessment_id: Optional[str] = Query(None),
    processing_status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Database = Depends(get_db),
    auth_context: AuthContext = Depends(get_auth_context)
):
    """List documents with optional filtering"""
    query = """
        SELECT
            d.id,
            d.filename,
            d.title,
            d.file_type,
            d.file_size,
            d.total_chunks,
            d.processing_status,
            d.uploaded_at,
            d.processed_at,
            COUNT(CASE WHEN dc.embedding IS NOT NULL THEN 1 END) as embedded_chunks
        FROM documents d
        LEFT JOIN document_chunks dc ON d.id = dc.document_id
        WHERE 1=1
    """

    params = []
    param_count = 1

    if organization_id:
        query += f" AND d.organization_id = ${param_count}"
        params.append(organization_id)
        param_count += 1

    if assessment_id:
        query += f" AND d.assessment_id = ${param_count}"
        params.append(assessment_id)
        param_count += 1

    if processing_status:
        query += f" AND d.processing_status = ${param_count}"
        params.append(processing_status)
        param_count += 1

    query += f"""
        GROUP BY d.id
        ORDER BY d.uploaded_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

    documents = [
        DocumentListItem(
            id=str(row['id']),
            filename=row['filename'],
            title=row['title'],
            file_type=row['file_type'],
            file_size=row['file_size'],
            total_chunks=row['total_chunks'] or 0,
            embedded_chunks=row['embedded_chunks'] or 0,
            processing_status=row['processing_status'],
            uploaded_at=row['uploaded_at'],
            processed_at=row['processed_at']
        )
        for row in rows
    ]

    return documents


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    db: Database = Depends(get_db),
    auth_context: AuthContext = Depends(get_auth_context)
):
    """Delete a document and its chunks"""
    pool = db.get_pool()

    async with pool.acquire() as conn:
        # Get document
        doc = await conn.fetchrow(
            "SELECT file_path FROM documents WHERE id = $1", document_id
        )

        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

        # Delete file
        file_path = Path(doc['file_path'])
        if file_path.exists():
            file_path.unlink()

        # Delete from database (cascades to chunks)
        await conn.execute("DELETE FROM documents WHERE id = $1", document_id)

    logger.info(f"Document deleted: {document_id}")

    return {"status": "deleted", "document_id": document_id}


@router.post("/rag/query", response_model=RAGQueryResponse)
async def rag_query(
    request: RAGQueryRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine),
    auth_context: AuthContext = Depends(get_auth_context)
):
    """
    Query documents using RAG (Retrieval-Augmented Generation)

    Performs semantic search across embedded document chunks
    """
    try:
        # Retrieve context
        rag_context = await rag_engine.retrieve_context(
            query=request.query,
            top_k=request.top_k,
            rerank_top_k=request.rerank_top_k,
            control_id=request.control_id,
            objective_id=request.objective_id,
            assessment_id=request.assessment_id
        )

        # Build prompt context if requested
        context_text = None
        if request.include_context:
            context_text = await rag_engine.build_prompt_context(rag_context)

        # Convert to response format
        results = [
            RAGChunkResult(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                document_title=chunk.document_title,
                chunk_text=chunk.chunk_text,
                chunk_index=chunk.chunk_index,
                similarity_score=chunk.similarity_score,
                control_id=chunk.control_id
            )
            for chunk in rag_context.retrieved_chunks
        ]

        return RAGQueryResponse(
            query=request.query,
            results=results,
            total_results=rag_context.total_retrieved,
            context=context_text
        )

    except Exception as e:
        logger.error(f"Error in RAG query: {e}")
        raise HTTPException(status_code=500, detail=f"Query failed: {str(e)}")


@router.get("/rag/stats", response_model=DocumentStatsResponse)
async def get_rag_stats(
    rag_engine: RAGEngine = Depends(get_rag_engine),
    auth_context: AuthContext = Depends(get_auth_context)
):
    """Get RAG system statistics"""
    try:
        stats = await rag_engine.get_statistics()

        # Calculate storage size
        upload_dir = Path("/var/cmmc/documents")
        storage_size = sum(f.stat().st_size for f in upload_dir.glob("*") if f.is_file()) if upload_dir.exists() else 0
        storage_size_mb = storage_size / (1024 * 1024)

        return DocumentStatsResponse(
            total_documents=stats['total_documents'],
            total_chunks=stats['total_chunks'],
            embedded_chunks=stats['embedded_chunks'],
            embedding_coverage=stats['embedding_coverage'],
            storage_size_mb=round(storage_size_mb, 2),
            documents_by_type=stats.get('chunks_by_type', [])
        )

    except Exception as e:
        logger.error(f"Error getting RAG stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")
