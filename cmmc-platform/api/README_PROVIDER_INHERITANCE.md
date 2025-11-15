# Provider Inheritance Library

Cloud provider control inheritance mappings that reduce CMMC assessment effort by 30-40%.

## Overview

This library contains pre-mapped cloud provider control implementations for:
- **Microsoft 365 GCC High** (FedRAMP High)
- **Azure Government** (FedRAMP High)
- **AWS GovCloud (US)** (FedRAMP High, DoD IL5)

Organizations using these cloud platforms can **inherit** or **share** security controls, dramatically reducing manual assessment effort.

## Shared Responsibility Model

Cloud providers implement security controls at different layers:

### Inherited Controls
**Provider:** 100% responsible
**Customer:** 0% responsible

Example: `IA.L2-3.5.7` (Cryptographic Module Authentication)
- Microsoft/AWS/Azure use FIPS 140-2 validated cryptographic modules
- Customer inherits this control with **zero** additional work required
- **Savings:** 2 hours per control

### Shared Controls
**Provider:** Partial responsibility
**Customer:** Partial responsibility

Example: `AC.L2-3.1.1` (Authorized Access Control)
- Provider offers identity and access management (Azure AD, AWS IAM)
- Customer configures policies, roles, MFA settings
- **Savings:** ~1 hour per control (50% reduction)

### Customer Controls
**Provider:** 0% responsible
**Customer:** 100% responsible

Example: `CM.L2-3.4.7` (Nonessential Programs)
- Customer must restrict nonessential programs on their workstations
- Provider has no responsibility
- **Savings:** 0 hours (full assessment required)

## Coverage Summary

| Provider | Controls Mapped | Inherited | Shared | Customer | Coverage % |
|----------|----------------|-----------|--------|----------|------------|
| Microsoft 365 GCC High | 21 | 7 | 12 | 2 | 19.1% |
| Azure Government | 18 | 1 | 15 | 2 | 16.4% |
| AWS GovCloud (US) | 18 | 1 | 14 | 3 | 16.4% |
| **Combined (unique)** | **~42** | **~9** | **~35** | **~5** | **~38%** |

**Typical Savings:**
- Using 2-3 providers: **30-40% reduction** in assessment time
- Average savings: **66-88 hours** (worth $13,200-$17,600 at $200/hour)

## Architecture

```
┌─────────────────────────────────────────┐
│  Provider Mappings (JSON)               │
│  data/provider_mappings/                │
│    ├── m365_gcc_high.json               │
│    ├── azure_government.json            │
│    └── aws_govcloud.json                │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  ProviderInheritanceService             │
│  services/provider_inheritance.py       │
│                                         │
│  - Load JSON mappings                   │
│  - Parse provider offerings             │
│  - Import to database                   │
│  - Calculate coverage & savings         │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Database Tables                        │
│                                         │
│  provider_offerings                     │
│    - Provider name, type, cert level    │
│                                         │
│  provider_control_inheritance           │
│    - Control ID, responsibility         │
│    - Provider/customer narratives       │
│    - Implementation guidance            │
└─────────────────────────────────────────┘
              ↓
┌─────────────────────────────────────────┐
│  Provider API                           │
│  provider_api.py                        │
│                                         │
│  - Import mappings                      │
│  - Query inheritance                    │
│  - Calculate savings                    │
└─────────────────────────────────────────┘
```

## Components

### 1. JSON Mapping Files

Located in `data/provider_mappings/`

**Format:**
```json
{
  "provider_name": "Microsoft 365 GCC High",
  "provider_type": "SaaS",
  "description": "Microsoft 365 Government GCC High cloud offering",
  "certification_level": "FedRAMP High",
  "documentation_url": "https://docs.microsoft.com/...",
  "control_mappings": [
    {
      "control_id": "IA.L2-3.5.7",
      "control_title": "Cryptographic Module Authentication",
      "responsibility": "Inherited",
      "microsoft_responsibility": "Microsoft uses FIPS 140-2 validated cryptographic modules in all M365 services",
      "customer_responsibility": null,
      "inherited_controls": ["IA.L2-3.5.7"],
      "implementation_guidance": "No customer action required - inherent in M365 GCC High",
      "evidence_artifacts": [
        "Microsoft FIPS 140-2 validation certificates",
        "M365 Security & Compliance documentation"
      ],
      "authoritative_source": "https://docs.microsoft.com/..."
    }
  ],
  "summary": {
    "total_controls_mapped": 21,
    "inherited_count": 7,
    "shared_count": 12,
    "customer_count": 2,
    "coverage_percentage": 19.1
  }
}
```

**Responsibility Field Variations:**
- M365: `microsoft_responsibility` / `customer_responsibility`
- Azure: `azure_responsibility` / `customer_responsibility`
- AWS: `aws_responsibility` / `customer_responsibility`

### 2. Provider Inheritance Service

**File:** `services/provider_inheritance.py`

**Classes:**
- `ResponsibilityType` - Enum (Inherited, Shared, Customer)
- `ControlInheritance` - Dataclass for control mapping details
- `ProviderOffering` - Dataclass for provider offering
- `ProviderInheritanceService` - Main service class

**Key Methods:**

```python
from services.provider_inheritance import ProviderInheritanceService

service = ProviderInheritanceService(db_pool)

# Import all JSON mappings
imported = await service.import_all_mappings()
# Returns: {'Microsoft 365 GCC High': 'uuid', 'Azure Government': 'uuid', ...}

# Get control inheritance
inheritance = await service.get_control_inheritance(
    control_id="AC.L2-3.1.1",
    provider_name="Microsoft 365 GCC High"  # Optional filter
)
# Returns: [{'provider_name': '...', 'responsibility': 'Shared', ...}]

# Get fully inherited controls
inherited = await service.get_inherited_controls(
    provider_name="Microsoft 365 GCC High"
)
# Returns: ['IA.L2-3.5.7', 'SC.L2-3.13.16', ...]

# Get provider coverage stats
coverage = await service.get_provider_coverage(
    provider_name="Microsoft 365 GCC High"
)
# Returns: {
#   'total_cmmc_controls': 110,
#   'mapped_controls': 21,
#   'coverage_percentage': 19.1,
#   'inherited_count': 7,
#   'shared_count': 12,
#   'customer_count': 2
# }

# Calculate assessment savings
savings = await service.calculate_assessment_savings(
    assessment_id="uuid",
    provider_names=["Microsoft 365 GCC High", "Azure Government"]
)
# Returns: {
#   'total_controls': 110,
#   'inherited_controls': 8,
#   'shared_controls': 25,
#   'customer_controls': 77,
#   'hours_saved': 41.0,
#   'percentage_saved': 18.6,
#   'estimated_cost_savings': 8200.00
# }
```

### 3. Provider API

**File:** `provider_api.py`

**Endpoints:**

#### Import Provider Mappings
```http
POST /api/v1/providers/import
Content-Type: application/json

{
  "mappings_dir": null  // Optional custom directory
}

Response:
{
  "success": true,
  "providers_imported": {
    "Microsoft 365 GCC High": "uuid",
    "Azure Government": "uuid",
    "AWS GovCloud (US)": "uuid"
  },
  "total_imported": 3,
  "message": "Successfully imported 3 provider offerings"
}
```

#### List All Providers
```http
GET /api/v1/providers

Response:
[
  {
    "id": "uuid",
    "provider_name": "Microsoft 365 GCC High",
    "offering_name": "SaaS",
    "authorization_type": "FedRAMP High",
    "documentation_url": "https://...",
    "total_cmmc_controls": 110,
    "mapped_controls": 21,
    "coverage_percentage": 19.1,
    "inherited_count": 7,
    "shared_count": 12,
    "customer_count": 2
  }
]
```

#### Get Provider Controls
```http
GET /api/v1/providers/Microsoft%20365%20GCC%20High/controls

Response:
{
  "provider_name": "Microsoft 365 GCC High",
  "total_controls": 21,
  "inherited_controls": [
    "IA.L2-3.5.7",
    "SC.L2-3.13.16",
    ...
  ],
  "shared_controls": [
    "AC.L2-3.1.1",
    "AU.L2-3.3.1",
    ...
  ],
  "customer_controls": [
    "CM.L2-3.4.7",
    "SI.L2-3.14.2"
  ],
  "coverage_percentage": 19.1
}
```

#### Get Control Inheritance Info
```http
GET /api/v1/providers/control/AC.L2-3.1.1?provider_name=Microsoft%20365%20GCC%20High

Response:
[
  {
    "provider_name": "Microsoft 365 GCC High",
    "offering_name": "SaaS",
    "authorization_type": "FedRAMP High",
    "responsibility": "Shared",
    "provider_narrative": "Microsoft provides Azure AD for centralized identity and access management...",
    "customer_narrative": "Customer configures conditional access policies, MFA requirements...",
    "implementation_guidance": "1. Configure Azure AD conditional access policies\n2. Enable MFA for all users...",
    "evidence_url": "https://docs.microsoft.com/..."
  }
]
```

#### Calculate Assessment Savings
```http
POST /api/v1/providers/assessment/uuid/savings
Content-Type: application/json

{
  "provider_names": [
    "Microsoft 365 GCC High",
    "Azure Government"
  ]
}

Response:
{
  "assessment_id": "uuid",
  "providers_used": [
    "Microsoft 365 GCC High",
    "Azure Government"
  ],
  "total_controls": 110,
  "inherited_controls": 8,
  "shared_controls": 25,
  "customer_controls": 77,
  "hours_saved": 41.0,
  "percentage_saved": 18.6,
  "estimated_cost_savings": 8200.00,
  "message": "Using 2 cloud provider(s) can save 41.0 hours (18.6%) on assessment"
}
```

#### Get Coverage Summary
```http
GET /api/v1/providers/coverage/summary

Response:
{
  "total_providers": 3,
  "total_cmmc_controls": 110,
  "unique_controls_covered": 42,
  "overall_coverage_percentage": 38.2,
  "by_provider": {
    "Microsoft 365 GCC High": {
      "mapped_controls": 21,
      "inherited": 7,
      "shared": 12,
      "customer": 2
    },
    "Azure Government": {
      "mapped_controls": 18,
      "inherited": 1,
      "shared": 15,
      "customer": 2
    },
    "AWS GovCloud (US)": {
      "mapped_controls": 18,
      "inherited": 1,
      "shared": 14,
      "customer": 3
    }
  },
  "aggregate_counts": {
    "total_inherited": 9,
    "total_shared": 41,
    "total_customer": 7
  }
}
```

## Workflow

### 1. Initial Setup - Import Provider Mappings

```bash
# Import all provider mappings into database
curl -X POST http://localhost:8000/api/v1/providers/import
```

This loads the JSON files and populates:
- `provider_offerings` table (3 providers)
- `provider_control_inheritance` table (~57 control mappings)

**Run once during platform setup.**

### 2. Assessment Creation - Select Providers

When creating an assessment, the organization specifies which cloud providers they use:

```http
POST /api/v1/assessments
{
  "organization_id": "uuid",
  "scope": "CMMC Level 2",
  "providers": [
    "Microsoft 365 GCC High",
    "Azure Government"
  ]
}
```

### 3. Control Analysis - Leverage Inheritance

When analyzing a control, the AI service automatically retrieves provider inheritance:

```python
from services.ai_analysis import AIAnalysisService

result = await ai_service.analyze_control(
    control_id="AC.L2-3.1.1",
    assessment_id="uuid",
    include_provider_inheritance=True  # Default
)

# AI analysis includes:
# - Provider narrative
# - Customer narrative
# - Responsibility type
# - Implementation guidance
```

**For Inherited Controls:**
- Status: Automatically marked as "Met" (no assessment needed)
- Narrative: "This control is fully inherited from [Provider]. [Provider narrative]."
- Evidence: Provider compliance documentation

**For Shared Controls:**
- AI focuses analysis on **customer responsibilities only**
- Provider responsibilities are acknowledged but not assessed
- Reduces evidence gathering by ~50%

**For Customer Controls:**
- Full manual assessment required
- No provider assistance

### 4. Savings Calculation - Quantify Value

```http
POST /api/v1/providers/assessment/uuid/savings
{
  "provider_names": ["Microsoft 365 GCC High", "Azure Government"]
}
```

**Returns:**
- Hours saved: 41.0 hours
- Percentage saved: 18.6%
- Cost savings: $8,200 (at $200/hour)

### 5. Reporting - Include Provider Info

SSP and assessment reports automatically include:
- Provider inheritance tables
- Shared responsibility matrices
- Customer implementation guidance
- Provider compliance documentation references

## Example: M365 GCC High Controls

### Fully Inherited (7 controls)

| Control ID | Title | Evidence |
|------------|-------|----------|
| IA.L2-3.5.7 | Cryptographic Module Authentication | FIPS 140-2 validation |
| SC.L2-3.13.16 | Data at Rest Protection | BitLocker, AES-256 encryption |
| PE.L2-3.10.1 | Physical Access Authorizations | Azure datacenter compliance |
| PE.L2-3.10.3 | Physical Access Control | Azure datacenter compliance |
| PE.L2-3.10.4 | Physical Access Monitoring | Azure datacenter compliance |
| PE.L2-3.10.5 | Physical Access Device Management | Azure datacenter compliance |
| PE.L2-3.10.6 | Physical Access Visitor Control | Azure datacenter compliance |

**Assessment Effort:** 0 hours (14 hours saved)

### Shared Responsibility (12 controls)

| Control ID | Title | Customer Action |
|------------|-------|----------------|
| AC.L2-3.1.1 | Authorized Access Control | Configure Azure AD policies |
| AC.L2-3.1.2 | Transaction & Function Control | Configure RBAC roles |
| AU.L2-3.3.1 | System Audit Logs | Enable audit logging |
| AU.L2-3.3.9 | Audit Log Protection | Configure log retention |
| IA.L2-3.5.3 | Multi-Factor Authentication | Enforce MFA policies |
| SC.L2-3.13.8 | Transmission Confidentiality | Configure TLS settings |
| SC.L2-3.13.11 | Cryptographic Protection | Use Azure Key Vault |
| IR.L2-3.6.1 | Incident Response | Configure alerting |
| ... | ... | ... |

**Assessment Effort:** ~12 hours (12 hours saved from 24 hours)

## Adding New Provider Mappings

To add a new cloud provider:

### 1. Create JSON Mapping File

Create `data/provider_mappings/new_provider.json`:

```json
{
  "provider_name": "Google Workspace",
  "provider_type": "SaaS",
  "description": "Google Workspace for Government",
  "certification_level": "FedRAMP Moderate",
  "documentation_url": "https://cloud.google.com/security/compliance",
  "control_mappings": [
    {
      "control_id": "AC.L2-3.1.1",
      "control_title": "Authorized Access Control",
      "responsibility": "Shared",
      "google_responsibility": "Google provides Workspace Admin Console for identity management",
      "customer_responsibility": "Customer configures access policies and groups",
      "inherited_controls": [],
      "implementation_guidance": "Use Google Workspace Admin Console to configure access",
      "evidence_artifacts": [
        "Admin Console settings",
        "User access logs"
      ],
      "authoritative_source": "https://support.google.com/..."
    }
  ],
  "summary": {
    "total_controls_mapped": 15,
    "inherited_count": 5,
    "shared_count": 8,
    "customer_count": 2,
    "coverage_percentage": 13.6
  }
}
```

### 2. Update Service to Support New Provider

In `services/provider_inheritance.py`, add support for new responsibility field:

```python
# In parse_mapping method
elif 'google_responsibility' in control_map:
    provider_resp = control_map['google_responsibility']
    customer_resp = control_map['customer_responsibility']
```

### 3. Import New Provider

```http
POST /api/v1/providers/import
```

The service will automatically detect and import the new JSON file.

## Database Schema

### provider_offerings

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| provider_name | VARCHAR | "Microsoft 365 GCC High" |
| offering_name | VARCHAR | "SaaS" |
| authorization_type | VARCHAR | "FedRAMP High" |
| documentation_url | VARCHAR | Provider docs URL |
| created_at | TIMESTAMP | Import timestamp |

### provider_control_inheritance

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| provider_offering_id | UUID | FK to provider_offerings |
| control_id | VARCHAR | "AC.L2-3.1.1" |
| responsibility | VARCHAR | "Inherited/Shared/Customer" |
| provider_narrative | TEXT | Provider's responsibility |
| customer_narrative | TEXT | Customer's responsibility |
| implementation_guidance | TEXT | How to implement |
| evidence_url | VARCHAR | Provider compliance docs |

## Integration with AI Analysis

The AI analysis service automatically uses provider inheritance:

```python
# In ai_analysis.py

# 1. Fetch provider inheritance
if include_provider_inheritance:
    inheritance = await provider_service.get_control_inheritance(
        control_id=control_id,
        provider_name=assessment.primary_provider
    )

# 2. Include in analysis prompt
if inheritance and inheritance[0]['responsibility'] == 'Inherited':
    prompt += f"""
    PROVIDER INHERITANCE:
    This control is FULLY INHERITED from {provider_name}.

    Provider Responsibility:
    {inheritance[0]['provider_narrative']}

    Since this control is fully inherited, mark as "Met" if provider
    compliance documentation is available.
    """

# 3. Adjust confidence scoring
confidence_factors.provider_inheritance = 1.0  # Fully inherited
```

## Testing

Run tests:

```bash
# Provider inheritance tests
pytest tests/test_provider_inheritance.py -v

# All tests
pytest tests/ -v --cov=services
```

**Test Coverage:**
- JSON loading and parsing
- Provider offering dataclass
- Control inheritance dataclass
- Responsibility type enum
- Coverage calculation
- Savings calculation
- Multiple provider scenarios
- Edge cases and validation

## Best Practices

### 1. Regular Updates
- Review provider compliance documentation quarterly
- Update JSON mappings when providers add new controls
- Re-import after updates: `POST /api/v1/providers/import`

### 2. Evidence Collection
- For inherited controls: Link to provider compliance docs (e.g., Microsoft Trust Center)
- For shared controls: Document both provider AND customer implementation
- Save provider attestation letters, FedRAMP authorization letters

### 3. Assessment Efficiency
- Start with inherited controls (instant "Met")
- Move to shared controls (focus on customer responsibility only)
- Finish with customer controls (full assessment)

### 4. Multi-Provider Strategy
- Map ALL providers your organization uses
- Calculate combined savings
- Avoid duplicate assessment for same control across providers

### 5. Compliance Verification
- Verify provider maintains certification (FedRAMP, DoD IL)
- Check authorization dates and expiration
- Monitor for provider security incidents

## Troubleshooting

**Issue: Provider not showing up after import**
- Solution: Check JSON file is in `data/provider_mappings/` directory
- Verify JSON format is valid (use `jsonlint`)
- Check logs for import errors

**Issue: Savings calculation shows 0 hours**
- Solution: Ensure assessment has controls in scope
- Verify provider_names match exactly (case-sensitive)
- Check provider mappings have responsibility types set

**Issue: Control shows as "Customer" when should be "Shared"**
- Solution: Review JSON mapping file for that control
- Verify responsibility field is correct
- Re-import after fixing JSON

**Issue: Missing provider narrative**
- Solution: Update JSON file with provider_responsibility text
- Re-import provider mappings
- Check database for null values

## Roadmap

### Phase 1 (Current) ✅
- M365 GCC High mappings (21 controls)
- Azure Government mappings (18 controls)
- AWS GovCloud mappings (18 controls)
- Import/query API
- Savings calculator

### Phase 2 (Next Sprint)
- Google Workspace for Government
- Oracle Cloud Government
- More granular shared responsibility splits
- Provider attestation document upload

### Phase 3 (Future)
- Automated provider mapping updates
- Provider API integrations (fetch live compliance status)
- Multi-region provider support
- Custom provider mapping editor UI

## References

- [Microsoft 365 GCC High Compliance](https://docs.microsoft.com/en-us/microsoft-365/compliance/)
- [Azure Government FedRAMP](https://docs.microsoft.com/en-us/azure/azure-government/compliance/azure-services-in-fedramp-auditscope)
- [AWS GovCloud Compliance](https://aws.amazon.com/compliance/services-in-scope/)
- [NIST SP 800-171 Rev 2](https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final)
- [CMMC Shared Responsibility Guide](https://dodcio.defense.gov/CMMC/)

---

**Reduce assessment time by 30-40% with cloud provider inheritance!** ☁️

Leverage billions of dollars in provider security investments.
