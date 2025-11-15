# CMMC Platform - Project Structure

## 📁 Directory Layout

```
cmmc-platform/
├── README.md                           # Main documentation
├── DEPLOYMENT.md                       # Hetzner deployment guide
├── docker-compose.yml                  # Multi-service orchestration
├── .env                                # Environment variables (not in repo)
├── .gitignore
│
├── api/                                # FastAPI Service
│   ├── main.py                         # Core API with all endpoints
│   ├── Dockerfile                      # Container configuration
│   ├── requirements.txt                # Python dependencies
│   ├── models/                         # Pydantic models
│   │   ├── __init__.py
│   │   ├── evidence.py
│   │   ├── findings.py
│   │   └── assessments.py
│   ├── services/                       # Business logic
│   │   ├── __init__.py
│   │   ├── ai_analysis.py             # AI control analysis
│   │   ├── rag_engine.py              # RAG implementation
│   │   └── report_generator.py        # SSP/POA&M generation
│   └── utils/
│       ├── __init__.py
│       ├── crypto.py                  # Hashing & encryption
│       └── evidence_storage.py        # File handling
│
├── database/                           # Database Schemas
│   ├── schema.sql                      # Main schema (evidence, controls, etc.)
│   ├── migrations/                     # Alembic migrations
│   │   ├── versions/
│   │   └── env.py
│   └── seeds/                          # Seed data
│       ├── control_domains.sql
│       └── provider_offerings.sql
│
├── scripts/                            # Utility Scripts
│   ├── import_cmmc_framework.py        # CMMC L2 + 800-171A import
│   ├── backup.sh                       # Database backup
│   ├── restore.sh                      # Database restore
│   └── migrate.sh                      # Run migrations
│
├── integrations/                       # External Service Connectors
│   ├── __init__.py
│   ├── nessus_connector.py             # Nessus (API + file)
│   ├── splunk_connector.py             # Splunk HEC + SPL
│   └── cloud_connectors/
│       ├── __init__.py
│       ├── azure_connector.py          # Azure Policy, Entra ID
│       ├── aws_connector.py            # AWS Security Hub, IAM
│       └── m365_connector.py           # M365 GCC High
│
├── config/                             # Configuration Files
│   ├── nginx.conf                      # Reverse proxy config
│   ├── postgres.conf                   # PostgreSQL tuning
│   ├── redis.conf                      # Redis configuration
│   └── ssl/                            # SSL certificates
│       ├── fullchain.pem
│       └── privkey.pem
│
├── data/                               # Persistent Data (gitignored)
│   ├── postgres/                       # Database files
│   ├── redis/                          # Redis persistence
│   ├── minio/                          # Object storage
│   ├── evidence/                       # Evidence files
│   └── ciso-assistant/                 # CISO Assistant media
│
├── logs/                               # Application Logs
│   ├── api/
│   ├── nginx/
│   └── celery/
│
├── tests/                              # Test Suite
│   ├── __init__.py
│   ├── conftest.py                     # Pytest fixtures
│   ├── test_database.py                # Database tests
│   ├── test_api.py                     # API endpoint tests
│   ├── test_integrations.py            # Integration tests
│   ├── test_ai_analysis.py             # AI/RAG tests
│   └── load_test.py                    # Locust load tests
│
└── docs/                               # Additional Documentation
    ├── architecture.md                 # Architecture deep dive
    ├── api_reference.md                # API documentation
    ├── control_mappings.md             # Nessus→CMMC mappings
    └── assessment_guide.md             # How to use for assessments
```

## 🗄️ Database Schema Overview

### Core Tables (Evidence & Assessment)
```
organizations
  ├── users
  ├── assessments
  │   ├── assessment_scope
  │   ├── evidence
  │   │   └── evidence_access_log
  │   ├── control_findings
  │   └── poam_items
  └── integration_runs
```

### Framework Tables (CMMC/800-171)
```
control_domains (AC, AU, AT, CM, IA, IR, MA, MP, PS, PE, RA, CA, SC, SI, SR)
  └── controls (110 NIST 800-171 requirements)
      └── assessment_objectives (800-171A: Examine/Interview/Test)
```

### Provider Inheritance
```
provider_offerings (M365 GCC High, Azure Gov, AWS GovCloud)
  └── provider_control_inheritance (Inherited/Shared/Customer)
```

### RAG & Documentation
```
documents
  └── document_chunks (with pgvector embeddings)
```

### System Architecture
```
system_diagrams
  ├── graph_nodes (assets, systems, boundaries)
  └── graph_edges (connections, data flows)
```

## 🔌 API Structure

### Document Management
- `POST /api/v1/ingest/document` - Upload & chunk documents
- `GET /api/v1/documents/{document_id}` - Get document details
- `GET /api/v1/documents/{document_id}/chunks` - Get chunks

### Control Analysis
- `POST /api/v1/analyze/{control_id}` - AI-assisted analysis
- `GET /api/v1/controls/{control_id}/findings` - Get findings
- `PUT /api/v1/findings/{finding_id}` - Update/override finding

### Evidence Management
- `POST /api/v1/evidence/upload` - Upload evidence
- `GET /api/v1/evidence/{evidence_id}` - Get evidence
- `GET /api/v1/evidence/{evidence_id}/access-log` - Chain-of-custody

### Report Generation
- `POST /api/v1/ssp/{assessment_id}` - Generate SSP
- `POST /api/v1/poam/{assessment_id}` - Generate POA&M
- `POST /api/v1/sar/{assessment_id}` - Generate SAR

### Provider Inheritance
- `GET /api/v1/provider-inheritance/{control_id}` - Get inheritance
- `POST /api/v1/provider-inheritance` - Add new provider

### Integrations
- `POST /api/v1/integrations/nessus/scan` - Trigger Nessus scan
- `POST /api/v1/integrations/splunk/query` - Run SPL query
- `POST /api/v1/integrations/azure/policies` - Pull Azure policies

## 🐳 Docker Services

### Core Services
1. **postgres** - Database with pgvector (port 5432)
2. **redis** - Cache & task queue (port 6379)
3. **minio** - Object storage (ports 9000, 9001)

### Application Services
4. **ciso-assistant** - GRC UI (port 8080 → nginx)
5. **api** - FastAPI service (port 8000 → nginx)
6. **celery-worker** - Background tasks

### Infrastructure
7. **nginx** - Reverse proxy & SSL termination (ports 80, 443)

## 🔐 Security Layers

### Network Security
```
Internet → Nginx (SSL/TLS)
         → CISO Assistant (8080)
         → FastAPI (8000)
         → PostgreSQL (internal only)
         → Redis (internal only)
         → MinIO (internal only)
```

### Data Security
- **At Rest**: AES-256 encryption (MinIO)
- **In Transit**: TLS 1.3 (Nginx)
- **Database**: RLS policies per tenant
- **Evidence**: SHA-256 hashing, immutable storage

### Access Control
```
User → JWT Token → RBAC Check → RLS Filter → Data Access
```

## 📊 Data Flow

### Evidence Ingestion Flow
```
1. File Upload → API
2. Calculate SHA-256 hash
3. Store in MinIO (immutable)
4. Create evidence record (database)
5. Log access (chain-of-custody)
6. Trigger AI analysis (optional)
```

### Control Analysis Flow
```
1. API receives analysis request
2. Query evidence for control
3. Fetch provider inheritance
4. Get diagram context
5. RAG retrieval from document chunks
6. Call AI model with context
7. Generate finding with rationale
8. Store for human review
```

### Report Generation Flow
```
1. Gather all findings
2. Apply template
3. Include diagrams
4. Add provider inheritance
5. Generate DOCX/PDF
6. Store in MinIO
7. Return download link
```

## 🧩 Integration Points

### Inbound (Evidence Collection)
- **Nessus** → Vulnerabilities → RA/SI/CM controls
- **Splunk** → Log events → AU/IR/CA controls
- **Azure Policy** → Compliance checks → CM/AC controls
- **AWS Security Hub** → Findings → Multiple domains

### Outbound (Audit Trail)
- **Splunk** ← Compliance events (HEC)
- **Jira** ← POA&M items (tasks)
- **Slack** ← Assessment alerts
- **Email** ← Report notifications

## 🎯 Key Design Patterns

### 1. Chain of Custody
Every evidence interaction is logged:
```python
evidence_access_log(
    evidence_id,
    user_id,
    action='view',
    ip_address,
    timestamp
)
```

### 2. Immutable Evidence
Evidence files never change:
```python
file_hash = SHA256(file_content)
if exists(file_hash):
    reference_existing()
else:
    store_new(file_hash)
```

### 3. Human-in-the-Loop
AI findings require approval:
```python
finding = ai_analyze(control)
finding.status = 'pending_review'
finding.ai_generated = True
# Human reviews and approves/overrides
```

### 4. Provider Inheritance
Reduce duplicate work:
```python
if provider_inherits(control):
    narrative = provider_narrative
    responsibility = 'Inherited'
else:
    narrative = customer_narrative
    responsibility = 'Customer'
```

## 📚 Framework Data

### CMMC Level 2 Structure
```
14 Domains
  └── 110 Controls (NIST 800-171)
      └── ~320 Assessment Objectives (800-171A)
          ├── Examine (documentation review)
          ├── Interview (personnel interviews)
          └── Test (technical testing)
```

### Example: Access Control Domain
```
AC - Access Control
  ├── AC.L2-3.1.1: Authorized Access Control
  │   ├── AC.L2-3.1.1[a] (Examine): authorized users identified
  │   ├── AC.L2-3.1.1[b] (Examine): processes identified
  │   ├── AC.L2-3.1.1[c] (Examine): devices identified
  │   └── AC.L2-3.1.1[d] (Test): access limited to authorized
  ├── AC.L2-3.1.2: Transaction Control
  │   └── ...
  └── ... (22 total AC controls)
```

## 🚀 Development Workflow

### Local Development
```bash
# Start dependencies only
docker-compose up -d postgres redis minio

# Run API locally
cd api
pip install -r requirements.txt
uvicorn main:app --reload

# Run tests
pytest tests/

# Access local CISO Assistant
docker-compose up ciso-assistant
```

### Production Deployment
```bash
# Deploy to Hetzner
ssh cmmc@your-server
cd ~/cmmc-platform
docker-compose pull
docker-compose up -d

# Run migrations
./scripts/migrate.sh

# Verify
curl https://your-domain.com/health
```

## 🔄 Continuous Integration

### GitHub Actions (Future)
```yaml
.github/workflows/
  ├── test.yml          # Run tests on PR
  ├── deploy.yml        # Deploy to production
  └── backup.yml        # Daily backups
```

## 📦 Dependencies

### Python (API)
- **fastapi** - Web framework
- **asyncpg** - PostgreSQL driver
- **celery** - Task queue
- **openai** - AI model
- **anthropic** - Claude API
- **minio** - Object storage
- **pypdf2** - PDF parsing
- **python-docx** - DOCX generation

### JavaScript (CISO Assistant)
- **Django** - Web framework
- **PostgreSQL** - Database
- **Celery** - Background tasks

### Infrastructure
- **PostgreSQL 16** with pgvector
- **Redis 7** - Cache & queue
- **MinIO** - S3-compatible storage
- **Nginx** - Reverse proxy

## 🎓 Learning Resources

- **CMMC 2.0**: https://dodcio.defense.gov/CMMC/
- **NIST 800-171**: https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final
- **800-171A Assessment**: https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf
- **CISO Assistant**: https://github.com/intuitem/ciso-assistant-community

---

**For questions about the project structure, see README.md or open an issue.**
