"""
Evidence Management Service

Handles evidence upload, tagging, and linking to controls and assessments.
"""

import logging
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncpg
from uuid import uuid4
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class EvidenceType(str, Enum):
    """Type of evidence"""
    DOCUMENT = "Document"
    SCREENSHOT = "Screenshot"
    CONFIGURATION = "Configuration"
    LOG = "Log"
    POLICY = "Policy"
    PROCEDURE = "Procedure"
    DIAGRAM = "Diagram"
    INTERVIEW_NOTES = "Interview Notes"
    TEST_RESULTS = "Test Results"
    OTHER = "Other"


class AssessmentMethod(str, Enum):
    """CMMC assessment method"""
    EXAMINE = "Examine"
    INTERVIEW = "Interview"
    TEST = "Test"


@dataclass
class EvidenceMetadata:
    """Evidence metadata"""
    title: str
    description: Optional[str]
    evidence_type: EvidenceType
    assessment_methods: List[AssessmentMethod]
    tags: List[str]
    collection_date: datetime
    collected_by: str


@dataclass
class Evidence:
    """Evidence entity"""
    id: str
    assessment_id: str
    document_id: Optional[str]  # Link to document if uploaded file
    title: str
    description: Optional[str]
    evidence_type: EvidenceType
    assessment_methods: List[AssessmentMethod]
    tags: List[str]
    file_path: Optional[str]
    file_name: Optional[str]
    file_size: Optional[int]
    file_hash: Optional[str]
    collection_date: datetime
    collected_by: str
    linked_controls: List[str]
    created_at: datetime
    updated_at: datetime


class EvidenceService:
    """
    Evidence Management Service

    Handles evidence upload, storage, tagging, and linking to controls
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        storage_service: Optional[Any] = None
    ):
        """
        Initialize evidence service

        Args:
            db_pool: Database connection pool
            storage_service: Optional file storage service (MinIO, S3, etc.)
        """
        self.db_pool = db_pool
        self.storage_service = storage_service

    async def upload_evidence(
        self,
        assessment_id: str,
        file_data: BinaryIO,
        file_name: str,
        metadata: EvidenceMetadata,
        link_to_controls: Optional[List[str]] = None
    ) -> str:
        """
        Upload evidence file

        Args:
            assessment_id: Assessment UUID
            file_data: File binary data
            file_name: Original file name
            metadata: Evidence metadata
            link_to_controls: Optional list of control IDs to link

        Returns:
            str: Evidence UUID
        """
        logger.info(f"Uploading evidence '{file_name}' for assessment {assessment_id}")

        evidence_id = str(uuid4())
        now = datetime.utcnow()

        # Calculate file hash
        file_hash = self._calculate_file_hash(file_data)
        file_data.seek(0)  # Reset for storage

        # Get file size
        file_data.seek(0, 2)  # Seek to end
        file_size = file_data.tell()
        file_data.seek(0)  # Reset

        # Store file (MinIO, S3, or local filesystem)
        file_path = await self._store_file(
            assessment_id,
            evidence_id,
            file_name,
            file_data
        )

        async with self.db_pool.acquire() as conn:
            # Create evidence record
            await conn.execute("""
                INSERT INTO evidence (
                    id, assessment_id, title, description,
                    evidence_type, assessment_methods, tags,
                    file_path, file_name, file_size, file_hash,
                    collection_date, collected_by,
                    created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            """,
                evidence_id,
                assessment_id,
                metadata.title,
                metadata.description,
                metadata.evidence_type.value,
                [m.value for m in metadata.assessment_methods],
                metadata.tags,
                file_path,
                file_name,
                file_size,
                file_hash,
                metadata.collection_date,
                metadata.collected_by,
                now,
                now
            )

            # Link to controls if specified
            if link_to_controls:
                await self._link_evidence_to_controls(
                    conn,
                    evidence_id,
                    assessment_id,
                    link_to_controls
                )

            # Create document record if it's a document type
            if metadata.evidence_type in [EvidenceType.DOCUMENT, EvidenceType.POLICY, EvidenceType.PROCEDURE]:
                document_id = await self._create_document_record(
                    conn,
                    assessment_id,
                    file_name,
                    file_path,
                    file_size,
                    file_hash,
                    metadata
                )

                # Link evidence to document
                await conn.execute("""
                    UPDATE evidence
                    SET document_id = $1
                    WHERE id = $2
                """, document_id, evidence_id)

        logger.info(f"Evidence {evidence_id} uploaded successfully")

        return evidence_id

    def _calculate_file_hash(self, file_data: BinaryIO) -> str:
        """Calculate SHA-256 hash of file"""
        sha256 = hashlib.sha256()
        for chunk in iter(lambda: file_data.read(4096), b""):
            sha256.update(chunk)
        return sha256.hexdigest()

    async def _store_file(
        self,
        assessment_id: str,
        evidence_id: str,
        file_name: str,
        file_data: BinaryIO
    ) -> str:
        """
        Store file in storage backend

        Args:
            assessment_id: Assessment UUID
            evidence_id: Evidence UUID
            file_name: Original file name
            file_data: File binary data

        Returns:
            str: File path/key
        """
        # Build storage path
        safe_filename = Path(file_name).name  # Remove any path components
        storage_path = f"assessments/{assessment_id}/evidence/{evidence_id}/{safe_filename}"

        if self.storage_service:
            # Use MinIO/S3
            await self.storage_service.upload_file(
                bucket="evidence",
                object_name=storage_path,
                file_data=file_data
            )
        else:
            # Use local filesystem (for development)
            local_dir = Path(f"/data/evidence/{assessment_id}/{evidence_id}")
            local_dir.mkdir(parents=True, exist_ok=True)

            local_path = local_dir / safe_filename

            with open(local_path, 'wb') as f:
                f.write(file_data.read())

        return storage_path

    async def _create_document_record(
        self,
        conn: asyncpg.Connection,
        assessment_id: str,
        file_name: str,
        file_path: str,
        file_size: int,
        file_hash: str,
        metadata: EvidenceMetadata
    ) -> str:
        """Create document record for document processing pipeline"""

        document_id = str(uuid4())

        await conn.execute("""
            INSERT INTO documents (
                id, assessment_id, title, file_name, file_path,
                file_size, file_hash, upload_date, uploaded_by,
                processing_status, created_at, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
        """,
            document_id,
            assessment_id,
            metadata.title,
            file_name,
            file_path,
            file_size,
            file_hash,
            metadata.collection_date,
            metadata.collected_by,
            "pending",  # Will be processed by document pipeline
            datetime.utcnow(),
            datetime.utcnow()
        )

        return document_id

    async def _link_evidence_to_controls(
        self,
        conn: asyncpg.Connection,
        evidence_id: str,
        assessment_id: str,
        control_ids: List[str]
    ):
        """Link evidence to specific controls"""

        for control_id in control_ids:
            # Check if control finding exists
            finding = await conn.fetchrow("""
                SELECT id FROM control_findings
                WHERE assessment_id = $1 AND control_id = $2
            """, assessment_id, control_id)

            if not finding:
                logger.warning(f"Control finding not found for {control_id} in assessment {assessment_id}")
                continue

            # Create evidence link (using evidence table's control linkage)
            # In this design, we track control linkage separately
            # Could also use a junction table for many-to-many
            await conn.execute("""
                INSERT INTO evidence_control_links (
                    id, evidence_id, control_id, assessment_id, created_at
                ) VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (evidence_id, control_id) DO NOTHING
            """,
                str(uuid4()),
                evidence_id,
                control_id,
                assessment_id,
                datetime.utcnow()
            )

    async def link_evidence_to_control(
        self,
        evidence_id: str,
        control_id: str,
        assessment_id: str
    ) -> bool:
        """
        Link existing evidence to a control

        Args:
            evidence_id: Evidence UUID
            control_id: Control ID
            assessment_id: Assessment UUID

        Returns:
            bool: Success status
        """
        async with self.db_pool.acquire() as conn:
            await self._link_evidence_to_controls(
                conn,
                evidence_id,
                assessment_id,
                [control_id]
            )

        return True

    async def unlink_evidence_from_control(
        self,
        evidence_id: str,
        control_id: str
    ) -> bool:
        """
        Unlink evidence from a control

        Args:
            evidence_id: Evidence UUID
            control_id: Control ID

        Returns:
            bool: Success status
        """
        async with self.db_pool.acquire() as conn:
            await conn.execute("""
                DELETE FROM evidence_control_links
                WHERE evidence_id = $1 AND control_id = $2
            """, evidence_id, control_id)

        return True

    async def get_evidence(
        self,
        evidence_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get evidence details

        Args:
            evidence_id: Evidence UUID

        Returns:
            Evidence details or None
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT
                    e.*,
                    ARRAY_AGG(DISTINCT ecl.control_id) FILTER (WHERE ecl.control_id IS NOT NULL) as linked_controls
                FROM evidence e
                LEFT JOIN evidence_control_links ecl ON e.id = ecl.evidence_id
                WHERE e.id = $1
                GROUP BY e.id
            """, evidence_id)

            if not row:
                return None

            return dict(row)

    async def list_evidence(
        self,
        assessment_id: str,
        evidence_type: Optional[EvidenceType] = None,
        control_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List evidence with optional filtering

        Args:
            assessment_id: Assessment UUID
            evidence_type: Filter by evidence type
            control_id: Filter by linked control
            tags: Filter by tags (any match)
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of evidence
        """
        query = """
            SELECT
                e.*,
                ARRAY_AGG(DISTINCT ecl.control_id) FILTER (WHERE ecl.control_id IS NOT NULL) as linked_controls
            FROM evidence e
            LEFT JOIN evidence_control_links ecl ON e.id = ecl.evidence_id
            WHERE e.assessment_id = $1
        """

        params = [assessment_id]
        param_count = 1

        if evidence_type:
            param_count += 1
            query += f" AND e.evidence_type = ${param_count}"
            params.append(evidence_type.value)

        if control_id:
            param_count += 1
            query += f" AND ecl.control_id = ${param_count}"
            params.append(control_id)

        if tags:
            param_count += 1
            query += f" AND e.tags && ${param_count}"  # Array overlap operator
            params.append(tags)

        query += f"""
            GROUP BY e.id
            ORDER BY e.collection_date DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def update_evidence_metadata(
        self,
        evidence_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        evidence_type: Optional[EvidenceType] = None,
        assessment_methods: Optional[List[AssessmentMethod]] = None,
        tags: Optional[List[str]] = None
    ) -> bool:
        """
        Update evidence metadata

        Args:
            evidence_id: Evidence UUID
            title: New title
            description: New description
            evidence_type: New evidence type
            assessment_methods: New assessment methods
            tags: New tags

        Returns:
            bool: Success status
        """
        updates = []
        params = []
        param_count = 0

        if title is not None:
            param_count += 1
            updates.append(f"title = ${param_count}")
            params.append(title)

        if description is not None:
            param_count += 1
            updates.append(f"description = ${param_count}")
            params.append(description)

        if evidence_type is not None:
            param_count += 1
            updates.append(f"evidence_type = ${param_count}")
            params.append(evidence_type.value)

        if assessment_methods is not None:
            param_count += 1
            updates.append(f"assessment_methods = ${param_count}")
            params.append([m.value for m in assessment_methods])

        if tags is not None:
            param_count += 1
            updates.append(f"tags = ${param_count}")
            params.append(tags)

        if not updates:
            return False

        # Add updated_at
        param_count += 1
        updates.append(f"updated_at = ${param_count}")
        params.append(datetime.utcnow())

        # Add evidence_id for WHERE clause
        param_count += 1
        params.append(evidence_id)

        query = f"""
            UPDATE evidence
            SET {', '.join(updates)}
            WHERE id = ${param_count}
        """

        async with self.db_pool.acquire() as conn:
            await conn.execute(query, *params)

        return True

    async def delete_evidence(
        self,
        evidence_id: str,
        delete_file: bool = True
    ) -> bool:
        """
        Delete evidence

        Args:
            evidence_id: Evidence UUID
            delete_file: Also delete the file from storage

        Returns:
            bool: Success status
        """
        logger.info(f"Deleting evidence {evidence_id}")

        async with self.db_pool.acquire() as conn:
            # Get file path before deleting
            if delete_file:
                row = await conn.fetchrow(
                    "SELECT file_path FROM evidence WHERE id = $1",
                    evidence_id
                )

                if row and row['file_path']:
                    await self._delete_file(row['file_path'])

            # Delete evidence control links
            await conn.execute("""
                DELETE FROM evidence_control_links
                WHERE evidence_id = $1
            """, evidence_id)

            # Delete evidence record
            await conn.execute("""
                DELETE FROM evidence
                WHERE id = $1
            """, evidence_id)

        return True

    async def _delete_file(self, file_path: str):
        """Delete file from storage"""
        if self.storage_service:
            await self.storage_service.delete_file(
                bucket="evidence",
                object_name=file_path
            )
        else:
            # Local filesystem
            local_path = Path(f"/data/{file_path}")
            if local_path.exists():
                local_path.unlink()

    async def get_control_evidence(
        self,
        assessment_id: str,
        control_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all evidence linked to a control

        Args:
            assessment_id: Assessment UUID
            control_id: Control ID

        Returns:
            List of evidence
        """
        return await self.list_evidence(
            assessment_id=assessment_id,
            control_id=control_id
        )

    async def get_evidence_statistics(
        self,
        assessment_id: str
    ) -> Dict[str, Any]:
        """
        Get evidence statistics for an assessment

        Args:
            assessment_id: Assessment UUID

        Returns:
            Dictionary with evidence statistics
        """
        async with self.db_pool.acquire() as conn:
            # Overall stats
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_evidence,
                    COUNT(DISTINCT evidence_type) as evidence_types,
                    SUM(file_size) as total_size,
                    COUNT(DISTINCT ecl.control_id) as controls_with_evidence
                FROM evidence e
                LEFT JOIN evidence_control_links ecl ON e.id = ecl.evidence_id
                WHERE e.assessment_id = $1
            """, assessment_id)

            # By type
            by_type = await conn.fetch("""
                SELECT
                    evidence_type,
                    COUNT(*) as count
                FROM evidence
                WHERE assessment_id = $1
                GROUP BY evidence_type
            """, assessment_id)

            # By assessment method
            by_method = await conn.fetch("""
                SELECT
                    method,
                    COUNT(*) as count
                FROM evidence e,
                    UNNEST(e.assessment_methods) as method
                WHERE e.assessment_id = $1
                GROUP BY method
            """, assessment_id)

            return {
                'total_evidence': stats['total_evidence'],
                'evidence_types': stats['evidence_types'],
                'total_size_bytes': stats['total_size'] or 0,
                'controls_with_evidence': stats['controls_with_evidence'] or 0,
                'by_type': {row['evidence_type']: row['count'] for row in by_type},
                'by_method': {row['method']: row['count'] for row in by_method}
            }
