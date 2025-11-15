# CMMC Documentation Download and RAG Setup Guide

This guide explains how to download CMMC documentation from various sources and import them into the RAG (Retrieval-Augmented Generation) system for AI-powered analysis.

## Quick Start

1. Download CMMC documentation (see sources below)
2. Upload via the platform UI or API
3. Documents are automatically processed, chunked, and embedded
4. Query documents using natural language

## Documentation Sources

### 1. CMMC Training Academy
**URL**: https://www.cmmctraining.academy/cmmc-documentation

**Available Documents** (as of 2024):
- CMMC Model Overview v2.0
- CMMC Assessment Process (CAP)
- CMMC Assessment Guide - Level 1 & 2
- CMMC Assessment Guides - Level 3
- Assessment Scoping Guidance
- Practice Quick Reference Guides
- External Cloud Service Provider (CSP) Assessment Guide
- Azure Cloud Assessment Guide
- AWS Cloud Assessment Guide
- Google Cloud Platform (GCP) Assessment Guide

**How to Download**:
1. Visit the website in your browser
2. Click on each document link to download
3. Save PDFs to a local folder (e.g., `cmmc-docs/`)

### 2. Official DoD CMMC Resources
**URL**: https://dodcio.defense.gov/CMMC/Documentation/

**Key Documents**:
- CMMC Model v2.0 (Current)
- CMMC Assessment Process (CAP)
- Cloud Security Requirement Guides (CSRG)
- Enclave Assessment Guides

**How to Download**:
1. Navigate to the DoD CMMC Documentation page
2. Download PDFs under "CMMC Model 2.0" section
3. Save to your `cmmc-docs/` folder

### 3. NIST SP 800-171 Documentation
**URL**: https://csrc.nist.gov/publications/detail/sp/800-171/rev-2/final

**Documents**:
- NIST SP 800-171 Rev 2 (PDF)
- NIST SP 800-171A (Assessment Procedures)
- NIST SP 800-171B (Enhanced Security Requirements)

**How to Download**:
1. Click "Download" button on NIST page
2. Select PDF format
3. Download all revisions and related publications

### 4. Additional Resources

#### CMMC Accreditation Body (CMMC-AB)
- **URL**: https://www.cmmcab.org/resources
- **Documents**: Marketplace guides, training materials

#### CMMC Resource Center
- **URL**: https://www.acq.osd.mil/cmmc/
- **Documents**: FAQs, policy updates, implementation guides

## Document Organization

Recommended folder structure:

```
cmmc-docs/
├── models/
│   ├── CMMC-Model-v2.0.pdf
│   └── CMMC-Assessment-Guide-Level-2.pdf
├── nist/
│   ├── NIST-SP-800-171-Rev2.pdf
│   ├── NIST-SP-800-171A.pdf
│   └── NIST-SP-800-53-Rev5.pdf
├── cloud/
│   ├── AWS-CMMC-Assessment-Guide.pdf
│   ├── Azure-CMMC-Assessment-Guide.pdf
│   └── GCP-CMMC-Assessment-Guide.pdf
├── policies/
│   ├── Access-Control-Policy-Template.pdf
│   └── Incident-Response-Plan-Template.pdf
└── guides/
    ├── CMMC-Scoping-Guide.pdf
    └── SSP-Template-CMMC.pdf
```

## Uploading to RAG System

### Method 1: Web UI

1. Navigate to **Documents** page in the CMMC Platform
2. Click **Upload Document**
3. Select file(s) from your `cmmc-docs/` folder
4. Add optional metadata:
   - Title (auto-detected from filename)
   - Organization
   - Assessment (if applicable)
5. Click **Upload & Process**
6. Wait for processing (automatic chunking and embedding)

### Method 2: API Upload

```bash
# Upload single document
curl -X POST "https://your-domain.com/api/v1/documents/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@cmmc-docs/models/CMMC-Model-v2.0.pdf" \
  -F "title=CMMC Model Version 2.0"

# The response includes document_id
{
  "document_id": "abc-123-def",
  "filename": "CMMC-Model-v2.0.pdf",
  "file_size": 2458624,
  "status": "uploaded",
  "message": "Document uploaded successfully"
}

# Processing happens automatically in background
# Check status:
curl -X GET "https://your-domain.com/api/v1/documents" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Method 3: Bulk Upload Script

```python
#!/usr/bin/env python3
"""
Bulk upload CMMC documentation to RAG system
"""

import os
import requests
from pathlib import Path

API_URL = "https://your-domain.com/api/v1"
API_TOKEN = "your_api_token_here"

def upload_document(file_path, title=None):
    """Upload single document"""
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {}
        if title:
            data['title'] = title

        response = requests.post(
            f"{API_URL}/documents/upload",
            headers={"Authorization": f"Bearer {API_TOKEN}"},
            files=files,
            data=data
        )

        if response.status_code == 200:
            print(f"✓ Uploaded: {file_path.name}")
            return response.json()
        else:
            print(f"✗ Failed: {file_path.name} - {response.text}")
            return None

def bulk_upload(directory):
    """Upload all PDFs in directory"""
    doc_dir = Path(directory)
    pdf_files = list(doc_dir.rglob("*.pdf"))

    print(f"Found {len(pdf_files)} PDF files")

    for pdf_file in pdf_files:
        # Use filename (without extension) as title
        title = pdf_file.stem.replace('-', ' ').replace('_', ' ')
        upload_document(pdf_file, title)

if __name__ == "__main__":
    # Upload all documents from cmmc-docs folder
    bulk_upload("./cmmc-docs")
```

## Querying Documents

### Simple Query

```python
import requests

response = requests.post(
    f"{API_URL}/rag/query",
    headers={"Authorization": f"Bearer {API_TOKEN}"},
    json={
        "query": "What are the requirements for multi-factor authentication?",
        "top_k": 5,
        "include_context": True
    }
)

results = response.json()

for result in results['results']:
    print(f"\nDocument: {result['document_title']}")
    print(f"Relevance: {1.0 - result['similarity_score']:.2%}")
    print(f"Text: {result['chunk_text'][:200]}...")
```

### Control-Specific Query

```python
# Query documents related to specific control
response = requests.post(
    f"{API_URL}/rag/query",
    json={
        "query": "How do we implement this control?",
        "control_id": "IA.L2-3.5.3",  # Multi-factor authentication
        "top_k": 5
    }
)
```

### Advanced Query with Filtering

```python
response = requests.post(
    f"{API_URL}/rag/query",
    json={
        "query": "AWS security configuration for CMMC compliance",
        "top_k": 10,
        "rerank_top_k": 20,  # Retrieve 20, re-rank to top 10
        "assessment_id": "assessment-123"  # Filter by assessment
    }
)
```

## Best Practices

### Document Preparation

1. **Use Official Sources**: Always download from official DoD, NIST, or CMMC-AB sources
2. **Check Versions**: Ensure you're using the latest version (currently CMMC 2.0)
3. **Organize by Category**: Group documents by type for easier management
4. **Name Consistently**: Use descriptive filenames (e.g., `CMMC-Model-v2.0.pdf` not `doc1.pdf`)

### Upload Strategy

1. **Start with Core Documents**:
   - CMMC Model v2.0
   - CMMC Assessment Guide - Level 2
   - NIST SP 800-171 Rev 2

2. **Add Cloud-Specific Guides** (if applicable):
   - AWS/Azure/GCP assessment guides

3. **Include Policy Templates**:
   - Access control policies
   - Incident response plans
   - Configuration management procedures

4. **Upload Custom Documents**:
   - Your organization's policies
   - SSP (System Security Plan)
   - POA&M (Plan of Action and Milestones)

### Query Optimization

1. **Be Specific**: "What are MFA requirements for CMMC Level 2?" vs. "Tell me about security"
2. **Use Control IDs**: Query with control IDs for targeted results
3. **Iterate Queries**: Refine based on results
4. **Use Context**: The `context` field provides formatted text for LLM prompts

## Processing Status

### Status Values

- **uploaded**: File uploaded, awaiting processing
- **processing**: Currently extracting text and chunking
- **processed**: Text extracted and chunked
- **embedded**: Chunks embedded (ready for RAG queries)
- **failed**: Processing failed (check error_message)

### Monitor Processing

```bash
# Check document status
curl -X GET "https://your-domain.com/api/v1/documents" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Get RAG statistics
curl -X GET "https://your-domain.com/api/v1/rag/stats" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Troubleshooting

### Upload Fails

- **Check file size**: Max 500MB per file
- **Verify file type**: Only PDF, DOCX, TXT supported
- **Check permissions**: Ensure you have upload permissions

### Processing Fails

- **Check logs**: Review error_message in document record
- **Verify file integrity**: Try opening PDF locally
- **Retry processing**: Delete and re-upload if needed

### No Query Results

- **Check embedding status**: Ensure documents are "embedded"
- **Verify query**: Try broader search terms
- **Check filters**: Remove control_id/assessment_id filters to test

### Low Relevance Scores

- **Rephrase query**: Use terminology from documents
- **Increase top_k**: Retrieve more results
- **Check document coverage**: Upload additional relevant documents

## Recommended Reading Order

For new users setting up CMMC compliance:

1. **CMMC Model v2.0** - Understand the framework
2. **CMMC Assessment Guide - Level 2** - Assessment methodology
3. **NIST SP 800-171 Rev 2** - Detailed control requirements
4. **NIST SP 800-171A** - Assessment procedures
5. **Scoping Guide** - Determine what's in scope
6. **Cloud-Specific Guides** - If using AWS/Azure/GCP

Upload in this order for best results.

## API Reference

### Upload Document
```
POST /api/v1/documents/upload
```

### Process Document
```
POST /api/v1/documents/process
```

### List Documents
```
GET /api/v1/documents
```

### Delete Document
```
DELETE /api/v1/documents/{document_id}
```

### RAG Query
```
POST /api/v1/rag/query
```

### Get Statistics
```
GET /api/v1/rag/stats
```

## Support

For issues or questions:
- Platform Issues: Check logs in `/var/cmmc/logs/`
- CMMC Questions: Consult official CMMC-AB resources
- Technical Support: Contact your system administrator

## Security Notes

- All uploaded documents are stored encrypted
- Access is controlled via RBAC
- Document embeddings use OpenAI API (ensure API key security)
- Audit logs track all document operations

---

**Last Updated**: 2024-11-15
**CMMC Version**: 2.0
**NIST Version**: SP 800-171 Rev 2
