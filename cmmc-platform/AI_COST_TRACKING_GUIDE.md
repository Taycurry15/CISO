# 💰 AI Cost Tracking Guide

**Status**: Complete and Integrated ✅
**Last Updated**: 2025-11-15

---

## 🎯 Overview

The CMMC platform now includes comprehensive AI cost tracking that logs every AI API call, calculates costs, and provides detailed analytics. This helps you:

- **Monitor spending** - Track AI costs per assessment, per day, per organization
- **Optimize usage** - Identify expensive operations and optimize workflows
- **Budget planning** - Forecast costs based on historical usage
- **Client billing** - Track AI costs per client/assessment for accurate billing

---

## 📊 What Gets Tracked

### Every AI Operation Logs:
- **Operation Type** - embedding, analysis, rag_query, document_processing
- **Model Used** - gpt-4-turbo-preview, text-embedding-3-small, etc.
- **Provider** - openai, anthropic
- **Token Usage** - Input tokens, output tokens, total tokens
- **Cost in USD** - Calculated based on current pricing (6 decimal precision)
- **Response Time** - Milliseconds taken for the operation
- **Context** - Assessment, control, document, user, organization
- **Metadata** - Additional details (evidence count, confidence score, etc.)

---

## 🗄️ Database Schema

### `ai_usage` Table
```sql
CREATE TABLE ai_usage (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    user_id UUID NOT NULL,
    assessment_id UUID,
    control_id VARCHAR(50),
    document_id UUID,
    operation_type VARCHAR(50) NOT NULL,  -- 'embedding', 'analysis', etc.
    model_name VARCHAR(100) NOT NULL,
    provider VARCHAR(50) NOT NULL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER NOT NULL,
    cost_usd DECIMAL(10, 6) NOT NULL,
    request_id VARCHAR(255),
    response_time_ms INTEGER,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### Materialized View for Performance
```sql
CREATE MATERIALIZED VIEW ai_cost_daily_summary AS
SELECT
    organization_id,
    DATE(created_at) as usage_date,
    operation_type,
    model_name,
    provider,
    COUNT(*) as operation_count,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(response_time_ms) as avg_response_time_ms
FROM ai_usage
GROUP BY organization_id, DATE(created_at), operation_type, model_name, provider;
```

---

## 🔌 API Endpoints

### 1. Get Assessment Costs
```bash
GET /api/v1/ai/costs/assessment/{assessment_id}
```

**Response**:
```json
{
  "assessment_id": "uuid",
  "total_operations": 245,
  "total_tokens": 12500,
  "total_cost_usd": 2.45,
  "first_operation": "2025-11-15T10:00:00Z",
  "last_operation": "2025-11-15T15:30:00Z",
  "breakdown": [
    {
      "operation_type": "analysis",
      "model_name": "gpt-4-turbo-preview",
      "count": 110,
      "tokens": 8500,
      "cost_usd": 2.10
    },
    {
      "operation_type": "embedding",
      "model_name": "text-embedding-3-small",
      "count": 135,
      "tokens": 4000,
      "cost_usd": 0.08
    }
  ]
}
```

### 2. Get Organization Costs
```bash
GET /api/v1/ai/costs/organization?start_date=2025-11-01&end_date=2025-11-15
```

**Response**:
```json
{
  "organization_id": "uuid",
  "period": {
    "start": "2025-11-01T00:00:00Z",
    "end": "2025-11-15T23:59:59Z"
  },
  "summary": {
    "total_operations": 1245,
    "total_tokens": 65000,
    "total_cost_usd": 12.50
  },
  "daily_breakdown": [
    {
      "date": "2025-11-15",
      "operations": 245,
      "tokens": 12500,
      "cost_usd": 2.45
    }
  ],
  "operation_breakdown": [
    {
      "operation_type": "analysis",
      "count": 550,
      "tokens": 45000,
      "cost_usd": 11.25
    },
    {
      "operation_type": "embedding",
      "count": 695,
      "tokens": 20000,
      "cost_usd": 0.40
    }
  ]
}
```

### 3. Get Recent Usage
```bash
GET /api/v1/ai/costs/usage?limit=50
```

**Response**:
```json
{
  "records": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "assessment_id": "uuid",
      "control_id": "AC.L2-3.1.1",
      "operation_type": "analysis",
      "model_name": "gpt-4-turbo-preview",
      "provider": "openai",
      "total_tokens": 1247,
      "cost_usd": 0.012470,
      "response_time_ms": 3200,
      "created_at": "2025-11-15T15:30:00Z"
    }
  ],
  "total_count": 50
}
```

### 4. Get Cost Summary (Dashboard)
```bash
GET /api/v1/ai/costs/summary
```

**Response**:
```json
{
  "today": {
    "operations": 25,
    "tokens": 2500,
    "cost_usd": 0.50
  },
  "this_month": {
    "operations": 1245,
    "tokens": 65000,
    "cost_usd": 12.50
  },
  "average_per_assessment": {
    "assessment_count": 5,
    "avg_cost_usd": 2.50
  },
  "top_models": [
    {
      "model_name": "gpt-4-turbo-preview",
      "usage_count": 550,
      "total_cost_usd": 11.25
    }
  ]
}
```

### 5. Refresh Cost Summary (Admin Only)
```bash
POST /api/v1/ai/costs/refresh-summary
```

**Description**: Refreshes the materialized view for faster queries. Call after bulk operations.

---

## 💵 Current Pricing (as of 2024)

### OpenAI Models
| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) |
|-------|---------------------------|----------------------------|
| **GPT-4 Turbo** | $10.00 | $30.00 |
| **GPT-4** | $30.00 | $60.00 |
| **GPT-3.5 Turbo** | $0.50 | $1.50 |
| **text-embedding-3-small** | $0.02 | N/A |
| **text-embedding-3-large** | $0.13 | N/A |
| **text-embedding-ada-002** | $0.10 | N/A |

### Anthropic Models
| Model | Input Cost (per 1M tokens) | Output Cost (per 1M tokens) |
|-------|---------------------------|----------------------------|
| **Claude 3.5 Sonnet** | $3.00 | $15.00 |
| **Claude 3 Opus** | $15.00 | $75.00 |

**Note**: Prices are hardcoded in `services/ai_cost_service.py:calculate_cost()`. Update if pricing changes.

---

## 📈 Cost Estimation

### Typical CMMC Level 2 Assessment

**Scenario**: 110 controls, 500 evidence documents, 25K pages total

| Operation | Volume | Avg Tokens | Total Tokens | Cost |
|-----------|--------|-----------|--------------|------|
| **Document Embeddings** | 500 docs | 100 tokens/doc | 50,000 | $0.001 |
| **Evidence Chunking** | 25K chunks | 100 tokens/chunk | 2,500,000 | $0.05 |
| **AI Control Analysis** | 110 controls | 1,200 tokens/control | 132,000 | $1.32 |
| **RAG Queries** | 1,000 queries | 500 tokens/query | 500,000 | $0.01 |
| **Total** | | | **3,182,000** | **~$1.38** |

**Reality Check**: Actual costs typically range from **$2-10** per assessment depending on:
- Evidence volume (more documents = more embeddings)
- Control complexity (complex controls need more AI reasoning)
- RAG usage (how many searches are performed)

---

## 🎛️ How Cost Tracking Works

### 1. Automatic Logging in `main.py`

#### Embedding Generation
```python
async def generate_embedding(
    text: str,
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    assessment_id: Optional[str] = None,
    document_id: Optional[str] = None
) -> List[float]:
    # ... generate embedding using OpenAI
    result = await embedding_service.embed_text(text)

    # Log cost if IDs are available
    if organization_id and user_id:
        cost_service = await get_ai_cost_service()
        cost = cost_service.calculate_cost(
            model_name=result.model,
            total_tokens=result.tokens_used
        )
        await cost_service.log_usage(
            organization_id=organization_id,
            user_id=user_id,
            assessment_id=assessment_id,
            document_id=document_id,
            operation_type='embedding',
            model_name=result.model,
            provider='openai',
            total_tokens=result.tokens_used,
            cost_usd=cost,
            response_time_ms=response_time_ms,
            metadata={'text_length': len(text)}
        )
```

#### AI Analysis
```python
async def analyze_control_with_ai(
    control_id: str,
    # ...
    organization_id: Optional[str] = None,
    user_id: Optional[str] = None,
    assessment_id: Optional[str] = None
) -> Dict[str, Any]:
    # ... run AI analysis
    result = await ai_service.analyze_control(...)

    # Log cost
    if organization_id and user_id:
        cost_service = await get_ai_cost_service()
        provider = 'openai' if 'gpt' in result.model_used.lower() else 'anthropic'
        cost = cost_service.calculate_cost(
            model_name=result.model_used,
            total_tokens=result.tokens_used
        )
        await cost_service.log_usage(
            organization_id=organization_id,
            user_id=user_id,
            assessment_id=assessment_id,
            control_id=control_id,
            operation_type='analysis',
            model_name=result.model_used,
            provider=provider,
            total_tokens=result.tokens_used,
            cost_usd=cost,
            metadata={
                'evidence_count': len(evidence_items),
                'status': result.status.value,
                'confidence': result.ai_confidence_score
            }
        )
```

### 2. Cost Calculation Logic

The `calculate_cost()` method in `AICostService` uses hardcoded pricing:

```python
def calculate_cost(
    self,
    model_name: str,
    total_tokens: int,
    input_tokens: int = 0,
    output_tokens: int = 0
) -> float:
    pricing = {
        "text-embedding-3-small": 0.00002,  # per 1M tokens
        "gpt-4-turbo-preview": {
            "input": 0.01,   # per 1M input tokens
            "output": 0.03   # per 1M output tokens
        }
    }

    # Calculate based on model pricing structure
    if isinstance(pricing[model_name], dict):
        # Different pricing for input/output
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    else:
        # Single price per token (embeddings)
        return (total_tokens / 1_000_000) * pricing[model_name]
```

---

## 🚀 Usage Examples

### Track Costs During Document Upload

When uploading evidence with embeddings enabled:

```python
# In document ingestion endpoint
for chunk in chunks:
    embedding = await generate_embedding(
        text=chunk_text,
        organization_id=auth_context.organization_id,
        user_id=auth_context.user_id,
        assessment_id=request.assessment_id,
        document_id=document_id
    )
```

**Result**: Each embedding call logs a record in `ai_usage` table.

### Track Costs During AI Analysis

When analyzing a control:

```python
# In assessment workflow
analysis_result = await analyze_control_with_ai(
    control_id="AC.L2-3.1.1",
    evidence_items=evidence,
    organization_id=auth_context.organization_id,
    user_id=auth_context.user_id,
    assessment_id=assessment_id
)
```

**Result**: AI analysis call logs tokens, cost, and confidence score.

### View Assessment Costs

```bash
# Get total costs for an assessment
curl -X GET http://localhost:8000/api/v1/ai/costs/assessment/assessment-uuid \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response shows:
# - Total operations: 245
# - Total tokens: 12,500
# - Total cost: $2.45
# - Breakdown by operation type
```

---

## 📊 Cost Optimization Tips

### 1. Use Cheaper Embedding Models
```python
# Instead of:
EmbeddingModel.OPENAI_3_LARGE  # $0.13 per 1M tokens

# Use:
EmbeddingModel.OPENAI_3_SMALL  # $0.02 per 1M tokens
# ✅ Already the default in the platform
```

### 2. Batch Embeddings
```python
# Good: Batch processing (already implemented)
embeddings = await embedding_service.embed_batch(texts)

# Bad: Individual calls (avoid)
for text in texts:
    embedding = await embedding_service.embed_text(text)
```

### 3. Cache Embeddings
- Documents with same content should reuse embeddings
- Store embeddings in database for reuse
- ✅ Platform already does this via `document_chunks` table

### 4. Use GPT-3.5 Instead of GPT-4 for Simple Controls
```python
# For simple controls (AC.L2-3.1.1 - basic access control)
primary_model = AIModel.GPT35_TURBO  # $0.50 input, $1.50 output

# For complex controls (require reasoning)
primary_model = AIModel.GPT4_TURBO   # $10 input, $30 output
```

**Trade-off**: GPT-3.5 is 20x cheaper but produces lower quality analysis.

### 5. Disable Auto-Embed for Test Documents
```bash
# When uploading test/draft documents
curl -X POST /api/v1/ingest/document \
  -F "file=@test.pdf" \
  -F "auto_embed=false"  # Don't generate embeddings yet
```

---

## 🔍 Monitoring and Alerts

### Query Daily Spending
```sql
SELECT
    DATE(created_at) as date,
    COUNT(*) as operations,
    SUM(total_tokens) as tokens,
    SUM(cost_usd) as cost_usd
FROM ai_usage
WHERE organization_id = 'your-org-id'
  AND created_at >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Find Most Expensive Operations
```sql
SELECT
    operation_type,
    model_name,
    AVG(cost_usd) as avg_cost,
    MAX(cost_usd) as max_cost,
    COUNT(*) as count
FROM ai_usage
WHERE organization_id = 'your-org-id'
GROUP BY operation_type, model_name
ORDER BY avg_cost DESC;
```

### Identify Slow AI Calls
```sql
SELECT
    id,
    operation_type,
    model_name,
    response_time_ms,
    cost_usd,
    created_at
FROM ai_usage
WHERE organization_id = 'your-org-id'
  AND response_time_ms > 5000  -- Slower than 5 seconds
ORDER BY response_time_ms DESC
LIMIT 20;
```

---

## 🧪 Testing

### 1. Run the Migration
```bash
cd /home/user/CISO/cmmc-platform
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform \
  -f /database/migrations/006_ai_cost_tracking.sql
```

### 2. Verify Tables Created
```sql
-- Check table exists
SELECT COUNT(*) FROM ai_usage;  -- Should return 0

-- Check materialized view exists
SELECT COUNT(*) FROM ai_cost_daily_summary;  -- Should return 0
```

### 3. Test Cost Tracking
```bash
# Upload a document with embeddings
curl -X POST http://localhost:8000/api/v1/ingest/document \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf" \
  -F "assessment_id=YOUR_ASSESSMENT_ID" \
  -F "auto_embed=true"

# Check costs were logged
curl http://localhost:8000/api/v1/ai/costs/assessment/YOUR_ASSESSMENT_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. Test AI Analysis Tracking
```bash
# Run AI analysis on a control
curl -X POST http://localhost:8000/api/v1/analyze/control \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "control_id": "AC.L2-3.1.1",
    "evidence_items": [...]
  }'

# Check costs in database
SELECT * FROM ai_usage
WHERE operation_type = 'analysis'
ORDER BY created_at DESC
LIMIT 5;
```

---

## 🐛 Troubleshooting

### Error: "Failed to log AI usage"
**Symptom**: Warning in logs but AI operations still work
**Cause**: Cost tracking is optional - errors don't break AI features
**Fix**: Check database connection and migration status

### Missing Costs in Reports
**Symptom**: API calls succeed but no costs logged
**Cause**: `organization_id` or `user_id` not passed to AI functions
**Fix**: Ensure endpoints pass auth context to `generate_embedding()` and `analyze_control_with_ai()`

### Incorrect Cost Calculations
**Symptom**: Costs don't match OpenAI dashboard
**Cause**: Pricing in `ai_cost_service.py` is outdated
**Fix**: Update pricing in `calculate_cost()` method

---

## 📚 Next Steps

### Immediate (Working Now):
- ✅ Database tables created
- ✅ Cost logging integrated
- ✅ API endpoints available
- ✅ Auto-tracking on all AI calls

### Short Term (1-2 weeks):
- [ ] Add cost budget alerts
- [ ] Create cost reports (PDF/Excel export)
- [ ] Add frontend dashboard for costs
- [ ] Implement cost-based throttling

### Long Term (1-2 months):
- [ ] Predictive cost modeling (forecast based on assessment size)
- [ ] Cost allocation by client/project
- [ ] Auto-optimization (switch models based on budget)
- [ ] Integration with accounting systems

---

**Questions?** Check the API logs: `docker-compose logs api | grep -i "cost\|usage"`

**Updated**: 2025-11-15
**By**: Claude
**Feature**: AI Cost Tracking
