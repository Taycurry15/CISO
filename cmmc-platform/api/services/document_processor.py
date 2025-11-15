"""
Document Processing Service
Handles PDF extraction, text chunking, and document preprocessing for RAG pipeline
"""

import re
import hashlib
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging
from dataclasses import dataclass
from enum import Enum

try:
    from PyPDF2 import PdfReader
except ImportError:
    PdfReader = None

logger = logging.getLogger(__name__)


class ChunkingStrategy(str, Enum):
    """Chunking strategies for document processing"""
    FIXED_SIZE = "fixed_size"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    SENTENCE = "sentence"


@dataclass
class DocumentChunk:
    """Represents a chunk of text from a document"""
    text: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: Dict
    token_count: Optional[int] = None


@dataclass
class ProcessedDocument:
    """Represents a processed document with chunks"""
    file_path: str
    file_hash: str
    title: str
    total_chunks: int
    chunks: List[DocumentChunk]
    metadata: Dict


class DocumentProcessor:
    """
    Document processing service for CMMC compliance documents

    Handles:
    - PDF text extraction
    - Intelligent text chunking
    - Metadata extraction
    - Token counting
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.HYBRID
    ):
        """
        Initialize document processor

        Args:
            chunk_size: Target size of each chunk in tokens
            chunk_overlap: Number of tokens to overlap between chunks
            min_chunk_size: Minimum chunk size (discard smaller chunks)
            chunking_strategy: Strategy to use for chunking
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.chunking_strategy = chunking_strategy

        if PdfReader is None:
            logger.warning("PyPDF2 not installed. PDF extraction will not work.")

    def extract_text_from_pdf(self, file_path: str) -> str:
        """
        Extract text from PDF file

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text
        """
        if PdfReader is None:
            raise ImportError("PyPDF2 is required for PDF extraction. Install with: pip install PyPDF2")

        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    # Add page marker for context
                    text_parts.append(f"\n[Page {page_num + 1}]\n{page_text}")

            full_text = "\n".join(text_parts)
            logger.info(f"Extracted {len(full_text)} characters from {len(reader.pages)} pages")

            return full_text

        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            raise

    def extract_text_from_file(self, file_path: str) -> str:
        """
        Extract text from file based on extension

        Args:
            file_path: Path to file

        Returns:
            Extracted text
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif extension in ['.txt', '.md']:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported file type: {extension}")

    def calculate_file_hash(self, file_path: str) -> str:
        """
        Calculate SHA-256 hash of file

        Args:
            file_path: Path to file

        Returns:
            Hexadecimal hash string
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read file in chunks to handle large files
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        return sha256_hash.hexdigest()

    def clean_text(self, text: str) -> str:
        """
        Clean and normalize text

        Args:
            text: Raw text

        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove special characters that may interfere with processing
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\xff]', '', text)

        # Normalize line breaks
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove excessive newlines
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count (rough approximation)

        Args:
            text: Text to count tokens for

        Returns:
            Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters for English text
        # OpenAI's tokenizer is more sophisticated, but this is a good approximation
        return len(text) // 4

    def split_into_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitter (can be enhanced with spaCy or nltk)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def chunk_by_fixed_size(self, text: str) -> List[DocumentChunk]:
        """
        Chunk text by fixed token size with overlap

        Args:
            text: Text to chunk

        Returns:
            List of DocumentChunk objects
        """
        chunks = []

        # Convert to approximate character size
        char_chunk_size = self.chunk_size * 4
        char_overlap = self.chunk_overlap * 4

        start = 0
        chunk_index = 0

        while start < len(text):
            end = start + char_chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence ending within next 200 chars
                search_end = min(end + 200, len(text))
                sentence_break = text[end:search_end].find('. ')

                if sentence_break != -1:
                    end = end + sentence_break + 1

            chunk_text = text[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size * 4:  # Convert to chars
                chunks.append(DocumentChunk(
                    text=chunk_text,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    metadata={},
                    token_count=self.estimate_tokens(chunk_text)
                ))
                chunk_index += 1

            # Move start position with overlap
            start = end - char_overlap

            # Prevent infinite loop
            if start >= len(text):
                break

        return chunks

    def chunk_by_semantic(self, text: str) -> List[DocumentChunk]:
        """
        Chunk text by semantic boundaries (paragraphs, sections)

        Args:
            text: Text to chunk

        Returns:
            List of DocumentChunk objects
        """
        chunks = []

        # Split by double newlines (paragraphs)
        paragraphs = text.split('\n\n')

        current_chunk = ""
        start_char = 0
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # Check if adding this paragraph would exceed chunk size
            potential_chunk = f"{current_chunk}\n\n{para}".strip()
            token_count = self.estimate_tokens(potential_chunk)

            if token_count > self.chunk_size and current_chunk:
                # Save current chunk
                chunks.append(DocumentChunk(
                    text=current_chunk,
                    chunk_index=chunk_index,
                    start_char=start_char,
                    end_char=start_char + len(current_chunk),
                    metadata={},
                    token_count=self.estimate_tokens(current_chunk)
                ))
                chunk_index += 1

                # Start new chunk
                start_char = start_char + len(current_chunk)
                current_chunk = para
            else:
                current_chunk = potential_chunk

        # Add final chunk
        if current_chunk and len(current_chunk) >= self.min_chunk_size * 4:
            chunks.append(DocumentChunk(
                text=current_chunk,
                chunk_index=chunk_index,
                start_char=start_char,
                end_char=start_char + len(current_chunk),
                metadata={},
                token_count=self.estimate_tokens(current_chunk)
            ))

        return chunks

    def chunk_by_hybrid(self, text: str) -> List[DocumentChunk]:
        """
        Hybrid chunking: semantic boundaries with fixed size fallback

        Args:
            text: Text to chunk

        Returns:
            List of DocumentChunk objects
        """
        # Try semantic chunking first
        semantic_chunks = self.chunk_by_semantic(text)

        # If semantic chunks are too large, further split with fixed size
        final_chunks = []

        for chunk in semantic_chunks:
            if chunk.token_count and chunk.token_count > self.chunk_size * 1.5:
                # Split large semantic chunks
                sub_chunks = self.chunk_by_fixed_size(chunk.text)

                # Re-index
                for sub_chunk in sub_chunks:
                    sub_chunk.chunk_index = len(final_chunks)
                    final_chunks.append(sub_chunk)
            else:
                chunk.chunk_index = len(final_chunks)
                final_chunks.append(chunk)

        return final_chunks

    def chunk_text(self, text: str) -> List[DocumentChunk]:
        """
        Chunk text based on configured strategy

        Args:
            text: Text to chunk

        Returns:
            List of DocumentChunk objects
        """
        text = self.clean_text(text)

        if self.chunking_strategy == ChunkingStrategy.FIXED_SIZE:
            return self.chunk_by_fixed_size(text)
        elif self.chunking_strategy == ChunkingStrategy.SEMANTIC:
            return self.chunk_by_semantic(text)
        elif self.chunking_strategy == ChunkingStrategy.HYBRID:
            return self.chunk_by_hybrid(text)
        else:
            raise ValueError(f"Unknown chunking strategy: {self.chunking_strategy}")

    def extract_metadata(self, file_path: str, text: str) -> Dict:
        """
        Extract metadata from document

        Args:
            file_path: Path to file
            text: Extracted text

        Returns:
            Metadata dictionary
        """
        path = Path(file_path)

        metadata = {
            'filename': path.name,
            'extension': path.suffix,
            'file_size_bytes': path.stat().st_size,
            'character_count': len(text),
            'estimated_tokens': self.estimate_tokens(text),
        }

        # Extract potential control references
        control_pattern = r'\b[A-Z]{2}\.L[1-3]-\d+\.\d+\.\d+\b'
        controls = re.findall(control_pattern, text)
        if controls:
            metadata['referenced_controls'] = list(set(controls))

        return metadata

    def process_document(
        self,
        file_path: str,
        title: Optional[str] = None
    ) -> ProcessedDocument:
        """
        Process a document: extract text, chunk, and extract metadata

        Args:
            file_path: Path to document file
            title: Optional title (defaults to filename)

        Returns:
            ProcessedDocument object
        """
        logger.info(f"Processing document: {file_path}")

        # Extract text
        text = self.extract_text_from_file(file_path)

        # Calculate hash
        file_hash = self.calculate_file_hash(file_path)

        # Chunk text
        chunks = self.chunk_text(text)

        # Extract metadata
        metadata = self.extract_metadata(file_path, text)

        # Use filename as title if not provided
        if title is None:
            title = Path(file_path).stem

        logger.info(f"Processed document into {len(chunks)} chunks")

        return ProcessedDocument(
            file_path=file_path,
            file_hash=file_hash,
            title=title,
            total_chunks=len(chunks),
            chunks=chunks,
            metadata=metadata
        )


# Example usage
if __name__ == "__main__":
    # Test the document processor
    processor = DocumentProcessor(
        chunk_size=512,
        chunk_overlap=50,
        chunking_strategy=ChunkingStrategy.HYBRID
    )

    # Test with sample text
    sample_text = """
    Access Control Policy

    Version 1.0
    Effective Date: 2024-01-01

    1. Purpose
    This policy establishes requirements for logical and physical access control
    in accordance with NIST SP 800-171 and CMMC Level 2 requirements.

    2. Scope
    This policy applies to all information systems that process, store, or
    transmit Controlled Unclassified Information (CUI).

    3. Requirements

    3.1 Access Control (AC.L2-3.1.1)
    The organization shall limit system access to authorized users, processes
    acting on behalf of authorized users, and devices.

    3.2 Multi-Factor Authentication (IA.L2-3.5.3)
    The organization shall implement multi-factor authentication for all
    remote network access and privileged local access.
    """

    chunks = processor.chunk_text(sample_text)

    print(f"Created {len(chunks)} chunks:")
    for chunk in chunks:
        print(f"\nChunk {chunk.chunk_index} ({chunk.token_count} tokens):")
        print(f"{chunk.text[:100]}...")
