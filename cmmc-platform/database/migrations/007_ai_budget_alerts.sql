-- AI Budget Alerts Migration
-- Configurable budget limits and automated alerts

-- AI Budget Settings Table
-- Defines spending limits and alert thresholds
CREATE TABLE IF NOT EXISTS ai_budget_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Scope
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,

    -- Budget Configuration
    budget_period VARCHAR(20) NOT NULL DEFAULT 'monthly',  -- 'daily', 'weekly', 'monthly', 'assessment'
    budget_limit_usd DECIMAL(10, 2) NOT NULL,              -- Maximum allowed spend

    -- Alert Thresholds (percentages)
    warning_threshold_percent INTEGER NOT NULL DEFAULT 75,  -- Warning at 75%
    critical_threshold_percent INTEGER NOT NULL DEFAULT 90, -- Critical at 90%

    -- Alert Channels
    email_alerts_enabled BOOLEAN DEFAULT true,
    slack_webhook_url VARCHAR(500),
    webhook_url VARCHAR(500),                               -- Custom webhook for alerts

    -- Enforcement
    block_at_limit BOOLEAN DEFAULT false,                   -- Block AI operations when limit reached

    -- Assessment-specific (optional)
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,

    -- Metadata
    created_by UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_budget_period CHECK (
        budget_period IN ('daily', 'weekly', 'monthly', 'assessment')
    ),
    CONSTRAINT positive_budget CHECK (budget_limit_usd > 0),
    CONSTRAINT valid_warning_threshold CHECK (
        warning_threshold_percent > 0 AND warning_threshold_percent <= 100
    ),
    CONSTRAINT valid_critical_threshold CHECK (
        critical_threshold_percent > 0 AND critical_threshold_percent <= 100
    ),
    CONSTRAINT warning_before_critical CHECK (
        warning_threshold_percent < critical_threshold_percent
    ),
    -- Either org-wide or assessment-specific, not both
    CONSTRAINT budget_scope CHECK (
        (assessment_id IS NULL) OR
        (assessment_id IS NOT NULL AND budget_period = 'assessment')
    )
);

-- AI Budget Alerts Table
-- History of all budget alerts triggered
CREATE TABLE IF NOT EXISTS ai_budget_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Relationships
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    budget_setting_id UUID REFERENCES ai_budget_settings(id) ON DELETE SET NULL,
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,

    -- Alert Details
    alert_level VARCHAR(20) NOT NULL,                      -- 'warning', 'critical', 'limit_reached'
    budget_period VARCHAR(20) NOT NULL,                    -- Which period triggered the alert

    -- Spending Information
    current_spend_usd DECIMAL(10, 6) NOT NULL,
    budget_limit_usd DECIMAL(10, 2) NOT NULL,
    percent_used DECIMAL(5, 2) NOT NULL,                   -- Percentage of budget used

    -- Time Period
    period_start TIMESTAMP WITH TIME ZONE NOT NULL,
    period_end TIMESTAMP WITH TIME ZONE NOT NULL,

    -- Alert Status
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_by UUID REFERENCES users(id) ON DELETE SET NULL,
    acknowledged_at TIMESTAMP WITH TIME ZONE,

    -- Notification Status
    notification_sent BOOLEAN DEFAULT false,
    notification_channels JSONB DEFAULT '[]',              -- ['email', 'slack', 'webhook']
    notification_error TEXT,

    -- Metadata
    metadata JSONB DEFAULT '{}',                           -- Additional context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Constraints
    CONSTRAINT valid_alert_level CHECK (
        alert_level IN ('warning', 'critical', 'limit_reached', 'resolved')
    ),
    CONSTRAINT positive_spend CHECK (current_spend_usd >= 0),
    CONSTRAINT valid_percent CHECK (percent_used >= 0 AND percent_used <= 200)
);

-- Indexes for efficient querying
CREATE INDEX idx_budget_settings_org ON ai_budget_settings(organization_id);
CREATE INDEX idx_budget_settings_assessment ON ai_budget_settings(assessment_id) WHERE assessment_id IS NOT NULL;
CREATE INDEX idx_budget_settings_active ON ai_budget_settings(organization_id) WHERE budget_limit_usd > 0;

CREATE INDEX idx_budget_alerts_org ON ai_budget_alerts(organization_id);
CREATE INDEX idx_budget_alerts_created ON ai_budget_alerts(created_at DESC);
CREATE INDEX idx_budget_alerts_unacknowledged ON ai_budget_alerts(organization_id) WHERE acknowledged = false;
CREATE INDEX idx_budget_alerts_level ON ai_budget_alerts(alert_level, created_at DESC);

-- Function to get current period spending
CREATE OR REPLACE FUNCTION get_period_spending(
    p_organization_id UUID,
    p_budget_period VARCHAR(20),
    p_assessment_id UUID DEFAULT NULL
) RETURNS DECIMAL AS $
DECLARE
    period_start TIMESTAMP WITH TIME ZONE;
    period_end TIMESTAMP WITH TIME ZONE;
    total_spend DECIMAL(10, 6);
BEGIN
    -- Calculate period boundaries
    period_end := NOW();

    CASE p_budget_period
        WHEN 'daily' THEN
            period_start := DATE_TRUNC('day', NOW());
        WHEN 'weekly' THEN
            period_start := DATE_TRUNC('week', NOW());
        WHEN 'monthly' THEN
            period_start := DATE_TRUNC('month', NOW());
        WHEN 'assessment' THEN
            -- For assessment budgets, get all spending for that assessment
            IF p_assessment_id IS NULL THEN
                RAISE EXCEPTION 'assessment_id required for assessment budget period';
            END IF;
            period_start := (
                SELECT MIN(created_at)
                FROM ai_usage
                WHERE assessment_id = p_assessment_id
            );
            IF period_start IS NULL THEN
                period_start := NOW();
            END IF;
        ELSE
            RAISE EXCEPTION 'Invalid budget period: %', p_budget_period;
    END CASE;

    -- Calculate spending
    IF p_budget_period = 'assessment' AND p_assessment_id IS NOT NULL THEN
        SELECT COALESCE(SUM(cost_usd), 0)
        INTO total_spend
        FROM ai_usage
        WHERE organization_id = p_organization_id
          AND assessment_id = p_assessment_id;
    ELSE
        SELECT COALESCE(SUM(cost_usd), 0)
        INTO total_spend
        FROM ai_usage
        WHERE organization_id = p_organization_id
          AND created_at >= period_start
          AND created_at <= period_end;
    END IF;

    RETURN total_spend;
END;
$ LANGUAGE plpgsql;

-- Function to check and trigger budget alerts
CREATE OR REPLACE FUNCTION check_budget_alerts(
    p_organization_id UUID,
    p_assessment_id UUID DEFAULT NULL
) RETURNS TABLE(
    alert_triggered BOOLEAN,
    alert_level VARCHAR(20),
    percent_used DECIMAL(5, 2),
    current_spend DECIMAL(10, 6),
    budget_limit DECIMAL(10, 2)
) AS $
DECLARE
    budget_record RECORD;
    current_spending DECIMAL(10, 6);
    usage_percent DECIMAL(5, 2);
    period_start TIMESTAMP WITH TIME ZONE;
    period_end TIMESTAMP WITH TIME ZONE;
    alert_exists BOOLEAN;
BEGIN
    -- Get active budget settings
    FOR budget_record IN
        SELECT * FROM ai_budget_settings
        WHERE organization_id = p_organization_id
          AND (
              (p_assessment_id IS NULL AND assessment_id IS NULL) OR
              (p_assessment_id IS NOT NULL AND assessment_id = p_assessment_id)
          )
          AND budget_limit_usd > 0
    LOOP
        -- Get current spending for this period
        current_spending := get_period_spending(
            p_organization_id,
            budget_record.budget_period,
            budget_record.assessment_id
        );

        -- Calculate percentage used
        usage_percent := (current_spending / budget_record.budget_limit_usd) * 100;

        -- Calculate period boundaries for alert record
        period_end := NOW();
        CASE budget_record.budget_period
            WHEN 'daily' THEN period_start := DATE_TRUNC('day', NOW());
            WHEN 'weekly' THEN period_start := DATE_TRUNC('week', NOW());
            WHEN 'monthly' THEN period_start := DATE_TRUNC('month', NOW());
            WHEN 'assessment' THEN
                period_start := (
                    SELECT MIN(created_at) FROM ai_usage
                    WHERE assessment_id = budget_record.assessment_id
                );
        END CASE;

        -- Check if alert already exists for this period
        SELECT EXISTS(
            SELECT 1 FROM ai_budget_alerts
            WHERE budget_setting_id = budget_record.id
              AND period_start = period_start
              AND alert_level != 'resolved'
              AND created_at >= period_start
        ) INTO alert_exists;

        -- Trigger alerts based on thresholds (only if no existing alert)
        IF NOT alert_exists THEN
            -- Critical threshold reached
            IF usage_percent >= budget_record.critical_threshold_percent THEN
                INSERT INTO ai_budget_alerts (
                    organization_id,
                    budget_setting_id,
                    assessment_id,
                    alert_level,
                    budget_period,
                    current_spend_usd,
                    budget_limit_usd,
                    percent_used,
                    period_start,
                    period_end
                ) VALUES (
                    p_organization_id,
                    budget_record.id,
                    budget_record.assessment_id,
                    'critical',
                    budget_record.budget_period,
                    current_spending,
                    budget_record.budget_limit_usd,
                    usage_percent,
                    period_start,
                    period_end
                );

                RETURN QUERY SELECT true, 'critical'::VARCHAR(20), usage_percent, current_spending, budget_record.budget_limit_usd;

            -- Warning threshold reached
            ELSIF usage_percent >= budget_record.warning_threshold_percent THEN
                INSERT INTO ai_budget_alerts (
                    organization_id,
                    budget_setting_id,
                    assessment_id,
                    alert_level,
                    budget_period,
                    current_spend_usd,
                    budget_limit_usd,
                    percent_used,
                    period_start,
                    period_end
                ) VALUES (
                    p_organization_id,
                    budget_record.id,
                    budget_record.assessment_id,
                    'warning',
                    budget_record.budget_period,
                    current_spending,
                    budget_record.budget_limit_usd,
                    usage_percent,
                    period_start,
                    period_end
                );

                RETURN QUERY SELECT true, 'warning'::VARCHAR(20), usage_percent, current_spending, budget_record.budget_limit_usd;
            END IF;
        END IF;

        -- Check if limit reached (always check, even if alert exists)
        IF usage_percent >= 100 AND budget_record.block_at_limit THEN
            RETURN QUERY SELECT true, 'limit_reached'::VARCHAR(20), usage_percent, current_spending, budget_record.budget_limit_usd;
        END IF;
    END LOOP;

    -- No alerts triggered
    RETURN QUERY SELECT false, NULL::VARCHAR(20), 0::DECIMAL(5, 2), 0::DECIMAL(10, 6), 0::DECIMAL(10, 2);
END;
$ LANGUAGE plpgsql;

-- Auto-update timestamp trigger
CREATE OR REPLACE FUNCTION update_budget_settings_timestamp()
RETURNS TRIGGER AS $
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$ LANGUAGE plpgsql;

CREATE TRIGGER budget_settings_updated
    BEFORE UPDATE ON ai_budget_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_budget_settings_timestamp();

-- Comments for documentation
COMMENT ON TABLE ai_budget_settings IS 'AI spending budget limits and alert configuration per organization or assessment';
COMMENT ON TABLE ai_budget_alerts IS 'History of budget alerts triggered when spending thresholds are reached';
COMMENT ON FUNCTION get_period_spending IS 'Calculate total AI spending for a given period (daily/weekly/monthly/assessment)';
COMMENT ON FUNCTION check_budget_alerts IS 'Check current spending against budgets and trigger alerts if thresholds are exceeded';

-- Grant permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ai_budget_settings TO cmmc_api;
GRANT SELECT, INSERT, UPDATE ON ai_budget_alerts TO cmmc_api;
GRANT EXECUTE ON FUNCTION get_period_spending TO cmmc_api;
GRANT EXECUTE ON FUNCTION check_budget_alerts TO cmmc_api;

-- Sample data (for testing)
-- Uncomment to insert sample budget settings
/*
INSERT INTO ai_budget_settings (
    organization_id,
    budget_period,
    budget_limit_usd,
    warning_threshold_percent,
    critical_threshold_percent,
    email_alerts_enabled,
    block_at_limit
) VALUES (
    (SELECT id FROM organizations LIMIT 1),
    'monthly',
    100.00,
    75,
    90,
    true,
    false
);
*/

-- Verification
DO $
DECLARE
    settings_exists BOOLEAN;
    alerts_exists BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'ai_budget_settings'
    ) INTO settings_exists;

    SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'ai_budget_alerts'
    ) INTO alerts_exists;

    IF settings_exists AND alerts_exists THEN
        RAISE NOTICE 'AI budget alerts migration completed successfully';
    ELSE
        RAISE EXCEPTION 'Budget tables were not created';
    END IF;
END $;
