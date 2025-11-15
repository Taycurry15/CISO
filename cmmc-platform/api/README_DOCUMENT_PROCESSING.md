# Document Processing Pipeline

Complete RAG (Retrieval-Augmented Generation) pipeline for CMMC compliance document processing.

## Overview

This pipeline handles:
1. **Document Upload & Extraction** - PDF, TXT, MD files
2. **Intelligent Chunking** - Hybrid semantic + fixed-size chunking
3. **Vector Embedding** - OpenAI text-embedding-3-large (3072 dimensions)
4. **Semantic Search** - pgvector-powered similarity search
5. **Context Retrieval** - MMR re-ranking for diverse results

## Architecture

```
Document Upload
    ↓
PDF/Text Extraction (PyPDF2)
    ↓
Text Cleaning & Normalization
    ↓
Chunking (Hybrid Strategy)
    ├─ Semantic (paragraph boundaries)
    └─ Fixed-size (with overlap)
    ↓
Embedding Generation (OpenAI API)
    ↓
Vector Storage (pgvector)
    ↓
Similarity Search + MMR Re-ranking
    ↓
Context for LLM Analysis
```

## Components

### 1. Document Processor (`services/document_processor.py`)

Handles document extraction and chunking.

**Features**:
- PDF text extraction with page markers
- Multiple chunking strategies:
  - **Fixed-size**: Token-based with overlap
  - **Semantic**: Paragraph-boundary aware
  - **Hybrid**: Combines both for optimal results
- Metadata extraction (control references, token counts)
- SHA-256 file hashing for deduplication

**Example Usage**:
```python
from services.document_processor import DocumentProcessor, ChunkingStrategy

processor = DocumentProcessor(
    chunk_size=512,
    chunk_overlap=50,
    chunking_strategy=ChunkingStrategy.HYBRID
)

processed_doc = processor.process_document(
    file_path="/path/to/policy.pdf",
    title="Access Control Policy"
)

print(f"Created {len(processed_doc.chunks)} chunks")
for chunk in processed_doc.chunks:
    print(f"Chunk {chunk.chunk_index}: {chunk.text[:100]}...")
```

**Chunking Strategy Comparison**:

| Strategy | Best For | Pros | Cons |
|----------|----------|------|------|
| **Fixed-size** | Consistent token budgets | Predictable size, simple | May break semantic units |
| **Semantic** | Document structure | Respects paragraphs | Variable size |
| **Hybrid** | General use (recommended) | Best of both worlds | More complex |

### 2. Embedding Service (`services/embedding_service.py`)

Generates vector embeddings using OpenAI API.

**Features**:
- Multiple models (ada-002, text-embedding-3-small, text-embedding-3-large)
- Batch processing (up to 100 texts per request)
- Automatic retry with exponential backoff
- Cost estimation

**Example Usage**:
```python
from services.embedding_service import EmbeddingService, EmbeddingModel

service = EmbeddingService(
    model=EmbeddingModel.OPENAI_3_LARGE  # 3072 dimensions (recommended)
)

# Single embedding
result = await service.embed_text("Access control policy requirements")
print(f"Embedding: {len(result.embedding)} dimensions")

# Batch embedding
texts = ["Policy 1", "Policy 2", "Policy 3"]
results = await service.embed_batch(texts)

total_tokens = sum(r.tokens_used for r in results)
cost = service.calculate_cost(total_tokens)
print(f"Cost: ${cost:.4f}")
```

**Model Comparison**:

| Model | Dimensions | Cost (per 1K tokens) | Use Case |
|-------|------------|---------------------|----------|
| ada-002 | 1536 | $0.0001 | Budget option |
| text-embedding-3-small | 1536 | $0.00002 | Cost-effective |
| text-embedding-3-large | 3072 | $0.00013 | **Best quality (recommended)** |

### 3. RAG Engine (`services/rag_engine.py`)

Retrieval engine with vector similarity search and re-ranking.

**Features**:
- pgvector-powered similarity search (cosine, L2, inner product)
- MMR (Maximal Marginal Relevance) re-ranking for diversity
- Control-aware filtering
- Metadata-based filtering
- Context formatting for LLM prompts

**Example Usage**:
```python
from services.rag_engine import RAGEngine, SimilarityMetric, ReRankingStrategy

rag_engine = RAGEngine(
    db_pool=db_pool,
    embedding_service=embedding_service,
    similarity_metric=SimilarityMetric.COSINE,
    reranking_strategy=ReRankingStrategy.MMR
)

# Retrieve context for a query
context = await rag_engine.retrieve_context(
    query="What are the requirements for multi-factor authentication?",
    top_k=5,
    control_id="IA.L2-3.5.3"  # Optional: filter by control
)

# Format for LLM prompt
prompt_context = await rag_engine.build_prompt_context(context, max_tokens=2000)

# Search by control
chunks = await rag_engine.search_by_control(
    control_id="AC.L2-3.1.1",
    top_k=10
)
```

**Re-ranking Strategies**:

- **None**: Returns results by similarity score only
- **MMR**: Balances relevance and diversity (prevents redundant results)
- **Cross-encoder** (planned): Neural re-ranking for better accuracy

## API Endpoints (`document_api.py`)

RESTful API for document processing.

### Upload Document

```http
POST /api/v1/documents/upload
Content-Type: multipart/form-data

{
  "file": <PDF/TXT file>,
  "assessment_id": "uuid",
  "title": "Access Control Policy",
  "document_type": "policy",
  "control_id": "AC.L2-3.1.1",
  "auto_chunk": true,
  "auto_embed": true
}

Response:
{
  "document_id": "uuid",
  "file_hash": "sha256...",
  "title": "Access Control Policy",
  "total_chunks": 15,
  "chunks_embedded": 15,
  "message": "Document uploaded and processed successfully"
}
```

### Semantic Search

```http
POST /api/v1/documents/search
Content-Type: application/json

{
  "query": "What are the MFA requirements?",
  "top_k": 5,
  "control_id": "IA.L2-3.5.3",
  "assessment_id": "uuid"
}

Response:
{
  "query": "What are the MFA requirements?",
  "results": [
    {
      "chunk_id": "uuid",
      "chunk_text": "Multi-factor authentication must use...",
      "similarity_score": 0.92,
      "document_title": "IA Policy",
      "control_id": "IA.L2-3.5.3",
      "chunk_index": 3
    }
  ],
  "total_retrieved": 5
}
```

### Get Control Context

```http
POST /api/v1/documents/control-context
Content-Type: application/json

{
  "control_id": "AC.L2-3.1.1",
  "assessment_id": "uuid",
  "max_chunks": 10
}

Response:
{
  "control_id": "AC.L2-3.1.1",
  "chunks": [...],
  "formatted_context": "[Document 1]\n\n..."
}
```

### Get Statistics

```http
GET /api/v1/documents/stats

Response:
{
  "total_documents": 25,
  "total_chunks": 342,
  "embedded_chunks": 342,
  "embedding_coverage": 1.0,
  "chunks_by_type": [
    {"doc_type": "policy", "count": 150},
    {"doc_type": "procedure", "count": 120}
  ],
  "top_controls": [
    {"control_id": "AC.L2-3.1.1", "count": 45}
  ]
}
```

## Database Schema

```sql
-- Documents table
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    assessment_id UUID REFERENCES assessments(id),
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(50),
    file_path TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Document chunks with vector embeddings
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    control_id VARCHAR(20) REFERENCES controls(id),
    objective_id VARCHAR(30) REFERENCES assessment_objectives(id),
    doc_type VARCHAR(50),
    embedding vector(3072),  -- OpenAI text-embedding-3-large
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
```

## Configuration

Set environment variables:

```bash
# OpenAI API
export OPENAI_API_KEY="sk-..."

# Database
export DATABASE_URL="postgresql://user:pass@localhost:5432/cmmc_platform"

# Storage
export EVIDENCE_PATH="/var/cmmc/evidence"

# Tuning
export CHUNK_SIZE=512
export CHUNK_OVERLAP=50
export EMBEDDING_MODEL="text-embedding-3-large"
export TOP_K_RETRIEVAL=10
export MMR_LAMBDA=0.7
```

## Performance Optimization

### 1. Batch Processing
- Process documents in batches of 10-50
- Use background tasks for embedding generation
- Implement rate limiting to avoid API throttling

### 2. Vector Index Tuning
```sql
-- IVFFlat index (good for <1M vectors)
CREATE INDEX ON document_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- HNSW index (better for >1M vectors)
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

### 3. Caching
- Cache frequently accessed embeddings
- Use Redis for query result caching
- Implement LRU cache for document chunks

## Cost Estimation

**Example: Processing 100 policy documents (average 10 pages each)**

- Total pages: 1,000
- Characters per page: ~2,000
- Total characters: 2,000,000
- Estimated tokens: 500,000
- Cost (text-embedding-3-large): 500 × $0.00013 = **$0.065**

**Monthly Cost Estimates**:
- 10 customers × 10 docs/month = 100 docs/month
- Cost per month: **$6.50**
- Annual cost: **$78**

Very cost-effective for embedding generation!

## Testing

Run tests:
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run document processor tests
pytest tests/test_document_processor.py -v

# Run embedding service tests (requires API key)
OPENAI_API_KEY="sk-..." pytest tests/test_embedding_service.py -v

# Run all tests
pytest tests/ -v --cov=services --cov-report=html
```

## Next Steps

1. **AI Analysis Integration**: Connect RAG context to GPT-4/Claude for control analysis
2. **Advanced Re-ranking**: Implement cross-encoder re-ranking
3. **Hybrid Search**: Combine vector search with keyword search (BM25)
4. **Document OCR**: Add support for scanned PDFs
5. **Multi-modal**: Support image extraction from PDFs

## Troubleshooting

**Issue: Embeddings not generating**
- Check OpenAI API key is set
- Verify API quota/rate limits
- Check network connectivity

**Issue: Poor search results**
- Increase `top_k` and `rerank_top_k`
- Adjust chunking strategy (try hybrid)
- Verify embeddings are generated for all chunks

**Issue: Slow performance**
- Add vector index to database
- Enable batch processing
- Use background tasks for embedding
- Implement caching

## References

- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings)
- [pgvector Documentation](https://github.com/pgvector/pgvector)
- [RAG Best Practices](https://www.anthropic.com/index/contextual-retrieval)
- [NIST SP 800-171](https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final)

---

**Built for assessor-grade CMMC compliance automation** 🚀
