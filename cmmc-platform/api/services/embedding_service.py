"""
CMMC Compliance Platform - Embedding Service
Generates vector embeddings for semantic search and RAG
"""

import asyncio
import logging
from typing import List, Optional, Dict, Any
from enum import Enum
import numpy as np

# Optional imports - gracefully handle missing dependencies
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


logger = logging.getLogger(__name__)


class EmbeddingProvider(str, Enum):
    """Supported embedding providers"""
    OPENAI = "openai"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    ANTHROPIC = "anthropic"  # Future support if Anthropic adds embeddings
    LOCAL = "local"


class EmbeddingConfig:
    """Configuration for embedding service"""

    def __init__(
        self,
        provider: EmbeddingProvider = EmbeddingProvider.OPENAI,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None,
        dimension: int = 1536,
        batch_size: int = 100,
        max_retries: int = 3,
        timeout: int = 30
    ):
        self.provider = provider
        self.api_key = api_key
        self.dimension = dimension
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.timeout = timeout

        # Set default model names based on provider
        if model_name is None:
            if provider == EmbeddingProvider.OPENAI:
                self.model_name = "text-embedding-3-small"  # 1536 dimensions, cost-effective
            elif provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
                self.model_name = "all-MiniLM-L6-v2"  # 384 dimensions, fast
            else:
                self.model_name = "default"
        else:
            self.model_name = model_name


class EmbeddingService:
    """
    Unified embedding service supporting multiple providers

    Supports:
    - OpenAI (text-embedding-3-small, text-embedding-3-large, ada-002)
    - Sentence Transformers (local models)
    - Future: Anthropic, Cohere, custom models
    """

    def __init__(self, config: EmbeddingConfig):
        self.config = config
        self.provider = config.provider
        self._model = None
        self._client = None

        # Initialize based on provider
        if self.provider == EmbeddingProvider.OPENAI:
            if not OPENAI_AVAILABLE:
                raise ImportError("openai package not installed. Run: pip install openai")
            if not config.api_key:
                raise ValueError("OpenAI API key required for OpenAI provider")
            self._client = openai.AsyncOpenAI(api_key=config.api_key)
            logger.info(f"Initialized OpenAI embedding service with model: {config.model_name}")

        elif self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError(
                    "sentence-transformers not installed. Run: pip install sentence-transformers"
                )
            # Load model lazily
            logger.info(f"Initializing Sentence Transformers model: {config.model_name}")

        else:
            raise ValueError(f"Unsupported embedding provider: {self.provider}")

    async def _get_sentence_transformer_model(self):
        """Lazy load sentence transformer model"""
        if self._model is None:
            # Run model loading in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self._model = await loop.run_in_executor(
                None,
                SentenceTransformer,
                self.config.model_name
            )
            logger.info(f"Loaded Sentence Transformers model: {self.config.model_name}")
        return self._model

    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text

        Args:
            text: Input text to embed

        Returns:
            List of floats representing the embedding vector
        """
        embeddings = await self.generate_embeddings([text])
        return embeddings[0]

    async def generate_embeddings(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts
            batch_size: Override default batch size

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        batch_size = batch_size or self.config.batch_size

        # Process in batches to avoid rate limits
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            if self.provider == EmbeddingProvider.OPENAI:
                batch_embeddings = await self._generate_openai_embeddings(batch)
            elif self.provider == EmbeddingProvider.SENTENCE_TRANSFORMERS:
                batch_embeddings = await self._generate_sentence_transformer_embeddings(batch)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            all_embeddings.extend(batch_embeddings)

            # Small delay between batches to respect rate limits
            if i + batch_size < len(texts):
                await asyncio.sleep(0.1)

        return all_embeddings

    async def _generate_openai_embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings using OpenAI API"""
        try:
            # Clean and truncate texts to avoid API errors
            cleaned_texts = [self._clean_text(text) for text in texts]

            response = await self._client.embeddings.create(
                model=self.config.model_name,
                input=cleaned_texts,
                encoding_format="float"
            )

            embeddings = [item.embedding for item in response.data]

            logger.debug(
                f"Generated {len(embeddings)} OpenAI embeddings "
                f"(model: {self.config.model_name}, tokens: {response.usage.total_tokens})"
            )

            return embeddings

        except Exception as e:
            logger.error(f"OpenAI embedding generation failed: {e}")
            raise

    async def _generate_sentence_transformer_embeddings(
        self,
        texts: List[str]
    ) -> List[List[float]]:
        """Generate embeddings using Sentence Transformers (local)"""
        try:
            model = await self._get_sentence_transformer_model()

            # Clean texts
            cleaned_texts = [self._clean_text(text) for text in texts]

            # Run encoding in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                model.encode,
                cleaned_texts
            )

            # Convert numpy arrays to lists
            embeddings_list = [emb.tolist() for emb in embeddings]

            logger.debug(
                f"Generated {len(embeddings_list)} local embeddings "
                f"(model: {self.config.model_name})"
            )

            return embeddings_list

        except Exception as e:
            logger.error(f"Sentence Transformer embedding generation failed: {e}")
            raise

    def _clean_text(self, text: str, max_length: int = 8000) -> str:
        """
        Clean and prepare text for embedding

        Args:
            text: Input text
            max_length: Maximum character length

        Returns:
            Cleaned text
        """
        if not text:
            return ""

        # Remove excessive whitespace
        text = " ".join(text.split())

        # Truncate if too long (OpenAI has token limits)
        if len(text) > max_length:
            text = text[:max_length]
            logger.warning(f"Text truncated from {len(text)} to {max_length} characters")

        return text

    async def cosine_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Similarity score (0-1, higher is more similar)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)

        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        return float(similarity)

    async def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find most similar embeddings to a query

        Args:
            query_embedding: Query vector
            candidate_embeddings: List of candidate vectors
            top_k: Number of results to return

        Returns:
            List of dicts with 'index' and 'similarity' keys
        """
        similarities = []

        for idx, candidate in enumerate(candidate_embeddings):
            similarity = await self.cosine_similarity(query_embedding, candidate)
            similarities.append({
                'index': idx,
                'similarity': similarity
            })

        # Sort by similarity (descending)
        similarities.sort(key=lambda x: x['similarity'], reverse=True)

        return similarities[:top_k]

    async def healthcheck(self) -> Dict[str, Any]:
        """
        Check if embedding service is working

        Returns:
            Status dict
        """
        try:
            test_text = "This is a test embedding for CMMC compliance."
            embedding = await self.generate_embedding(test_text)

            return {
                "status": "healthy",
                "provider": self.provider.value,
                "model": self.config.model_name,
                "dimension": len(embedding),
                "expected_dimension": self.config.dimension
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.provider.value,
                "model": self.config.model_name,
                "error": str(e)
            }


# Factory function for easy initialization
def create_embedding_service(
    provider: str = "openai",
    api_key: Optional[str] = None,
    model_name: Optional[str] = None
) -> EmbeddingService:
    """
    Factory function to create embedding service

    Args:
        provider: "openai" or "sentence_transformers"
        api_key: API key for cloud providers
        model_name: Optional model override

    Returns:
        Configured EmbeddingService instance

    Example:
        # OpenAI (requires API key)
        service = create_embedding_service(
            provider="openai",
            api_key="sk-..."
        )

        # Local (no API key needed)
        service = create_embedding_service(
            provider="sentence_transformers",
            model_name="all-MiniLM-L6-v2"
        )
    """
    provider_enum = EmbeddingProvider(provider.lower())

    config = EmbeddingConfig(
        provider=provider_enum,
        model_name=model_name,
        api_key=api_key
    )

    return EmbeddingService(config)
