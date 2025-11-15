"""
Human-in-the-Loop (HITL) Review Service
Manages review workflow for AI-generated content requiring human validation
"""

import asyncpg
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)


class ReviewStatus(str, Enum):
    """Review request statuses"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    NEEDS_REVISION = "needs_revision"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ReviewItemType(str, Enum):
    """Types of items that can be reviewed"""
    CONTROL_ASSESSMENT = "control_assessment"
    GAP_ANALYSIS = "gap_analysis"
    RECOMMENDATION = "recommendation"
    SSP_SECTION = "ssp_section"
    POAM_ITEM = "poam_item"
    EVIDENCE_ANALYSIS = "evidence_analysis"
    REPORT_FINDING = "report_finding"
    COST_FORECAST = "cost_forecast"


class ReviewPriority(str, Enum):
    """Review priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ReviewDecision(str, Enum):
    """Review decision types"""
    APPROVE = "approve"
    APPROVE_WITH_CHANGES = "approve_with_changes"
    REQUEST_REVISION = "request_revision"
    REJECT = "reject"


class HITLReviewService:
    """Service for managing human-in-the-loop review workflows"""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    # ========================================================================
    # Review Request Management
    # ========================================================================

    async def create_review_request(
        self,
        organization_id: str,
        requested_by: str,
        item_type: ReviewItemType,
        item_id: str,
        ai_generated_content: Dict[str, Any],
        item_name: Optional[str] = None,
        assessment_id: Optional[str] = None,
        reference_content: Optional[Dict[str, Any]] = None,
        context_data: Optional[Dict[str, Any]] = None,
        ai_confidence_score: Optional[float] = None,
        ai_model_version: Optional[str] = None,
        priority: ReviewPriority = ReviewPriority.MEDIUM,
        required_reviewers: int = 1,
        assigned_to: Optional[List[str]] = None,
        due_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Create a new review request for AI-generated content

        Args:
            organization_id: Organization ID
            requested_by: User ID who requested the review
            item_type: Type of item being reviewed
            item_id: ID of the item
            ai_generated_content: The AI output to review
            item_name: Human-readable name
            assessment_id: Optional assessment ID
            reference_content: Previous version or reference data
            context_data: Additional context for reviewers
            ai_confidence_score: AI's confidence in its output (0-1)
            ai_model_version: Model version used
            priority: Review priority
            required_reviewers: Number of approvals needed
            assigned_to: List of user IDs to assign
            due_date: When review should be completed

        Returns:
            Created review request
        """
        async with self.db_pool.acquire() as conn:
            # Check if there's already a pending review for this item
            existing = await conn.fetchrow(
                """
                SELECT id FROM review_requests
                WHERE item_type = $1 AND item_id = $2
                  AND status IN ('pending', 'assigned', 'in_review')
                ORDER BY version DESC
                LIMIT 1
                """,
                item_type.value,
                item_id,
            )

            if existing:
                logger.warning(
                    f"Review already exists for {item_type}:{item_id}: {existing['id']}"
                )
                return await self.get_review_request(str(existing["id"]))

            # Determine initial status
            initial_status = ReviewStatus.ASSIGNED if assigned_to else ReviewStatus.PENDING

            # Create review request
            review = await conn.fetchrow(
                """
                INSERT INTO review_requests (
                    organization_id,
                    assessment_id,
                    item_type,
                    item_id,
                    item_name,
                    ai_generated_content,
                    ai_confidence_score,
                    ai_model_version,
                    ai_generation_date,
                    reference_content,
                    context_data,
                    status,
                    priority,
                    required_reviewers,
                    assigned_to,
                    requested_by,
                    due_date
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), $9, $10, $11, $12, $13, $14, $15, $16)
                RETURNING *
                """,
                organization_id,
                assessment_id,
                item_type.value,
                item_id,
                item_name or f"{item_type.value}_{item_id}",
                ai_generated_content,
                ai_confidence_score,
                ai_model_version,
                reference_content,
                context_data,
                initial_status.value,
                priority.value,
                required_reviewers,
                assigned_to or [],
                requested_by,
                due_date,
            )

            # Log creation event
            await self._log_event(
                conn,
                str(review["id"]),
                "created",
                {"priority": priority.value, "required_reviewers": required_reviewers},
                requested_by,
            )

            # If assigned, log assignment events
            if assigned_to:
                for reviewer_id in assigned_to:
                    await self._log_event(
                        conn,
                        str(review["id"]),
                        "reviewer_assigned",
                        {"reviewer_id": reviewer_id},
                        requested_by,
                    )

            logger.info(f"Created review request {review['id']} for {item_type}:{item_id}")
            return dict(review)

    async def get_review_request(self, review_request_id: str) -> Dict[str, Any]:
        """Get a review request by ID"""
        async with self.db_pool.acquire() as conn:
            review = await conn.fetchrow(
                "SELECT * FROM review_requests WHERE id = $1", review_request_id
            )
            if not review:
                raise ValueError(f"Review request {review_request_id} not found")
            return dict(review)

    async def get_review_requests(
        self,
        organization_id: str,
        status: Optional[ReviewStatus] = None,
        item_type: Optional[ReviewItemType] = None,
        assessment_id: Optional[str] = None,
        assigned_to: Optional[str] = None,
        priority: Optional[ReviewPriority] = None,
        overdue_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get review requests with filters

        Args:
            organization_id: Organization ID
            status: Filter by status
            item_type: Filter by item type
            assessment_id: Filter by assessment
            assigned_to: Filter by assigned user
            priority: Filter by priority
            overdue_only: Only show overdue reviews
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of review requests
        """
        conditions = ["organization_id = $1"]
        params: List[Any] = [organization_id]
        param_idx = 2

        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status.value)
            param_idx += 1

        if item_type:
            conditions.append(f"item_type = ${param_idx}")
            params.append(item_type.value)
            param_idx += 1

        if assessment_id:
            conditions.append(f"assessment_id = ${param_idx}")
            params.append(assessment_id)
            param_idx += 1

        if assigned_to:
            conditions.append(f"${param_idx} = ANY(assigned_to)")
            params.append(assigned_to)
            param_idx += 1

        if priority:
            conditions.append(f"priority = ${param_idx}")
            params.append(priority.value)
            param_idx += 1

        if overdue_only:
            conditions.append("due_date < NOW()")
            conditions.append("status IN ('pending', 'assigned', 'in_review')")

        where_clause = " AND ".join(conditions)

        query = f"""
            SELECT * FROM review_requests
            WHERE {where_clause}
            ORDER BY
                CASE priority
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                END,
                due_date NULLS LAST,
                requested_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]

    async def assign_reviewers(
        self,
        review_request_id: str,
        reviewer_ids: List[str],
        assigned_by: str,
    ) -> Dict[str, Any]:
        """
        Assign reviewers to a review request

        Args:
            review_request_id: Review request ID
            reviewer_ids: List of user IDs to assign
            assigned_by: User ID performing the assignment

        Returns:
            Updated review request
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Get current review
                review = await conn.fetchrow(
                    "SELECT * FROM review_requests WHERE id = $1", review_request_id
                )
                if not review:
                    raise ValueError(f"Review request {review_request_id} not found")

                # Add new reviewers
                current_reviewers = set(review["assigned_to"] or [])
                new_reviewers = [r for r in reviewer_ids if r not in current_reviewers]

                if not new_reviewers:
                    logger.info("No new reviewers to assign")
                    return dict(review)

                updated_reviewers = list(current_reviewers.union(set(reviewer_ids)))

                # Update review request
                updated = await conn.fetchrow(
                    """
                    UPDATE review_requests
                    SET assigned_to = $1,
                        assigned_at = NOW(),
                        assigned_by = $2,
                        status = CASE
                            WHEN status = 'pending' THEN 'assigned'::review_status
                            ELSE status
                        END,
                        updated_at = NOW()
                    WHERE id = $3
                    RETURNING *
                    """,
                    updated_reviewers,
                    assigned_by,
                    review_request_id,
                )

                # Log assignment events
                for reviewer_id in new_reviewers:
                    await self._log_event(
                        conn,
                        review_request_id,
                        "reviewer_assigned",
                        {"reviewer_id": reviewer_id},
                        assigned_by,
                    )

                logger.info(
                    f"Assigned {len(new_reviewers)} reviewers to {review_request_id}"
                )
                return dict(updated)

    async def update_review_status(
        self,
        review_request_id: str,
        new_status: ReviewStatus,
        user_id: str,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Update review request status"""
        async with self.db_pool.acquire() as conn:
            updated = await conn.fetchrow(
                """
                UPDATE review_requests
                SET status = $1, updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                new_status.value,
                review_request_id,
            )

            if not updated:
                raise ValueError(f"Review request {review_request_id} not found")

            await self._log_event(
                conn,
                review_request_id,
                "status_changed",
                {"new_status": new_status.value, "notes": notes},
                user_id,
            )

            return dict(updated)

    # ========================================================================
    # Review Submission
    # ========================================================================

    async def submit_review(
        self,
        review_request_id: str,
        reviewer_id: str,
        decision: ReviewDecision,
        overall_feedback: Optional[str] = None,
        detailed_feedback: Optional[Dict[str, Any]] = None,
        suggested_changes: Optional[Dict[str, Any]] = None,
        accuracy_rating: Optional[int] = None,
        completeness_rating: Optional[int] = None,
        quality_rating: Optional[int] = None,
        time_spent_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Submit a review for a review request

        Args:
            review_request_id: Review request ID
            reviewer_id: User ID of reviewer
            decision: Review decision
            overall_feedback: General feedback text
            detailed_feedback: Structured feedback by section
            suggested_changes: Specific change suggestions
            accuracy_rating: Rating 1-5
            completeness_rating: Rating 1-5
            quality_rating: Rating 1-5
            time_spent_minutes: Time spent on review

        Returns:
            Created review
        """
        async with self.db_pool.acquire() as conn:
            async with conn.transaction():
                # Verify review request exists
                review_request = await conn.fetchrow(
                    "SELECT * FROM review_requests WHERE id = $1", review_request_id
                )
                if not review_request:
                    raise ValueError(f"Review request {review_request_id} not found")

                # Check if reviewer is assigned
                if reviewer_id not in (review_request["assigned_to"] or []):
                    raise ValueError(
                        f"User {reviewer_id} is not assigned to this review"
                    )

                # Check if already reviewed
                existing = await conn.fetchrow(
                    """
                    SELECT id FROM reviews
                    WHERE review_request_id = $1 AND reviewer_id = $2
                    """,
                    review_request_id,
                    reviewer_id,
                )
                if existing:
                    raise ValueError(
                        f"User {reviewer_id} has already submitted a review"
                    )

                # Create review
                review = await conn.fetchrow(
                    """
                    INSERT INTO reviews (
                        review_request_id,
                        reviewer_id,
                        decision,
                        overall_feedback,
                        detailed_feedback,
                        suggested_changes,
                        accuracy_rating,
                        completeness_rating,
                        quality_rating,
                        time_spent_minutes
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                    RETURNING *
                    """,
                    review_request_id,
                    reviewer_id,
                    decision.value,
                    overall_feedback,
                    detailed_feedback,
                    suggested_changes,
                    accuracy_rating,
                    completeness_rating,
                    quality_rating,
                    time_spent_minutes,
                )

                # Update review request status based on decision
                new_status = None
                if decision == ReviewDecision.REQUEST_REVISION:
                    new_status = ReviewStatus.NEEDS_REVISION
                elif decision == ReviewDecision.REJECT:
                    new_status = ReviewStatus.REJECTED

                if new_status:
                    await conn.execute(
                        """
                        UPDATE review_requests
                        SET status = $1,
                            final_decision = $2,
                            final_decision_by = $3,
                            final_decision_at = NOW(),
                            final_decision_notes = $4,
                            updated_at = NOW()
                        WHERE id = $5
                        """,
                        new_status.value,
                        decision.value,
                        reviewer_id,
                        overall_feedback,
                        review_request_id,
                    )
                else:
                    # Just update status to in_review
                    await conn.execute(
                        """
                        UPDATE review_requests
                        SET status = 'in_review',
                            updated_at = NOW()
                        WHERE id = $1 AND status = 'assigned'
                        """,
                        review_request_id,
                    )

                # Log review submission
                await self._log_event(
                    conn,
                    review_request_id,
                    "review_submitted",
                    {"decision": decision.value, "reviewer_id": reviewer_id},
                    reviewer_id,
                )

                logger.info(
                    f"Review submitted for {review_request_id} by {reviewer_id}: {decision.value}"
                )
                return dict(review)

    async def get_reviews_for_request(
        self, review_request_id: str
    ) -> List[Dict[str, Any]]:
        """Get all reviews for a review request"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT r.*, u.name as reviewer_name, u.email as reviewer_email
                FROM reviews r
                LEFT JOIN users u ON r.reviewer_id = u.id
                WHERE r.review_request_id = $1
                ORDER BY r.submitted_at DESC
                """,
                review_request_id,
            )
            return [dict(row) for row in rows]

    # ========================================================================
    # Comments and Discussion
    # ========================================================================

    async def add_comment(
        self,
        review_request_id: str,
        user_id: str,
        comment_text: str,
        parent_comment_id: Optional[str] = None,
        highlighted_section: Optional[str] = None,
        highlighted_text: Optional[str] = None,
        is_internal: bool = False,
    ) -> Dict[str, Any]:
        """
        Add a comment to a review request

        Args:
            review_request_id: Review request ID
            user_id: User making the comment
            comment_text: Comment text
            parent_comment_id: Parent comment for threading
            highlighted_section: Section of content being discussed
            highlighted_text: Specific text being discussed
            is_internal: Whether comment is internal team only

        Returns:
            Created comment
        """
        async with self.db_pool.acquire() as conn:
            comment = await conn.fetchrow(
                """
                INSERT INTO review_comments (
                    review_request_id,
                    user_id,
                    comment_text,
                    parent_comment_id,
                    highlighted_section,
                    highlighted_text,
                    is_internal
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING *
                """,
                review_request_id,
                user_id,
                comment_text,
                parent_comment_id,
                highlighted_section,
                highlighted_text,
                is_internal,
            )

            await self._log_event(
                conn,
                review_request_id,
                "comment_added",
                {
                    "comment_id": str(comment["id"]),
                    "is_reply": parent_comment_id is not None,
                },
                user_id,
            )

            logger.info(f"Comment added to {review_request_id} by {user_id}")
            return dict(comment)

    async def get_comments(
        self, review_request_id: str, include_internal: bool = True
    ) -> List[Dict[str, Any]]:
        """Get all comments for a review request"""
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT c.*, u.name as user_name, u.email as user_email
                FROM review_comments c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.review_request_id = $1
            """
            if not include_internal:
                query += " AND c.is_internal = false"
            query += " ORDER BY c.created_at ASC"

            rows = await conn.fetch(query, review_request_id)
            return [dict(row) for row in rows]

    async def resolve_comment(
        self, comment_id: str, resolved_by: str
    ) -> Dict[str, Any]:
        """Mark a comment as resolved"""
        async with self.db_pool.acquire() as conn:
            comment = await conn.fetchrow(
                """
                UPDATE review_comments
                SET is_resolved = true,
                    resolved_by = $1,
                    resolved_at = NOW(),
                    updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                resolved_by,
                comment_id,
            )
            if not comment:
                raise ValueError(f"Comment {comment_id} not found")
            return dict(comment)

    # ========================================================================
    # Analytics and Metrics
    # ========================================================================

    async def get_user_review_queue(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending reviews for a user"""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM get_user_pending_reviews($1)", user_id
            )
            return [dict(row) for row in rows]

    async def get_organization_stats(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get review statistics for organization"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()

        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow(
                "SELECT * FROM get_organization_review_stats($1, $2, $3)",
                organization_id,
                start_date,
                end_date,
            )
            return dict(stats) if stats else {}

    async def get_reviewer_performance(
        self, reviewer_id: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get performance metrics for a reviewer"""
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_reviews,
                    AVG(time_spent_minutes) as avg_time_minutes,
                    AVG(accuracy_rating) as avg_accuracy,
                    AVG(completeness_rating) as avg_completeness,
                    AVG(quality_rating) as avg_quality,
                    COUNT(*) FILTER (WHERE decision = 'approve') as approved_count,
                    COUNT(*) FILTER (WHERE decision = 'reject') as rejected_count,
                    COUNT(*) FILTER (WHERE decision = 'request_revision') as revision_count
                FROM reviews
                WHERE reviewer_id = $1
                  AND submitted_at >= NOW() - $2::INTERVAL
                """,
                reviewer_id,
                f"{days} days",
            )
            return dict(stats) if stats else {}

    # ========================================================================
    # Helper Methods
    # ========================================================================

    async def _log_event(
        self,
        conn: asyncpg.Connection,
        review_request_id: str,
        event_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
    ) -> None:
        """Log an event to review history"""
        await conn.execute(
            """
            INSERT INTO review_history (
                review_request_id,
                event_type,
                event_data,
                user_id
            ) VALUES ($1, $2, $3, $4)
            """,
            review_request_id,
            event_type,
            event_data,
            user_id,
        )

    async def cancel_review(
        self, review_request_id: str, user_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cancel a review request"""
        async with self.db_pool.acquire() as conn:
            updated = await conn.fetchrow(
                """
                UPDATE review_requests
                SET status = 'cancelled',
                    final_decision_notes = $1,
                    updated_at = NOW()
                WHERE id = $2
                RETURNING *
                """,
                reason,
                review_request_id,
            )

            if not updated:
                raise ValueError(f"Review request {review_request_id} not found")

            await self._log_event(
                conn,
                review_request_id,
                "cancelled",
                {"reason": reason},
                user_id,
            )

            return dict(updated)
