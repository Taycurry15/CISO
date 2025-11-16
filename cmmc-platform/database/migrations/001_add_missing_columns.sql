-- Migration: Add missing columns to controls and evidence tables
-- Run this migration on existing databases to add compatibility columns

-- Add family and framework columns to controls table
ALTER TABLE controls ADD COLUMN IF NOT EXISTS family VARCHAR(10);
ALTER TABLE controls ADD COLUMN IF NOT EXISTS framework VARCHAR(50) DEFAULT 'NIST 800-171';

-- Update family column to match domain_id for existing records
UPDATE controls SET family = domain_id WHERE family IS NULL;

-- Add content column to evidence table
ALTER TABLE evidence ADD COLUMN IF NOT EXISTS content JSONB;

-- Add indexes for new columns
CREATE INDEX IF NOT EXISTS idx_controls_family ON controls(family);
CREATE INDEX IF NOT EXISTS idx_controls_framework ON controls(framework);

-- Add missing indexes for performance
CREATE INDEX IF NOT EXISTS idx_evidence_created_at ON evidence(created_at);
CREATE INDEX IF NOT EXISTS idx_evidence_updated_at ON evidence(updated_at);
CREATE INDEX IF NOT EXISTS idx_findings_created_at ON control_findings(created_at);
CREATE INDEX IF NOT EXISTS idx_findings_updated_at ON control_findings(updated_at);
CREATE INDEX IF NOT EXISTS idx_poam_created_at ON poam_items(created_at);
CREATE INDEX IF NOT EXISTS idx_poam_updated_at ON poam_items(updated_at);

-- Improve vector index configuration for better performance
DROP INDEX IF EXISTS document_chunks_embedding_idx;
CREATE INDEX document_chunks_embedding_idx ON document_chunks
    USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

COMMENT ON COLUMN controls.family IS 'Control family (duplicate of domain_id for query compatibility)';
COMMENT ON COLUMN controls.framework IS 'Framework identifier (NIST 800-171, CMMC, etc.)';
COMMENT ON COLUMN evidence.content IS 'Additional structured evidence content (logs, findings, etc.) in JSON format';
