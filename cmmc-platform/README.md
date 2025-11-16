# CMMC Compliance Platform - Assessor-Grade SaaS

An open-source, AI-powered compliance automation platform for **CMMC Level 1 & 2** certification, built on proven open-source GRC foundations with assessor-grade features.

## 🎯 What This Platform Does

This platform helps Defense Industrial Base (DIB) contractors achieve and maintain CMMC certification by:

- **Automating evidence collection** from vulnerability scanners, SIEM, and cloud providers
- **AI-assisted control analysis** with transparent reasoning and human-in-the-loop review
- **Provider inheritance** documentation for M365, Azure, AWS (saves 30-40% of effort)
- **Immutable evidence storage** with chain-of-custody tracking
- **Diagram-to-graph extraction** for system architecture documentation
- **Automated SSP, POA&M, and SAR generation** for assessments
- **Continuous monitoring** with real-time compliance scoring

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   CMMC Platform Stack                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Frontend: CISO Assistant (Django-based GRC UI)            │
│            https://github.com/intuitem/ciso-assistant       │
│                                                             │
│  API Layer: FastAPI (AI/RAG/Integrations)                  │
│             - Document ingestion & chunking                 │
│             - Control analysis with AI                      │
│             - Evidence management                           │
│             - Report generation                             │
│                                                             │
│  Data Layer: PostgreSQL + pgvector                          │
│              - Controls & objectives (800-171A)             │
│              - Evidence with chain-of-custody               │
│              - Findings & assessments                       │
│              - Document chunks for RAG                      │
│                                                             │
│  Storage: MinIO (S3-compatible)                             │
│           - Evidence files (immutable)                      │
│           - Generated reports                               │
│           - System diagrams                                 │
│                                                             │
│  Queue: Redis + Celery                                      │
│         - Background tasks                                  │
│         - Integration jobs                                  │
│         - Report generation                                 │
│                                                             │
│  Integrations:                                              │
│  ├─ Nessus (API + file-based)                              │
│  ├─ Splunk (HEC + SPL queries)                             │
│  ├─ Azure Policy                                            │
│  ├─ AWS Security Hub                                        │
│  └─ M365 / Entra ID                                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## ✨ Key Features

### 1. Evidence Model Built for Auditability
- **Immutable storage** with SHA-256 hashing
- **Chain-of-custody logging** for every access
- **Version control** for evidence updates
- **Method tagging** (Examine/Interview/Test per 800-171A)
- **Export-ready** for SAR generation

### 2. Provider Inheritance Library
Pre-populated with common services:
- **M365 GCC High** (E3/E5)
- **Azure Government**
- **AWS GovCloud**
- **CrowdStrike** (EDR)
- **Okta** (Identity)

Each includes:
- Control-level responsibility mapping (Inherited/Shared/Customer)
- Authoritative documentation links
- Pre-written narratives
- Evidence references

### 3. AI-Assisted Assessment
- **RAG tuned to 800-171A objectives** for targeted retrieval
- **Transparent reasoning** with confidence scores
- **Evidence traceability** - every claim linked to source
- **Human-in-the-loop** approval/override workflow
- **"Show why" feature** to explain AI decisions

### 4. Diagram → Graph Extraction
- **Vision model** extracts nodes and edges from architecture diagrams
- **JSON graph storage** for programmatic access
- **Context injection** into AI analysis
- **Automated SSP appendix** generation

### 5. Assessment-Ready Exports
- **System Security Plan (SSP)** - DOCX/PDF
- **Plan of Action & Milestones (POA&M)** - Excel/CSV
- **Security Assessment Report (SAR)** - Full template
- **SPRS score calculator** for NIST 800-171

## 📊 CMMC Support

### Level 1 (17 Practices)
- Basic cyber hygiene for Federal Contract Information (FCI)
- Annual self-assessment
- Controls: AC, IA, MP, PE, SC, SI

### Level 2 (110 Practices)
- All NIST SP 800-171 requirements for CUI
- Triennial C3PAO assessment
- 14 domains with 800-171A assessment objectives

## 🚀 Quick Start (Hetzner Deployment)

### Prerequisites
- Hetzner VPS (CPX41 recommended: 8 vCPU, 16GB RAM)
- Ubuntu 24.04 LTS
- Domain with DNS configured
- ~€50/month budget

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/cmmc-platform
cd cmmc-platform
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings:
# - Database passwords
# - API keys (OpenAI/Anthropic)
# - Domain name
# - MinIO credentials
nano .env
```

### 3. Deploy with Docker Compose
```bash
# Start all services
docker-compose up -d

# Initialize database
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -f /docker-entrypoint-initdb.d/01-schema.sql

# Import CMMC framework
python3 scripts/import_cmmc_framework.py
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -f cmmc_l2_import.sql

# Create admin user
docker-compose exec ciso-assistant python manage.py createsuperuser
```

### 4. Access Platform
- **CISO Assistant**: https://smartgnosis.com
- **API Docs**: https://smartgnosis.com/api/docs
- **MinIO Console**: http://your-ip:9001 (SSH tunnel only)

**Full deployment guide**: [DEPLOYMENT.md](./DEPLOYMENT.md)

## 📚 Documentation

### Core Files
- `database/schema.sql` - Complete database schema with evidence model
- `api/main.py` - FastAPI service with all endpoints
- `scripts/import_cmmc_framework.py` - CMMC L2 + 800-171A import
- `integrations/nessus_connector.py` - Vulnerability scanner integration
- `DEPLOYMENT.md` - Complete Hetzner deployment guide

### API Endpoints

#### Document Ingestion
```http
POST /api/v1/ingest/document
Content-Type: multipart/form-data

{
  "assessment_id": "uuid",
  "title": "Access Control Policy",
  "document_type": "policy",
  "control_id": "AC.L2-3.1.1",
  "auto_chunk": true,
  "auto_embed": true
}
```

#### Control Analysis
```http
POST /api/v1/analyze/{control_id}
Content-Type: application/json

{
  "assessment_id": "uuid",
  "objective_id": "AC.L2-3.1.1[a]",
  "include_provider_inheritance": true,
  "include_diagram_context": true
}

Response:
{
  "finding_id": "uuid",
  "status": "Met",
  "assessor_narrative": "...",
  "ai_confidence_score": 85.0,
  "ai_rationale": "...",
  "evidence_used": [...],
  "provider_inheritance": {...}
}
```

#### SSP Export
```http
POST /api/v1/ssp/{assessment_id}
Content-Type: application/json

{
  "include_inherited_controls": true,
  "include_diagrams": true,
  "format": "docx"
}
```

#### POA&M Export
```http
POST /api/v1/poam/{assessment_id}
Content-Type: application/json

{
  "format": "xlsx"
}
```

#### Evidence Upload
```http
POST /api/v1/evidence/upload
Content-Type: multipart/form-data

{
  "assessment_id": "uuid",
  "control_id": "AC.L2-3.1.1",
  "title": "MFA Configuration Screenshot",
  "evidence_type": "screenshot",
  "method": "Examine"
}
```

## 🔌 Integrations

### Nessus Integration
```python
from integrations.nessus_connector import NessusConnector

# API mode (Tenable.io)
config = {
    'mode': 'api',
    'base_url': 'https://cloud.tenable.com',
    'access_key': 'your-key',
    'secret_key': 'your-secret'
}

# File mode (Nessus Professional)
config = {
    'mode': 'file',
    'export_path': '/var/cmmc/nessus_exports'
}

connector = NessusConnector(config)
vulnerabilities = connector.parse_nessus_xml('scan.nessus')
await connector.ingest_to_database(vulnerabilities, assessment_id, conn)
```

### Splunk Integration
```python
# Coming soon: integrations/splunk_connector.py
# - HEC for outbound audit events
# - SPL queries for inbound log evidence
# - Auto-mapping to AU, IR, CA controls
```

### Cloud Provider Integration
```python
# Coming soon: integrations/cloud_connectors/
# - azure_connector.py (Azure Policy, Entra ID)
# - aws_connector.py (Security Hub, IAM)
# - m365_connector.py (Conditional Access, DLP)
```

## 🛡️ Security Features

### Multi-Tenancy Hardening
- Row-level security (RLS) policies
- Per-tenant KMS encryption keys
- Scoped search indices
- Redacted evidence previews

### Evidence Integrity
- SHA-256 hashing on upload
- Immutable storage (no overwrites)
- Access audit log
- Chain-of-custody report

### Authentication & Authorization
- JWT-based authentication
- Role-based access control (admin/assessor/viewer)
- SSO/SAML support (via CISO Assistant)
- API key management

## 📈 Roadmap

### Phase 1 (Weeks 1-4) ✅
- [x] Database schema with evidence model
- [x] FastAPI service with core endpoints
- [x] CMMC L2 + 800-171A framework import
- [x] Nessus integration (hybrid API/file)
- [x] Docker Compose deployment

### Phase 2 (Weeks 5-8)
- [ ] AI-powered control analysis (GPT-4/Claude)
- [ ] Document chunking & RAG pipeline
- [ ] Provider inheritance for M365/Azure/AWS
- [ ] Diagram extraction (vision model)
- [ ] SSP/POA&M/SAR generation

### Phase 3 (Weeks 9-12)
- [ ] Continuous monitoring dashboard
- [ ] SPRS score calculator
- [ ] Splunk integration (HEC + queries)
- [ ] Cloud connector suite
- [ ] Multi-tenant onboarding

### Phase 4 (SaaS Launch)
- [ ] Customer portal & self-service
- [ ] Billing integration (Stripe)
- [ ] White-labeling options
- [ ] C3PAO workflow support
- [ ] Assessment scheduling

## 🧪 Testing

```bash
# Run database tests
pytest tests/test_database.py

# Test API endpoints
pytest tests/test_api.py

# Integration tests
pytest tests/test_integrations.py

# Load testing
locust -f tests/load_test.py
```

## 🤝 Contributing

This is a business-focused project, but we welcome:
- Bug reports and fixes
- Integration connectors
- Control mapping improvements
- Documentation enhancements

Please open issues for major changes before submitting PRs.

## 📄 License

**Dual License**:
- **AGPL-3.0** for open-source/personal use
- **Commercial License** for SaaS/enterprise deployments

Contact: [support@smartgnosis.com]

## 🙏 Credits

Built on top of:
- **CISO Assistant** - https://github.com/intuitem/ciso-assistant-community
- **NIST SP 800-171** - Public domain framework
- **CMMC Program** - DoD Cyber AB

## 📞 Support

- Documentation: [docs.smartgnosis.com]
- Community: [Slack/Discord link]
- Enterprise: [sales@smartgnosis.com]
- Issues: [GitHub Issues]

## 🚧 Status

**Current**: Alpha / Private Beta  
**Next**: Public Beta (Q2 2025)  
**Target**: GA (Q3 2025)

---

**Built with ❤️ for the Defense Industrial Base**

*Helping contractors protect CUI and win DoD contracts*
