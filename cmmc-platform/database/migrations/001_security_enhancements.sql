-- Security Enhancements Migration
-- Adds user session management, enhanced audit logging, and security features
-- Generated: 2025-11-16

-- ============================================================================
-- USER SESSION MANAGEMENT
-- ============================================================================

-- Create user_sessions table for session tracking and revocation
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,                    -- Session ID (token from secrets.token_urlsafe)
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    revoked_at TIMESTAMPTZ,
    ip_address TEXT,                        -- Optional: Track session IP
    user_agent TEXT,                        -- Optional: Track user agent
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),

    -- Indexes
    CONSTRAINT valid_expiry CHECK (expires_at > created_at)
);

-- Indexes for performance
CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_active ON user_sessions(active) WHERE active = TRUE;
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Auto-cleanup expired sessions (optional background job)
CREATE OR REPLACE FUNCTION cleanup_expired_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM user_sessions
    WHERE expires_at < NOW() - INTERVAL '7 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE user_sessions IS 'Tracks user sessions for JWT token revocation and security';
COMMENT ON FUNCTION cleanup_expired_sessions() IS 'Cleans up sessions expired more than 7 days ago';

-- ============================================================================
-- FAILED LOGIN ATTEMPTS TRACKING (Brute Force Protection)
-- ============================================================================

CREATE TABLE IF NOT EXISTS failed_login_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT NOT NULL,
    ip_address TEXT NOT NULL,
    attempted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_agent TEXT,
    reason TEXT                             -- 'invalid_password', 'user_not_found', etc.
);

-- Indexes
CREATE INDEX idx_failed_login_email ON failed_login_attempts(email);
CREATE INDEX idx_failed_login_ip ON failed_login_attempts(ip_address);
CREATE INDEX idx_failed_login_attempted_at ON failed_login_attempts(attempted_at);

-- Function to check if account should be locked
CREATE OR REPLACE FUNCTION check_account_lockout(
    p_email TEXT,
    p_window_minutes INTEGER DEFAULT 15,
    p_max_attempts INTEGER DEFAULT 5
)
RETURNS BOOLEAN AS $$
DECLARE
    attempt_count INTEGER;
BEGIN
    SELECT COUNT(*)
    INTO attempt_count
    FROM failed_login_attempts
    WHERE email = p_email
      AND attempted_at > NOW() - (p_window_minutes || ' minutes')::INTERVAL;

    RETURN attempt_count >= p_max_attempts;
END;
$$ LANGUAGE plpgsql;

-- Auto-cleanup old failed attempts
CREATE OR REPLACE FUNCTION cleanup_old_failed_attempts()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM failed_login_attempts
    WHERE attempted_at < NOW() - INTERVAL '30 days';

    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON TABLE failed_login_attempts IS 'Tracks failed login attempts for brute force protection';
COMMENT ON FUNCTION check_account_lockout IS 'Checks if account should be temporarily locked due to failed login attempts';

-- ============================================================================
-- ENHANCED AUDIT LOGGING
-- ============================================================================

-- Add columns to audit_log for better security tracking
ALTER TABLE audit_log
ADD COLUMN IF NOT EXISTS ip_address TEXT,
ADD COLUMN IF NOT EXISTS user_agent TEXT,
ADD COLUMN IF NOT EXISTS session_id TEXT;

-- Index for security investigations
CREATE INDEX IF NOT EXISTS idx_audit_log_ip_address ON audit_log(ip_address);
CREATE INDEX IF NOT EXISTS idx_audit_log_session_id ON audit_log(session_id);

-- ============================================================================
-- PASSWORD POLICY ENFORCEMENT
-- ============================================================================

-- Add password policy tracking to users table
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ DEFAULT NOW(),
ADD COLUMN IF NOT EXISTS password_expires_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS require_password_change BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS failed_login_count INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS locked_until TIMESTAMPTZ;

-- Function to validate password complexity
CREATE OR REPLACE FUNCTION validate_password_strength(password TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    -- Minimum 12 characters
    IF LENGTH(password) < 12 THEN
        RETURN FALSE;
    END IF;

    -- Must contain uppercase
    IF password !~ '[A-Z]' THEN
        RETURN FALSE;
    END IF;

    -- Must contain lowercase
    IF password !~ '[a-z]' THEN
        RETURN FALSE;
    END IF;

    -- Must contain digit
    IF password !~ '[0-9]' THEN
        RETURN FALSE;
    END IF;

    -- Must contain special character
    IF password !~ '[^A-Za-z0-9]' THEN
        RETURN FALSE;
    END IF;

    RETURN TRUE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION validate_password_strength IS 'Validates password meets complexity requirements (12+ chars, upper, lower, digit, special)';

-- ============================================================================
-- API KEY ENHANCEMENTS
-- ============================================================================

-- Add security fields to api_keys
ALTER TABLE api_keys
ADD COLUMN IF NOT EXISTS ip_whitelist TEXT[],      -- Optional IP whitelist
ADD COLUMN IF NOT EXISTS rate_limit_override INTEGER,  -- Optional custom rate limit
ADD COLUMN IF NOT EXISTS scopes TEXT[];             -- Optional permission scopes

-- Index for faster lookups
CREATE INDEX IF NOT EXISTS idx_api_keys_organization_active ON api_keys(organization_id, active) WHERE active = TRUE;

-- ============================================================================
-- SECURITY EVENTS LOG
-- ============================================================================

CREATE TABLE IF NOT EXISTS security_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type TEXT NOT NULL,               -- 'unauthorized_access', 'suspicious_activity', 'rate_limit_exceeded', etc.
    severity TEXT NOT NULL,                 -- 'low', 'medium', 'high', 'critical'
    user_id UUID REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    ip_address TEXT,
    user_agent TEXT,
    description TEXT NOT NULL,
    metadata JSONB,                         -- Additional context
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    resolved_by UUID REFERENCES users(id)
);

-- Indexes
CREATE INDEX idx_security_events_event_type ON security_events(event_type);
CREATE INDEX idx_security_events_severity ON security_events(severity);
CREATE INDEX idx_security_events_user_id ON security_events(user_id);
CREATE INDEX idx_security_events_org_id ON security_events(organization_id);
CREATE INDEX idx_security_events_created_at ON security_events(created_at);
CREATE INDEX idx_security_events_unresolved ON security_events(resolved) WHERE resolved = FALSE;

COMMENT ON TABLE security_events IS 'Centralized security event logging for monitoring and incident response';

-- ============================================================================
-- DATA ENCRYPTION TRACKING
-- ============================================================================

-- Track which data is encrypted at rest
CREATE TABLE IF NOT EXISTS encryption_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_name TEXT UNIQUE NOT NULL,
    key_type TEXT NOT NULL,                -- 'aes-256', 'rsa-4096', etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    rotated_at TIMESTAMPTZ,
    active BOOLEAN DEFAULT TRUE,
    metadata JSONB
);

COMMENT ON TABLE encryption_keys IS 'Tracks encryption keys for data encryption at rest (stores metadata only, not actual keys)';

-- ============================================================================
-- COMPLIANCE TRACKING
-- ============================================================================

-- Add compliance metadata to existing tables
ALTER TABLE evidence
ADD COLUMN IF NOT EXISTS encryption_key_id UUID REFERENCES encryption_keys(id),
ADD COLUMN IF NOT EXISTS data_classification TEXT DEFAULT 'internal',  -- 'public', 'internal', 'confidential', 'restricted'
ADD COLUMN IF NOT EXISTS retention_until TIMESTAMPTZ;

COMMENT ON COLUMN evidence.data_classification IS 'Data classification level per NIST 800-171';
COMMENT ON COLUMN evidence.retention_until IS 'Evidence retention date per compliance requirements (3 years for CMMC)';

-- ============================================================================
-- SECURITY GRANTS AND PERMISSIONS
-- ============================================================================

-- Ensure proper RLS (Row Level Security) is enabled
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;

-- RLS Policy for user_sessions (users can only see their own sessions)
DROP POLICY IF EXISTS user_sessions_isolation ON user_sessions;
CREATE POLICY user_sessions_isolation ON user_sessions
    FOR ALL
    USING (user_id::TEXT = current_setting('app.current_user_id', TRUE));

-- Grant usage on schemas
GRANT USAGE ON SCHEMA public TO cmmc_admin;

-- ============================================================================
-- INITIALIZATION
-- ============================================================================

-- Insert default encryption key metadata (actual key stored in secrets manager)
INSERT INTO encryption_keys (key_name, key_type, metadata)
VALUES ('minio-sse-key', 'aes-256', '{"purpose": "MinIO server-side encryption", "provider": "minio"}')
ON CONFLICT (key_name) DO NOTHING;

-- Log migration completion
DO $$
BEGIN
    INSERT INTO audit_log (table_name, operation, record_id, changed_data)
    VALUES ('migrations', 'execute', gen_random_uuid()::TEXT,
            jsonb_build_object(
                'migration', '001_security_enhancements',
                'timestamp', NOW()::TEXT,
                'description', 'Applied security enhancements: session management, brute force protection, enhanced audit logging'
            ));
END $$;

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Security enhancements migration completed successfully';
    RAISE NOTICE 'Added: user_sessions, failed_login_attempts, security_events, encryption_keys';
    RAISE NOTICE 'Enhanced: audit_log, users, api_keys, evidence';
END $$;
