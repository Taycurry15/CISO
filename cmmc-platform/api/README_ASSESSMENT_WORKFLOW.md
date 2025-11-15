# Assessment Workflow System

Complete CMMC assessment lifecycle management from creation through completion, including evidence collection and control tracking.

## Overview

This system provides the complete user journey for CMMC assessments:

1. **Create Assessment** - Define scope, team, and timeline
2. **Collect Evidence** - Upload and tag evidence files
3. **Analyze Controls** - AI-powered control analysis
4. **Track Progress** - Real-time completion metrics
5. **Generate Reports** - SSP and POA&M documents

## Architecture

```
┌─────────────────────────────────────┐
│  Assessment API                     │
│  assessment_api.py                  │
│                                     │
│  Endpoints:                         │
│  • POST   /assessments              │
│  • GET    /assessments              │
│  • GET    /assessments/{id}         │
│  • PUT    /assessments/{id}/status  │
│  • PUT    /assessments/{id}/scope   │
│  • PUT    /assessments/{id}/team    │
│  • DELETE /assessments/{id}         │
│                                     │
│  • POST   /assessments/{id}/evidence│
│  • GET    /assessments/{id}/evidence│
│  • DELETE /assessments/{id}/evidence│
└─────────────────────────────────────┘
          ↓                   ↓
┌──────────────────┐  ┌──────────────────┐
│ Assessment       │  │ Evidence         │
│ Service          │  │ Service          │
│                  │  │                  │
│ • Create         │  │ • Upload         │
│ • Update status  │  │ • Tag            │
│ • Update scope   │  │ • Link controls  │
│ • Track progress │  │ • Statistics     │
└──────────────────┘  └──────────────────┘
          ↓                   ↓
┌─────────────────────────────────────┐
│  Database                           │
│  • assessments                      │
│  • control_findings                 │
│  • evidence                         │
│  • evidence_control_links           │
└─────────────────────────────────────┘
```

## Assessment Lifecycle

### 1. Draft Status
- Initial creation
- Define scope (CMMC level, domains, cloud providers)
- Assign team (lead assessor, team members)
- Set timeline (target completion date)

### 2. Scoping Status
- Refine scope
- Identify exclusions
- Finalize cloud provider list
- Initialize control findings (110 controls for CMMC L2)

### 3. In Progress Status
- Collect evidence
- Analyze controls with AI
- Link evidence to controls
- Track completion percentage

### 4. Review Status
- Review AI findings
- Validate evidence
- Adjust control statuses
- Prepare for completion

### 5. Completed Status
- All controls analyzed
- Reports generated (SSP, POA&M)
- Final review complete
- Ready for C3PAO submission

### 6. Archived Status
- Soft delete
- Historical record
- No longer active

## Components

### 1. Assessment Service (`services/assessment_service.py`)

**Key Methods:**

```python
# Create assessment
assessment_id = await service.create_assessment(
    organization_id="org-uuid",
    assessment_type=AssessmentType.INITIAL,
    scope=AssessmentScope(
        cmmc_level=2,
        domains=["ALL"],
        cloud_providers=["Microsoft 365 GCC High", "Azure Government"],
        system_boundary="Cloud-based contract management system",
        include_inherited=True
    ),
    lead_assessor="Jane Doe, C3PAO",
    team_members=["John Smith", "Bob Wilson"],
    target_end_date=datetime(2024, 3, 31)
)

# Update status
await service.update_status(assessment_id, AssessmentStatus.IN_PROGRESS)

# Get progress
progress = await service.get_assessment_progress(assessment_id)
# Returns: total_controls, controls_analyzed, completion_percentage, etc.

# Get summary
summary = await service.get_assessment_summary(assessment_id)
```

### 2. Evidence Service (`services/evidence_service.py`)

**Key Methods:**

```python
# Upload evidence
evidence_id = await service.upload_evidence(
    assessment_id="uuid",
    file_data=file_obj,
    file_name="access_policy.pdf",
    metadata=EvidenceMetadata(
        title="Access Control Policy",
        description="Organization-wide access control policy",
        evidence_type=EvidenceType.POLICY,
        assessment_methods=[AssessmentMethod.EXAMINE],
        tags=["access-control", "policy", "cmmc-l2"],
        collection_date=datetime.utcnow(),
        collected_by="Jane Doe"
    ),
    link_to_controls=["AC.L2-3.1.1", "AC.L2-3.1.2"]
)

# List evidence for control
evidence = await service.get_control_evidence(
    assessment_id="uuid",
    control_id="AC.L2-3.1.1"
)

# Get statistics
stats = await service.get_evidence_statistics(assessment_id)
```

### 3. Assessment API (`assessment_api.py`)

**Full workflow endpoints documented below.**

## API Reference

### Create Assessment

```http
POST /api/v1/assessments
Content-Type: application/json

{
  "organization_id": "org-uuid",
  "assessment_type": "Initial Assessment",
  "cmmc_level": 2,
  "domains": ["ALL"],
  "cloud_providers": ["Microsoft 365 GCC High", "Azure Government"],
  "system_boundary": "Cloud-based contract management system hosted in Azure Government",
  "exclusions": "Physical security controls (PE.L2-3.10.x) handled by cloud provider",
  "include_inherited": true,
  "lead_assessor": "Jane Doe, C3PAO",
  "team_members": ["John Smith", "Bob Wilson"],
  "target_end_date": "2024-03-31T00:00:00Z"
}

Response:
{
  "id": "assessment-uuid",
  "organization_id": "org-uuid",
  "organization_name": "Defense Contractor Inc.",
  "assessment_type": "Initial Assessment",
  "status": "Draft",
  "start_date": null,
  "target_end_date": "2024-03-31T00:00:00Z",
  "end_date": null,
  "lead_assessor": "Jane Doe, C3PAO",
  "team_members": ["John Smith", "Bob Wilson"],
  "created_at": "2024-01-15T10:30:00Z"
}
```

### List Assessments

```http
GET /api/v1/assessments?status=In%20Progress&limit=10

Response:
[
  {
    "id": "uuid",
    "organization_name": "Defense Contractor Inc.",
    "assessment_type": "Initial Assessment",
    "status": "In Progress",
    "start_date": "2024-01-15T00:00:00Z",
    "target_end_date": "2024-03-31T00:00:00Z",
    "lead_assessor": "Jane Doe",
    "team_members": ["John Smith", "Bob Wilson"],
    "created_at": "2024-01-15T10:30:00Z"
  }
]
```

### Get Assessment Summary

```http
GET /api/v1/assessments/{assessment_id}

Response:
{
  "assessment": {
    "id": "uuid",
    "organization_name": "Defense Contractor Inc.",
    "assessment_type": "Initial Assessment",
    "status": "In Progress",
    "start_date": "2024-01-15T00:00:00Z",
    "target_end_date": "2024-03-31T00:00:00Z",
    "lead_assessor": "Jane Doe",
    "team_members": ["John Smith", "Bob Wilson"]
  },
  "scope": {
    "cmmc_level": 2,
    "domains": ["ALL"],
    "cloud_providers": ["Microsoft 365 GCC High", "Azure Government"],
    "system_boundary": "Cloud-based contract management...",
    "include_inherited": true
  },
  "progress": {
    "total_controls": 110,
    "controls_analyzed": 85,
    "controls_met": 70,
    "controls_not_met": 10,
    "controls_partial": 5,
    "controls_na": 0,
    "evidence_collected": 142,
    "completion_percentage": 77.3,
    "avg_confidence_score": 0.82
  }
}
```

### Update Status

```http
PUT /api/v1/assessments/{assessment_id}/status
Content-Type: application/json

{
  "status": "In Progress"
}

Response:
{
  "success": true,
  "message": "Status updated to In Progress"
}
```

### Upload Evidence

```http
POST /api/v1/assessments/{assessment_id}/evidence
Content-Type: multipart/form-data

Form Data:
  file: access_control_policy.pdf
  title: "Access Control Policy"
  description: "Organization-wide access control policy document"
  evidence_type: "Policy"
  assessment_methods: ["Examine"]
  tags: ["access-control", "policy", "cmmc-l2"]
  link_to_controls: ["AC.L2-3.1.1", "AC.L2-3.1.2"]
  collected_by: "Jane Doe, Assessor"

Response:
{
  "success": true,
  "evidence_id": "evidence-uuid",
  "message": "Evidence 'Access Control Policy' uploaded successfully"
}
```

### List Evidence

```http
GET /api/v1/assessments/{assessment_id}/evidence?control_id=AC.L2-3.1.1

Response:
[
  {
    "id": "evidence-uuid",
    "assessment_id": "uuid",
    "title": "Access Control Policy",
    "description": "Organization-wide access control policy",
    "evidence_type": "Policy",
    "assessment_methods": ["Examine"],
    "tags": ["access-control", "policy"],
    "file_name": "access_control_policy.pdf",
    "file_size": 524288,
    "collection_date": "2024-01-15T14:30:00Z",
    "collected_by": "Jane Doe",
    "linked_controls": ["AC.L2-3.1.1", "AC.L2-3.1.2"]
  }
]
```

### Get Evidence Statistics

```http
GET /api/v1/assessments/{assessment_id}/evidence/statistics

Response:
{
  "total_evidence": 142,
  "evidence_types": 6,
  "total_size_bytes": 52428800,
  "controls_with_evidence": 95,
  "by_type": {
    "Document": 45,
    "Screenshot": 38,
    "Configuration": 25,
    "Log": 20,
    "Policy": 10,
    "Diagram": 4
  },
  "by_method": {
    "Examine": 85,
    "Interview": 32,
    "Test": 25
  }
}
```

## End-to-End Workflow

### Complete Assessment Process

```
1. Create Assessment
   POST /api/v1/assessments
   → Status: Draft
   → 110 control findings initialized

2. Define Scope & Team
   PUT /api/v1/assessments/{id}/scope
   PUT /api/v1/assessments/{id}/team
   → Scope finalized
   → Team assigned

3. Start Assessment
   PUT /api/v1/assessments/{id}/status {"status": "In Progress"}
   → start_date set automatically
   → Ready for evidence collection

4. Upload Evidence (repeat for each evidence item)
   POST /api/v1/assessments/{id}/evidence
   → Files stored in MinIO/S3
   → Linked to controls
   → Tagged and categorized

5. Analyze Controls (using AI Analysis API)
   POST /api/v1/analysis/control/AC.L2-3.1.1
   → AI generates findings
   → Evidence automatically retrieved
   → Confidence score calculated

6. Monitor Progress
   GET /api/v1/assessments/{id}
   → View completion percentage
   → Track controls analyzed
   → Check evidence collected

7. Review Findings
   PUT /api/v1/assessments/{id}/status {"status": "Review"}
   → Review AI findings
   → Validate evidence
   → Adjust as needed

8. Complete Assessment
   PUT /api/v1/assessments/{id}/status {"status": "Completed"}
   → end_date set automatically
   → Ready for report generation

9. Generate Reports
   POST /api/v1/reports/ssp/{id}
   POST /api/v1/reports/poam/{id}
   → SSP (100-400 pages)
   → POA&M (for non-compliant controls)

10. Submit to C3PAO
    → SSP + POA&M + Evidence Package
    → Ready for certification
```

## Database Schema

### Required Tables

```sql
-- Assessment lifecycle
CREATE TABLE assessments (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    assessment_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    scope JSONB NOT NULL,
    start_date TIMESTAMP,
    target_end_date TIMESTAMP,
    end_date TIMESTAMP,
    lead_assessor VARCHAR(255),
    team_members TEXT[],
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_by VARCHAR(255) NOT NULL
);

-- Evidence storage
CREATE TABLE evidence (
    id UUID PRIMARY KEY,
    assessment_id UUID NOT NULL REFERENCES assessments(id),
    document_id UUID REFERENCES documents(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    evidence_type VARCHAR(50) NOT NULL,
    assessment_methods TEXT[] NOT NULL,
    tags TEXT[],
    file_path VARCHAR(500),
    file_name VARCHAR(255),
    file_size BIGINT,
    file_hash VARCHAR(64),
    collection_date TIMESTAMP NOT NULL,
    collected_by VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Evidence-control linkage
CREATE TABLE evidence_control_links (
    id UUID PRIMARY KEY,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE CASCADE,
    control_id VARCHAR(50) NOT NULL REFERENCES controls(id),
    assessment_id UUID NOT NULL REFERENCES assessments(id),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(evidence_id, control_id)
);

CREATE INDEX idx_evidence_control_links_evidence ON evidence_control_links(evidence_id);
CREATE INDEX idx_evidence_control_links_control ON evidence_control_links(control_id);
CREATE INDEX idx_evidence_assessment ON evidence(assessment_id);
CREATE INDEX idx_evidence_type ON evidence(evidence_type);
```

## Best Practices

### Assessment Creation

1. **Define Clear Scope**
   - Specify exact CMMC level needed
   - Include all relevant cloud providers
   - Document system boundary clearly
   - List any exclusions

2. **Assign Qualified Team**
   - Lead assessor must be C3PAO certified
   - Include subject matter experts (SMEs)
   - Assign roles and responsibilities
   - Plan for adequate staffing

3. **Set Realistic Timeline**
   - CMMC L2: 4-8 weeks typical
   - Account for remediation time
   - Build in review periods
   - Plan for C3PAO engagement

### Evidence Collection

1. **Organize Evidence**
   - Use consistent naming conventions
   - Tag evidence appropriately
   - Link to all relevant controls
   - Document collection date and source

2. **Evidence Types**
   - **Examine**: Policies, procedures, configurations, diagrams
   - **Interview**: Interview notes, meeting minutes
   - **Test**: Test results, logs, screenshots

3. **Quality Over Quantity**
   - Direct evidence is best
   - Ensure evidence is current (within 6 months)
   - Avoid duplicate evidence
   - Include sufficient context

### Progress Tracking

1. **Monitor Regularly**
   - Check completion percentage daily
   - Review confidence scores
   - Identify gaps early
   - Adjust timeline as needed

2. **Focus on High-Risk Controls**
   - Prioritize AC, IA, SC domains
   - Address "Not Met" controls first
   - Gather strong evidence for critical controls

3. **Maintain Momentum**
   - Set weekly milestones
   - Assign control ownership
   - Hold regular team meetings
   - Document decisions

## Integration Points

### With AI Analysis

```python
# After uploading evidence, run AI analysis
await evidence_service.upload_evidence(...)

# AI automatically retrieves evidence
await ai_service.analyze_control(
    control_id="AC.L2-3.1.1",
    assessment_id=assessment_id,
    include_provider_inheritance=True
)

# Evidence is included in AI analysis context
```

### With Provider Inheritance

```python
# Include cloud providers in scope
scope = AssessmentScope(
    cmmc_level=2,
    domains=["ALL"],
    cloud_providers=["Microsoft 365 GCC High"],
    include_inherited=True  # Include inherited controls
)

# Provider inheritance automatically applied
# Inherited controls marked as "Met"
# Shared controls focus on customer responsibility
```

### With Report Generation

```python
# Assessment complete → Generate reports
await assessment_service.update_status(
    assessment_id,
    AssessmentStatus.COMPLETED
)

# Generate SSP (includes all evidence)
ssp_bytes = await ssp_generator.generate_ssp(assessment_id, ...)

# Generate POA&M (for non-compliant controls)
poam_bytes = await poam_generator.generate_poam(assessment_id, ...)
```

## Performance

**Benchmarks:**

| Operation | Time | Notes |
|-----------|------|-------|
| Create Assessment | <500ms | Initializes 110 controls |
| Upload Evidence | 1-3s | Depends on file size |
| List Evidence | <200ms | 100 items |
| Update Status | <100ms | Single DB update |
| Get Progress | <300ms | Aggregates control stats |
| Get Summary | <500ms | Includes all metrics |

## Testing

```bash
# Run workflow tests
pytest tests/test_assessment_workflow.py -v

# Run all tests
pytest tests/ -v --cov=services
```

## Troubleshooting

**Issue: Cannot update scope**
- Solution: Scope can only be changed in Draft or Scoping status
- Move back to Scoping status or create new assessment

**Issue: Evidence upload fails**
- Solution: Check file size limits (default 100MB)
- Verify storage service is configured
- Check file permissions

**Issue: Progress shows 0% complete**
- Solution: Ensure control findings are initialized
- Run AI analysis on controls
- Check that status is not "Not Assessed"

**Issue: Cannot complete assessment**
- Solution: Ensure all required controls are analyzed
- Check for validation errors
- Verify evidence is linked to critical controls

## Roadmap

### Phase 1 (Current) ✅
- Assessment lifecycle management
- Evidence upload and tagging
- Progress tracking
- API endpoints

### Phase 2 (Next Sprint)
- Web UI for assessment creation
- Evidence viewer and editor
- Bulk evidence upload
- Advanced search and filtering

### Phase 3 (Future)
- Automated evidence collection
- Integration with IT systems (SIEM, IAM, etc.)
- Real-time compliance monitoring
- Mobile app for evidence collection

---

**Complete assessment workflow from creation to certification!** ✅

Manage the entire CMMC assessment lifecycle with ease.
