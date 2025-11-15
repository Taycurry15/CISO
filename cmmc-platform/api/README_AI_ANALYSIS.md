# AI Control Analysis System

AI-powered control analysis engine that generates assessor-grade findings for CMMC Level 2 compliance.

## Overview

This system analyzes CMMC controls against 800-171A assessment objectives using:
1. **RAG-Enhanced Context** - Retrieves relevant evidence from documents
2. **Multi-Model AI** - GPT-4 Turbo and Claude 3.5 Sonnet with fallback
3. **Confidence Scoring** - Multi-factor algorithm to assess finding reliability
4. **Evidence Traceability** - Every claim linked to specific evidence
5. **Human Review Workflow** - Assessor approval/override system

## Architecture

```
Assessment Request
       ↓
┌─────────────────────────────────────┐
│  AI Analysis Service                │
│                                     │
│  1. Fetch control details           │
│  2. Fetch 800-171A objectives       │
│  3. RAG: Retrieve evidence ━━━━━━━┐ │
│  4. Fetch provider inheritance    │ │
│  5. Build analysis prompt         │ │
│  6. Call AI model (GPT-4/Claude)  │ │
│  7. Parse JSON response           │ │
│  8. Calculate confidence score    │ │
│  9. Store finding in database     │ │
└─────────────────────────────────────┘ │
                                        │
              RAG Engine ←──────────────┘
                ↓
        Vector Similarity Search
                ↓
        Top-5 Evidence Chunks
```

## Components

### 1. AI Analysis Service (`services/ai_analysis.py`)

**Primary class:** `AIAnalysisService`

**Features:**
- Multi-model support (GPT-4 Turbo, Claude 3.5 Sonnet)
- Automatic fallback if primary model fails
- Structured JSON output enforcement
- Provider inheritance integration
- Evidence traceability
- Token usage tracking

**Example Usage:**
```python
from services.ai_analysis import AIAnalysisService, AIModel

# Initialize service
ai_service = AIAnalysisService(
    db_pool=db_pool,
    rag_engine=rag_engine,
    confidence_scorer=confidence_scorer,
    primary_model=AIModel.GPT4_TURBO,
    fallback_model=AIModel.CLAUDE_35_SONNET
)

# Analyze a control
result = await ai_service.analyze_control(
    control_id="AC.L2-3.1.1",
    assessment_id="uuid",
    include_provider_inheritance=True,
    top_k_evidence=10
)

print(f"Status: {result.status}")
print(f"Confidence: {result.ai_confidence_score:.1%}")
print(f"Narrative: {result.assessor_narrative}")
print(f"Evidence used: {len(result.evidence_references)}")
```

**Key Method: `analyze_control()`**

Returns `FindingResult` with:
- `status`: Met | Not Met | Partially Met | Not Applicable
- `assessor_narrative`: 2-4 paragraph finding narrative
- `ai_confidence_score`: 0-1 confidence score
- `ai_rationale`: AI's reasoning process
- `evidence_references`: List of evidence used
- `provider_inheritance`: Provider info (if applicable)
- `requires_human_review`: Boolean flag

### 2. Confidence Scorer (`services/confidence_scorer.py`)

**Primary class:** `ConfidenceScorer`

**Confidence Formula:**
```
Confidence = (
    evidence_quality    × 40% +
    evidence_quantity   × 20% +
    evidence_recency    × 15% +
    provider_inheritance × 15% +
    ai_certainty        × 10%
)
```

**Confidence Levels:**
| Score | Level | Interpretation |
|-------|-------|----------------|
| 90-100% | Very High | High certainty, strong evidence |
| 75-89% | High | Good confidence, likely accurate |
| 60-74% | Medium | Moderate confidence, review recommended |
| 40-59% | Low | Low confidence, manual review required |
| 0-39% | Very Low | Very uncertain, insufficient evidence |

**Example Usage:**
```python
from services.confidence_scorer import ConfidenceScorer, ConfidenceFactors

scorer = ConfidenceScorer()

# Calculate confidence
factors = ConfidenceFactors(
    evidence_quality=0.85,    # High quality evidence
    evidence_quantity=0.75,   # Sufficient quantity
    evidence_recency=0.90,    # Very recent
    provider_inheritance=1.0,  # Fully inherited
    ai_certainty=0.80         # High AI confidence
)

breakdown = scorer.calculate_with_breakdown(factors)

print(f"Score: {breakdown.overall_score:.1%}")
print(f"Level: {breakdown.confidence_level.value}")
print(breakdown.explanation)
print("\nRecommendations:")
for rec in breakdown.recommendations:
    print(f"  • {rec}")
```

**Helper Methods:**
- `assess_evidence_quality()` - Evaluates evidence quality from relevance, diversity, directness
- `assess_evidence_quantity()` - Checks if sufficient evidence for objectives
- `assess_evidence_recency()` - Scores based on age (< 30 days = 1.0, > 6 months = decay)
- `assess_provider_inheritance()` - Scores based on Inherited (1.0) vs Shared (0.7) vs Customer (0.5)

### 3. Prompt Engineering

**System Prompt:**
```
You are an expert CMMC Level 2 assessor with deep knowledge of NIST SP 800-171
and the CMMC Assessment Guide.

Your role is to analyze controls based on available evidence and determine
compliance status according to 800-171A assessment objectives.

You must:
1. Base your analysis ONLY on the evidence provided
2. Map evidence to specific assessment objectives (Examine/Interview/Test)
3. Determine if objectives are Met, Not Met, or Partially Met
4. Provide clear, assessor-grade narratives
5. Reference specific evidence for every claim
6. Be conservative - if evidence is insufficient, mark as Not Met
7. Output your response in valid JSON format
```

**User Prompt Structure:**
1. **Control Information** - ID, title, requirement text, discussion
2. **Assessment Objectives** - All objectives with determination statements
3. **Provider Inheritance** (if applicable) - Provider name, responsibility, narrative
4. **Available Evidence** - Top-K retrieved chunks with relevance scores
5. **Analysis Instructions** - JSON format specification

**Expected JSON Output:**
```json
{
  "status": "Met | Not Met | Partially Met | Not Applicable",
  "narrative": "Detailed assessor narrative...",
  "rationale": "AI reasoning process...",
  "evidence_mapping": [
    {
      "evidence_number": 1,
      "objective_letter": "a",
      "supports": "Met",
      "explanation": "How evidence supports objective"
    }
  ],
  "confidence": "75",
  "gaps": ["List of evidence gaps"],
  "recommendations": ["Recommendations for improvement"]
}
```

## API Endpoints (`analysis_api.py`)

### Analyze Single Control

```http
POST /api/v1/analysis/control/{control_id}
Content-Type: application/json

{
  "assessment_id": "uuid",
  "objective_id": "AC.L2-3.1.1[a]",  // Optional: specific objective
  "include_provider_inheritance": true,
  "top_k_evidence": 10,
  "model": "gpt-4-turbo-preview"
}

Response:
{
  "finding_id": "uuid",
  "control_id": "AC.L2-3.1.1",
  "status": "Met",
  "assessor_narrative": "The organization has implemented...",
  "confidence_score": 0.85,
  "confidence_level": "High",
  "ai_rationale": "Evidence 1 demonstrates...",
  "evidence_count": 3,
  "evidence_references": [
    {
      "evidence_id": "uuid",
      "document_title": "Access Control Policy",
      "relevance_score": 0.92
    }
  ],
  "requires_human_review": false,
  "model_used": "gpt-4-turbo-preview",
  "tokens_used": 2453
}
```

### Analyze Full Assessment

```http
POST /api/v1/analysis/assessment/{assessment_id}
Content-Type: application/json

{
  "control_ids": ["AC.L2-3.1.1", "AC.L2-3.1.2"],  // Optional
  "domain_filter": "AC",  // Optional
  "batch_size": 5
}

Response:
{
  "job_id": "uuid",
  "assessment_id": "uuid",
  "total_controls": 22,
  "status": "running",
  "message": "Started analysis of 22 controls"
}
```

### Analyze Domain

```http
POST /api/v1/analysis/domain/AC
Content-Type: application/json

{
  "assessment_id": "uuid",
  "batch_size": 5
}

Response:
{
  "job_id": "uuid",
  "assessment_id": "uuid",
  "total_controls": 22,
  "status": "running",
  "message": "Started analysis of domain AC (22 controls)"
}
```

### Get Finding

```http
GET /api/v1/analysis/finding/{finding_id}

Response:
{
  "finding_id": "uuid",
  "control_id": "AC.L2-3.1.1",
  "status": "Met",
  "assessor_narrative": "...",
  "confidence_score": 0.85,
  "evidence_references": [...]
}
```

### Update Finding (Human Review)

```http
PUT /api/v1/analysis/finding/{finding_id}
Content-Type: application/json

{
  "status": "Partially Met",  // Optional override
  "assessor_narrative": "Updated narrative...",  // Optional override
  "override_reason": "Additional testing revealed...",
  "reviewed_by": "user-uuid"
}

Response:
{
  "message": "Finding updated successfully",
  "finding_id": "uuid"
}
```

### Get Assessment Statistics

```http
GET /api/v1/analysis/assessment/{assessment_id}/stats

Response:
{
  "total_findings": 110,
  "by_status": {
    "Met": 85,
    "Not Met": 12,
    "Partially Met": 10,
    "Not Applicable": 3
  },
  "avg_confidence": 0.78,
  "requires_review_count": 15,
  "by_domain": {
    "AC": 22,
    "IA": 11,
    "AU": 9
  }
}
```

## Workflow

### End-to-End Analysis Flow

```
1. Upload Documents
   └─> POST /api/v1/documents/upload
       (policies, procedures, evidence)

2. Analyze Controls
   └─> POST /api/v1/analysis/control/AC.L2-3.1.1
       AI retrieves evidence, analyzes, returns finding

3. Review Findings
   └─> GET /api/v1/analysis/assessment/{id}/stats
       Check status distribution, confidence scores

4. Human Review
   └─> PUT /api/v1/analysis/finding/{id}
       Assessor approves or overrides AI findings

5. Generate Reports
   └─> POST /api/v1/reports/ssp/{assessment_id}
       SSP includes all approved findings
```

### Batch Analysis Flow

```
1. Trigger Batch Analysis
   POST /api/v1/analysis/assessment/{id}
   └─> Returns job_id, starts background task

2. Monitor Progress
   Periodically check:
   GET /api/v1/analysis/assessment/{id}/stats

3. Review Results
   GET /api/v1/analysis/finding/{finding_id}
   (for each finding)

4. Approve or Override
   PUT /api/v1/analysis/finding/{finding_id}
```

## Configuration

### Environment Variables

```bash
# AI Models
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Model Selection
export AI_PRIMARY_MODEL="gpt-4-turbo-preview"
export AI_FALLBACK_MODEL="claude-3-5-sonnet-20241022"

# RAG Settings
export RAG_TOP_K=10
export RAG_RERANK_TOP_K=20

# Confidence Thresholds
export CONFIDENCE_REQUIRE_REVIEW_THRESHOLD=0.70
export CONFIDENCE_AUTO_APPROVE_THRESHOLD=0.85
```

### Confidence Scoring Tuning

Adjust weights based on your priorities:

```python
scorer = ConfidenceScorer(
    evidence_quality_weight=0.50,    # Emphasize quality
    evidence_quantity_weight=0.20,
    evidence_recency_weight=0.10,    # De-emphasize recency
    provider_inheritance_weight=0.15,
    ai_certainty_weight=0.05         # De-emphasize AI confidence
)
```

## Cost Estimation

**Per Control Analysis:**
- Prompt tokens: ~1,500-2,000 (control + objectives + evidence)
- Completion tokens: ~500-800 (narrative + rationale)
- Total tokens: ~2,000-2,800 per control

**Costs (as of 2024):**
- **GPT-4 Turbo**: $0.01/1K input + $0.03/1K output = ~$0.03 per control
- **Claude 3.5 Sonnet**: $0.003/1K input + $0.015/1K output = ~$0.015 per control

**Full CMMC L2 Assessment (110 controls):**
- GPT-4 Turbo: **$3.30**
- Claude 3.5 Sonnet: **$1.65**

Very cost-effective for automation!

## Performance

**Benchmarks:**
- Single control analysis: 5-10 seconds
- Evidence retrieval: <100ms
- AI inference: 4-8 seconds (GPT-4), 3-6 seconds (Claude)
- Confidence calculation: <1ms
- Database storage: <100ms

**Throughput:**
- Sequential: 6-12 controls/minute
- Batch (5 parallel): 20-30 controls/minute
- Full assessment (110 controls): 4-6 minutes

## Testing

Run tests:
```bash
# Confidence scorer tests
pytest tests/test_confidence_scorer.py -v

# AI analysis tests (requires API keys)
export OPENAI_API_KEY="sk-..."
pytest tests/test_ai_analysis.py -v

# All tests
pytest tests/ -v --cov=services
```

## Best Practices

### 1. Evidence Quality
- Upload comprehensive documentation before analysis
- Include policies, procedures, screenshots, configuration exports
- Tag evidence with control IDs when possible

### 2. Human Review
- Always review findings with confidence < 70%
- Review all "Not Met" findings
- Spot-check "Met" findings across domains

### 3. Provider Inheritance
- Configure provider inheritance before analysis
- Verify inherited controls don't require customer evidence
- Document shared responsibility splits

### 4. Iterative Improvement
- Start with one domain (e.g., AC)
- Review AI findings for accuracy
- Adjust evidence, re-analyze if needed
- Expand to other domains once confident

### 5. Cost Optimization
- Use Claude 3.5 Sonnet for cost savings (50% cheaper)
- Batch analyze during off-peak hours
- Cache results to avoid re-analysis

## Troubleshooting

**Issue: Low confidence scores across board**
- Solution: Upload more evidence, especially direct evidence (screenshots, configs)
- Check RAG retrieval is finding relevant chunks

**Issue: AI marks controls as "Not Met" despite evidence**
- Solution: Check evidence relevance scores
- Ensure evidence is tagged with correct control IDs
- Review prompt engineering

**Issue: Inconsistent findings**
- Solution: Lower temperature in AI model call (currently 0.3)
- Use same model consistently
- Increase evidence quantity

**Issue: High API costs**
- Solution: Switch to Claude 3.5 Sonnet (cheaper)
- Reduce top_k_evidence parameter
- Batch analyze instead of sequential

## Roadmap

### Phase 1 (Current) ✅
- GPT-4 and Claude integration
- Confidence scoring
- Evidence traceability
- Human review workflow

### Phase 2 (Next Sprint)
- Cross-encoder re-ranking for better evidence
- Few-shot examples in prompts
- Domain-specific prompt templates
- Automated remediation suggestions

### Phase 3 (Future)
- Fine-tuned model on CMMC assessments
- Active learning from human overrides
- Multi-objective optimization
- Real-time confidence updates

## References

- [NIST SP 800-171 Rev 2](https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final)
- [CMMC Assessment Guide](https://dodcio.defense.gov/CMMC/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [Anthropic Claude Documentation](https://docs.anthropic.com/)

---

**Built for assessor-grade CMMC compliance automation** 🚀

Generate findings in minutes, not days!
