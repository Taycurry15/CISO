"""
Embedding Service
Generates vector embeddings for text chunks using OpenAI or Anthropic APIs
"""

import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import asyncio
from enum import Enum

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

try:
    import anthropic
except ImportError:
    anthropic = None

logger = logging.getLogger(__name__)


class EmbeddingModel(str, Enum):
    """Available embedding models"""
    OPENAI_ADA_002 = "text-embedding-ada-002"  # 1536 dimensions
    OPENAI_3_SMALL = "text-embedding-3-small"  # 1536 dimensions
    OPENAI_3_LARGE = "text-embedding-3-large"  # 3072 dimensions (recommended)


@dataclass
class EmbeddingResult:
    """Result of embedding operation"""
    text: str
    embedding: List[float]
    model: str
    dimensions: int
    tokens_used: int


class EmbeddingService:
    """
    Service for generating vector embeddings for RAG pipeline

    Supports:
    - OpenAI embeddings (ada-002, text-embedding-3-small, text-embedding-3-large)
    - Batch processing for efficiency
    - Automatic retries on failure
    - Token counting
    """

    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.OPENAI_3_LARGE,
        api_key: Optional[str] = None,
        batch_size: int = 100,
        max_retries: int = 3
    ):
        """
        Initialize embedding service

        Args:
            model: Embedding model to use
            api_key: API key (defaults to OPENAI_API_KEY env var)
            batch_size: Maximum number of texts to embed in single request
            max_retries: Maximum number of retry attempts on failure
        """
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries

        # Initialize OpenAI client
        if AsyncOpenAI is None:
            raise ImportError("openai package required. Install with: pip install openai")

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key required. Set OPENAI_API_KEY environment variable.")

        self.client = AsyncOpenAI(api_key=self.api_key)

        # Model dimensions
        self.dimensions = self._get_dimensions()

        logger.info(f"Initialized EmbeddingService with model {self.model} ({self.dimensions} dimensions)")

    def _get_dimensions(self) -> int:
        """Get embedding dimensions for model"""
        if self.model in [EmbeddingModel.OPENAI_ADA_002, EmbeddingModel.OPENAI_3_SMALL]:
            return 1536
        elif self.model == EmbeddingModel.OPENAI_3_LARGE:
            return 3072
        else:
            return 1536  # Default

    async def embed_text(
        self,
        text: str,
        retry_count: int = 0
    ) -> EmbeddingResult:
        """
        Generate embedding for a single text

        Args:
            text: Text to embed
            retry_count: Current retry attempt

        Returns:
            EmbeddingResult object
        """
        try:
            # Truncate text if too long (8191 tokens for ada-002, 8191 for text-embedding-3)
            # Rough estimate: 1 token ≈ 4 characters
            max_chars = 8191 * 4
            if len(text) > max_chars:
                logger.warning(f"Text too long ({len(text)} chars), truncating to {max_chars}")
                text = text[:max_chars]

            response = await self.client.embeddings.create(
                input=text,
                model=self.model.value
            )

            embedding = response.data[0].embedding
            tokens_used = response.usage.total_tokens

            return EmbeddingResult(
                text=text,
                embedding=embedding,
                model=self.model.value,
                dimensions=len(embedding),
                tokens_used=tokens_used
            )

        except Exception as e:
            if retry_count < self.max_retries:
                logger.warning(f"Embedding failed (attempt {retry_count + 1}/{self.max_retries}): {e}")
                await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                return await self.embed_text(text, retry_count + 1)
            else:
                logger.error(f"Embedding failed after {self.max_retries} retries: {e}")
                raise

    async def embed_batch(
        self,
        texts: List[str]
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts efficiently

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResult objects
        """
        results = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            logger.info(f"Embedding batch {i // self.batch_size + 1} ({len(batch)} texts)")

            try:
                response = await self.client.embeddings.create(
                    input=batch,
                    model=self.model.value
                )

                for j, item in enumerate(response.data):
                    results.append(EmbeddingResult(
                        text=batch[j],
                        embedding=item.embedding,
                        model=self.model.value,
                        dimensions=len(item.embedding),
                        tokens_used=response.usage.total_tokens // len(batch)  # Estimate per text
                    ))

            except Exception as e:
                logger.error(f"Batch embedding failed: {e}")
                # Fall back to individual embedding
                logger.info("Falling back to individual embedding")
                for text in batch:
                    try:
                        result = await self.embed_text(text)
                        results.append(result)
                    except Exception as e2:
                        logger.error(f"Failed to embed text: {e2}")
                        # Add placeholder for failed embedding
                        results.append(EmbeddingResult(
                            text=text,
                            embedding=[0.0] * self.dimensions,
                            model=self.model.value,
                            dimensions=self.dimensions,
                            tokens_used=0
                        ))

        logger.info(f"Successfully embedded {len(results)} texts")
        return results

    async def embed_chunks(
        self,
        chunks: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Embed document chunks and add embeddings to chunk data

        Args:
            chunks: List of chunk dictionaries with 'text' field

        Returns:
            List of chunks with 'embedding' field added
        """
        texts = [chunk['text'] for chunk in chunks]
        embeddings = await self.embed_batch(texts)

        for chunk, embedding_result in zip(chunks, embeddings):
            chunk['embedding'] = embedding_result.embedding
            chunk['embedding_model'] = embedding_result.model
            chunk['tokens_used'] = embedding_result.tokens_used

        return chunks

    def calculate_cost(self, total_tokens: int) -> float:
        """
        Calculate approximate cost for embedding tokens

        Args:
            total_tokens: Total tokens processed

        Returns:
            Cost in USD
        """
        # OpenAI pricing (as of 2024)
        # ada-002: $0.0001 / 1K tokens
        # text-embedding-3-small: $0.00002 / 1K tokens
        # text-embedding-3-large: $0.00013 / 1K tokens

        pricing = {
            EmbeddingModel.OPENAI_ADA_002: 0.0001,
            EmbeddingModel.OPENAI_3_SMALL: 0.00002,
            EmbeddingModel.OPENAI_3_LARGE: 0.00013,
        }

        cost_per_1k = pricing.get(self.model, 0.0001)
        return (total_tokens / 1000) * cost_per_1k

    async def test_connection(self) -> bool:
        """
        Test OpenAI API connection

        Returns:
            True if connection successful
        """
        try:
            result = await self.embed_text("test")
            logger.info(f"API connection successful. Embedding dimension: {len(result.embedding)}")
            return True
        except Exception as e:
            logger.error(f"API connection failed: {e}")
            return False


# Synchronous wrapper for compatibility
class SyncEmbeddingService:
    """Synchronous wrapper for EmbeddingService"""

    def __init__(self, **kwargs):
        self.async_service = EmbeddingService(**kwargs)

    def embed_text(self, text: str) -> EmbeddingResult:
        """Synchronous version of embed_text"""
        return asyncio.run(self.async_service.embed_text(text))

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Synchronous version of embed_batch"""
        return asyncio.run(self.async_service.embed_batch(texts))

    def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Synchronous version of embed_chunks"""
        return asyncio.run(self.async_service.embed_chunks(chunks))


# Example usage and testing
async def test_embedding_service():
    """Test the embedding service"""

    # Initialize service
    service = EmbeddingService(
        model=EmbeddingModel.OPENAI_3_LARGE
    )

    # Test single embedding
    print("Testing single embedding...")
    result = await service.embed_text("This is a test document about access control.")
    print(f"✓ Generated {result.dimensions}-dimensional embedding")
    print(f"  Tokens used: {result.tokens_used}")

    # Test batch embedding
    print("\nTesting batch embedding...")
    texts = [
        "Access control policy for user authentication",
        "Multi-factor authentication requirements",
        "Password complexity and rotation policies",
        "Privileged access management procedures",
        "Role-based access control implementation"
    ]

    results = await service.embed_batch(texts)
    print(f"✓ Generated {len(results)} embeddings")

    total_tokens = sum(r.tokens_used for r in results)
    cost = service.calculate_cost(total_tokens)
    print(f"  Total tokens: {total_tokens}")
    print(f"  Estimated cost: ${cost:.4f}")

    # Test chunks
    print("\nTesting chunk embedding...")
    chunks = [
        {"text": text, "chunk_index": i}
        for i, text in enumerate(texts)
    ]

    embedded_chunks = await service.embed_chunks(chunks)
    print(f"✓ Embedded {len(embedded_chunks)} chunks")
    print(f"  First chunk has {len(embedded_chunks[0]['embedding'])} dimensions")


if __name__ == "__main__":
    # Run tests
    asyncio.run(test_embedding_service())
