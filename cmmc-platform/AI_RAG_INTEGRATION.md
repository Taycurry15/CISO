# AI/RAG Integration Guide

Complete guide for the AI-powered control analysis and Retrieval-Augmented Generation (RAG) system in the CMMC Compliance Platform.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Services](#services)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Cost Optimization](#cost-optimization)
- [Troubleshooting](#troubleshooting)

---

## Overview

The AI/RAG integration provides:

1. **AI-Assisted Control Analysis** - GPT-4 or Claude analyzes evidence against NIST SP 800-171 controls
2. **Semantic Search** - Vector embeddings enable finding relevant documentation
3. **Context-Aware Analysis** - RAG retrieves relevant policy/procedure excerpts to inform AI
4. **Transparent Reasoning** - AI explains its determinations with evidence references
5. **Human-in-the-Loop** - All AI determinations require human review/approval

### Key Benefits

- **Consistency**: AI applies the same rigorous standards to all controls
- **Speed**: Analyze 110 controls in hours instead of weeks
- **Traceability**: Every determination linked to specific evidence
- **Quality**: Professional assessor-grade narratives
- **Defensibility**: Detailed rationale for audit purposes

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI/RAG Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Document Ingestion                                       │
│     └─> PDF/DOCX → Text Extraction → Chunking               │
│         └─> Embedding Generation → PostgreSQL (pgvector)    │
│                                                              │
│  2. Control Analysis Request                                 │
│     ├─> Retrieve Evidence (database)                        │
│     ├─> RAG: Semantic Search (vector similarity)            │
│     ├─> Fetch Provider Inheritance (if applicable)          │
│     └─> Build Context (control + evidence + docs)           │
│                                                              │
│  3. AI Analysis                                              │
│     ├─> Prompt Construction (CMMC-specific templates)       │
│     ├─> API Call (OpenAI GPT-4 or Anthropic Claude)         │
│     └─> Response Parsing (structured JSON)                  │
│                                                              │
│  4. Human Review                                             │
│     └─> Assessor reviews/edits → Approval → Database        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| **Embedding Service** | Converts text to vectors | OpenAI API or Sentence Transformers |
| **RAG Service** | Retrieves relevant context | PostgreSQL pgvector |
| **AI Analyzer** | Analyzes compliance | OpenAI GPT-4 or Anthropic Claude |
| **Prompt Templates** | CMMC-specific prompts | Python (prompts.py) |

---

## Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env
```

### 2. Configuration

Minimal `.env` configuration:

```bash
# Choose AI provider
AI_PROVIDER=openai  # or "anthropic"
AI_MODEL=gpt-4-turbo-preview
AI_API_KEY=sk-your-openai-api-key

# Choose embedding provider
EMBEDDING_PROVIDER=openai  # or "sentence_transformers" for local
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=  # Leave blank to use AI_API_KEY
```

### 3. Database Setup

```bash
# Initialize database with pgvector extension
psql -U cmmc_admin -d cmmc_platform <<EOF
CREATE EXTENSION IF NOT EXISTS vector;
EOF
```

### 4. Start the API

```bash
# Run the FastAPI server
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

# Check AI service health
curl http://localhost:8000/health/ai
```

Expected response:
```json
{
  "timestamp": "2024-01-15T10:30:00",
  "overall_status": "healthy",
  "services": {
    "embedding": {
      "status": "healthy",
      "provider": "openai",
      "model": "text-embedding-3-small",
      "dimension": 1536
    },
    "rag": {
      "status": "healthy",
      "indexed_chunks": 1523
    },
    "ai_analyzer": {
      "status": "healthy",
      "provider": "openai",
      "model": "gpt-4-turbo-preview"
    }
  }
}
```

---

## Services

### Embedding Service

**Purpose**: Converts text into vector embeddings for semantic search.

**Supported Providers**:
- **OpenAI** (API-based, requires API key)
  - `text-embedding-3-small` - 1536 dimensions, $0.02/1M tokens
  - `text-embedding-3-large` - 3072 dimensions, $0.13/1M tokens
  - `text-embedding-ada-002` - 1536 dimensions (legacy)

- **Sentence Transformers** (Local, free)
  - `all-MiniLM-L6-v2` - 384 dimensions, fast
  - `all-mpnet-base-v2` - 768 dimensions, higher quality

**Code Example**:
```python
from services import create_embedding_service

# OpenAI (requires API key)
service = create_embedding_service(
    provider="openai",
    api_key="sk-...",
    model_name="text-embedding-3-small"
)

# Local (no API key needed)
service = create_embedding_service(
    provider="sentence_transformers",
    model_name="all-MiniLM-L6-v2"
)

# Generate embeddings
text = "Multi-factor authentication is required for privileged access."
embedding = await service.generate_embedding(text)
print(f"Embedding dimension: {len(embedding)}")
```

**Cost Comparison** (1M tokens = ~750,000 words):
- OpenAI `text-embedding-3-small`: $0.02
- Sentence Transformers: $0 (local CPU/GPU)

---

### RAG Service

**Purpose**: Retrieves relevant document chunks using semantic search.

**Key Features**:
- Vector similarity search (cosine distance)
- Control-specific filtering
- Assessment method filtering (Examine/Interview/Test)
- Configurable similarity threshold

**Code Example**:
```python
from services import RAGService

rag = RAGService(embedding_service, db_pool)

# Search for relevant documentation
results = await rag.retrieve_relevant_context(
    query="How is multi-factor authentication implemented?",
    control_id="AC.L2-3.1.1",
    assessment_id="...",
    top_k=5,
    similarity_threshold=0.7
)

for doc in results:
    print(f"Document: {doc['document_title']}")
    print(f"Similarity: {doc['similarity_score']:.2f}")
    print(f"Excerpt: {doc['chunk_text'][:200]}...")
```

**Database Query** (under the hood):
```sql
SELECT
    chunk_text,
    1 - (embedding <=> query_embedding) as similarity_score
FROM document_chunks
WHERE control_id = 'AC.L2-3.1.1'
  AND (1 - (embedding <=> query_embedding)) >= 0.7
ORDER BY similarity_score DESC
LIMIT 5;
```

---

### AI Analyzer

**Purpose**: Analyzes control compliance using GPT-4 or Claude.

**Supported Models**:

| Provider | Model | Context | Cost (Input) | Cost (Output) |
|----------|-------|---------|--------------|---------------|
| OpenAI | `gpt-4-turbo-preview` | 128k tokens | $10/1M | $30/1M |
| OpenAI | `gpt-4o` | 128k tokens | $5/1M | $15/1M |
| Anthropic | `claude-3-5-sonnet` | 200k tokens | $3/1M | $15/1M |
| Anthropic | `claude-3-opus` | 200k tokens | $15/1M | $75/1M |

**Code Example**:
```python
from services import create_ai_analyzer

analyzer = create_ai_analyzer(
    provider="openai",
    api_key="sk-...",
    model_name="gpt-4-turbo-preview",
    rag_service=rag_service  # Optional
)

# Analyze a control
control_data = {
    'id': 'AC.L2-3.1.1',
    'title': 'Authorized Access Control',
    'requirement_text': 'Limit information system access to authorized users...',
    'objective_id': 'AC.L2-3.1.1[a]',
    'objective_text': 'Authorized users are determined',
    'method': 'Examine'
}

evidence = [
    {
        'title': 'Access Control Policy',
        'evidence_type': 'document',
        'description': 'Policy defining authorized user roles',
        'collected_date': '2024-01-15'
    },
    {
        'title': 'Active Directory Screenshot',
        'evidence_type': 'screenshot',
        'description': 'Shows user permissions and groups',
        'collected_date': '2024-01-15'
    }
]

result = await analyzer.analyze_control(
    control_data=control_data,
    evidence_items=evidence,
    assessment_id="...",
    include_rag=True
)

print(f"Determination: {result['determination']}")  # "Met", "Not Met", etc.
print(f"Confidence: {result['confidence_score']}%")
print(f"Narrative: {result['assessor_narrative']}")
```

**Response Structure**:
```json
{
  "determination": "Met",
  "confidence_score": 85.0,
  "assessor_narrative": "The organization has implemented...",
  "key_findings": [
    "Access Control Policy defines authorized user roles",
    "Active Directory configured with role-based permissions"
  ],
  "evidence_analysis": {
    "evidence-1": {
      "contribution": "Demonstrates policy requirement",
      "weight": 40
    },
    "evidence-2": {
      "contribution": "Shows technical implementation",
      "weight": 60
    }
  },
  "gaps_identified": [],
  "recommendations": [
    "Consider implementing privileged access management"
  ],
  "rationale": "Analysis based on 2 evidence items showing both policy and implementation..."
}
```

---

## Configuration

### Environment Variables

See [.env.example](.env.example) for full configuration options.

**Critical Settings**:

```bash
# AI Provider Selection
AI_PROVIDER=openai          # or "anthropic"
AI_MODEL=gpt-4-turbo-preview
AI_API_KEY=sk-...

# Embedding Provider
EMBEDDING_PROVIDER=openai   # or "sentence_transformers"
EMBEDDING_MODEL=text-embedding-3-small

# AI Behavior
AI_TEMPERATURE=0.1          # Low for consistency (0.0-1.0)
AI_MAX_TOKENS=4000          # Max response length

# RAG Settings
RAG_TOP_K=10                # Number of chunks to retrieve
RAG_SIMILARITY_THRESHOLD=0.7  # Min similarity (0-1)
RAG_CHUNK_SIZE=1000         # Characters per chunk
RAG_CHUNK_OVERLAP=200       # Overlap for context preservation
```

### Provider Comparison

#### OpenAI vs. Anthropic

| Factor | OpenAI GPT-4 | Anthropic Claude |
|--------|--------------|------------------|
| **Cost** | Higher ($10-15/1M input) | Lower ($3-5/1M input) |
| **Speed** | Fast | Very fast |
| **Context** | 128k tokens | 200k tokens |
| **Structured Output** | Native JSON mode | Via prompt engineering |
| **Use Case** | Best for structured analysis | Best for long documents |

**Recommendation**:
- Start with **Claude 3.5 Sonnet** (lower cost, excellent quality)
- Upgrade to **GPT-4 Turbo** if you need native JSON mode

#### OpenAI Embeddings vs. Local

| Factor | OpenAI | Sentence Transformers |
|--------|--------|----------------------|
| **Cost** | $0.02/1M tokens | $0 (one-time setup) |
| **Quality** | Excellent | Good |
| **Speed** | API latency (~100ms) | Local (instant) |
| **Dimension** | 1536 (standard) | 384 (smaller) |
| **Privacy** | Data sent to OpenAI | Fully local |

**Recommendation**:
- Use **OpenAI** for best quality and ease of setup
- Use **Sentence Transformers** for privacy, cost savings, or high volume

---

## Usage Examples

### Example 1: Analyze a Control

```bash
curl -X POST http://localhost:8000/api/v1/analyze/AC.L2-3.1.1 \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "550e8400-e29b-41d4-a716-446655440000",
    "objective_id": "AC.L2-3.1.1[a]",
    "include_provider_inheritance": true,
    "include_diagram_context": true
  }'
```

**Response**:
```json
{
  "control_id": "AC.L2-3.1.1",
  "finding_id": "...",
  "status": "Met",
  "assessor_narrative": "The organization has implemented...",
  "ai_confidence_score": 85.0,
  "ai_rationale": "Analysis based on 3 evidence items...",
  "evidence_used": [
    {
      "id": "...",
      "title": "Access Control Policy",
      "evidence_type": "document",
      "confidence_contribution": 28.3
    }
  ],
  "provider_inheritance": {
    "provider_name": "Microsoft M365 GCC High",
    "responsibility": "Shared"
  },
  "processing_time_ms": 3421
}
```

### Example 2: Ingest a Policy Document

```bash
curl -X POST http://localhost:8000/api/v1/ingest/document \
  -F "file=@access_control_policy.pdf" \
  -F "assessment_id=550e8400-e29b-41d4-a716-446655440000" \
  -F "title=Access Control Policy" \
  -F "document_type=policy" \
  -F "control_id=AC.L2-3.1.1" \
  -F "auto_chunk=true" \
  -F "auto_embed=true"
```

**Response**:
```json
{
  "document_id": "...",
  "chunks_created": 15,
  "file_hash": "a3b2c1...",
  "processing_time_ms": 2145
}
```

### Example 3: Search Documentation

```python
# In your code
from services import RAGService

rag = RAGService(embedding_service, db_pool)

# Find all references to MFA
results = await rag.retrieve_relevant_context(
    query="multi-factor authentication configuration",
    assessment_id="...",
    top_k=10
)

for doc in results:
    print(f"{doc['document_title']} (similarity: {doc['similarity_score']:.2f})")
    print(f"  {doc['chunk_text'][:200]}...")
```

---

## Cost Optimization

### Estimated Costs (Per Assessment)

Assuming 110 controls, 3 evidence items per control, 50 documents:

| Component | Usage | Provider | Cost |
|-----------|-------|----------|------|
| **Embeddings** | 50 docs × 20 chunks × 500 tokens | OpenAI | $0.01 |
| **AI Analysis** | 110 controls × 4k tokens input | GPT-4 Turbo | $4.40 |
| **AI Responses** | 110 controls × 1k tokens output | GPT-4 Turbo | $3.30 |
| **Total per Assessment** | | | **~$7.71** |

### Cost Reduction Strategies

1. **Use Claude Instead of GPT-4**
   ```bash
   AI_PROVIDER=anthropic
   AI_MODEL=claude-3-5-sonnet-20241022
   ```
   **Savings**: ~50% on AI analysis costs

2. **Use Local Embeddings**
   ```bash
   EMBEDDING_PROVIDER=sentence_transformers
   EMBEDDING_MODEL=all-MiniLM-L6-v2
   ```
   **Savings**: 100% on embedding costs (after one-time setup)

3. **Cache AI Responses**
   ```bash
   CACHE_AI_RESPONSES=true
   AI_CACHE_TTL=3600
   ```
   **Savings**: Eliminates repeat analysis costs

4. **Reduce RAG Context**
   ```bash
   RAG_TOP_K=5  # Instead of 10
   ```
   **Savings**: ~20% on input tokens

5. **Use Smaller Models for Simple Controls**
   - Level 1 controls: Use GPT-3.5 Turbo ($0.50/1M)
   - Level 2 controls: Use GPT-4 Turbo

### Total Cost: OpenAI vs. Local

| Scenario | Embeddings | AI Model | Cost per Assessment |
|----------|------------|----------|---------------------|
| **Full OpenAI** | OpenAI | GPT-4 Turbo | $7.71 |
| **Hybrid** | Local | GPT-4 Turbo | $7.70 |
| **Budget** | Local | Claude Sonnet | $3.85 |
| **Premium** | OpenAI | GPT-4o | $5.50 |

**Recommendation for SaaS**:
- **Starter tier**: Local embeddings + Claude Sonnet ($3.85/assessment)
- **Professional tier**: OpenAI embeddings + GPT-4 Turbo ($7.71/assessment)
- **Margin**: Charge $500-2000/month, cost is <1%

---

## Troubleshooting

### Issue: "Embedding service not initialized"

**Cause**: Missing or invalid API key

**Solution**:
```bash
# Check .env file
cat .env | grep API_KEY

# Verify API key works
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $AI_API_KEY"
```

### Issue: "AI analysis returns low confidence"

**Causes**:
1. Insufficient evidence
2. Evidence not related to control
3. Missing RAG context

**Solutions**:
```python
# Check evidence quality
analyzer = create_ai_analyzer(...)
quality = await analyzer.assess_evidence_quality(
    evidence_title="MFA Screenshot",
    evidence_type="screenshot",
    evidence_content="...",
    control_id="AC.L2-3.1.1",
    objective_text="MFA is required for privileged access",
    method="Examine"
)

# Ensure RAG is working
rag_results = await rag_service.retrieve_relevant_context(
    query=control_data['requirement_text'],
    control_id=control_id,
    top_k=10
)
print(f"Retrieved {len(rag_results)} relevant chunks")
```

### Issue: "Vector search returns no results"

**Cause**: No documents indexed

**Solution**:
```sql
-- Check indexed documents
SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;

-- Manually reindex a document
UPDATE document_chunks SET embedding = NULL WHERE document_id = '...';
-- Then re-run ingestion
```

### Issue: "API timeout errors"

**Cause**: AI request taking too long

**Solution**:
```bash
# Increase timeout
AI_TIMEOUT=120  # Default is 60 seconds

# Reduce context size
RAG_TOP_K=5
AI_MAX_TOKENS=2000
```

### Issue: "Rate limit exceeded"

**Cause**: Too many API requests

**Solution**:
```python
# Add exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=60)
)
async def analyze_with_retry(analyzer, control_data, evidence):
    return await analyzer.analyze_control(control_data, evidence)
```

---

## Advanced Topics

### Custom Prompt Engineering

Modify `api/services/prompts.py` to customize AI behavior:

```python
class CMCCPromptTemplates:
    @staticmethod
    def control_analysis_prompt(...):
        # Add your custom instructions
        prompt = f"""
        You are a CMMC Level 2 assessor with expertise in {control_data['domain']}.

        **Special Instructions for {control_id}:**
        - Focus on CUI data flows
        - Verify both policy and technical implementation
        - Consider cloud provider inheritance

        ...
        """
        return prompt
```

### Fine-Tuning for Your Organization

1. **Collect training data** from past assessments
2. **Create fine-tuned model** (OpenAI API)
3. **Update .env**:
   ```bash
   AI_MODEL=ft:gpt-4-turbo:your-org:cmmc-assessor:abc123
   ```

### Multi-Tenant Considerations

```python
# Scope embeddings by organization
await rag_service.retrieve_relevant_context(
    query="...",
    assessment_id="...",  # This filters by organization via RLS
    control_id="..."
)

# RLS policy ensures tenant isolation
CREATE POLICY assessment_isolation ON assessments
    FOR ALL TO authenticated
    USING (organization_id = current_setting('app.current_organization_id')::UUID);
```

---

## Next Steps

1. **Deploy to Production**: See [DEPLOYMENT.md](./DEPLOYMENT.md)
2. **Import CMMC Framework**: Run `scripts/import_cmmc_framework.py`
3. **Test AI Analysis**: Upload sample evidence and run analysis
4. **Monitor Costs**: Track API usage in OpenAI/Anthropic dashboards
5. **Gather Feedback**: Have assessors review AI-generated narratives

---

## Support

- **Documentation**: This file + [README.md](./README.md)
- **API Reference**: `http://localhost:8000/docs` (FastAPI Swagger UI)
- **Issues**: GitHub Issues
- **Community**: [Discord/Slack link]

---

**Built with ❤️ for CMMC assessors**

*Making compliance analysis faster, more consistent, and more defensible*
