#!/usr/bin/env python3
"""
CMMC Platform - Reference Documentation Ingestion Script
Extracts text from official NIST/CMMC PDFs and loads into RAG knowledge base
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import re
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import PyPDF2
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    print("Warning: PDF libraries not available. Install with: pip install PyPDF2 pdfplumber")
    PDF_SUPPORT = False

try:
    import asyncpg
    from dotenv import load_dotenv
    import os

    # Import our AI services
    from api.services import create_embedding_service, RAGService
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Make sure you're running from the project root and have installed requirements.txt")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ReferenceDocumentIngester:
    """Ingests official CMMC/NIST documentation into RAG knowledge base"""

    def __init__(self, db_pool: asyncpg.Pool, rag_service: RAGService):
        self.db_pool = db_pool
        self.rag_service = rag_service
        self.manifest_path = Path(__file__).parent.parent / "docs" / "reference" / "manifest.json"
        self.docs_base = Path(__file__).parent.parent / "docs" / "reference"

        # Load manifest
        with open(self.manifest_path) as f:
            self.manifest = json.load(f)

    def extract_text_from_pdf(self, pdf_path: Path) -> str:
        """
        Extract text from PDF file

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text
        """
        if not PDF_SUPPORT:
            raise RuntimeError("PDF support not available. Install PyPDF2 and pdfplumber.")

        logger.info(f"Extracting text from: {pdf_path}")

        text_parts = []

        # Try pdfplumber first (better quality)
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

                    if page_num % 10 == 0:
                        logger.debug(f"  Processed {page_num}/{len(pdf.pages)} pages")

            logger.info(f"  Extracted {len(text_parts)} pages with pdfplumber")
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.warning(f"  pdfplumber failed: {e}, trying PyPDF2...")

        # Fallback to PyPDF2
        try:
            text_parts = []
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)

            logger.info(f"  Extracted {len(text_parts)} pages with PyPDF2")
            return "\n\n".join(text_parts)

        except Exception as e:
            logger.error(f"  PDF extraction failed: {e}")
            raise

    def extract_control_ids(self, text: str) -> List[str]:
        """
        Extract NIST/CMMC control IDs from text

        Args:
            text: Text to search

        Returns:
            List of control IDs found
        """
        control_ids = set()

        # NIST 800-171 format: 3.1.1, 3.1.2, etc.
        nist_pattern = r'\b3\.\d{1,2}\.\d{1,2}\b'
        control_ids.update(re.findall(nist_pattern, text))

        # CMMC format: AC.L2-3.1.1, AU.L1-3.3.1, etc.
        cmmc_pattern = r'\b[A-Z]{2}\.L[1-3]-3\.\d{1,2}\.\d{1,2}\b'
        control_ids.update(re.findall(cmmc_pattern, text))

        # Assessment objective format: AC.L2-3.1.1[a], AC.L2-3.1.1[b], etc.
        objective_pattern = r'\b[A-Z]{2}\.L[1-3]-3\.\d{1,2}\.\d{1,2}\[[a-z]\]\b'
        control_ids.update(re.findall(objective_pattern, text))

        return list(control_ids)

    def detect_assessment_method(self, text: str) -> Optional[str]:
        """
        Detect assessment method from text

        Args:
            text: Text to analyze

        Returns:
            "Examine", "Interview", "Test", or None
        """
        text_lower = text.lower()

        # Count method keywords
        examine_count = text_lower.count('examine')
        interview_count = text_lower.count('interview')
        test_count = text_lower.count('test')

        # Return predominant method
        max_count = max(examine_count, interview_count, test_count)
        if max_count > 0:
            if examine_count == max_count:
                return "Examine"
            elif interview_count == max_count:
                return "Interview"
            else:
                return "Test"

        return None

    async def ingest_document(
        self,
        doc_metadata: Dict[str, Any],
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Ingest a single document into RAG

        Args:
            doc_metadata: Document metadata from manifest
            assessment_id: Optional assessment ID to associate with

        Returns:
            Ingestion statistics
        """
        pdf_path = self.docs_base / doc_metadata['filename']

        if not pdf_path.exists():
            logger.warning(f"File not found: {pdf_path}")
            logger.warning(f"  Download manually or run: docs/reference/download_docs.sh")
            return {
                'status': 'skipped',
                'reason': 'file_not_found',
                'path': str(pdf_path)
            }

        logger.info(f"\nIngesting: {doc_metadata['title']}")
        logger.info(f"  Type: {doc_metadata['document_type']}")
        logger.info(f"  Priority: {doc_metadata['priority']}")

        try:
            # Extract text
            text = self.extract_text_from_pdf(pdf_path)

            if not text or len(text) < 100:
                logger.error(f"  Failed: No text extracted (got {len(text)} chars)")
                return {
                    'status': 'failed',
                    'reason': 'no_text_extracted',
                    'chars': len(text)
                }

            logger.info(f"  Extracted {len(text):,} characters")

            # Calculate file hash
            import hashlib
            file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()

            # Check if already ingested
            async with self.db_pool.acquire() as conn:
                existing = await conn.fetchrow(
                    "SELECT id FROM documents WHERE file_hash = $1",
                    file_hash
                )

                if existing and not assessment_id:
                    logger.info(f"  Already ingested (document_id: {existing['id']})")
                    return {
                        'status': 'already_exists',
                        'document_id': str(existing['id'])
                    }

                # Create document record
                if not assessment_id:
                    # Create a special "reference" assessment for official docs
                    assessment_id = await conn.fetchval(
                        """
                        INSERT INTO assessments (organization_id, name, cmmc_level, assessment_type, status)
                        VALUES (
                            (SELECT id FROM organizations LIMIT 1),
                            'Reference Documentation',
                            2,
                            'reference',
                            'complete'
                        )
                        ON CONFLICT DO NOTHING
                        RETURNING id
                        """
                    )

                    if not assessment_id:
                        # Get existing reference assessment
                        assessment_id = await conn.fetchval(
                            "SELECT id FROM assessments WHERE name = 'Reference Documentation' LIMIT 1"
                        )

                document_id = await conn.fetchval(
                    """
                    INSERT INTO documents (
                        assessment_id, title, document_type,
                        file_path, file_hash, uploaded_by
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                    RETURNING id
                    """,
                    assessment_id,
                    doc_metadata['title'],
                    doc_metadata['document_type'],
                    str(pdf_path),
                    file_hash,
                    '00000000-0000-0000-0000-000000000000'  # System user
                )

                logger.info(f"  Created document record: {document_id}")

            # Extract control IDs from full text
            control_ids = self.extract_control_ids(text)
            logger.info(f"  Found {len(control_ids)} control references")

            # Ingest into RAG with chunking and embedding
            chunks_created = await self.rag_service.chunk_and_embed_document(
                document_id=str(document_id),
                text=text,
                control_id=None,  # Will be extracted per chunk
                method=None,
                doc_type=doc_metadata['document_type'],
                chunk_size=1000,
                chunk_overlap=200
            )

            logger.info(f"  Created {chunks_created} chunks with embeddings")

            # Update chunks with extracted control IDs and methods
            async with self.db_pool.acquire() as conn:
                chunks = await conn.fetch(
                    "SELECT id, chunk_text FROM document_chunks WHERE document_id = $1",
                    document_id
                )

                for chunk in chunks:
                    # Extract control IDs from this chunk
                    chunk_controls = self.extract_control_ids(chunk['chunk_text'])
                    chunk_method = self.detect_assessment_method(chunk['chunk_text'])

                    if chunk_controls or chunk_method:
                        await conn.execute(
                            """
                            UPDATE document_chunks
                            SET control_id = $1, method = $2
                            WHERE id = $3
                            """,
                            chunk_controls[0] if chunk_controls else None,
                            chunk_method,
                            chunk['id']
                        )

            return {
                'status': 'success',
                'document_id': str(document_id),
                'chunks_created': chunks_created,
                'control_references': len(control_ids),
                'chars_extracted': len(text)
            }

        except Exception as e:
            logger.error(f"  Ingestion failed: {e}", exc_info=True)
            return {
                'status': 'failed',
                'reason': str(e)
            }

    async def ingest_all(self, priority_filter: Optional[str] = None):
        """
        Ingest all documents from manifest

        Args:
            priority_filter: Filter by priority (critical, high, medium, optional)
        """
        logger.info("=" * 60)
        logger.info("CMMC Reference Documentation Ingestion")
        logger.info("=" * 60)

        documents = self.manifest['documents']

        if priority_filter:
            documents = [d for d in documents if d['priority'] == priority_filter]
            logger.info(f"Filtering by priority: {priority_filter}")

        logger.info(f"Total documents to ingest: {len(documents)}\n")

        results = []
        for doc in documents:
            result = await self.ingest_document(doc)
            result['doc_id'] = doc['id']
            result['title'] = doc['title']
            results.append(result)

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("Ingestion Summary")
        logger.info("=" * 60)

        success = sum(1 for r in results if r['status'] == 'success')
        skipped = sum(1 for r in results if r['status'] == 'skipped')
        failed = sum(1 for r in results if r['status'] == 'failed')
        exists = sum(1 for r in results if r['status'] == 'already_exists')

        logger.info(f"Success: {success}")
        logger.info(f"Already Exists: {exists}")
        logger.info(f"Skipped (file not found): {skipped}")
        logger.info(f"Failed: {failed}")

        if success > 0:
            total_chunks = sum(r.get('chunks_created', 0) for r in results if r['status'] == 'success')
            total_chars = sum(r.get('chars_extracted', 0) for r in results if r['status'] == 'success')
            logger.info(f"\nTotal chunks created: {total_chunks:,}")
            logger.info(f"Total characters: {total_chars:,}")

        if skipped > 0:
            logger.info("\nSkipped files (download required):")
            for r in results:
                if r['status'] == 'skipped':
                    logger.info(f"  - {r['title']}")

        logger.info("\nNext steps:")
        logger.info("1. Test semantic search: python scripts/test_rag_search.py")
        logger.info("2. Analyze a control: curl http://localhost:8000/api/v1/analyze/AC.L2-3.1.1")
        logger.info("3. Check database: SELECT document_type, COUNT(*) FROM document_chunks GROUP BY document_type;")

    async def get_status(self):
        """Get ingestion status from database"""
        logger.info("=" * 60)
        logger.info("RAG Knowledge Base Status")
        logger.info("=" * 60)

        async with self.db_pool.acquire() as conn:
            # Document counts
            doc_stats = await conn.fetch(
                """
                SELECT document_type, COUNT(*) as count, SUM(LENGTH(file_path))/1024/1024 as mb
                FROM documents
                WHERE document_type IN (
                    'nist_800_171', 'nist_800_171a', 'cmmc_model',
                    'cmmc_assessment_guide', 'dod_assessment_methodology'
                )
                GROUP BY document_type
                ORDER BY count DESC
                """
            )

            logger.info("\nDocuments Ingested:")
            if doc_stats:
                for row in doc_stats:
                    logger.info(f"  {row['document_type']}: {row['count']} documents")
            else:
                logger.info("  None (run ingestion first)")

            # Chunk counts
            chunk_stats = await conn.fetch(
                """
                SELECT d.document_type, COUNT(dc.id) as chunks, COUNT(dc.embedding) as with_embeddings
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE d.document_type IN (
                    'nist_800_171', 'nist_800_171a', 'cmmc_model',
                    'cmmc_assessment_guide', 'dod_assessment_methodology'
                )
                GROUP BY d.document_type
                ORDER BY chunks DESC
                """
            )

            logger.info("\nChunks with Embeddings:")
            total_chunks = 0
            total_embedded = 0
            if chunk_stats:
                for row in chunk_stats:
                    logger.info(f"  {row['document_type']}: {row['chunks']} chunks ({row['with_embeddings']} embedded)")
                    total_chunks += row['chunks']
                    total_embedded += row['with_embeddings']

                logger.info(f"\nTotal: {total_chunks:,} chunks, {total_embedded:,} embedded")
                if total_chunks > 0:
                    pct = (total_embedded / total_chunks) * 100
                    logger.info(f"Embedding coverage: {pct:.1f}%")
            else:
                logger.info("  None (run ingestion first)")

            # Control coverage
            control_coverage = await conn.fetchval(
                """
                SELECT COUNT(DISTINCT control_id)
                FROM document_chunks
                WHERE control_id IS NOT NULL
                """
            )

            logger.info(f"\nControl IDs found: {control_coverage or 0}")

            # Method distribution
            method_dist = await conn.fetch(
                """
                SELECT method, COUNT(*) as count
                FROM document_chunks
                WHERE method IS NOT NULL
                GROUP BY method
                ORDER BY count DESC
                """
            )

            if method_dist:
                logger.info("\nAssessment Methods:")
                for row in method_dist:
                    logger.info(f"  {row['method']}: {row['count']} chunks")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Ingest CMMC/NIST reference documentation into RAG")
    parser.add_argument('--file', help='Ingest specific file only')
    parser.add_argument('--priority', choices=['critical', 'high', 'medium', 'optional'],
                       help='Filter by priority level')
    parser.add_argument('--status', action='store_true', help='Show ingestion status')
    parser.add_argument('--force', action='store_true', help='Force re-ingestion of existing documents')

    args = parser.parse_args()

    # Initialize database connection
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/cmmc_platform")
    logger.info(f"Connecting to database...")

    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        logger.error("Make sure PostgreSQL is running and DATABASE_URL is correct in .env")
        return 1

    # Initialize embedding service
    logger.info("Initializing embedding service...")
    try:
        embedding_service = create_embedding_service(
            provider=os.getenv("EMBEDDING_PROVIDER", "openai"),
            api_key=os.getenv("EMBEDDING_API_KEY") or os.getenv("AI_API_KEY"),
            model_name=os.getenv("EMBEDDING_MODEL")
        )
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {e}")
        logger.error("Make sure API keys are set in .env file")
        await db_pool.close()
        return 1

    # Initialize RAG service
    rag_service = RAGService(embedding_service, db_pool)

    # Create ingester
    ingester = ReferenceDocumentIngester(db_pool, rag_service)

    # Execute command
    try:
        if args.status:
            await ingester.get_status()
        elif args.file:
            # Find document in manifest
            doc = next((d for d in ingester.manifest['documents'] if args.file in d['filename']), None)
            if not doc:
                logger.error(f"Document not found in manifest: {args.file}")
                return 1
            result = await ingester.ingest_document(doc)
            logger.info(f"\nResult: {json.dumps(result, indent=2)}")
        else:
            await ingester.ingest_all(priority_filter=args.priority)

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1
    finally:
        await db_pool.close()

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
