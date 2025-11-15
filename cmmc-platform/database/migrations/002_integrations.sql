-- Integration Hub Schema
-- Tables for managing third-party integrations, webhooks, and API connectors

-- Integration Providers
CREATE TABLE integration_providers (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL, -- cloud, security, ticketing, sso, other
    description TEXT,
    logo_url VARCHAR(500),
    documentation_url VARCHAR(500),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Organization Integrations
CREATE TABLE organization_integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    provider_id VARCHAR(50) NOT NULL REFERENCES integration_providers(id),
    name VARCHAR(100) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'active', -- active, disabled, error, pending
    configuration JSONB NOT NULL DEFAULT '{}',
    credentials_encrypted TEXT, -- Encrypted credentials
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_sync_status VARCHAR(50),
    last_sync_error TEXT,
    sync_frequency_minutes INTEGER DEFAULT 60,
    auto_sync_enabled BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, provider_id, name)
);

CREATE INDEX idx_org_integrations_org ON organization_integrations(organization_id);
CREATE INDEX idx_org_integrations_provider ON organization_integrations(provider_id);
CREATE INDEX idx_org_integrations_status ON organization_integrations(status);

-- Webhooks
CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    url VARCHAR(500) NOT NULL,
    secret VARCHAR(100) NOT NULL,
    events TEXT[] NOT NULL, -- assessment.created, control.updated, etc.
    is_active BOOLEAN DEFAULT true,
    headers JSONB DEFAULT '{}',
    retry_count INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 30,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_webhooks_org ON webhooks(organization_id);
CREATE INDEX idx_webhooks_active ON webhooks(is_active);

-- Webhook Deliveries (for tracking)
CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    webhook_id UUID NOT NULL REFERENCES webhooks(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    response_status INTEGER,
    response_body TEXT,
    attempts INTEGER DEFAULT 1,
    delivered_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_webhook_deliveries_webhook ON webhook_deliveries(webhook_id);
CREATE INDEX idx_webhook_deliveries_created ON webhook_deliveries(created_at DESC);

-- API Keys (for external systems to access the platform)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    key_hash VARCHAR(256) NOT NULL UNIQUE,
    key_prefix VARCHAR(20) NOT NULL,
    permissions TEXT[] NOT NULL, -- read:assessments, write:controls, etc.
    rate_limit_per_minute INTEGER DEFAULT 100,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT true,
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_api_keys_org ON api_keys(organization_id);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON api_keys(is_active);

-- Cloud Resource Inventory (synced from cloud providers)
CREATE TABLE cloud_resources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    integration_id UUID NOT NULL REFERENCES organization_integrations(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL, -- aws, azure, gcp, google_cloud
    resource_type VARCHAR(100) NOT NULL, -- ec2, rds, storage, vm, etc.
    resource_id VARCHAR(500) NOT NULL,
    resource_name VARCHAR(500),
    region VARCHAR(100),
    tags JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    compliance_status VARCHAR(50), -- compliant, non_compliant, unknown
    last_scanned_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, provider, resource_id)
);

CREATE INDEX idx_cloud_resources_org ON cloud_resources(organization_id);
CREATE INDEX idx_cloud_resources_integration ON cloud_resources(integration_id);
CREATE INDEX idx_cloud_resources_provider ON cloud_resources(provider);
CREATE INDEX idx_cloud_resources_type ON cloud_resources(resource_type);

-- Security Tool Findings (from vulnerability scanners, SIEM, etc.)
CREATE TABLE security_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    integration_id UUID NOT NULL REFERENCES organization_integrations(id) ON DELETE CASCADE,
    finding_id VARCHAR(500) NOT NULL,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    severity VARCHAR(50) NOT NULL, -- critical, high, medium, low, info
    status VARCHAR(50) NOT NULL, -- open, resolved, acknowledged, false_positive
    affected_resource VARCHAR(500),
    cvss_score DECIMAL(3,1),
    cve_ids TEXT[],
    remediation TEXT,
    metadata JSONB DEFAULT '{}',
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(organization_id, integration_id, finding_id)
);

CREATE INDEX idx_security_findings_org ON security_findings(organization_id);
CREATE INDEX idx_security_findings_integration ON security_findings(integration_id);
CREATE INDEX idx_security_findings_severity ON security_findings(severity);
CREATE INDEX idx_security_findings_status ON security_findings(status);

-- Integration Sync Logs
CREATE TABLE integration_sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    integration_id UUID NOT NULL REFERENCES organization_integrations(id) ON DELETE CASCADE,
    sync_type VARCHAR(50) NOT NULL, -- full, incremental, manual
    status VARCHAR(50) NOT NULL, -- success, failed, partial
    items_synced INTEGER DEFAULT 0,
    items_failed INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER
);

CREATE INDEX idx_integration_sync_logs_integration ON integration_sync_logs(integration_id);
CREATE INDEX idx_integration_sync_logs_started ON integration_sync_logs(started_at DESC);

-- Insert default integration providers
INSERT INTO integration_providers (id, name, category, description) VALUES
('aws', 'Amazon Web Services', 'cloud', 'AWS cloud infrastructure and compliance data'),
('azure', 'Microsoft Azure', 'cloud', 'Azure cloud infrastructure and security posture'),
('gcp', 'Google Cloud Platform', 'cloud', 'GCP cloud resources and security findings'),
('google_workspace', 'Google Workspace', 'cloud', 'Google Workspace security and compliance'),
('microsoft_365', 'Microsoft 365', 'cloud', 'Microsoft 365 security and compliance features'),
('okta', 'Okta', 'sso', 'Single Sign-On and identity management'),
('azure_ad', 'Azure Active Directory', 'sso', 'Microsoft identity platform'),
('tenable', 'Tenable', 'security', 'Vulnerability scanning and assessment'),
('qualys', 'Qualys', 'security', 'Cloud security and compliance platform'),
('crowdstrike', 'CrowdStrike', 'security', 'Endpoint detection and response'),
('splunk', 'Splunk', 'security', 'Security information and event management'),
('jira', 'Jira', 'ticketing', 'Issue tracking and project management'),
('servicenow', 'ServiceNow', 'ticketing', 'IT service management'),
('slack', 'Slack', 'other', 'Team communication and notifications'),
('teams', 'Microsoft Teams', 'other', 'Collaboration and notifications');

COMMENT ON TABLE organization_integrations IS 'Third-party integrations configured by organizations';
COMMENT ON TABLE webhooks IS 'Outbound webhooks for real-time notifications';
COMMENT ON TABLE api_keys IS 'API keys for external systems to access the platform';
COMMENT ON TABLE cloud_resources IS 'Cloud resources synced from provider APIs';
COMMENT ON TABLE security_findings IS 'Security vulnerabilities and findings from scanning tools';
