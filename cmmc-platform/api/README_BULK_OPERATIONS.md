# Bulk Operations

High-performance batch processing for CMMC assessments. Save 5-10 hours per assessment with bulk control updates, evidence uploads, and Excel import/export.

## Table of Contents

- [Overview](#overview)
- [Time Savings](#time-savings)
- [Features](#features)
- [API Endpoints](#api-endpoints)
- [Usage Examples](#usage-examples)
- [Excel Format](#excel-format)
- [Best Practices](#best-practices)
- [Error Handling](#error-handling)

## Overview

Bulk operations allow you to perform high-volume tasks efficiently:

- **Bulk Control Updates** - Update 50+ controls at once
- **Bulk Evidence Upload** - Upload 20+ files from ZIP archives
- **Excel Import/Export** - Batch import/export control findings
- **Mass Assignments** - Assign controls to teams by domain
- **Domain Operations** - Mark entire domains as N/A or assign to users

All operations include:
- Progress tracking
- Partial success handling
- Detailed error reporting
- Transaction safety

## Time Savings

| Operation | Manual Time | Bulk Time | Savings |
|-----------|-------------|-----------|---------|
| Update 110 controls | 3-4 hours | 10-15 minutes | **3.5 hours** |
| Upload 50 evidence files | 2-3 hours | 5-10 minutes | **2.5 hours** |
| Excel import 110 controls | 4-5 hours | 5-10 minutes | **4.5 hours** |
| Assign controls by domain | 30-45 minutes | 2-3 minutes | **40 minutes** |
| **Total per assessment** | **10-12 hours** | **25-40 minutes** | **~10 hours** |

## Features

### 1. Bulk Control Updates

Update multiple control findings in a single API call.

**Use Cases:**
- Apply findings from previous assessment
- Bulk status changes (Met/Not Met)
- Update narratives from templates
- Apply risk levels across domains

**Endpoint:** `POST /api/v1/bulk/controls/update`

**Example:**
```python
import httpx

updates = [
    {
        "control_id": "AC.L2-3.1.1",
        "status": "Met",
        "implementation_narrative": "Access control implemented via Azure AD",
        "risk_level": "Low"
    },
    {
        "control_id": "AC.L2-3.1.2",
        "status": "Partially Met",
        "findings": "Some gaps in transaction logging",
        "recommendations": "Implement comprehensive audit logging"
    }
]

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/bulk/controls/update",
        json={
            "assessment_id": "assessment-uuid",
            "updates": updates
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )

result = response.json()
print(f"Updated {result['success']}/{result['total']} controls")
```

### 2. Bulk Evidence Upload

Upload multiple evidence files from a ZIP archive.

**Use Cases:**
- Upload evidence collected during on-site assessment
- Batch upload policies and procedures
- Import screenshots and logs
- Upload scanned documents

**Endpoint:** `POST /api/v1/bulk/evidence/upload-zip`

**Example:**
```python
# Create ZIP file with evidence
import zipfile

with zipfile.ZipFile('evidence.zip', 'w') as zf:
    zf.write('access_control_policy.pdf')
    zf.write('audit_logs.xlsx')
    zf.write('firewall_config.txt')
    # ... add more files

# Upload ZIP
with open('evidence.zip', 'rb') as f:
    files = {'zip_file': ('evidence.zip', f, 'application/zip')}
    params = {
        'assessment_id': 'assessment-uuid',
        'organization_id': 'org-uuid',
        'evidence_type': 'Policy',
        'control_ids': 'AC.L2-3.1.1,AC.L2-3.1.2'
    }

    response = httpx.post(
        "http://localhost:8000/api/v1/bulk/evidence/upload-zip",
        params=params,
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )

result = response.json()
print(f"Uploaded {result['success']} files")
for file in result['uploaded_files']:
    print(f"  - {file['file_name']} ({file['file_size']} bytes)")
```

### 3. Excel Import/Export

Import and export control findings via Excel for offline editing.

**Use Cases:**
- Offline assessment work
- Team collaboration via shared Excel files
- Bulk updates from external sources
- Reporting and documentation

**Export Endpoint:** `GET /api/v1/bulk/controls/export-excel`

**Export Example:**
```python
async with httpx.AsyncClient() as client:
    response = await client.get(
        "http://localhost:8000/api/v1/bulk/controls/export-excel",
        params={"assessment_id": "assessment-uuid"},
        headers={"Authorization": f"Bearer {access_token}"}
    )

# Save Excel file
with open('assessment_findings.xlsx', 'wb') as f:
    f.write(response.content)

print("Excel file exported: assessment_findings.xlsx")
```

**Import Endpoint:** `POST /api/v1/bulk/controls/import-excel`

**Import Example:**
```python
with open('updated_findings.xlsx', 'rb') as f:
    files = {'excel_file': ('findings.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    params = {'assessment_id': 'assessment-uuid'}

    response = httpx.post(
        "http://localhost:8000/api/v1/bulk/controls/import-excel",
        params=params,
        files=files,
        headers={"Authorization": f"Bearer {access_token}"}
    )

result = response.json()
print(f"Imported {result['success']}/{result['total']} controls")
if result['failed'] > 0:
    print(f"Errors:")
    for error in result['errors']:
        print(f"  Row {error.get('row', '?')}: {error['error']}")
```

### 4. Mass Assignments

Assign multiple controls to users at once.

**Use Cases:**
- Distribute workload across team
- Assign by domain expertise
- Reassign controls when personnel changes

**Endpoint:** `POST /api/v1/bulk/controls/assign`

**Example:**
```python
# Assign all AC controls to security engineer
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/bulk/controls/assign",
        json={
            "assessment_id": "assessment-uuid",
            "control_ids": [
                "AC.L2-3.1.1",
                "AC.L2-3.1.2",
                "AC.L2-3.1.3",
                # ... more AC controls
            ],
            "assigned_to": "engineer-uuid"
        },
        headers={"Authorization": f"Bearer {access_token}"}
    )

result = response.json()
print(f"Assigned {result['success']} controls")
```

### 5. Domain Operations

Convenience operations for entire domains.

**Assign by Domain:**
```python
# Assign all AC (Access Control) controls to user
response = httpx.post(
    "http://localhost:8000/api/v1/bulk/controls/assign-by-domain",
    params={
        "assessment_id": "assessment-uuid",
        "domain": "AC",
        "assigned_to": "user-uuid"
    },
    headers={"Authorization": f"Bearer {access_token}"}
)
```

**Mark Domain as N/A:**
```python
# Mark all PE (Physical) controls as Not Applicable (for cloud-only environments)
response = httpx.post(
    "http://localhost:8000/api/v1/bulk/controls/mark-na-by-domain",
    params={
        "assessment_id": "assessment-uuid",
        "domain": "PE"
    },
    headers={"Authorization": f"Bearer {access_token}"}
)
```

## API Endpoints

### Bulk Control Operations

| Endpoint | Method | Description | Time Savings |
|----------|--------|-------------|--------------|
| `/bulk/controls/update` | POST | Bulk control status updates | 2-5 hours |
| `/bulk/controls/assign` | POST | Mass assignment to users | 15-30 minutes |
| `/bulk/controls/assign-by-domain` | POST | Assign all controls in domain | 5-10 minutes |
| `/bulk/controls/mark-na-by-domain` | POST | Mark domain as Not Applicable | 5-10 minutes |

### Excel Operations

| Endpoint | Method | Description | Time Savings |
|----------|--------|-------------|--------------|
| `/bulk/controls/export-excel` | GET | Export findings to Excel | 30 minutes |
| `/bulk/controls/import-excel` | POST | Import findings from Excel | 3-5 hours |

### Evidence Operations

| Endpoint | Method | Description | Time Savings |
|----------|--------|-------------|--------------|
| `/bulk/evidence/upload-zip` | POST | Upload ZIP with multiple files | 1-2 hours |

## Usage Examples

### Complete Assessment Workflow

```python
import httpx

async def complete_assessment_workflow():
    """Example: Complete bulk operations workflow"""

    async with httpx.AsyncClient() as client:
        base_url = "http://localhost:8000/api/v1/bulk"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Step 1: Upload evidence from ZIP
        with open('collected_evidence.zip', 'rb') as f:
            upload_response = await client.post(
                f"{base_url}/evidence/upload-zip",
                params={
                    "assessment_id": assessment_id,
                    "organization_id": org_id,
                    "evidence_type": "Policy"
                },
                files={'zip_file': f},
                headers=headers
            )
        print(f"Uploaded {upload_response.json()['success']} evidence files")

        # Step 2: Export to Excel for offline review
        export_response = await client.get(
            f"{base_url}/controls/export-excel",
            params={"assessment_id": assessment_id},
            headers=headers
        )
        with open('assessment_draft.xlsx', 'wb') as f:
            f.write(export_response.content)
        print("Excel exported for offline review")

        # Step 3: After team review, import updates
        with open('assessment_reviewed.xlsx', 'rb') as f:
            import_response = await client.post(
                f"{base_url}/controls/import-excel",
                params={"assessment_id": assessment_id},
                files={'excel_file': f},
                headers=headers
            )
        print(f"Imported {import_response.json()['success']} control updates")

        # Step 4: Mark out-of-scope domains as N/A
        for domain in ['PE', 'PS']:  # Physical and Personnel (cloud-only)
            na_response = await client.post(
                f"{base_url}/controls/mark-na-by-domain",
                params={
                    "assessment_id": assessment_id,
                    "domain": domain
                },
                headers=headers
            )
            print(f"Marked {domain} as N/A: {na_response.json()['success']} controls")

        # Step 5: Assign remaining controls by domain
        assignments = {
            "AC": "alice-uuid",  # Access Control -> Alice
            "AU": "bob-uuid",    # Audit -> Bob
            "SC": "charlie-uuid" # System Protection -> Charlie
        }

        for domain, user_id in assignments.items():
            assign_response = await client.post(
                f"{base_url}/controls/assign-by-domain",
                params={
                    "assessment_id": assessment_id,
                    "domain": domain,
                    "assigned_to": user_id
                },
                headers=headers
            )
            print(f"Assigned {domain} to {user_id}: {assign_response.json()['success']} controls")

        print("\n✓ Assessment workflow completed!")
        print("Time saved: ~8-10 hours vs manual operations")
```

## Excel Format

### Export Format

The exported Excel file contains:

**Sheet 1: Control Findings**
- Column A: Control ID (e.g., AC.L2-3.1.1)
- Column B: Domain (AC, AT, AU, etc.)
- Column C: Title
- Column D: Status (Met, Not Met, Partially Met, etc.)
- Column E: Implementation Status
- Column F: Implementation Narrative
- Column G: Test Results
- Column H: Findings
- Column I: Recommendations
- Column J: Risk Level
- Column K: Residual Risk
- Column L: Assigned To
- Column M-O: Assessment Methods (Examine, Interview, Test)
- Column P: AI Confidence Score
- Column Q: Last Updated

**Sheet 2: Metadata**
- Assessment name, type, level
- Export date
- Total control count

### Import Format

For import, only these columns are required:
- **Column A: Control ID** (required)
- **Column D: Status** (required)

Optional columns (E-J) will update if provided.

**Tips:**
- Keep the header row intact
- Control IDs must match exactly (e.g., "AC.L2-3.1.1")
- Valid statuses: "Met", "Not Met", "Partially Met", "Not Applicable", "Not Started", "In Progress"
- Empty cells are ignored (won't overwrite existing data)

## Best Practices

### 1. Bulk Control Updates

**Do:**
- Group similar updates together
- Validate control IDs before bulk update
- Use consistent status values
- Include error handling

**Don't:**
- Update more than 200 controls at once (split into batches)
- Mix different assessment IDs in same request
- Skip validation of input data

### 2. Bulk Evidence Upload

**Do:**
- Organize files in ZIP before upload
- Use descriptive filenames
- Remove hidden/system files from ZIP
- Link evidence to relevant controls

**Don't:**
- Upload extremely large ZIPs (>100MB, split instead)
- Include empty files
- Use special characters in filenames
- Forget to verify upload completion

### 3. Excel Import/Export

**Do:**
- Export before making bulk changes (backup)
- Review imported data for accuracy
- Use Excel's filter/sort for offline analysis
- Keep original export for comparison

**Don't:**
- Modify the header row
- Change Control IDs
- Use invalid status values
- Import without reviewing errors

### 4. Performance Tips

**Batch Size Recommendations:**
- Control updates: 50-100 per request
- Evidence upload: 20-50 files per ZIP
- Excel import: Up to 200 rows
- Mass assignments: Up to 50 controls

**Parallel Processing:**
```python
import asyncio

async def parallel_bulk_operations():
    """Process multiple bulk operations in parallel"""

    tasks = [
        upload_evidence_batch_1(),
        upload_evidence_batch_2(),
        update_controls_batch_1(),
        update_controls_batch_2()
    ]

    results = await asyncio.gather(*tasks)
    return results
```

## Error Handling

All bulk operations return detailed error information:

```json
{
    "operation": "control_update",
    "total": 10,
    "success": 8,
    "failed": 2,
    "errors": [
        {
            "control_id": "INVALID.ID",
            "error": "Control not found"
        },
        {
            "control_id": "AC.L2-3.1.1",
            "error": "Invalid status value"
        }
    ],
    "status": "partial"
}
```

### Status Values

- `completed` - All operations successful
- `partial` - Some succeeded, some failed
- `failed` - All operations failed

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Control not found" | Invalid control ID | Verify control ID format (e.g., AC.L2-3.1.1) |
| "Invalid status value" | Wrong status string | Use: Met, Not Met, Partially Met, Not Applicable |
| "Invalid ZIP file" | Corrupted ZIP | Re-create ZIP file |
| "Missing required field" | Incomplete data | Ensure control_id and status are provided |
| "Assessment not found" | Wrong assessment ID | Verify assessment UUID |

### Retry Logic

```python
async def bulk_update_with_retry(updates, max_retries=3):
    """Bulk update with automatic retry on failure"""

    for attempt in range(max_retries):
        try:
            result = await bulk_service.bulk_update_control_status(
                assessment_id, updates, user_id
            )

            if result['status'] == 'completed':
                return result

            # If partial failure, retry only failed items
            if result['status'] == 'partial':
                failed_ids = [e['control_id'] for e in result['errors']]
                updates = [u for u in updates if u['control_id'] in failed_ids]

        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    return result
```

## Advanced Use Cases

### 1. Template-Based Assessment

```python
async def apply_assessment_template(template_id, new_assessment_id):
    """Apply findings from template assessment to new assessment"""

    # Export template
    template_findings = await export_findings_to_excel(template_id)

    # Modify assessment_id in metadata
    # ... modify Excel file ...

    # Import to new assessment
    result = await import_findings_from_excel(new_assessment_id, template_findings)

    print(f"Applied template: {result['success']} controls copied")
```

### 2. Multi-Assessor Workflow

```python
async def distribute_assessment_workload(assessment_id, team):
    """Distribute controls across team by domain"""

    domain_assignments = {
        "AC": team['alice'],
        "AT": team['bob'],
        "AU": team['charlie'],
        "CA": team['alice'],
        # ... assign all domains
    }

    for domain, assessor in domain_assignments.items():
        await assign_controls_by_domain(assessment_id, domain, assessor)

    print("Workload distributed across team")
```

### 3. Automated Evidence Collection

```python
async def collect_and_upload_evidence():
    """Automated evidence collection from multiple sources"""

    import os
    import zipfile

    # Collect evidence files
    evidence_dir = "/path/to/evidence"
    zip_path = "collected_evidence.zip"

    with zipfile.ZipFile(zip_path, 'w') as zf:
        for root, dirs, files in os.walk(evidence_dir):
            for file in files:
                file_path = os.path.join(root, file)
                zf.write(file_path, os.path.basename(file_path))

    # Upload to assessment
    with open(zip_path, 'rb') as f:
        result = await bulk_upload_evidence_zip(
            assessment_id, org_id, f, 'Policy', None, user_id
        )

    print(f"Uploaded {result['success']} evidence files")
```

## Contributing

When adding new bulk operations:

1. Add service method to `services/bulk_service.py`
2. Add API endpoint to `bulk_api.py`
3. Add tests to `tests/test_bulk_operations.py`
4. Update this README with examples
5. Include time savings estimates

## License

Internal use only - CMMC Compliance Platform
