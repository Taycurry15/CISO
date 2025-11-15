```
# Report Generation System

AI-powered generation of CMMC compliance documents including System Security Plans (SSP) and Plans of Action & Milestones (POA&M).

## Overview

This system automatically generates professional certification documents from assessment data:

- **SSP (System Security Plan)** - Comprehensive 100-400 page DOCX document required for CMMC certification
- **POA&M (Plan of Action & Milestones)** - Excel workbook tracking remediation for non-compliant controls

### Value Proposition

**Manual SSP creation:** 40-80 hours ($8,000-$16,000 at $200/hour)
**Automated SSP generation:** 5-10 seconds

**Manual POA&M creation:** 8-16 hours ($1,600-$3,200)
**Automated POA&M generation:** 2-5 seconds

**Total savings per assessment:** $9,600-$19,200 and 2-4 weeks of calendar time

## Architecture

```
Assessment Data + AI Findings
          ↓
┌────────────────────────────────────┐
│  Report Generation API             │
│  report_api.py                     │
│                                    │
│  Endpoints:                        │
│  • POST /ssp/{assessment_id}       │
│  • POST /poam/{assessment_id}      │
│  • GET  /assessment/{id}/summary   │
└────────────────────────────────────┘
          ↓
┌────────────────────────────────────┐
│  SSP Generator                     │
│  services/ssp_generator.py         │
│                                    │
│  • Collect assessment findings     │
│  • Generate control narratives     │
│  • Include provider inheritance    │
│  • Create DOCX document            │
│  • Export to PDF (optional)        │
└────────────────────────────────────┘
          ↓
     SSP.docx (100-400 pages)


┌────────────────────────────────────┐
│  POA&M Generator                   │
│  services/poam_generator.py        │
│                                    │
│  • Identify non-compliant controls │
│  • Calculate risk levels           │
│  • Generate remediation plans      │
│  • Create Excel workbook           │
│  • Track milestones                │
└────────────────────────────────────┘
          ↓
     POAM.xlsx (tracking sheet)
```

## Components

### 1. SSP Generator (`services/ssp_generator.py`)

**Primary class:** `SSPGenerator`

**Generates:**
- Cover page with system info and classification
- Table of contents (requires Word update after opening)
- Section 1: System Identification
- Section 2: System Description (mission, data types)
- Section 3: System Environment
- **Section 4: Control Implementation** (main content)
  - All 110 controls organized by domain
  - Implementation status (Implemented, Partially Implemented, Planned, N/A)
  - Control narratives (from AI analysis)
  - Evidence references
  - Provider inheritance details
- Section 5: System Interconnections
- Section 6: Personnel Roles
- Section 7: Plan Maintenance

**Example Usage:**

```python
from services.ssp_generator import SSPGenerator, SystemInfo, SSPMetadata
from datetime import datetime

# Initialize generator
ssp_generator = SSPGenerator(db_pool, ai_service)

# Build system information
system_info = SystemInfo(
    system_name="DoD Contract Management System",
    system_id="CMS-001",
    system_type="Cloud-based SaaS",
    system_owner="John Smith",
    system_owner_email="john.smith@example.com",
    authorization_date=None,
    cmmc_level=2,
    organization_name="Defense Contractor Inc.",
    organization_address="123 Main St, Arlington, VA 22201",
    organization_phone="(703) 555-1234",
    organization_email="compliance@example.com",
    data_types=["CUI", "Contract Data", "Technical Data"],
    mission="Manage DoD contracts and associated CUI documentation",
    system_description="Cloud-based contract management system hosted in Azure Government..."
)

# Build metadata
metadata = SSPMetadata(
    version="1.0",
    date=datetime.utcnow(),
    prepared_by="Jane Doe, ISSO",
    reviewed_by="Bob Wilson, ISSM",
    approved_by="Alice Johnson, Authorizing Official",
    classification="CUI"
)

# Generate SSP
doc_bytes = await ssp_generator.generate_ssp(
    assessment_id="uuid",
    system_info=system_info,
    metadata=metadata,
    include_provider_inheritance=True,
    generate_narratives=True
)

# Save to file
with open("SSP_CMS-001.docx", "wb") as f:
    f.write(doc_bytes.getvalue())
```

**Key Methods:**

- `generate_ssp()` - Main method to generate complete SSP document
- `_add_cover_page()` - Cover page with classification and metadata
- `_add_control_implementation()` - Main section with all control details
- `_get_provider_inheritance()` - Pull cloud provider control mappings
- `_get_evidence_references()` - Link evidence to controls
- `_map_status_to_implementation()` - Convert assessment status to SSP terminology

### 2. POA&M Generator (`services/poam_generator.py`)

**Primary class:** `POAMGenerator`

**Generates:**
- Summary Dashboard sheet
  - Total items by risk level
  - Total items by status
  - Overdue items count
- POA&M Items sheet (main tracking sheet)
  - POA&M ID
  - Control ID and title
  - Weakness description
  - Risk level (Very High, High, Moderate, Low)
  - Impact and likelihood
  - Remediation plan (AI-generated)
  - Resources required
  - Milestone date
  - Responsible person
  - Status tracking
  - Completion date
  - Cost estimate
  - Comments
- Instructions sheet

**Risk Level Calculation:**

| Control Status | High-Risk Domain* | Other Domains |
|---------------|------------------|---------------|
| Not Met | Very High (30 days) | High (90 days) |
| Partially Met | High (90 days) | Moderate (180 days) |

*High-risk domains: AC, IA, SC, AU (Access Control, Identity, Cryptography, Audit)

**Example Usage:**

```python
from services.poam_generator import POAMGenerator, POAMMetadata
from datetime import datetime

# Initialize generator
poam_generator = POAMGenerator(db_pool, ai_service)

# Build metadata
metadata = POAMMetadata(
    system_name="DoD Contract Management System",
    organization="Defense Contractor Inc.",
    prepared_by="Jane Doe, ISSO",
    preparation_date=datetime.utcnow(),
    review_date=None,
    version="1.0"
)

# Generate POA&M
excel_bytes = await poam_generator.generate_poam(
    assessment_id="uuid",
    metadata=metadata,
    generate_recommendations=True,  # Use AI for remediation plans
    auto_assign_risk=True  # Auto-calculate risk levels
)

# Save to file
with open("POAM_CMS-001.xlsx", "wb") as f:
    f.write(excel_bytes.getvalue())
```

**Key Methods:**

- `generate_poam()` - Main method to generate complete POA&M workbook
- `_get_poam_items()` - Collect all "Not Met" and "Partially Met" controls
- `_calculate_risk_level()` - Auto-assign risk based on control and status
- `_generate_remediation_plan()` - AI-generated remediation recommendations
- `_determine_impact()` - Calculate impact description from risk level
- `_create_poam_workbook()` - Build Excel workbook with formatting

### 3. Report API (`report_api.py`)

**Endpoints:**

#### Generate SSP

```http
POST /api/v1/reports/ssp/{assessment_id}
Content-Type: application/json

{
  "system_name": "DoD Contract Management System",
  "system_id": "CMS-001",
  "system_type": "Cloud-based SaaS",
  "system_owner": "John Smith",
  "system_owner_email": "john.smith@example.com",
  "organization_name": "Defense Contractor Inc.",
  "organization_address": "123 Main St, Arlington, VA 22201",
  "organization_phone": "(703) 555-1234",
  "organization_email": "compliance@example.com",
  "cmmc_level": 2,
  "data_types": ["CUI", "Contract Data"],
  "mission": "Manage DoD contracts and CUI documentation",
  "system_description": "Cloud-based contract management system...",
  "version": "1.0",
  "prepared_by": "Jane Doe, ISSO",
  "reviewed_by": "Bob Wilson, ISSM",
  "approved_by": "Alice Johnson, AO",
  "classification": "CUI",
  "include_provider_inheritance": true,
  "generate_narratives": true
}

Response:
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="SSP_DoD_Contract_Management_System_20240115.docx"
X-Generation-Time: 8.5

[DOCX file download]
```

#### Generate POA&M

```http
POST /api/v1/reports/poam/{assessment_id}
Content-Type: application/json

{
  "system_name": "DoD Contract Management System",
  "organization": "Defense Contractor Inc.",
  "prepared_by": "Jane Doe, ISSO",
  "version": "1.0",
  "generate_recommendations": true,
  "auto_assign_risk": true
}

Response:
Content-Type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
Content-Disposition: attachment; filename="POAM_DoD_Contract_Management_System_20240115.xlsx"
X-Generation-Time: 3.2

[Excel file download]
```

#### Get Assessment Summary

```http
GET /api/v1/reports/assessment/{assessment_id}/summary

Response:
{
  "assessment_id": "uuid",
  "total_controls": 110,
  "by_status": {
    "Met": 85,
    "Partially Met": 12,
    "Not Met": 10,
    "Not Applicable": 3
  },
  "requires_poam": 22,
  "avg_confidence": 0.82,
  "start_date": "2024-01-15",
  "end_date": null,
  "status": "In Progress",
  "scope": "CMMC Level 2 Full Assessment"
}
```

#### Get Assessment Controls

```http
GET /api/v1/reports/assessment/{assessment_id}/controls?status_filter=Not%20Met

Response:
[
  {
    "control_id": "AC.L2-3.1.5",
    "control_title": "Separation of Duties",
    "domain": "AC",
    "status": "Not Met",
    "narrative": "The organization has not implemented separation of duties...",
    "confidence_score": 0.78,
    "evidence_count": 2
  },
  {
    "control_id": "IA.L2-3.5.8",
    "control_title": "Password Policies",
    "domain": "IA",
    "status": "Not Met",
    "narrative": "Password complexity requirements are insufficient...",
    "confidence_score": 0.85,
    "evidence_count": 1
  }
]
```

## Workflow

### End-to-End Report Generation

```
1. Complete Assessment
   └─> All 110 controls analyzed
       AI findings generated
       Evidence collected

2. Generate SSP
   └─> POST /api/v1/reports/ssp/{assessment_id}
       Include system information
       AI narratives for each control
       Provider inheritance details
       Evidence references

3. Generate POA&M
   └─> POST /api/v1/reports/poam/{assessment_id}
       Identify non-compliant controls (22 items)
       Calculate risk levels
       Generate remediation plans
       Assign milestone dates

4. Review & Edit
   └─> Open SSP in Microsoft Word
       Review control narratives
       Update table of contents
       Add organization-specific details
       Export to PDF if needed

5. Track Remediation
   └─> Open POA&M in Excel
       Assign responsible persons
       Update status as work progresses
       Track completion dates
       Monitor milestones

6. Submit for Certification
   └─> SSP + POA&M + Evidence
       Ready for C3PAO review
```

## SSP Document Structure

### Cover Page
- Document title: "SYSTEM SECURITY PLAN"
- System name
- CMMC level
- Classification marking (CUI)
- Version, date, prepared by, reviewed by, approved by
- Organization name

### Table of Contents
*Auto-generated by Word (requires manual update)*

### Section 1: System Identification
- System name and ID
- System type (Cloud, On-premise, Hybrid)
- CMMC level
- System owner and contact info
- Organization info and address

### Section 2: System Description
- **2.1 Mission** - System's mission/purpose
- **2.2 System Description** - Detailed technical description
- **2.3 Data Types** - Types of data processed (CUI, PII, etc.)

### Section 3: System Environment
- Assessment scope
- Assessment period
- Cloud providers used (if applicable)

### Section 4: Control Implementation ⭐ **MAIN SECTION**

Organized by domain (AC, AU, CM, IA, etc.):

**For each control:**

```
AC.L2-3.1.1: Authorized Access Control

Implementation Status: Implemented

Control Requirement:
"Limit information system access to authorized users, processes acting on behalf of authorized users, or devices (including other information systems)."

Implementation Description:
The organization implements Azure AD for centralized identity and access management. All users are authenticated via Azure AD with MFA enforcement. Conditional access policies restrict access based on user role, device compliance, and location. Application access is controlled through Azure AD app registrations with role-based access control (RBAC).

Provider Inheritance:
• Microsoft 365 GCC High (Shared): Microsoft provides Azure AD for centralized identity and access management across all M365 services with built-in MFA capabilities and conditional access policies.

Evidence:
• Azure AD Conditional Access Policies
• MFA Enrollment Report
• Access Review Log
```

### Section 5: System Interconnections
- External system connections
- Data flow descriptions
- Security controls for interconnections

### Section 6: Personnel Roles and Responsibilities
- System Owner
- Information System Security Officer (ISSO)
- System Administrator
- Other key roles

### Section 7: Plan Maintenance
- Review schedule (annually or upon significant change)
- Update procedures
- Version history

## POA&M Excel Structure

### Sheet 1: Summary Dashboard

```
POA&M Summary Dashboard

System: DoD Contract Management System
Total Items: 22
Report Date: 2024-01-15

Items by Risk Level:
Very High:    2
High:         8
Moderate:    10
Low:          2

Items by Status:
Open:            22
In Progress:      0
Completed:        0
Risk Accepted:    0
Delayed:          0

Overdue Items: 0
```

### Sheet 2: POA&M Items (Main Tracking Sheet)

| POA&M ID | Control ID | Control Title | Weakness Description | Risk Level | Impact | Likelihood | Remediation Plan | Resources Required | Milestone Date | Responsible Person | Status | Completion Date | Cost Estimate | Comments |
|----------|-----------|---------------|---------------------|-----------|--------|-----------|-----------------|-------------------|---------------|-------------------|--------|-----------------|---------------|----------|
| POAM-001 | AC.L2-3.1.5 | Separation of Duties | Control not implemented. No separation between... | Very High | Critical impact to CUI | High | 1. Review current roles<br>2. Define separation requirements... | 1 FTE, 60 days | 2024-02-15 | John Smith | Open | | $45,000 | Priority item |

**Color Coding:**
- **Very High Risk:** Red background, white text
- **High Risk:** Orange background
- **Moderate Risk:** Yellow background
- **Completed Status:** Green background, white text
- **In Progress Status:** Light green background

### Sheet 3: Instructions

Detailed instructions for:
- How to use the POA&M
- Status definitions
- Risk level guidance
- Remediation timelines
- Review procedures

## AI-Powered Features

### 1. Control Narrative Generation

For each control, the system can optionally use AI to generate implementation narratives:

```
Input:
- Control ID and requirement
- Assessment findings
- Evidence descriptions
- Provider inheritance info

AI Processing:
- Analyze evidence
- Map to assessment objectives
- Generate 2-4 paragraph narrative
- Include specific evidence references

Output:
"The organization implements Azure AD for centralized identity and access management. All users are authenticated via Azure AD with MFA enforcement configured through conditional access policies. Evidence review shows 342 users with MFA enabled (98.5% enrollment rate). Access to CUI resources is restricted through Azure AD app registrations with role-based access control..."
```

### 2. Remediation Plan Generation

For POA&M items, AI generates specific remediation steps:

```
Input:
- Control ID and requirement
- Weakness description
- Current implementation status

AI Processing:
- Identify gaps
- Generate remediation steps
- Estimate effort and resources
- Suggest implementation approach

Output:
"1. Review current role definitions and document existing privileges
2. Identify functions requiring separation (e.g., approval vs. execution)
3. Redesign role structure to enforce least privilege
4. Implement technical controls (Azure RBAC roles)
5. Update policies and procedures
6. Train personnel on new processes
7. Validate implementation with test scenarios
8. Document separation of duties matrix"
```

### 3. Risk Assessment

Automatic risk level calculation based on:
- Control domain (AC, IA, SC = higher risk)
- Implementation status (Not Met = higher risk)
- AI confidence score (lower confidence = higher likelihood of exploitation)

## Integration with Assessment Data

The report generators pull data from:

### Database Tables
- `assessments` - Assessment metadata
- `control_findings` - Control status and narratives
- `controls` - Control requirements and details
- `control_domains` - Domain organization
- `evidence` - Evidence artifacts
- `documents` - Document metadata
- `provider_control_inheritance` - Cloud provider mappings

### AI Analysis Results
- Control status (Met, Not Met, Partially Met, N/A)
- Assessor narratives (AI-generated)
- Confidence scores
- Evidence mappings
- AI rationale

### Provider Inheritance
- Inherited controls (fully automated)
- Shared responsibility controls
- Provider narratives
- Customer responsibilities
- Implementation guidance

## Best Practices

### SSP Generation

1. **Complete Assessment First**
   - Analyze all 110 controls
   - Generate AI findings
   - Gather all evidence
   - Review and approve findings

2. **Provide Detailed System Info**
   - Accurate system description
   - Complete mission statement
   - All data types processed
   - Current personnel roles

3. **Review and Edit**
   - AI narratives are 80-90% accurate
   - Add organization-specific details
   - Update table of contents in Word
   - Verify all evidence references

4. **Version Control**
   - Increment version for significant changes
   - Track review and approval dates
   - Maintain change log

### POA&M Management

1. **Prioritize by Risk Level**
   - Very High: Address within 30 days
   - High: Address within 90 days
   - Moderate: Address within 180 days
   - Low: Address within 365 days

2. **Assign Clear Ownership**
   - Specific person responsible (not just role)
   - Ensure they have authority and resources
   - Track progress weekly for high-risk items

3. **Update Regularly**
   - Monthly POA&M reviews
   - Update status as work progresses
   - Document delays with justification
   - Track actual costs vs. estimates

4. **Close Items Properly**
   - Validate remediation is complete
   - Gather evidence of implementation
   - Request re-assessment
   - Document completion date

## Customization

### Adding Custom SSP Sections

To add custom sections to SSP:

```python
# In ssp_generator.py

async def generate_ssp(self, ...):
    # After standard sections
    await self._add_system_interconnections(doc, assessment_id)
    doc.add_page_break()

    # Add custom section
    await self._add_custom_section(doc, assessment_id)
    doc.add_page_break()

async def _add_custom_section(self, doc: Document, assessment_id: str):
    """Add custom organization-specific section"""
    doc.add_heading("8. Custom Section", level=1)
    doc.add_paragraph("Custom content...")
```

### Customizing POA&M Columns

To add custom columns to POA&M:

```python
# In poam_generator.py

@dataclass
class POAMItem:
    # Existing fields...
    comments: Optional[str]

    # Add custom fields
    criticality_score: Optional[int] = None
    dependency: Optional[str] = None
    vendor: Optional[str] = None

# Update _add_poam_sheet() to include new columns
```

### Custom Risk Calculations

To customize risk level calculation:

```python
# In poam_generator.py

def _calculate_risk_level(self, finding: Dict[str, Any]) -> RiskLevel:
    """Custom risk calculation logic"""
    control_id = finding['control_id']

    # Custom logic based on organization priorities
    critical_controls = ['AC.L2-3.1.1', 'IA.L2-3.5.7', 'SC.L2-3.13.11']

    if control_id in critical_controls and finding['status'] == 'Not Met':
        return RiskLevel.VERY_HIGH

    # Fall back to default logic
    ...
```

## Performance

**Benchmarks:**

| Operation | Time | Notes |
|-----------|------|-------|
| SSP Generation | 5-10 seconds | 110 controls, 150-300 pages |
| POA&M Generation | 2-5 seconds | 20-30 non-compliant controls |
| SSP with AI Narratives | 8-15 seconds | +5 seconds for AI generation |
| PDF Export | 3-8 seconds | Requires docx2pdf |

**Scaling:**

- Parallel generation: Generate multiple reports simultaneously
- Caching: Cache system info for multiple report generations
- Async processing: Use Celery for background report generation

## Testing

Run tests:

```bash
# Report generation tests
pytest tests/test_report_generation.py -v

# All tests
pytest tests/ -v --cov=services
```

**Test Coverage:**
- SSP generator initialization
- POA&M generator initialization
- System info dataclasses
- Document structure creation
- Risk level calculation
- Remediation plan generation
- Excel workbook creation
- Edge cases and validation

## Troubleshooting

**Issue: SSP missing control narratives**
- Solution: Ensure all controls have findings in database
- Run AI analysis first: `POST /api/v1/analysis/assessment/{id}`
- Check `generate_narratives=true` in SSP request

**Issue: POA&M shows 0 items**
- Solution: Check if any controls are "Not Met" or "Partially Met"
- Filter controls: `GET /api/v1/reports/assessment/{id}/controls?status_filter=Not%20Met`
- Verify findings exist in database

**Issue: SSP document formatting issues**
- Solution: Ensure python-docx version is current
- Check system has Word installed for TOC generation
- Try opening in LibreOffice if Word unavailable

**Issue: Excel file corrupted**
- Solution: Verify openpyxl version is current
- Check no special characters in system name
- Try with simplified POA&M metadata

**Issue: Generation timeout**
- Solution: Increase timeout in API call
- Use Celery for background processing
- Generate SSP and POA&M separately

## Export to PDF

To export SSP to PDF:

```python
from docx2pdf import convert

# Generate SSP
doc_bytes = await generate_ssp_for_assessment(...)

# Save to temp file
with open("temp_ssp.docx", "wb") as f:
    f.write(doc_bytes.getvalue())

# Convert to PDF
convert("temp_ssp.docx", "SSP_Final.pdf")
```

**Note:** Requires Microsoft Word (Windows/Mac) or LibreOffice (Linux)

**Alternative:** Use online conversion API:
- CloudConvert API
- PDF.co API
- Aspose.Words Cloud API

## Roadmap

### Phase 1 (Current) ✅
- SSP generator with control implementation
- POA&M generator with risk levels
- Provider inheritance integration
- DOCX and Excel export
- RESTful API endpoints

### Phase 2 (Next Sprint)
- PDF export capability
- Custom SSP templates (organization branding)
- Assessment summary report
- Evidence package generator (ZIP all evidence)
- Continuous monitoring report

### Phase 3 (Future)
- Interactive SSP editor (web UI)
- Real-time POA&M tracking dashboard
- Automated POA&M updates from ticketing systems
- SSP diff/comparison (version-to-version)
- C3PAO report package generator

## References

- [NIST SP 800-171 Rev 2](https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final)
- [CMMC Assessment Guide](https://dodcio.defense.gov/CMMC/)
- [NIST SP 800-18 Rev 1 - Guide for Developing Security Plans](https://csrc.nist.gov/publications/detail/sp/800-18/rev-1/final)
- [NIST SP 800-37 Rev 2 - Risk Management Framework](https://csrc.nist.gov/publications/detail/sp/800-37/rev-2/final)

---

**Generate certification-ready documents in seconds, not weeks!** 📄

Save $10K-$20K per assessment with automated SSP and POA&M generation.
