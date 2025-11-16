-- CMMC Compliance Platform - Assessor-Grade Database Schema
-- Designed for immutable evidence, chain-of-custody, and CMMC L2/800-171A compliance

-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- ============================================================================
-- TENANCY & ORGANIZATIONS
-- ============================================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    duns_number VARCHAR(13),
    cage_code VARCHAR(5),
    cmmc_level INTEGER CHECK (cmmc_level IN (1, 2, 3)),
    target_certification_date DATE,
    organization_type VARCHAR(50), -- prime_contractor, subcontractor, osc, supplier
    current_authorization VARCHAR(100), -- FedRAMP, StateRAMP, etc.
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- admin, assessor, viewer, integration
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- CMMC FRAMEWORK & CONTROLS
-- ============================================================================

CREATE TABLE control_domains (
    id VARCHAR(10) PRIMARY KEY, -- AC, AU, AT, CM, etc.
    name VARCHAR(255) NOT NULL,
    description TEXT,
    cmmc_level INTEGER CHECK (cmmc_level IN (1, 2, 3))
);

CREATE TABLE controls (
    id VARCHAR(20) PRIMARY KEY, -- AC.L1-3.1.1, AC.L2-3.1.2, etc.
    domain_id VARCHAR(10) REFERENCES control_domains(id),
    family VARCHAR(10), -- Duplicate of domain_id for query compatibility (AC, AU, etc.)
    control_number VARCHAR(20) NOT NULL,
    title TEXT NOT NULL,
    nist_800_171_ref VARCHAR(20), -- 3.1.1, 3.1.2, etc.
    framework VARCHAR(50) DEFAULT 'NIST 800-171', -- Framework identifier
    cmmc_level INTEGER CHECK (cmmc_level IN (1, 2, 3)),
    requirement_text TEXT NOT NULL,
    discussion TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 800-171A Assessment Objectives (Examine/Interview/Test)
CREATE TABLE assessment_objectives (
    id VARCHAR(30) PRIMARY KEY, -- AC.L2-3.1.1[a], AC.L2-3.1.1[b], etc.
    control_id VARCHAR(20) REFERENCES controls(id),
    objective_letter VARCHAR(5) NOT NULL, -- [a], [b], [c], etc.
    method VARCHAR(20) NOT NULL CHECK (method IN ('Examine', 'Interview', 'Test')),
    determination_statement TEXT NOT NULL,
    potential_assessment_methods TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- ASSESSMENTS & SCOPING
-- ============================================================================

CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    cmmc_level INTEGER CHECK (cmmc_level IN (1, 2, 3)),
    assessment_type VARCHAR(50) NOT NULL, -- self, c3pao, surveillance
    status VARCHAR(50) NOT NULL, -- planning, in_progress, under_review, complete
    start_date DATE,
    target_completion_date DATE,
    lead_assessor_id UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE assessment_scope (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    asset_type VARCHAR(50) NOT NULL, -- system, network, facility, personnel
    asset_name VARCHAR(255) NOT NULL,
    asset_description TEXT,
    cui_present BOOLEAN DEFAULT FALSE,
    in_scope BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- PROVIDER INHERITANCE (M365, Azure, AWS, etc.)
-- ============================================================================

CREATE TABLE provider_offerings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_name VARCHAR(100) NOT NULL, -- M365 GCC High, Azure Government, AWS GovCloud
    offering_name VARCHAR(100) NOT NULL, -- E5, P2, etc.
    authorization_type VARCHAR(50), -- FedRAMP High, FedRAMP Moderate, etc.
    authorization_date DATE,
    authorization_expiry DATE,
    documentation_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE provider_control_inheritance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider_offering_id UUID REFERENCES provider_offerings(id) ON DELETE CASCADE,
    control_id VARCHAR(20) REFERENCES controls(id),
    objective_id VARCHAR(30) REFERENCES assessment_objectives(id),
    responsibility VARCHAR(50) NOT NULL CHECK (responsibility IN ('Inherited', 'Shared', 'Customer')),
    provider_narrative TEXT, -- What the provider does
    customer_narrative TEXT, -- What customer must do
    evidence_url TEXT, -- Link to provider's documentation
    last_verified_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- EVIDENCE MANAGEMENT (Immutable, Chain-of-Custody)
-- ============================================================================

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    control_id VARCHAR(20) REFERENCES controls(id),
    objective_id VARCHAR(30) REFERENCES assessment_objectives(id),

    -- Evidence metadata
    evidence_type VARCHAR(50) NOT NULL, -- document, screenshot, log, interview_notes, test_result, configuration
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content JSONB, -- Additional structured evidence content (logs, findings, etc.)
    method VARCHAR(20) CHECK (method IN ('Examine', 'Interview', 'Test')),

    -- Immutability & chain-of-custody
    file_path TEXT, -- Path to actual file in object storage
    file_hash VARCHAR(64) NOT NULL, -- SHA-256 hash of file
    file_size_bytes BIGINT,
    mime_type VARCHAR(100),

    -- Provenance
    collected_by UUID REFERENCES users(id),
    collected_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    collection_method VARCHAR(100), -- manual_upload, api_nessus, api_splunk, automated_screenshot

    -- Version control
    version INTEGER DEFAULT 1,
    supersedes_evidence_id UUID REFERENCES evidence(id), -- Link to previous version

    -- Status
    status VARCHAR(50) DEFAULT 'pending_review', -- pending_review, approved, rejected, superseded
    reviewed_by UUID REFERENCES users(id),
    reviewed_date TIMESTAMP WITH TIME ZONE,
    reviewer_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_file_hash UNIQUE (file_hash)
);

-- Evidence access log (chain-of-custody audit trail)
CREATE TABLE evidence_access_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evidence_id UUID REFERENCES evidence(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    action VARCHAR(50) NOT NULL, -- view, download, approve, reject, supersede
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- FINDINGS & DETERMINATIONS
-- ============================================================================

CREATE TABLE control_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    control_id VARCHAR(20) REFERENCES controls(id),
    objective_id VARCHAR(30) REFERENCES assessment_objectives(id),
    
    -- Assessment determination
    status VARCHAR(20) NOT NULL CHECK (status IN ('Met', 'Not Met', 'Partially Met', 'Not Applicable', 'Not Assessed')),
    assessor_narrative TEXT NOT NULL, -- Human-readable explanation
    
    -- AI-assisted analysis
    ai_generated BOOLEAN DEFAULT FALSE,
    ai_confidence_score DECIMAL(5,2), -- 0.00 to 100.00
    ai_rationale TEXT, -- Why AI made this determination
    ai_evidence_ids UUID[], -- Array of evidence IDs used by AI
    
    -- Human review
    human_reviewed BOOLEAN DEFAULT FALSE,
    human_override BOOLEAN DEFAULT FALSE, -- Did human change AI determination?
    reviewer_id UUID REFERENCES users(id),
    reviewed_date TIMESTAMP WITH TIME ZONE,
    reviewer_notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- PLAN OF ACTION & MILESTONES (POA&M)
-- ============================================================================

CREATE TABLE poam_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    control_id VARCHAR(20) REFERENCES controls(id),
    finding_id UUID REFERENCES control_findings(id),
    
    poam_id VARCHAR(50) NOT NULL, -- POA&M-001, POA&M-002, etc.
    weakness_description TEXT NOT NULL,
    risk_level VARCHAR(20) CHECK (risk_level IN ('Critical', 'High', 'Medium', 'Low')),
    
    -- Remediation plan
    remediation_plan TEXT NOT NULL,
    resources_required TEXT,
    milestones JSONB, -- Array of milestone objects: [{name, target_date, status}]
    
    -- Tracking
    status VARCHAR(50) DEFAULT 'open', -- open, in_progress, completed, risk_accepted
    assigned_to UUID REFERENCES users(id),
    estimated_completion_date DATE,
    actual_completion_date DATE,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- SYSTEM DIAGRAMS & GRAPH EXTRACTION
-- ============================================================================

CREATE TABLE system_diagrams (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    diagram_type VARCHAR(50), -- network, data_flow, logical, physical
    file_path TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    
    -- Graph extraction
    graph_extracted BOOLEAN DEFAULT FALSE,
    graph_data JSONB, -- Nodes and edges extracted from diagram
    extraction_confidence DECIMAL(5,2),
    
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Graph nodes (assets, systems, users, etc.)
CREATE TABLE graph_nodes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diagram_id UUID REFERENCES system_diagrams(id) ON DELETE CASCADE,
    node_type VARCHAR(50) NOT NULL, -- server, workstation, network, user, boundary, service
    label VARCHAR(255) NOT NULL,
    properties JSONB, -- Additional metadata
    position_x DECIMAL(10,2),
    position_y DECIMAL(10,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Graph edges (connections, data flows)
CREATE TABLE graph_edges (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    diagram_id UUID REFERENCES system_diagrams(id) ON DELETE CASCADE,
    source_node_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    target_node_id UUID REFERENCES graph_nodes(id) ON DELETE CASCADE,
    edge_type VARCHAR(50), -- data_flow, network_connection, trust_boundary
    label VARCHAR(255),
    properties JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- DOCUMENT CHUNKS & RAG (Retrieval-Augmented Generation)
-- ============================================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    document_type VARCHAR(50), -- policy, procedure, ssp, poam, manual, guide
    file_path TEXT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,
    uploaded_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    
    -- RAG metadata for targeted retrieval
    control_id VARCHAR(20) REFERENCES controls(id),
    objective_id VARCHAR(30) REFERENCES assessment_objectives(id),
    method VARCHAR(20) CHECK (method IN ('Examine', 'Interview', 'Test')),
    doc_type VARCHAR(50), -- policy, procedure, evidence, guide
    
    -- Vector embedding for semantic search
    embedding vector(1536), -- OpenAI ada-002 or similar
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    CONSTRAINT unique_chunk UNIQUE (document_id, chunk_index)
);

-- Index for vector similarity search
CREATE INDEX document_chunks_embedding_idx ON document_chunks USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- INTEGRATION LOGS
-- ============================================================================

CREATE TABLE integration_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_type VARCHAR(50) NOT NULL, -- nessus, splunk, azure, aws, m365
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL, -- running, success, failed
    records_processed INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    error_details JSONB,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE
);

-- ============================================================================
-- SCORING & METRICS
-- ============================================================================

CREATE TABLE sprs_scores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    score INTEGER CHECK (score >= -203 AND score <= 110), -- SPRS range: -203 to 110
    calculation_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    details JSONB -- Breakdown by control family
);

-- ============================================================================
-- AUTHENTICATION & API KEYS
-- ============================================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    key_hash VARCHAR(255) NOT NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    last_used_at TIMESTAMP WITH TIME ZONE,
    active BOOLEAN DEFAULT TRUE
);

-- ============================================================================
-- MONITORING & ALERTS
-- ============================================================================

CREATE TABLE alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- sprs_drop, new_high_findings, overdue_poam, etc.
    condition JSONB NOT NULL, -- Rule conditions (threshold, count, etc.)
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    rule_id UUID REFERENCES alert_rules(id),
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low', 'info')),
    message TEXT NOT NULL,
    details JSONB,
    status VARCHAR(50) DEFAULT 'active', -- active, acknowledged, resolved, dismissed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    acknowledged_at TIMESTAMP WITH TIME ZONE,
    acknowledged_by UUID REFERENCES users(id),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE integration_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    integration_type VARCHAR(50) NOT NULL, -- nessus, splunk, azure, aws, m365
    interval VARCHAR(20) NOT NULL CHECK (interval IN ('hourly', 'daily', 'weekly', 'monthly')),
    active BOOLEAN DEFAULT TRUE,
    last_run_at TIMESTAMP WITH TIME ZONE,
    next_run_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- ONBOARDING
-- ============================================================================

CREATE TABLE onboarding_workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_name VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'initiated',
    request_data JSONB,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE integration_credentials (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    integration_type VARCHAR(50) NOT NULL,
    credentials JSONB NOT NULL, -- Encrypted credentials
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- COMPLIANCE REPORTING
-- ============================================================================

CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL, -- weekly, monthly, quarterly, annual
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,
    summary JSONB NOT NULL,
    file_path TEXT,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_evidence_assessment ON evidence(assessment_id);
CREATE INDEX idx_evidence_control ON evidence(control_id);
CREATE INDEX idx_evidence_hash ON evidence(file_hash);
CREATE INDEX idx_evidence_status ON evidence(status);

CREATE INDEX idx_findings_assessment ON control_findings(assessment_id);
CREATE INDEX idx_findings_control ON control_findings(control_id);
CREATE INDEX idx_findings_status ON control_findings(status);

CREATE INDEX idx_poam_assessment ON poam_items(assessment_id);
CREATE INDEX idx_poam_status ON poam_items(status);

CREATE INDEX idx_doc_chunks_control ON document_chunks(control_id);
CREATE INDEX idx_doc_chunks_objective ON document_chunks(objective_id);

CREATE INDEX idx_provider_control ON provider_control_inheritance(control_id);
CREATE INDEX idx_provider_offering ON provider_control_inheritance(provider_offering_id);

-- ============================================================================
-- ROW LEVEL SECURITY (Multi-tenancy)
-- ============================================================================

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE control_findings ENABLE ROW LEVEL SECURITY;
ALTER TABLE poam_items ENABLE ROW LEVEL SECURITY;

-- RLS policies (example - expand based on user roles)
CREATE POLICY organization_isolation ON organizations
    FOR ALL TO authenticated
    USING (id = current_setting('app.current_organization_id')::UUID);

CREATE POLICY assessment_isolation ON assessments
    FOR ALL TO authenticated
    USING (organization_id = current_setting('app.current_organization_id')::UUID);

-- ============================================================================
-- AUDIT TRIGGERS
-- ============================================================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(20) NOT NULL, -- INSERT, UPDATE, DELETE
    old_data JSONB,
    new_data JSONB,
    user_id UUID,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Trigger function for audit logging
CREATE OR REPLACE FUNCTION audit_trigger_func() 
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log(table_name, record_id, action, old_data, user_id)
        VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD), current_setting('app.current_user_id', TRUE)::UUID);
        RETURN OLD;
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO audit_log(table_name, record_id, action, old_data, new_data, user_id)
        VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(OLD), row_to_json(NEW), current_setting('app.current_user_id', TRUE)::UUID);
        RETURN NEW;
    ELSIF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log(table_name, record_id, action, new_data, user_id)
        VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW), current_setting('app.current_user_id', TRUE)::UUID);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to critical tables
CREATE TRIGGER audit_evidence AFTER INSERT OR UPDATE OR DELETE ON evidence
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_findings AFTER INSERT OR UPDATE OR DELETE ON control_findings
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();

CREATE TRIGGER audit_poam AFTER INSERT OR UPDATE OR DELETE ON poam_items
    FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
