-- ============================================================================
-- CMMC Compliance Platform Database Schema
-- PostgreSQL 14+
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgvector for embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- Organizations (Multi-Tenant)
-- ============================================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    organization_type VARCHAR(50) NOT NULL, -- Enterprise, SMB, Consultant, C3PAO
    status VARCHAR(50) NOT NULL DEFAULT 'Trial', -- Active, Trial, Suspended, Inactive
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255)
);

CREATE INDEX idx_organizations_status ON organizations(status);
CREATE INDEX idx_organizations_type ON organizations(organization_type);

-- ============================================================================
-- Users & Authentication
-- ============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- Admin, Assessor, Auditor, Viewer
    status VARCHAR(50) NOT NULL DEFAULT 'Pending', -- Active, Inactive, Pending, Suspended
    phone VARCHAR(20),
    job_title VARCHAR(100),
    email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255)
);

CREATE INDEX idx_users_organization_id ON users(organization_id);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_role ON users(role);

-- ============================================================================
-- CMMC Controls (Master Data)
-- ============================================================================

CREATE TABLE cmmc_controls (
    id VARCHAR(50) PRIMARY KEY, -- e.g., "AC.L2-3.1.1"
    level INTEGER NOT NULL, -- 1, 2, or 3
    domain VARCHAR(50) NOT NULL, -- AC, AT, AU, CA, CM, IA, IR, MA, MP, PE, PS, RA, SA, SC, SI
    practice_id VARCHAR(50) NOT NULL, -- e.g., "3.1.1"
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    discussion TEXT,
    nist_control_id VARCHAR(50), -- Reference to NIST SP 800-171
    assessment_objectives TEXT[],
    examine_items TEXT[],
    interview_items TEXT[],
    test_items TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_controls_level ON cmmc_controls(level);
CREATE INDEX idx_controls_domain ON cmmc_controls(domain);
CREATE INDEX idx_controls_nist ON cmmc_controls(nist_control_id);

-- ============================================================================
-- Provider Inheritance (Master Data)
-- ============================================================================

CREATE TABLE provider_inheritance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    control_id VARCHAR(50) NOT NULL REFERENCES cmmc_controls(id),
    provider VARCHAR(50) NOT NULL, -- Microsoft365, Azure, AWS, GCP
    service VARCHAR(255) NOT NULL, -- e.g., "Exchange Online", "Azure AD"
    inheritance_type VARCHAR(50) NOT NULL, -- Inherited, Shared, Customer
    coverage_percentage INTEGER NOT NULL DEFAULT 0, -- 0-100
    configuration_required BOOLEAN DEFAULT FALSE,
    configuration_steps TEXT[],
    verification_steps TEXT[],
    documentation_url TEXT,
    last_verified TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_provider_inheritance_control ON provider_inheritance(control_id);
CREATE INDEX idx_provider_inheritance_provider ON provider_inheritance(provider);
CREATE INDEX idx_provider_inheritance_type ON provider_inheritance(inheritance_type);

-- ============================================================================
-- Assessments
-- ============================================================================

CREATE TABLE assessments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    assessment_type VARCHAR(50) NOT NULL, -- CMMC_L1, CMMC_L2, CMMC_L3, NIST_171
    target_level INTEGER NOT NULL DEFAULT 2,
    status VARCHAR(50) NOT NULL DEFAULT 'Draft', -- Draft, Scoping, In Progress, Review, Completed, Archived

    -- Scope
    scope_domains TEXT[], -- Domains in scope (or 'all')
    scope_cloud_providers TEXT[], -- Cloud providers in use
    scope_systems TEXT[], -- Systems in scope
    scope_locations TEXT[], -- Physical locations

    -- Dates
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    target_completion_date TIMESTAMP WITH TIME ZONE,

    -- Metadata
    lead_assessor_id UUID REFERENCES users(id),
    assigned_users UUID[], -- Array of user IDs
    tags TEXT[],

    -- Progress tracking
    total_controls INTEGER DEFAULT 0,
    controls_met INTEGER DEFAULT 0,
    controls_not_met INTEGER DEFAULT 0,
    controls_partial INTEGER DEFAULT 0,
    controls_na INTEGER DEFAULT 0,
    completion_percentage INTEGER DEFAULT 0,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_assessments_organization_id ON assessments(organization_id);
CREATE INDEX idx_assessments_status ON assessments(status);
CREATE INDEX idx_assessments_type ON assessments(assessment_type);
CREATE INDEX idx_assessments_lead_assessor ON assessments(lead_assessor_id);
CREATE INDEX idx_assessments_created_at ON assessments(created_at DESC);

-- ============================================================================
-- Control Findings (Assessment Results)
-- ============================================================================

CREATE TABLE control_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    control_id VARCHAR(50) NOT NULL REFERENCES cmmc_controls(id),

    -- Finding details
    status VARCHAR(50) NOT NULL DEFAULT 'Not Started', -- Not Started, In Progress, Met, Not Met, Partially Met, Not Applicable
    implementation_status VARCHAR(50), -- Implemented, Partially Implemented, Planned, Not Implemented

    -- Narratives
    implementation_narrative TEXT,
    test_results TEXT,
    findings TEXT,
    recommendations TEXT,

    -- Evidence linkage
    evidence_ids UUID[], -- Array of evidence IDs

    -- Provider inheritance
    uses_provider_inheritance BOOLEAN DEFAULT FALSE,
    provider_inheritance_id UUID REFERENCES provider_inheritance(id),
    provider_notes TEXT,

    -- AI Analysis
    ai_generated_narrative TEXT,
    ai_confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    ai_analysis_date TIMESTAMP WITH TIME ZONE,
    ai_reviewed BOOLEAN DEFAULT FALSE,

    -- Assessment methods (800-171A)
    examine_completed BOOLEAN DEFAULT FALSE,
    interview_completed BOOLEAN DEFAULT FALSE,
    test_completed BOOLEAN DEFAULT FALSE,

    -- Risk assessment
    risk_level VARCHAR(50), -- Critical, High, Moderate, Low
    residual_risk TEXT,

    -- Tracking
    assigned_to UUID REFERENCES users(id),
    last_reviewed_by UUID REFERENCES users(id),
    last_reviewed_at TIMESTAMP WITH TIME ZONE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_control_findings_assessment ON control_findings(assessment_id);
CREATE INDEX idx_control_findings_control ON control_findings(control_id);
CREATE INDEX idx_control_findings_status ON control_findings(status);
CREATE INDEX idx_control_findings_assigned_to ON control_findings(assigned_to);
CREATE UNIQUE INDEX idx_control_findings_unique ON control_findings(assessment_id, control_id);

-- ============================================================================
-- Evidence
-- ============================================================================

CREATE TABLE evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- File metadata
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_type VARCHAR(100) NOT NULL,
    mime_type VARCHAR(100),
    file_hash VARCHAR(64), -- SHA-256

    -- Evidence metadata
    title VARCHAR(255) NOT NULL,
    description TEXT,
    evidence_type VARCHAR(50) NOT NULL, -- Policy, Procedure, Configuration, Screenshot, Log, Scan, Certificate, Training, Other
    assessment_method VARCHAR(50), -- Examine, Interview, Test

    -- Tagging & categorization
    control_ids VARCHAR(50)[], -- Array of control IDs this evidence supports
    tags TEXT[],

    -- Collection info
    collection_date TIMESTAMP WITH TIME ZONE,
    collected_by UUID REFERENCES users(id),

    -- Document processing
    extracted_text TEXT,
    embedding vector(3072), -- OpenAI embedding dimension

    -- Status
    status VARCHAR(50) DEFAULT 'Active', -- Active, Archived, Deleted

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_evidence_assessment ON evidence(assessment_id);
CREATE INDEX idx_evidence_organization ON evidence(organization_id);
CREATE INDEX idx_evidence_type ON evidence(evidence_type);
CREATE INDEX idx_evidence_status ON evidence(status);
CREATE INDEX idx_evidence_control_ids ON evidence USING GIN(control_ids);
CREATE INDEX idx_evidence_embedding ON evidence USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- Documents (For RAG System)
-- ============================================================================

CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Document metadata
    title VARCHAR(255) NOT NULL,
    description TEXT,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    document_type VARCHAR(50) NOT NULL, -- Policy, Standard, Guideline, Procedure, Template, Reference

    -- Content
    content TEXT, -- Extracted text
    embedding vector(3072), -- Document-level embedding

    -- Categorization
    category VARCHAR(100),
    tags TEXT[],
    control_ids VARCHAR(50)[], -- Related controls

    -- Version control
    version VARCHAR(50),
    is_current_version BOOLEAN DEFAULT TRUE,

    -- Status
    status VARCHAR(50) DEFAULT 'Active', -- Active, Archived, Superseded

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_documents_organization ON documents(organization_id);
CREATE INDEX idx_documents_type ON documents(document_type);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_embedding ON documents USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- Document Chunks (For RAG System)
-- ============================================================================

CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,

    -- Chunk metadata
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(3072),

    -- Position in document
    page_number INTEGER,
    section VARCHAR(255),

    -- Metadata
    char_count INTEGER,
    token_count INTEGER,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_embedding ON document_chunks USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- AI Analysis Results
-- ============================================================================

CREATE TABLE ai_analysis_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    control_id VARCHAR(50) NOT NULL REFERENCES cmmc_controls(id),

    -- Analysis details
    analysis_type VARCHAR(50) NOT NULL, -- ControlNarrative, EvidenceReview, GapAnalysis, RiskAssessment
    prompt_used TEXT,
    model_used VARCHAR(100), -- e.g., "gpt-4-turbo", "claude-3-opus"

    -- Results
    result_text TEXT,
    confidence_score DECIMAL(3,2), -- 0.00 to 1.00
    reasoning TEXT,

    -- Factors influencing confidence
    evidence_quality_score DECIMAL(3,2),
    evidence_quantity_score DECIMAL(3,2),
    evidence_recency_score DECIMAL(3,2),
    provider_inheritance_score DECIMAL(3,2),

    -- Evidence used
    evidence_ids UUID[],
    document_chunks_used UUID[],

    -- Metadata
    tokens_used INTEGER,
    cost_usd DECIMAL(10,4),
    processing_time_ms INTEGER,

    -- Review
    reviewed BOOLEAN DEFAULT FALSE,
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_ai_results_assessment ON ai_analysis_results(assessment_id);
CREATE INDEX idx_ai_results_control ON ai_analysis_results(control_id);
CREATE INDEX idx_ai_results_type ON ai_analysis_results(analysis_type);
CREATE INDEX idx_ai_results_created_at ON ai_analysis_results(created_at DESC);

-- ============================================================================
-- Audit Logs
-- ============================================================================

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,

    -- Actor
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    user_email VARCHAR(255),
    user_role VARCHAR(50),

    -- Action
    action VARCHAR(100) NOT NULL, -- create, update, delete, login, logout, etc.
    resource_type VARCHAR(100) NOT NULL, -- assessment, evidence, user, etc.
    resource_id UUID,

    -- Details
    description TEXT NOT NULL,
    changes JSONB, -- Before/after values
    metadata JSONB, -- Additional context

    -- Request context
    ip_address INET,
    user_agent TEXT,
    request_method VARCHAR(10),
    request_path TEXT,

    -- Result
    status VARCHAR(50), -- success, failure, error
    error_message TEXT,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_organization ON audit_logs(organization_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ============================================================================
-- Comments & Collaboration
-- ============================================================================

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Parent resource
    resource_type VARCHAR(100) NOT NULL, -- assessment, control_finding, evidence
    resource_id UUID NOT NULL,

    -- Comment details
    content TEXT NOT NULL,
    mentions UUID[], -- Array of mentioned user IDs

    -- Threading
    parent_comment_id UUID REFERENCES comments(id) ON DELETE CASCADE,
    thread_depth INTEGER DEFAULT 0,

    -- Status
    is_edited BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID NOT NULL REFERENCES users(id)
);

CREATE INDEX idx_comments_organization ON comments(organization_id);
CREATE INDEX idx_comments_resource ON comments(resource_type, resource_id);
CREATE INDEX idx_comments_parent ON comments(parent_comment_id);
CREATE INDEX idx_comments_created_by ON comments(created_by);
CREATE INDEX idx_comments_created_at ON comments(created_at DESC);

-- ============================================================================
-- Notifications
-- ============================================================================

CREATE TABLE notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Notification details
    type VARCHAR(100) NOT NULL, -- assessment_assigned, comment_mention, deadline_reminder, etc.
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,

    -- Related resource
    resource_type VARCHAR(100),
    resource_id UUID,
    resource_url TEXT,

    -- Status
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE,

    -- Delivery
    sent_via VARCHAR(50)[], -- Array: in_app, email, slack
    email_sent BOOLEAN DEFAULT FALSE,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_organization ON notifications(organization_id);
CREATE INDEX idx_notifications_is_read ON notifications(is_read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);

-- ============================================================================
-- POA&M Items (Plan of Action & Milestones)
-- ============================================================================

CREATE TABLE poam_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    assessment_id UUID NOT NULL REFERENCES assessments(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    control_id VARCHAR(50) NOT NULL REFERENCES cmmc_controls(id),

    -- Finding details
    weakness_description TEXT NOT NULL,
    risk_level VARCHAR(50) NOT NULL, -- Critical, High, Moderate, Low
    impact VARCHAR(50), -- Very High, High, Moderate, Low
    likelihood VARCHAR(50), -- Very High, High, Moderate, Low

    -- Remediation
    remediation_plan TEXT NOT NULL,
    resources_required TEXT,
    estimated_cost DECIMAL(12,2),

    -- Milestones
    milestone_date DATE NOT NULL,
    scheduled_completion_date DATE NOT NULL,
    actual_completion_date DATE,

    -- Status tracking
    status VARCHAR(50) NOT NULL DEFAULT 'Open', -- Open, In Progress, Completed, Risk Accepted, False Positive
    percent_complete INTEGER DEFAULT 0,

    -- Assignment
    assigned_to UUID REFERENCES users(id),
    point_of_contact VARCHAR(255),

    -- External tracking
    external_tracking_id VARCHAR(100), -- For Jira, ServiceNow, etc.

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_poam_assessment ON poam_items(assessment_id);
CREATE INDEX idx_poam_organization ON poam_items(organization_id);
CREATE INDEX idx_poam_control ON poam_items(control_id);
CREATE INDEX idx_poam_status ON poam_items(status);
CREATE INDEX idx_poam_assigned_to ON poam_items(assigned_to);
CREATE INDEX idx_poam_milestone_date ON poam_items(milestone_date);

-- ============================================================================
-- System Configuration
-- ============================================================================

CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    is_encrypted BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_by UUID REFERENCES users(id)
);

-- ============================================================================
-- Functions & Triggers
-- ============================================================================

-- Update updated_at timestamp automatically
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON organizations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_assessments_updated_at BEFORE UPDATE ON assessments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_control_findings_updated_at BEFORE UPDATE ON control_findings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_evidence_updated_at BEFORE UPDATE ON evidence FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_poam_items_updated_at BEFORE UPDATE ON poam_items FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_comments_updated_at BEFORE UPDATE ON comments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Views
-- ============================================================================

-- Assessment Summary View
CREATE OR REPLACE VIEW assessment_summary AS
SELECT
    a.id,
    a.organization_id,
    a.name,
    a.status,
    a.assessment_type,
    a.target_level,
    a.start_date,
    a.end_date,
    a.lead_assessor_id,
    u.full_name as lead_assessor_name,
    a.total_controls,
    a.controls_met,
    a.controls_not_met,
    a.controls_partial,
    a.controls_na,
    a.completion_percentage,
    CASE
        WHEN a.total_controls > 0 THEN
            ROUND((a.controls_met::DECIMAL / a.total_controls) * 100, 2)
        ELSE 0
    END as compliance_percentage,
    COUNT(DISTINCT e.id) as evidence_count,
    COUNT(DISTINCT cf.id) as findings_count,
    a.created_at,
    a.updated_at
FROM assessments a
LEFT JOIN users u ON a.lead_assessor_id = u.id
LEFT JOIN evidence e ON a.id = e.assessment_id AND e.status = 'Active'
LEFT JOIN control_findings cf ON a.id = cf.assessment_id
GROUP BY a.id, u.full_name;

-- Control Compliance View
CREATE OR REPLACE VIEW control_compliance AS
SELECT
    c.id as control_id,
    c.domain,
    c.level,
    c.title,
    COUNT(DISTINCT cf.id) as total_findings,
    COUNT(DISTINCT CASE WHEN cf.status = 'Met' THEN cf.id END) as met_count,
    COUNT(DISTINCT CASE WHEN cf.status = 'Not Met' THEN cf.id END) as not_met_count,
    COUNT(DISTINCT CASE WHEN cf.status = 'Partially Met' THEN cf.id END) as partial_count,
    AVG(cf.ai_confidence_score) as avg_confidence_score,
    COUNT(DISTINCT e.id) as total_evidence
FROM cmmc_controls c
LEFT JOIN control_findings cf ON c.id = cf.control_id
LEFT JOIN evidence e ON c.id = ANY(e.control_ids)
GROUP BY c.id, c.domain, c.level, c.title;

-- ============================================================================
-- Grants (Example - adjust per your user setup)
-- ============================================================================

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cmmc_app;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cmmc_app;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO cmmc_app;
