-- ============================================================================
-- Human-in-the-Loop (HITL) Review Workflow
-- ============================================================================
-- Tracks AI-generated content requiring human validation and approval
-- Supports multi-level review, comments, version history, and audit trails

-- Review request statuses
CREATE TYPE review_status AS ENUM (
    'pending',           -- Waiting for reviewer assignment
    'assigned',          -- Assigned to reviewer(s)
    'in_review',         -- Actively being reviewed
    'needs_revision',    -- Rejected with feedback, needs AI re-generation
    'approved',          -- Approved by reviewer
    'rejected',          -- Permanently rejected
    'cancelled'          -- Review cancelled
);

-- Types of content that can be reviewed
CREATE TYPE review_item_type AS ENUM (
    'control_assessment',    -- AI assessment of a control
    'gap_analysis',          -- Gap analysis results
    'recommendation',        -- AI-generated recommendation
    'ssp_section',          -- SSP document section
    'poam_item',            -- POA&M item
    'evidence_analysis',    -- Evidence document analysis
    'report_finding',       -- Report finding or conclusion
    'cost_forecast'         -- Cost forecast/estimate
);

-- Review priority levels
CREATE TYPE review_priority AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

-- Review decision types
CREATE TYPE review_decision AS ENUM (
    'approve',
    'approve_with_changes',
    'request_revision',
    'reject'
);

-- ============================================================================
-- Main review requests table
-- ============================================================================
CREATE TABLE review_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    assessment_id UUID REFERENCES assessments(id) ON DELETE CASCADE,

    -- Item being reviewed
    item_type review_item_type NOT NULL,
    item_id VARCHAR(255) NOT NULL,  -- ID of the item (control_id, document_id, etc.)
    item_name VARCHAR(500),          -- Human-readable name

    -- AI-generated content
    ai_generated_content JSONB NOT NULL,  -- The AI output to be reviewed
    ai_confidence_score DECIMAL(5, 4),    -- AI confidence (0-1)
    ai_model_version VARCHAR(100),        -- Model used for generation
    ai_generation_date TIMESTAMPTZ,       -- When AI generated this

    -- Original/reference content for comparison
    reference_content JSONB,              -- Previous version or reference data
    context_data JSONB,                   -- Additional context for reviewer

    -- Review metadata
    status review_status DEFAULT 'pending',
    priority review_priority DEFAULT 'medium',
    required_reviewers INTEGER DEFAULT 1, -- How many approvals needed
    approved_count INTEGER DEFAULT 0,      -- How many have approved

    -- Assignment
    assigned_to UUID[],                   -- Array of user IDs assigned
    assigned_at TIMESTAMPTZ,
    assigned_by UUID REFERENCES users(id),

    -- Timing
    requested_by UUID NOT NULL REFERENCES users(id),
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    due_date TIMESTAMPTZ,

    -- Final decision
    final_decision review_decision,
    final_decision_by UUID REFERENCES users(id),
    final_decision_at TIMESTAMPTZ,
    final_decision_notes TEXT,

    -- Version tracking
    version INTEGER DEFAULT 1,            -- Version of this review
    parent_review_id UUID REFERENCES review_requests(id), -- If this is a revision

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_review_item UNIQUE (item_type, item_id, version)
);

-- Indexes for review requests
CREATE INDEX idx_review_requests_org ON review_requests(organization_id);
CREATE INDEX idx_review_requests_assessment ON review_requests(assessment_id);
CREATE INDEX idx_review_requests_status ON review_requests(status);
CREATE INDEX idx_review_requests_item ON review_requests(item_type, item_id);
CREATE INDEX idx_review_requests_assigned ON review_requests USING GIN(assigned_to);
CREATE INDEX idx_review_requests_requested_by ON review_requests(requested_by);
CREATE INDEX idx_review_requests_due_date ON review_requests(due_date) WHERE status IN ('pending', 'assigned', 'in_review');

-- ============================================================================
-- Individual reviews (one per reviewer)
-- ============================================================================
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_request_id UUID NOT NULL REFERENCES review_requests(id) ON DELETE CASCADE,

    -- Reviewer
    reviewer_id UUID NOT NULL REFERENCES users(id),
    reviewer_role VARCHAR(100),          -- Role at time of review

    -- Review details
    decision review_decision NOT NULL,
    confidence_level VARCHAR(50),        -- How confident is the reviewer
    time_spent_minutes INTEGER,          -- Time spent on review

    -- Feedback
    overall_feedback TEXT,
    detailed_feedback JSONB,             -- Structured feedback by section
    suggested_changes JSONB,             -- Specific change suggestions

    -- Ratings (optional)
    accuracy_rating INTEGER CHECK (accuracy_rating BETWEEN 1 AND 5),
    completeness_rating INTEGER CHECK (completeness_rating BETWEEN 1 AND 5),
    quality_rating INTEGER CHECK (quality_rating BETWEEN 1 AND 5),

    -- Metadata
    started_at TIMESTAMPTZ DEFAULT NOW(),
    submitted_at TIMESTAMPTZ DEFAULT NOW(),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT unique_reviewer_per_request UNIQUE (review_request_id, reviewer_id)
);

-- Indexes for reviews
CREATE INDEX idx_reviews_request ON reviews(review_request_id);
CREATE INDEX idx_reviews_reviewer ON reviews(reviewer_id);
CREATE INDEX idx_reviews_decision ON reviews(decision);
CREATE INDEX idx_reviews_submitted ON reviews(submitted_at);

-- ============================================================================
-- Review comments and discussion
-- ============================================================================
CREATE TABLE review_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_request_id UUID NOT NULL REFERENCES review_requests(id) ON DELETE CASCADE,
    review_id UUID REFERENCES reviews(id) ON DELETE CASCADE,

    -- Comment details
    user_id UUID NOT NULL REFERENCES users(id),
    comment_text TEXT NOT NULL,

    -- Threading
    parent_comment_id UUID REFERENCES review_comments(id) ON DELETE CASCADE,
    thread_id UUID,                      -- Root comment ID for threading

    -- Highlighting specific content
    highlighted_section VARCHAR(255),    -- Section of content being discussed
    highlighted_text TEXT,               -- Specific text being discussed

    -- Metadata
    is_internal BOOLEAN DEFAULT false,   -- Internal team comment vs shared with AI
    is_resolved BOOLEAN DEFAULT false,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for comments
CREATE INDEX idx_review_comments_request ON review_comments(review_request_id);
CREATE INDEX idx_review_comments_review ON review_comments(review_id);
CREATE INDEX idx_review_comments_user ON review_comments(user_id);
CREATE INDEX idx_review_comments_thread ON review_comments(thread_id);
CREATE INDEX idx_review_comments_parent ON review_comments(parent_comment_id);

-- ============================================================================
-- Review workflow history and audit trail
-- ============================================================================
CREATE TABLE review_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    review_request_id UUID NOT NULL REFERENCES review_requests(id) ON DELETE CASCADE,

    -- Event details
    event_type VARCHAR(100) NOT NULL,    -- 'created', 'assigned', 'status_changed', etc.
    event_data JSONB,                    -- Event-specific data

    -- Who and when
    user_id UUID REFERENCES users(id),
    user_name VARCHAR(255),
    user_role VARCHAR(100),

    -- Old and new values
    old_value JSONB,
    new_value JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for history
CREATE INDEX idx_review_history_request ON review_history(review_request_id);
CREATE INDEX idx_review_history_event ON review_history(event_type);
CREATE INDEX idx_review_history_user ON review_history(user_id);
CREATE INDEX idx_review_history_created ON review_history(created_at);

-- ============================================================================
-- Review metrics and analytics
-- ============================================================================
CREATE MATERIALIZED VIEW review_metrics AS
SELECT
    organization_id,
    item_type,
    status,
    priority,
    DATE_TRUNC('day', requested_at) AS request_date,
    COUNT(*) AS request_count,
    COUNT(*) FILTER (WHERE final_decision = 'approve') AS approved_count,
    COUNT(*) FILTER (WHERE final_decision = 'reject') AS rejected_count,
    COUNT(*) FILTER (WHERE final_decision = 'request_revision') AS revision_count,
    AVG(EXTRACT(EPOCH FROM (final_decision_at - requested_at)) / 3600)::DECIMAL(10, 2) AS avg_review_hours,
    AVG(ai_confidence_score) AS avg_ai_confidence,
    COUNT(*) FILTER (WHERE final_decision_at > due_date) AS overdue_count
FROM review_requests
WHERE requested_at >= NOW() - INTERVAL '90 days'
GROUP BY organization_id, item_type, status, priority, DATE_TRUNC('day', requested_at);

-- Index for metrics view
CREATE INDEX idx_review_metrics_org ON review_metrics(organization_id);
CREATE INDEX idx_review_metrics_date ON review_metrics(request_date);

-- ============================================================================
-- Functions and triggers
-- ============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_review_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER review_requests_updated_at
    BEFORE UPDATE ON review_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_review_updated_at();

CREATE TRIGGER reviews_updated_at
    BEFORE UPDATE ON reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_review_updated_at();

CREATE TRIGGER review_comments_updated_at
    BEFORE UPDATE ON review_comments
    FOR EACH ROW
    EXECUTE FUNCTION update_review_updated_at();

-- Auto-populate thread_id for top-level comments
CREATE OR REPLACE FUNCTION set_comment_thread_id()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.parent_comment_id IS NULL THEN
        NEW.thread_id = NEW.id;
    ELSE
        SELECT thread_id INTO NEW.thread_id
        FROM review_comments
        WHERE id = NEW.parent_comment_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER set_thread_id
    BEFORE INSERT ON review_comments
    FOR EACH ROW
    EXECUTE FUNCTION set_comment_thread_id();

-- Log review history on status changes
CREATE OR REPLACE FUNCTION log_review_status_change()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        INSERT INTO review_history (
            review_request_id,
            event_type,
            event_data,
            old_value,
            new_value
        ) VALUES (
            NEW.id,
            'status_changed',
            jsonb_build_object(
                'from', OLD.status,
                'to', NEW.status
            ),
            to_jsonb(OLD.status),
            to_jsonb(NEW.status)
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER log_status_changes
    AFTER UPDATE ON review_requests
    FOR EACH ROW
    EXECUTE FUNCTION log_review_status_change();

-- Update approved count when reviews are submitted
CREATE OR REPLACE FUNCTION update_review_approved_count()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.decision IN ('approve', 'approve_with_changes') THEN
        UPDATE review_requests
        SET approved_count = approved_count + 1
        WHERE id = NEW.review_request_id;

        -- Auto-approve if all required reviews are in
        UPDATE review_requests
        SET status = 'approved',
            final_decision = 'approve',
            final_decision_at = NOW()
        WHERE id = NEW.review_request_id
          AND approved_count >= required_reviewers
          AND status != 'approved';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_approved_count
    AFTER INSERT ON reviews
    FOR EACH ROW
    EXECUTE FUNCTION update_review_approved_count();

-- ============================================================================
-- Helper functions for review management
-- ============================================================================

-- Get pending reviews for a user
CREATE OR REPLACE FUNCTION get_user_pending_reviews(p_user_id UUID)
RETURNS TABLE (
    review_request_id UUID,
    item_type review_item_type,
    item_name VARCHAR,
    priority review_priority,
    requested_at TIMESTAMPTZ,
    due_date TIMESTAMPTZ,
    is_overdue BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        rr.id,
        rr.item_type,
        rr.item_name,
        rr.priority,
        rr.requested_at,
        rr.due_date,
        (rr.due_date IS NOT NULL AND rr.due_date < NOW()) AS is_overdue
    FROM review_requests rr
    WHERE p_user_id = ANY(rr.assigned_to)
      AND rr.status IN ('assigned', 'in_review')
      AND NOT EXISTS (
          SELECT 1 FROM reviews r
          WHERE r.review_request_id = rr.id
            AND r.reviewer_id = p_user_id
      )
    ORDER BY
        CASE rr.priority
            WHEN 'critical' THEN 1
            WHEN 'high' THEN 2
            WHEN 'medium' THEN 3
            WHEN 'low' THEN 4
        END,
        rr.due_date NULLS LAST,
        rr.requested_at;
END;
$$ LANGUAGE plpgsql;

-- Get review statistics for organization
CREATE OR REPLACE FUNCTION get_organization_review_stats(
    p_organization_id UUID,
    p_start_date TIMESTAMPTZ DEFAULT NOW() - INTERVAL '30 days',
    p_end_date TIMESTAMPTZ DEFAULT NOW()
)
RETURNS TABLE (
    total_reviews INTEGER,
    pending_reviews INTEGER,
    approved_reviews INTEGER,
    rejected_reviews INTEGER,
    avg_review_time_hours DECIMAL,
    overdue_reviews INTEGER,
    ai_accuracy_rate DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::INTEGER AS total_reviews,
        COUNT(*) FILTER (WHERE status IN ('pending', 'assigned', 'in_review'))::INTEGER AS pending_reviews,
        COUNT(*) FILTER (WHERE final_decision = 'approve')::INTEGER AS approved_reviews,
        COUNT(*) FILTER (WHERE final_decision IN ('reject', 'request_revision'))::INTEGER AS rejected_reviews,
        AVG(EXTRACT(EPOCH FROM (final_decision_at - requested_at)) / 3600)::DECIMAL(10, 2) AS avg_review_time_hours,
        COUNT(*) FILTER (WHERE due_date < NOW() AND status IN ('pending', 'assigned', 'in_review'))::INTEGER AS overdue_reviews,
        (COUNT(*) FILTER (WHERE final_decision = 'approve')::DECIMAL / NULLIF(COUNT(*) FILTER (WHERE final_decision IS NOT NULL), 0) * 100)::DECIMAL(5, 2) AS ai_accuracy_rate
    FROM review_requests
    WHERE organization_id = p_organization_id
      AND requested_at BETWEEN p_start_date AND p_end_date;
END;
$$ LANGUAGE plpgsql;

-- Assign reviewer to review request
CREATE OR REPLACE FUNCTION assign_reviewer(
    p_review_request_id UUID,
    p_reviewer_id UUID,
    p_assigned_by UUID
)
RETURNS VOID AS $$
BEGIN
    UPDATE review_requests
    SET
        assigned_to = array_append(assigned_to, p_reviewer_id),
        assigned_at = NOW(),
        assigned_by = p_assigned_by,
        status = CASE
            WHEN status = 'pending' THEN 'assigned'::review_status
            ELSE status
        END
    WHERE id = p_review_request_id
      AND NOT (p_reviewer_id = ANY(assigned_to));

    -- Log the assignment
    INSERT INTO review_history (
        review_request_id,
        event_type,
        event_data,
        user_id
    ) VALUES (
        p_review_request_id,
        'reviewer_assigned',
        jsonb_build_object('reviewer_id', p_reviewer_id),
        p_assigned_by
    );
END;
$$ LANGUAGE plpgsql;

-- Refresh materialized view
CREATE OR REPLACE FUNCTION refresh_review_metrics()
RETURNS VOID AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY review_metrics;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Sample data and comments
-- ============================================================================

COMMENT ON TABLE review_requests IS 'Human-in-the-loop review requests for AI-generated content';
COMMENT ON TABLE reviews IS 'Individual reviewer responses and feedback';
COMMENT ON TABLE review_comments IS 'Discussion threads and comments on review items';
COMMENT ON TABLE review_history IS 'Audit trail of all review workflow events';
COMMENT ON COLUMN review_requests.ai_generated_content IS 'The AI output requiring validation';
COMMENT ON COLUMN review_requests.required_reviewers IS 'Number of approvals needed before auto-approval';
COMMENT ON COLUMN reviews.detailed_feedback IS 'Structured feedback organized by section or field';
COMMENT ON COLUMN reviews.suggested_changes IS 'Specific edits or modifications suggested by reviewer';
