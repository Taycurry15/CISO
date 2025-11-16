"""
CMMC Compliance Platform - RAG Service
Retrieval-Augmented Generation for control analysis
"""

import asyncpg
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from .embedding_service import EmbeddingService


logger = logging.getLogger(__name__)


class RAGService:
    """
    Retrieval-Augmented Generation service for CMMC assessments

    Features:
    - Semantic search over document chunks
    - Control-specific context retrieval
    - Provider inheritance documentation lookup
    - System architecture context injection
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        db_pool: asyncpg.Pool
    ):
        self.embedding_service = embedding_service
        self.db_pool = db_pool

    async def retrieve_relevant_context(
        self,
        query: str,
        control_id: Optional[str] = None,
        objective_id: Optional[str] = None,
        assessment_id: Optional[str] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.7,
        method_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant document chunks for a query using semantic search

        Args:
            query: Search query (e.g., control objective text)
            control_id: Optional filter by control
            objective_id: Optional filter by objective
            assessment_id: Optional filter by assessment
            top_k: Number of results to return
            similarity_threshold: Minimum cosine similarity (0-1)
            method_filter: Optional filter by method (Examine/Interview/Test)

        Returns:
            List of relevant document chunks with metadata
        """
        # Generate embedding for query
        query_embedding = await self.embedding_service.generate_embedding(query)

        # Build SQL query with filters
        sql_parts = [
            """
            SELECT
                dc.id,
                dc.document_id,
                dc.chunk_index,
                dc.chunk_text,
                dc.control_id,
                dc.objective_id,
                dc.method,
                dc.doc_type,
                d.title as document_title,
                d.document_type,
                1 - (dc.embedding <=> $1::vector) as similarity_score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE 1=1
            """
        ]

        params = [query_embedding]
        param_count = 1

        # Add filters
        if control_id:
            param_count += 1
            sql_parts.append(f"AND dc.control_id = ${param_count}")
            params.append(control_id)

        if objective_id:
            param_count += 1
            sql_parts.append(f"AND dc.objective_id = ${param_count}")
            params.append(objective_id)

        if assessment_id:
            param_count += 1
            sql_parts.append(f"AND d.assessment_id = ${param_count}")
            params.append(assessment_id)

        if method_filter:
            param_count += 1
            sql_parts.append(f"AND dc.method = ${param_count}")
            params.append(method_filter)

        # Add similarity threshold and ordering
        param_count += 1
        sql_parts.append(f"""
            AND (1 - (dc.embedding <=> $1::vector)) >= ${param_count}
            ORDER BY similarity_score DESC
            LIMIT {top_k}
        """)
        params.append(similarity_threshold)

        sql = " ".join(sql_parts)

        # Execute query
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)

        results = [dict(row) for row in rows]

        logger.info(
            f"RAG retrieval: query='{query[:50]}...', "
            f"control={control_id}, results={len(results)}"
        )

        return results

    async def retrieve_for_control_analysis(
        self,
        control_id: str,
        objective_id: Optional[str],
        assessment_id: str,
        method: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive context for control analysis

        Args:
            control_id: Control being analyzed
            objective_id: Specific objective (optional)
            assessment_id: Assessment context
            method: Assessment method filter

        Returns:
            Dict with all relevant context including:
            - Control/objective details
            - Relevant document chunks
            - Provider inheritance info
            - Evidence summary
        """
        async with self.db_pool.acquire() as conn:
            # Get control details
            control = await conn.fetchrow(
                """
                SELECT id, domain_id, control_number, title,
                       nist_800_171_ref, cmmc_level, requirement_text, discussion
                FROM controls
                WHERE id = $1
                """,
                control_id
            )

            if not control:
                raise ValueError(f"Control {control_id} not found")

            # Get objective details if specified
            objective = None
            if objective_id:
                objective = await conn.fetchrow(
                    """
                    SELECT id, control_id, objective_letter, method,
                           determination_statement, potential_assessment_methods
                    FROM assessment_objectives
                    WHERE id = $1
                    """,
                    objective_id
                )

            # Build search query from control requirement + objective
            search_query = control['requirement_text']
            if objective:
                search_query += f" {objective['determination_statement']}"

            # Retrieve relevant documents
            relevant_docs = await self.retrieve_relevant_context(
                query=search_query,
                control_id=control_id,
                assessment_id=assessment_id,
                top_k=10,
                method_filter=method
            )

            # Get provider inheritance if available
            provider_inheritance = await conn.fetchrow(
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

            # Get evidence summary
            evidence_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM evidence
                WHERE assessment_id = $1 AND control_id = $2 AND status = 'approved'
                """,
                assessment_id,
                control_id
            )

            # Get diagram context
            diagram = await conn.fetchrow(
                """
                SELECT id, title, graph_data
                FROM system_diagrams
                WHERE assessment_id = $1 AND graph_extracted = TRUE
                ORDER BY created_at DESC
                LIMIT 1
                """,
                assessment_id
            )

        return {
            'control': dict(control) if control else None,
            'objective': dict(objective) if objective else None,
            'relevant_docs': relevant_docs,
            'provider_inheritance': dict(provider_inheritance) if provider_inheritance else None,
            'evidence_count': evidence_count,
            'diagram_context': dict(diagram) if diagram else None
        }

    async def chunk_and_embed_document(
        self,
        document_id: str,
        text: str,
        control_id: Optional[str] = None,
        method: Optional[str] = None,
        doc_type: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> int:
        """
        Chunk a document and generate embeddings for each chunk

        Args:
            document_id: UUID of document
            text: Full text content
            control_id: Associated control (optional)
            method: Assessment method (optional)
            doc_type: Document type (policy, procedure, etc.)
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks

        Returns:
            Number of chunks created
        """
        # Split into chunks with overlap
        chunks = self._create_overlapping_chunks(text, chunk_size, chunk_overlap)

        if not chunks:
            logger.warning(f"No chunks created for document {document_id}")
            return 0

        # Generate embeddings for all chunks
        chunk_texts = [chunk['text'] for chunk in chunks]
        embeddings = await self.embedding_service.generate_embeddings(chunk_texts)

        # Insert chunks into database
        async with self.db_pool.acquire() as conn:
            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                await conn.execute(
                    """
                    INSERT INTO document_chunks
                    (document_id, chunk_index, chunk_text, control_id, method, doc_type, embedding)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT (document_id, chunk_index) DO UPDATE
                    SET chunk_text = EXCLUDED.chunk_text,
                        embedding = EXCLUDED.embedding
                    """,
                    document_id,
                    idx,
                    chunk['text'],
                    control_id,
                    method,
                    doc_type,
                    embedding
                )

        logger.info(
            f"Created {len(chunks)} chunks with embeddings for document {document_id}"
        )

        return len(chunks)

    def _create_overlapping_chunks(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[Dict[str, Any]]:
        """
        Create overlapping text chunks

        Args:
            text: Input text
            chunk_size: Target size per chunk
            overlap: Overlap between chunks

        Returns:
            List of chunk dicts with 'text' and metadata
        """
        if not text:
            return []

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                search_start = max(start, end - 200)
                search_text = text[search_start:end + 100]

                # Find last sentence ending
                for delimiter in ['. ', '.\n', '! ', '?\n']:
                    last_delim = search_text.rfind(delimiter)
                    if last_delim != -1:
                        end = search_start + last_delim + len(delimiter)
                        break

            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    'text': chunk_text,
                    'start_char': start,
                    'end_char': end
                })

            # Move start position with overlap
            start = end - overlap

            # Prevent infinite loop
            if start >= len(text):
                break

        return chunks

    async def reindex_document(
        self,
        document_id: str,
        control_id: Optional[str] = None
    ) -> int:
        """
        Reindex a document's chunks with new embeddings

        Useful when:
        - Switching embedding models
        - Updating document content
        - Fixing indexing issues

        Args:
            document_id: Document to reindex
            control_id: Optional control association

        Returns:
            Number of chunks reindexed
        """
        async with self.db_pool.acquire() as conn:
            # Get document
            doc = await conn.fetchrow(
                "SELECT id, title, document_type FROM documents WHERE id = $1",
                document_id
            )

            if not doc:
                raise ValueError(f"Document {document_id} not found")

            # Get existing chunks
            chunks = await conn.fetch(
                "SELECT id, chunk_text FROM document_chunks WHERE document_id = $1 ORDER BY chunk_index",
                document_id
            )

            if not chunks:
                logger.warning(f"No chunks found for document {document_id}")
                return 0

            # Generate new embeddings
            chunk_texts = [chunk['chunk_text'] for chunk in chunks]
            embeddings = await self.embedding_service.generate_embeddings(chunk_texts)

            # Update embeddings
            for chunk, embedding in zip(chunks, embeddings):
                await conn.execute(
                    "UPDATE document_chunks SET embedding = $1 WHERE id = $2",
                    embedding,
                    chunk['id']
                )

        logger.info(f"Reindexed {len(chunks)} chunks for document {document_id}")
        return len(chunks)

    async def search_evidence_content(
        self,
        query: str,
        assessment_id: str,
        control_id: Optional[str] = None,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search within evidence content using semantic search

        Args:
            query: Search query
            assessment_id: Assessment context
            control_id: Optional control filter
            top_k: Number of results

        Returns:
            List of matching evidence items
        """
        # This would require evidence content to be indexed
        # For now, return a placeholder

        async with self.db_pool.acquire() as conn:
            sql = """
                SELECT id, title, evidence_type, control_id, file_hash,
                       collected_date, description
                FROM evidence
                WHERE assessment_id = $1 AND status = 'approved'
            """
            params = [assessment_id]

            if control_id:
                sql += " AND control_id = $2"
                params.append(control_id)

            sql += " ORDER BY collected_date DESC LIMIT $" + str(len(params) + 1)
            params.append(top_k)

            rows = await conn.fetch(sql, *params)

        return [dict(row) for row in rows]

    async def get_similar_assessments(
        self,
        assessment_id: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar completed assessments for reference

        Uses:
        - Similar control findings
        - Similar organization profiles
        - Similar technology stacks

        Args:
            assessment_id: Current assessment
            top_k: Number of similar assessments to return

        Returns:
            List of similar assessment metadata
        """
        # Placeholder - would require assessment similarity indexing
        async with self.db_pool.acquire() as conn:
            # Get current assessment details
            current = await conn.fetchrow(
                """
                SELECT organization_id, cmmc_level, assessment_type
                FROM assessments
                WHERE id = $1
                """,
                assessment_id
            )

            if not current:
                return []

            # Find similar assessments
            similar = await conn.fetch(
                """
                SELECT id, name, cmmc_level, status,
                       start_date, target_completion_date
                FROM assessments
                WHERE id != $1
                  AND cmmc_level = $2
                  AND status = 'complete'
                ORDER BY start_date DESC
                LIMIT $3
                """,
                assessment_id,
                current['cmmc_level'],
                top_k
            )

        return [dict(row) for row in similar]

    async def healthcheck(self) -> Dict[str, Any]:
        """Check RAG service health"""
        try:
            # Test database connection
            async with self.db_pool.acquire() as conn:
                chunk_count = await conn.fetchval(
                    "SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL"
                )

            # Test embedding service
            embed_health = await self.embedding_service.healthcheck()

            return {
                "status": "healthy",
                "indexed_chunks": chunk_count,
                "embedding_service": embed_health
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e)
            }
