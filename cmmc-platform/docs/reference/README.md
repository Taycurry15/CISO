# CMMC Reference Documentation

This directory contains official NIST and CMMC documentation for the RAG knowledge base.

## Required Documents

### NIST Documentation

#### NIST SP 800-171 Rev 2 (Primary Source)
- **File**: `nist/NIST.SP.800-171r2.pdf`
- **Title**: Protecting Controlled Unclassified Information in Nonfederal Systems and Organizations
- **URL**: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r2.pdf
- **Purpose**: Defines the 110 security requirements for protecting CUI
- **Status**: Withdrawn (superseded by Rev 3, but still used for CMMC 2.0)

#### NIST SP 800-171A
- **File**: `nist/NIST.SP.800-171A.pdf`
- **Title**: Assessing Security Requirements for Controlled Unclassified Information
- **URL**: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171a.pdf
- **Purpose**: Assessment procedures for each control (Examine/Interview/Test)
- **Status**: Withdrawn (superseded by Rev 3)

#### NIST SP 800-171 Rev 3 (Optional - Future)
- **File**: `nist/NIST.SP.800-171r3.pdf`
- **Title**: Protecting Controlled Unclassified Information in Nonfederal Systems and Organizations
- **URL**: https://csrc.nist.gov/pubs/sp/800/171/r3/final
- **Purpose**: Updated requirements (published May 2024)
- **Status**: Current version (not yet adopted by CMMC)

#### NIST SP 800-171A Rev 3 (Optional - Future)
- **File**: `nist/NIST.SP.800-171Ar3.pdf`
- **Title**: Assessing Security Requirements for Controlled Unclassified Information
- **URL**: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171Ar3.pdf
- **Purpose**: Updated assessment procedures
- **Status**: Current version (published May 2024)

### CMMC Documentation

#### CMMC Model v2.13
- **File**: `cmmc/CMMC-Model-v2.13.pdf`
- **Title**: Cybersecurity Maturity Model Certification (CMMC) Model Overview
- **URL**: https://dodcio.defense.gov/Portals/0/Documents/CMMC/ModelOverviewv2.pdf
- **Purpose**: Official CMMC Level 1, 2, and 3 requirements
- **Status**: Current official DoD version

#### CMMC Assessment Guide - Level 2 v2.13
- **File**: `cmmc/CMMC-AssessmentGuide-L2-v2.13.pdf`
- **Title**: CMMC Assessment Guide – Level 2
- **URL**: https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf
- **Purpose**: C3PAO assessment methodology and criteria
- **Status**: Current official guide

#### CMMC Scoping Guide - Level 2 v2.13
- **File**: `cmmc/CMMC-ScopingGuide-L2-v2.13.pdf`
- **Title**: CMMC Scoping Guide Level 2
- **URL**: https://dodcio.defense.gov/Portals/0/Documents/CMMC/ScopingGuideL2v2.pdf
- **Purpose**: Guidance on defining assessment scope
- **Status**: Current official guide

#### CMMC Level 2 Scoping (v2.0 - Legacy)
- **File**: `cmmc/CMMC-Scope-L2-v2.0.pdf`
- **Title**: Identifying the CMMC Assessment Scope Level 2
- **URL**: https://dodcio.defense.gov/Portals/0/Documents/CMMC/Scope_Level2_V2.0_FINAL_20211202_508.pdf
- **Purpose**: Assessment scope requirements
- **Status**: December 2021 version

### Additional Guides (Optional but Recommended)

#### NIST SP 800-171 DoD Assessment Methodology
- **File**: `guides/NIST-SP-800-171-DoD-Assessment-Methodology.pdf`
- **Title**: NIST SP 800-171 DoD Assessment Methodology
- **URL**: https://www.acq.osd.mil/asda/dpc/cp/cyber/docs/safeguarding/NIST-SP-800-171-Assessment-Methodology-Version-1.2.1-6.24.2020.pdf
- **Purpose**: DoD-specific assessment procedures
- **Status**: Version 1.2.1 (June 2020)

#### Microsoft CMMC 2.0 Technical Reference Guide
- **File**: `guides/Microsoft-CMMC-2.0-Technical-Reference.pdf`
- **Title**: Microsoft Technical Reference Guide for CMMC 2.0
- **URL**: https://download.microsoft.com/download/c/a/6/ca67ab87-4832-476e-8f01-b1572c7a740c/Microsoft Technical Reference Guide for CMMC v2_(Public Preview)_20220304 (2).pdf
- **Purpose**: Microsoft 365 GCC High compliance mapping
- **Status**: Public preview

## Quick Download

### Option 1: Automated Download Script

Run the provided download script (requires internet access):

```bash
cd /home/user/CISO/cmmc-platform/docs/reference
./download_docs.sh
```

**Note**: Some government sites block automated downloads. If the script fails, use Option 2.

### Option 2: Manual Download

1. Open each URL in a web browser
2. Download the PDF manually
3. Save to the appropriate directory with the specified filename
4. Run the ingestion script to load into RAG

```bash
# Example: Download NIST SP 800-171 Rev 2
# 1. Visit: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r2.pdf
# 2. Save as: docs/reference/nist/NIST.SP.800-171r2.pdf

# After downloading all PDFs, ingest them:
python scripts/ingest_reference_docs.py
```

## Directory Structure

```
docs/reference/
├── README.md (this file)
├── download_docs.sh (automated download script)
├── manifest.json (document metadata)
├── nist/
│   ├── NIST.SP.800-171r2.pdf
│   ├── NIST.SP.800-171A.pdf
│   ├── NIST.SP.800-171r3.pdf (optional)
│   └── NIST.SP.800-171Ar3.pdf (optional)
├── cmmc/
│   ├── CMMC-Model-v2.13.pdf
│   ├── CMMC-AssessmentGuide-L2-v2.13.pdf
│   ├── CMMC-ScopingGuide-L2-v2.13.pdf
│   └── CMMC-Scope-L2-v2.0.pdf
└── guides/
    ├── NIST-SP-800-171-DoD-Assessment-Methodology.pdf
    └── Microsoft-CMMC-2.0-Technical-Reference.pdf
```

## Ingestion into RAG

After downloading the PDFs, run the ingestion script to load them into the RAG knowledge base:

```bash
# From project root
python scripts/ingest_reference_docs.py

# Or ingest specific document
python scripts/ingest_reference_docs.py --file docs/reference/nist/NIST.SP.800-171r2.pdf

# Check ingestion status
python scripts/ingest_reference_docs.py --status
```

### What the Ingestion Does

1. **Extracts text** from PDFs using PyPDF2/pdfplumber
2. **Chunks documents** into 1000-character segments with 200-character overlap
3. **Generates embeddings** for each chunk using configured embedding service
4. **Stores in PostgreSQL** with pgvector for semantic search
5. **Tags chunks** with:
   - Document type (nist_800_171, cmmc_model, assessment_guide)
   - Control IDs (extracted from text)
   - Assessment methods (Examine/Interview/Test)

### Verification

After ingestion, verify the documents are indexed:

```sql
-- Check document count
SELECT document_type, COUNT(*) as doc_count
FROM documents
WHERE document_type IN ('nist_800_171', 'nist_800_171a', 'cmmc_model')
GROUP BY document_type;

-- Check chunk count with embeddings
SELECT d.document_type, COUNT(dc.id) as chunk_count
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE dc.embedding IS NOT NULL
GROUP BY d.document_type;

-- Test semantic search
SELECT d.title, dc.chunk_text, 1 - (dc.embedding <=> query_embedding) as similarity
FROM document_chunks dc
JOIN documents d ON dc.document_id = d.id
WHERE (1 - (dc.embedding <=> query_embedding)) > 0.7
ORDER BY similarity DESC
LIMIT 10;
```

## Document Checksums (for verification)

After downloading, verify file integrity:

```bash
cd docs/reference
sha256sum -c checksums.txt
```

Expected checksums will be generated after first successful download.

## License & Usage

All NIST and DoD CMMC documents are **public domain** and freely available for use in compliance assessments.

- NIST Special Publications: Public domain (U.S. Government work)
- CMMC Documentation: Public domain (DoD published)
- No attribution required, but recommended for transparency

## Updates

Documents should be updated when new versions are released:

- **NIST SP 800-171**: Check https://csrc.nist.gov/publications
- **CMMC Documentation**: Check https://dodcio.defense.gov/CMMC/Documentation/

Last updated: 2024-11-16

## Troubleshooting

### "Access denied" when downloading

**Cause**: Government sites may block automated downloads or require browser access.

**Solution**:
1. Use manual download method (Option 2 above)
2. Try different browser or incognito mode
3. Verify URL is still valid (documents may move)

### PDF extraction fails

**Cause**: Some PDFs are image-based (scanned) or have complex formatting.

**Solution**:
1. Ensure `pdfplumber` is installed (better OCR support)
2. Use `--ocr` flag with ingestion script
3. Check PDF is not encrypted or password-protected

### Large file sizes

Some documents are large (>10MB). Ensure adequate:
- Disk space: ~200MB for all documents
- Memory: ~2GB for PDF processing
- Network bandwidth: ~100MB total download

## Support

For issues with documentation:
- **NIST**: https://csrc.nist.gov/about/contact-us
- **CMMC**: https://dodcio.defense.gov/CMMC/
- **Platform issues**: GitHub Issues
