"""
Document Processing API Endpoints
Handles document upload, chunking, embedding, and RAG retrieval
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, BackgroundTasks
from pydantic import BaseModel, UUID4, Field
from typing import List, Optional, Dict, Any
from pathlib import Path
import logging
import uuid
import os
import asyncpg

from services.document_processor import DocumentProcessor, ChunkingStrategy
from services.embedding_service import EmbeddingService, EmbeddingModel
from services.rag_engine import RAGEngine, SimilarityMetric, ReRankingStrategy

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class DocumentUploadRequest(BaseModel):
    """Request model for document upload"""
    assessment_id: UUID4
    title: Optional[str] = None
    document_type: str = Field(..., description="policy, procedure, ssp, manual, guide, evidence")
    control_id: Optional[str] = None
    auto_chunk: bool = True
    auto_embed: bool = True


class DocumentUploadResponse(BaseModel):
    """Response model for document upload"""
    document_id: UUID4
    file_hash: str
    title: str
    total_chunks: int
    chunks_embedded: int
    message: str


class ChunkRequest(BaseModel):
    """Request model for manual chunking"""
    document_id: UUID4
    chunk_size: int = 512
    chunk_overlap: int = 50
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.HYBRID


class ChunkResponse(BaseModel):
    """Response model for chunking"""
    document_id: UUID4
    total_chunks: int
    message: str


class EmbedRequest(BaseModel):
    """Request model for manual embedding"""
    document_id: UUID4
    embedding_model: EmbeddingModel = EmbeddingModel.OPENAI_3_LARGE


class EmbedResponse(BaseModel):
    """Response model for embedding"""
    document_id: UUID4
    chunks_embedded: int
    total_tokens: int
    estimated_cost: float
    message: str


class SearchRequest(BaseModel):
    """Request model for semantic search"""
    query: str
    top_k: int = 5
    control_id: Optional[str] = None
    objective_id: Optional[str] = None
    assessment_id: Optional[UUID4] = None
    document_type: Optional[str] = None


class SearchResult(BaseModel):
    """Individual search result"""
    chunk_id: UUID4
    chunk_text: str
    similarity_score: float
    document_title: str
    document_type: Optional[str]
    control_id: Optional[str]
    chunk_index: int


class SearchResponse(BaseModel):
    """Response model for semantic search"""
    query: str
    results: List[SearchResult]
    total_retrieved: int


class ControlContextRequest(BaseModel):
    """Request model for control context retrieval"""
    control_id: str
    assessment_id: Optional[UUID4] = None
    max_chunks: int = 10


class ControlContextResponse(BaseModel):
    """Response model for control context"""
    control_id: str
    chunks: List[SearchResult]
    formatted_context: str


# ============================================================================
# DEPENDENCIES
# ============================================================================

# Global instances (will be initialized on startup)
_db_pool: Optional[asyncpg.Pool] = None
_document_processor: Optional[DocumentProcessor] = None
_embedding_service: Optional[EmbeddingService] = None
_rag_engine: Optional[RAGEngine] = None


async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool"""
    global _db_pool
    if _db_pool is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL not set")
        _db_pool = await asyncpg.create_pool(database_url, min_size=5, max_size=20)
    return _db_pool


def get_document_processor() -> DocumentProcessor:
    """Get document processor instance"""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor(
            chunk_size=512,
            chunk_overlap=50,
            chunking_strategy=ChunkingStrategy.HYBRID
        )
    return _document_processor


def get_embedding_service() -> EmbeddingService:
    """Get embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService(
            model=EmbeddingModel.OPENAI_3_LARGE
        )
    return _embedding_service


async def get_rag_engine() -> RAGEngine:
    """Get RAG engine instance"""
    global _rag_engine
    if _rag_engine is None:
        db_pool = await get_db_pool()
        embedding_service = get_embedding_service()
        _rag_engine = RAGEngine(
            db_pool=db_pool,
            embedding_service=embedding_service,
            similarity_metric=SimilarityMetric.COSINE,
            reranking_strategy=ReRankingStrategy.MMR
        )
    return _rag_engine


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    assessment_id: UUID4 = None,
    title: Optional[str] = None,
    document_type: str = "document",
    control_id: Optional[str] = None,
    auto_chunk: bool = True,
    auto_embed: bool = True,
    background_tasks: BackgroundTasks = None,
    db_pool: asyncpg.Pool = Depends(get_db_pool),
    processor: DocumentProcessor = Depends(get_document_processor),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
):
    """
    Upload and process a document

    - Saves file to storage
    - Extracts text (PDF support)
    - Optionally chunks text
    - Optionally generates embeddings
    """
    try:
        # Create upload directory
        upload_dir = Path(os.getenv("EVIDENCE_PATH", "/var/cmmc/evidence"))
        upload_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique filename
        file_ext = Path(file.filename).suffix
        file_id = uuid.uuid4()
        file_path = upload_dir / f"{file_id}{file_ext}"

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        logger.info(f"Saved file to {file_path}")

        # Process document
        processed_doc = processor.process_document(
            file_path=str(file_path),
            title=title or file.filename
        )

        # Insert document record
        async with db_pool.acquire() as conn:
            document_id = await conn.fetchval("""
                INSERT INTO documents (assessment_id, title, document_type, file_path, file_hash)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id
            """, assessment_id, processed_doc.title, document_type, str(file_path), processed_doc.file_hash)

        logger.info(f"Created document record: {document_id}")

        chunks_embedded = 0

        if auto_chunk:
            # Insert chunks
            async with db_pool.acquire() as conn:
                for chunk in processed_doc.chunks:
                    await conn.execute("""
                        INSERT INTO document_chunks (document_id, chunk_index, chunk_text, control_id, doc_type)
                        VALUES ($1, $2, $3, $4, $5)
                    """, document_id, chunk.chunk_index, chunk.text, control_id, document_type)

            logger.info(f"Inserted {len(processed_doc.chunks)} chunks")

            if auto_embed:
                # Generate embeddings in background
                if background_tasks:
                    background_tasks.add_task(
                        embed_document_chunks,
                        document_id=document_id,
                        db_pool=db_pool,
                        embedding_service=embedding_service
                    )
                    chunks_embedded = len(processed_doc.chunks)
                else:
                    # Synchronous embedding
                    chunks_embedded = await embed_document_chunks(
                        document_id=document_id,
                        db_pool=db_pool,
                        embedding_service=embedding_service
                    )

        return DocumentUploadResponse(
            document_id=document_id,
            file_hash=processed_doc.file_hash,
            title=processed_doc.title,
            total_chunks=len(processed_doc.chunks) if auto_chunk else 0,
            chunks_embedded=chunks_embedded,
            message=f"Document uploaded and processed successfully"
        )

    except Exception as e:
        logger.error(f"Error uploading document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chunk", response_model=ChunkResponse)
async def chunk_document(
    request: ChunkRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Manually chunk an existing document

    - Retrieves document from database
    - Applies chunking strategy
    - Stores chunks
    """
    try:
        processor = DocumentProcessor(
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            chunking_strategy=request.chunking_strategy
        )

        # Get document
        async with db_pool.acquire() as conn:
            doc = await conn.fetchrow("""
                SELECT file_path, document_type
                FROM documents
                WHERE id = $1
            """, request.document_id)

            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")

            # Delete existing chunks
            await conn.execute("""
                DELETE FROM document_chunks WHERE document_id = $1
            """, request.document_id)

        # Process document
        processed_doc = processor.process_document(file_path=doc['file_path'])

        # Insert new chunks
        async with db_pool.acquire() as conn:
            for chunk in processed_doc.chunks:
                await conn.execute("""
                    INSERT INTO document_chunks (document_id, chunk_index, chunk_text, doc_type)
                    VALUES ($1, $2, $3, $4)
                """, request.document_id, chunk.chunk_index, chunk.text, doc['document_type'])

        return ChunkResponse(
            document_id=request.document_id,
            total_chunks=len(processed_doc.chunks),
            message=f"Document chunked successfully with {request.chunking_strategy} strategy"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error chunking document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/embed", response_model=EmbedResponse)
async def embed_document(
    request: EmbedRequest,
    db_pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Generate embeddings for document chunks

    - Retrieves chunks from database
    - Generates vector embeddings
    - Updates database with embeddings
    """
    try:
        embedding_service = EmbeddingService(model=request.embedding_model)

        chunks_embedded = await embed_document_chunks(
            document_id=request.document_id,
            db_pool=db_pool,
            embedding_service=embedding_service
        )

        # Calculate cost (rough estimate)
        async with db_pool.acquire() as conn:
            total_chars = await conn.fetchval("""
                SELECT SUM(LENGTH(chunk_text))
                FROM document_chunks
                WHERE document_id = $1
            """, request.document_id)

        total_tokens = (total_chars or 0) // 4
        estimated_cost = embedding_service.calculate_cost(total_tokens)

        return EmbedResponse(
            document_id=request.document_id,
            chunks_embedded=chunks_embedded,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            message=f"Generated embeddings for {chunks_embedded} chunks"
        )

    except Exception as e:
        logger.error(f"Error embedding document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """
    Semantic search across document chunks

    - Generates query embedding
    - Performs vector similarity search
    - Re-ranks results
    """
    try:
        # Retrieve context
        context = await rag_engine.retrieve_context(
            query=request.query,
            top_k=request.top_k,
            control_id=request.control_id,
            objective_id=request.objective_id,
            assessment_id=str(request.assessment_id) if request.assessment_id else None
        )

        # Convert to response format
        results = [
            SearchResult(
                chunk_id=UUID4(chunk.chunk_id),
                chunk_text=chunk.chunk_text,
                similarity_score=1.0 - chunk.similarity_score,  # Convert distance to similarity
                document_title=chunk.document_title or "Unknown",
                document_type=chunk.document_type,
                control_id=chunk.control_id,
                chunk_index=chunk.chunk_index
            )
            for chunk in context.retrieved_chunks
        ]

        return SearchResponse(
            query=request.query,
            results=results,
            total_retrieved=context.total_retrieved
        )

    except Exception as e:
        logger.error(f"Error searching documents: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/control-context", response_model=ControlContextResponse)
async def get_control_context(
    request: ControlContextRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """
    Get all relevant context for a specific control

    - Retrieves chunks tagged with control ID
    - Formats for LLM prompt
    """
    try:
        # Search for control-specific chunks
        chunks = await rag_engine.search_by_control(
            control_id=request.control_id,
            top_k=request.max_chunks,
            assessment_id=str(request.assessment_id) if request.assessment_id else None
        )

        # Convert to search results
        results = [
            SearchResult(
                chunk_id=UUID4(chunk.chunk_id),
                chunk_text=chunk.chunk_text,
                similarity_score=1.0,
                document_title=chunk.document_title or "Unknown",
                document_type=chunk.document_type,
                control_id=chunk.control_id,
                chunk_index=chunk.chunk_index
            )
            for chunk in chunks
        ]

        # Build formatted context
        formatted_context = "\n\n".join([
            f"[{result.document_title}]\n{result.chunk_text}"
            for result in results
        ])

        return ControlContextResponse(
            control_id=request.control_id,
            chunks=results,
            formatted_context=formatted_context
        )

    except Exception as e:
        logger.error(f"Error retrieving control context: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_statistics(
    rag_engine: RAGEngine = Depends(get_rag_engine)
):
    """Get document processing statistics"""
    try:
        stats = await rag_engine.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Error retrieving statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def embed_document_chunks(
    document_id: UUID4,
    db_pool: asyncpg.Pool,
    embedding_service: EmbeddingService
) -> int:
    """
    Background task to embed document chunks

    Args:
        document_id: Document ID
        db_pool: Database pool
        embedding_service: Embedding service

    Returns:
        Number of chunks embedded
    """
    try:
        # Get chunks
        async with db_pool.acquire() as conn:
            chunks = await conn.fetch("""
                SELECT id, chunk_text
                FROM document_chunks
                WHERE document_id = $1 AND embedding IS NULL
                ORDER BY chunk_index
            """, document_id)

        if not chunks:
            logger.info(f"No chunks to embed for document {document_id}")
            return 0

        # Prepare chunks for embedding
        chunk_data = [
            {'id': str(chunk['id']), 'text': chunk['chunk_text']}
            for chunk in chunks
        ]

        # Generate embeddings
        texts = [c['text'] for c in chunk_data]
        embeddings = await embedding_service.embed_batch(texts)

        # Update database
        async with db_pool.acquire() as conn:
            for chunk, embedding_result in zip(chunk_data, embeddings):
                await conn.execute("""
                    UPDATE document_chunks
                    SET embedding = $1
                    WHERE id = $2
                """, embedding_result.embedding, UUID4(chunk['id']))

        logger.info(f"Embedded {len(embeddings)} chunks for document {document_id}")
        return len(embeddings)

    except Exception as e:
        logger.error(f"Error embedding chunks: {e}", exc_info=True)
        return 0
