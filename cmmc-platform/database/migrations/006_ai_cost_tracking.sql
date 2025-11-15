-- AI Cost Tracking Migration
-- Tracks token usage and costs for all AI operations

-- AI Usage Table
-- Records every AI API call for cost tracking and analytics
CREATE TABLE IF NOT EXISTS ai_usage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,
    control_id VARCHAR(50) REFERENCES cmmc_controls(id) ON DELETE SET NULL,
    document_id UUID REFERENCES documents(id) ON DELETE SET NULL,

    -- Operation Details
    operation_type VARCHAR(50) NOT NULL,  -- 'embedding', 'analysis', 'rag_query', 'document_processing'
    model_name VARCHAR(100) NOT NULL,     -- 'text-embedding-3-small', 'gpt-4-turbo-preview', etc.
    provider VARCHAR(50) NOT NULL,        -- 'openai', 'anthropic'

    -- Token Usage
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER NOT NULL,

    -- Cost Calculation
    cost_usd DECIMAL(10, 6) NOT NULL,     -- Cost in USD (6 decimal places for precision)

    -- Request Details (for debugging and auditing)
    request_id VARCHAR(255),               -- Provider's request ID
    response_time_ms INTEGER,              -- Response time in milliseconds

    -- Metadata
    metadata JSONB DEFAULT '{}',           -- Additional context (e.g., query text, chunk count)

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT positive_tokens CHECK (total_tokens >= 0),
    CONSTRAINT positive_cost CHECK (cost_usd >= 0),
    CONSTRAINT valid_operation CHECK (
        operation_type IN ('embedding', 'analysis', 'rag_query', 'document_processing', 'chat', 'other')
    ),
    CONSTRAINT valid_provider CHECK (
        provider IN ('openai', 'anthropic', 'other')
    )
);

-- Indexes for efficient querying
CREATE INDEX idx_ai_usage_organization ON ai_usage(organization_id);
CREATE INDEX idx_ai_usage_user ON ai_usage(user_id);
CREATE INDEX idx_ai_usage_assessment ON ai_usage(assessment_id) WHERE assessment_id IS NOT NULL;
CREATE INDEX idx_ai_usage_control ON ai_usage(control_id) WHERE control_id IS NOT NULL;
CREATE INDEX idx_ai_usage_created_at ON ai_usage(created_at DESC);
CREATE INDEX idx_ai_usage_operation_type ON ai_usage(operation_type);
CREATE INDEX idx_ai_usage_model ON ai_usage(model_name);

-- Composite index for common queries
CREATE INDEX idx_ai_usage_org_date ON ai_usage(organization_id, created_at DESC);
CREATE INDEX idx_ai_usage_assessment_operation ON ai_usage(assessment_id, operation_type) WHERE assessment_id IS NOT NULL;

-- Materialized view for daily cost summaries (for performance)
CREATE MATERIALIZED VIEW ai_cost_daily_summary AS
SELECT
    organization_id,
    DATE(created_at) as usage_date,
    operation_type,
    model_name,
    provider,
    COUNT(*) as operation_count,
    SUM(total_tokens) as total_tokens,
    SUM(cost_usd) as total_cost_usd,
    AVG(response_time_ms) as avg_response_time_ms
FROM ai_usage
GROUP BY organization_id, DATE(created_at), operation_type, model_name, provider;

-- Index for materialized view
CREATE UNIQUE INDEX idx_ai_cost_daily_summary_unique
ON ai_cost_daily_summary(organization_id, usage_date, operation_type, model_name, provider);
CREATE INDEX idx_ai_cost_daily_summary_org ON ai_cost_daily_summary(organization_id, usage_date DESC);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_ai_cost_daily_summary()
RETURNS void AS $
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY ai_cost_daily_summary;
END;
$ LANGUAGE plpgsql;

-- Comments for documentation
COMMENT ON TABLE ai_usage IS 'Tracks all AI API calls for cost monitoring and analytics';
COMMENT ON COLUMN ai_usage.operation_type IS 'Type of AI operation: embedding, analysis, rag_query, etc.';
COMMENT ON COLUMN ai_usage.cost_usd IS 'Cost in USD with 6 decimal precision (e.g., $0.000123)';
COMMENT ON COLUMN ai_usage.metadata IS 'Additional context about the operation (JSON)';
COMMENT ON MATERIALIZED VIEW ai_cost_daily_summary IS 'Daily aggregated AI costs per organization';

-- Grant permissions
GRANT SELECT, INSERT ON ai_usage TO cmmc_api;
GRANT SELECT ON ai_cost_daily_summary TO cmmc_api;
GRANT EXECUTE ON FUNCTION refresh_ai_cost_daily_summary() TO cmmc_api;

-- Sample data (for testing)
-- Uncomment to insert sample usage records
/*
INSERT INTO ai_usage (
    organization_id,
    user_id,
    assessment_id,
    operation_type,
    model_name,
    provider,
    total_tokens,
    cost_usd,
    metadata
) VALUES (
    (SELECT id FROM organizations LIMIT 1),
    (SELECT id FROM users LIMIT 1),
    (SELECT id FROM assessments LIMIT 1),
    'embedding',
    'text-embedding-3-small',
    'openai',
    75,
    0.000002,
    '{"text_length": 312, "dimension": 1536}'
);
*/

-- Verification
DO $
DECLARE
    table_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'ai_usage'
    ) INTO table_exists;

    IF table_exists THEN
        RAISE NOTICE 'AI cost tracking migration completed successfully';
    ELSE
        RAISE EXCEPTION 'AI usage table was not created';
    END IF;
END $;
