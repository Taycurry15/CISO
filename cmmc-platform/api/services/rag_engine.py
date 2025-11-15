"""
RAG (Retrieval-Augmented Generation) Engine
Handles vector similarity search, retrieval, and re-ranking for CMMC compliance analysis
"""

import logging
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import asyncpg

from .embedding_service import EmbeddingService, EmbeddingModel

logger = logging.getLogger(__name__)


class SimilarityMetric(str, Enum):
    """Vector similarity metrics"""
    COSINE = "cosine"
    L2 = "l2"
    INNER_PRODUCT = "inner_product"


class ReRankingStrategy(str, Enum):
    """Re-ranking strategies"""
    NONE = "none"
    MMR = "mmr"  # Maximal Marginal Relevance
    CROSS_ENCODER = "cross_encoder"
    HYBRID = "hybrid"


@dataclass
class RetrievedChunk:
    """Represents a retrieved document chunk"""
    chunk_id: str
    document_id: str
    chunk_text: str
    chunk_index: int
    similarity_score: float
    control_id: Optional[str] = None
    objective_id: Optional[str] = None
    document_title: Optional[str] = None
    document_type: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class RAGContext:
    """Context for RAG-based analysis"""
    query: str
    retrieved_chunks: List[RetrievedChunk]
    total_retrieved: int
    control_id: Optional[str] = None
    objective_id: Optional[str] = None


class RAGEngine:
    """
    RAG Engine for CMMC compliance analysis

    Features:
    - Vector similarity search using pgvector
    - Multiple similarity metrics (cosine, L2, inner product)
    - Re-ranking strategies (MMR, cross-encoder)
    - Control-aware retrieval
    - Metadata filtering
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        embedding_service: EmbeddingService,
        similarity_metric: SimilarityMetric = SimilarityMetric.COSINE,
        reranking_strategy: ReRankingStrategy = ReRankingStrategy.MMR
    ):
        """
        Initialize RAG engine

        Args:
            db_pool: AsyncPG connection pool
            embedding_service: Embedding service for query embedding
            similarity_metric: Similarity metric for vector search
            reranking_strategy: Strategy for re-ranking results
        """
        self.db_pool = db_pool
        self.embedding_service = embedding_service
        self.similarity_metric = similarity_metric
        self.reranking_strategy = reranking_strategy

        logger.info(f"Initialized RAG Engine with {similarity_metric} similarity and {reranking_strategy} re-ranking")

    def _get_similarity_operator(self) -> str:
        """Get pgvector operator for similarity metric"""
        if self.similarity_metric == SimilarityMetric.COSINE:
            return "<=>"  # Cosine distance
        elif self.similarity_metric == SimilarityMetric.L2:
            return "<->"  # L2 distance
        elif self.similarity_metric == SimilarityMetric.INNER_PRODUCT:
            return "<#>"  # Inner product (negative)
        else:
            return "<=>"  # Default to cosine

    async def retrieve_similar_chunks(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        control_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        document_type: Optional[str] = None,
        assessment_id: Optional[str] = None
    ) -> List[RetrievedChunk]:
        """
        Retrieve similar chunks using vector similarity search

        Args:
            query_embedding: Query vector embedding
            top_k: Number of results to retrieve
            control_id: Filter by control ID (optional)
            objective_id: Filter by objective ID (optional)
            document_type: Filter by document type (optional)
            assessment_id: Filter by assessment ID (optional)

        Returns:
            List of retrieved chunks with similarity scores
        """
        # Build query with optional filters
        similarity_op = self._get_similarity_operator()

        # Base query
        query = f"""
            SELECT
                dc.id as chunk_id,
                dc.document_id,
                dc.chunk_text,
                dc.chunk_index,
                dc.control_id,
                dc.objective_id,
                dc.doc_type,
                d.title as document_title,
                d.document_type,
                (dc.embedding {similarity_op} $1::vector) as similarity_score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.embedding IS NOT NULL
        """

        params = [query_embedding]
        param_count = 2

        # Add filters
        if control_id:
            query += f" AND dc.control_id = ${param_count}"
            params.append(control_id)
            param_count += 1

        if objective_id:
            query += f" AND dc.objective_id = ${param_count}"
            params.append(objective_id)
            param_count += 1

        if document_type:
            query += f" AND dc.doc_type = ${param_count}"
            params.append(document_type)
            param_count += 1

        if assessment_id:
            query += f" AND d.assessment_id = ${param_count}"
            params.append(assessment_id)
            param_count += 1

        # Order by similarity and limit
        query += f" ORDER BY similarity_score ASC LIMIT ${param_count}"
        params.append(top_k)

        # Execute query
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        # Convert to RetrievedChunk objects
        chunks = [
            RetrievedChunk(
                chunk_id=str(row['chunk_id']),
                document_id=str(row['document_id']),
                chunk_text=row['chunk_text'],
                chunk_index=row['chunk_index'],
                similarity_score=float(row['similarity_score']),
                control_id=row['control_id'],
                objective_id=row['objective_id'],
                document_title=row['document_title'],
                document_type=row['document_type']
            )
            for row in rows
        ]

        logger.info(f"Retrieved {len(chunks)} chunks (top_k={top_k})")
        return chunks

    def _mmr_rerank(
        self,
        chunks: List[RetrievedChunk],
        lambda_param: float = 0.5,
        top_k: int = 5
    ) -> List[RetrievedChunk]:
        """
        Re-rank using Maximal Marginal Relevance (MMR)

        MMR balances relevance and diversity to avoid redundant results

        Args:
            chunks: Retrieved chunks to re-rank
            lambda_param: Balance between relevance (1.0) and diversity (0.0)
            top_k: Number of results to return

        Returns:
            Re-ranked chunks
        """
        if len(chunks) <= top_k:
            return chunks

        selected = []
        remaining = chunks.copy()

        # First, select the most similar chunk
        if remaining:
            best = min(remaining, key=lambda c: c.similarity_score)
            selected.append(best)
            remaining.remove(best)

        # Iteratively select chunks that maximize MMR score
        while len(selected) < top_k and remaining:
            mmr_scores = []

            for chunk in remaining:
                # Relevance score (lower distance = higher relevance)
                relevance = 1.0 - chunk.similarity_score

                # Diversity score (dissimilarity to already selected chunks)
                # Simplified: count unique documents
                unique_docs = len(set(c.document_id for c in selected + [chunk]))
                diversity = unique_docs / (len(selected) + 1)

                # MMR score
                mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity
                mmr_scores.append((chunk, mmr_score))

            # Select chunk with highest MMR score
            if mmr_scores:
                best_chunk, _ = max(mmr_scores, key=lambda x: x[1])
                selected.append(best_chunk)
                remaining.remove(best_chunk)

        return selected

    async def rerank_chunks(
        self,
        chunks: List[RetrievedChunk],
        query: str,
        top_k: int = 5
    ) -> List[RetrievedChunk]:
        """
        Re-rank retrieved chunks based on strategy

        Args:
            chunks: Retrieved chunks
            query: Original query
            top_k: Number of results to return

        Returns:
            Re-ranked chunks
        """
        if self.reranking_strategy == ReRankingStrategy.NONE:
            return chunks[:top_k]

        elif self.reranking_strategy == ReRankingStrategy.MMR:
            return self._mmr_rerank(chunks, lambda_param=0.7, top_k=top_k)

        else:
            # Default: no re-ranking
            logger.warning(f"Re-ranking strategy {self.reranking_strategy} not implemented, using default")
            return chunks[:top_k]

    async def retrieve_context(
        self,
        query: str,
        top_k: int = 5,
        rerank_top_k: int = 10,
        control_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        assessment_id: Optional[str] = None
    ) -> RAGContext:
        """
        Retrieve relevant context for a query

        Args:
            query: Query text
            top_k: Final number of chunks to return
            rerank_top_k: Number of chunks to retrieve before re-ranking
            control_id: Filter by control ID (optional)
            objective_id: Filter by objective ID (optional)
            assessment_id: Filter by assessment ID (optional)

        Returns:
            RAGContext with retrieved and re-ranked chunks
        """
        logger.info(f"Retrieving context for query: {query[:100]}...")

        # Generate query embedding
        embedding_result = await self.embedding_service.embed_text(query)
        query_embedding = embedding_result.embedding

        # Retrieve similar chunks
        retrieved_chunks = await self.retrieve_similar_chunks(
            query_embedding=query_embedding,
            top_k=rerank_top_k,
            control_id=control_id,
            objective_id=objective_id,
            assessment_id=assessment_id
        )

        # Re-rank chunks
        reranked_chunks = await self.rerank_chunks(
            chunks=retrieved_chunks,
            query=query,
            top_k=top_k
        )

        return RAGContext(
            query=query,
            retrieved_chunks=reranked_chunks,
            total_retrieved=len(retrieved_chunks),
            control_id=control_id,
            objective_id=objective_id
        )

    async def build_prompt_context(
        self,
        rag_context: RAGContext,
        max_tokens: int = 2000
    ) -> str:
        """
        Build formatted context string for LLM prompt

        Args:
            rag_context: RAG context with retrieved chunks
            max_tokens: Maximum tokens for context

        Returns:
            Formatted context string
        """
        context_parts = []

        for i, chunk in enumerate(rag_context.retrieved_chunks):
            # Format chunk with metadata
            chunk_text = f"""
[Document {i+1}: {chunk.document_title or 'Unknown'}]
Type: {chunk.document_type or 'Unknown'}
Relevance Score: {1.0 - chunk.similarity_score:.2f}

{chunk.chunk_text}
---
""".strip()

            # Rough token estimate (1 token ≈ 4 characters)
            estimated_tokens = len(' '.join(context_parts)) // 4 + len(chunk_text) // 4

            if estimated_tokens > max_tokens:
                logger.info(f"Reached max tokens ({max_tokens}), stopping at {i} chunks")
                break

            context_parts.append(chunk_text)

        return "\n\n".join(context_parts)

    async def search_by_control(
        self,
        control_id: str,
        top_k: int = 10,
        assessment_id: Optional[str] = None
    ) -> List[RetrievedChunk]:
        """
        Search for all chunks related to a specific control

        Args:
            control_id: Control ID (e.g., "AC.L2-3.1.1")
            top_k: Maximum chunks to return
            assessment_id: Filter by assessment ID (optional)

        Returns:
            List of related chunks
        """
        query = f"""
            SELECT
                dc.id as chunk_id,
                dc.document_id,
                dc.chunk_text,
                dc.chunk_index,
                dc.control_id,
                dc.objective_id,
                dc.doc_type,
                d.title as document_title,
                d.document_type,
                0.0 as similarity_score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.control_id = $1
        """

        params = [control_id]

        if assessment_id:
            query += " AND d.assessment_id = $2"
            params.append(assessment_id)

        query += f" ORDER BY dc.chunk_index LIMIT {top_k}"

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        chunks = [
            RetrievedChunk(
                chunk_id=str(row['chunk_id']),
                document_id=str(row['document_id']),
                chunk_text=row['chunk_text'],
                chunk_index=row['chunk_index'],
                similarity_score=0.0,  # Not based on similarity
                control_id=row['control_id'],
                objective_id=row['objective_id'],
                document_title=row['document_title'],
                document_type=row['document_type']
            )
            for row in rows
        ]

        logger.info(f"Found {len(chunks)} chunks for control {control_id}")
        return chunks

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get RAG engine statistics

        Returns:
            Dictionary with statistics
        """
        async with self.db_pool.acquire() as conn:
            # Total documents
            total_docs = await conn.fetchval("SELECT COUNT(*) FROM documents")

            # Total chunks
            total_chunks = await conn.fetchval("SELECT COUNT(*) FROM document_chunks")

            # Embedded chunks
            embedded_chunks = await conn.fetchval(
                "SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL"
            )

            # Chunks by document type
            chunks_by_type = await conn.fetch("""
                SELECT doc_type, COUNT(*) as count
                FROM document_chunks
                WHERE doc_type IS NOT NULL
                GROUP BY doc_type
                ORDER BY count DESC
            """)

            # Chunks by control
            chunks_by_control = await conn.fetch("""
                SELECT control_id, COUNT(*) as count
                FROM document_chunks
                WHERE control_id IS NOT NULL
                GROUP BY control_id
                ORDER BY count DESC
                LIMIT 10
            """)

        return {
            'total_documents': total_docs,
            'total_chunks': total_chunks,
            'embedded_chunks': embedded_chunks,
            'embedding_coverage': embedded_chunks / total_chunks if total_chunks > 0 else 0,
            'chunks_by_type': [dict(row) for row in chunks_by_type],
            'top_controls': [dict(row) for row in chunks_by_control]
        }


# Example usage
async def test_rag_engine():
    """Test RAG engine"""
    import os

    # Mock database pool (in real usage, use actual pool)
    # db_pool = await asyncpg.create_pool(os.getenv('DATABASE_URL'))

    # Initialize embedding service
    embedding_service = EmbeddingService(
        model=EmbeddingModel.OPENAI_3_LARGE
    )

    # Initialize RAG engine
    # rag_engine = RAGEngine(
    #     db_pool=db_pool,
    #     embedding_service=embedding_service,
    #     similarity_metric=SimilarityMetric.COSINE,
    #     reranking_strategy=ReRankingStrategy.MMR
    # )

    # Test retrieval
    # context = await rag_engine.retrieve_context(
    #     query="What are the requirements for multi-factor authentication?",
    #     top_k=5,
    #     control_id="IA.L2-3.5.3"
    # )

    # Build prompt context
    # prompt_context = await rag_engine.build_prompt_context(context)
    # print(prompt_context)

    print("RAG engine tests would run with actual database connection")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_rag_engine())
