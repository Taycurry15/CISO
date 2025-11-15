"""
Human-in-the-Loop (HITL) Review API
REST API endpoints for review workflow management
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncpg
import logging

from services.hitl_review_service import (
    HITLReviewService,
    ReviewStatus,
    ReviewItemType,
    ReviewPriority,
    ReviewDecision,
)
from middleware import get_auth_context, AuthContext

logger = logging.getLogger(__name__)

router = APIRouter()

# Placeholder for database pool - will be overridden by dependency injection
async def get_db_pool() -> asyncpg.Pool:
    raise RuntimeError("Database pool dependency not configured")


# ============================================================================
# Request/Response Models
# ============================================================================


class CreateReviewRequestModel(BaseModel):
    """Request model for creating a review request"""

    item_type: ReviewItemType
    item_id: str
    item_name: Optional[str] = None
    assessment_id: Optional[str] = None
    ai_generated_content: Dict[str, Any]
    reference_content: Optional[Dict[str, Any]] = None
    context_data: Optional[Dict[str, Any]] = None
    ai_confidence_score: Optional[float] = Field(None, ge=0, le=1)
    ai_model_version: Optional[str] = None
    priority: ReviewPriority = ReviewPriority.MEDIUM
    required_reviewers: int = Field(1, ge=1)
    assigned_to: Optional[List[str]] = None
    due_date: Optional[datetime] = None


class AssignReviewersModel(BaseModel):
    """Request model for assigning reviewers"""

    reviewer_ids: List[str] = Field(..., min_items=1)


class SubmitReviewModel(BaseModel):
    """Request model for submitting a review"""

    decision: ReviewDecision
    overall_feedback: Optional[str] = None
    detailed_feedback: Optional[Dict[str, Any]] = None
    suggested_changes: Optional[Dict[str, Any]] = None
    accuracy_rating: Optional[int] = Field(None, ge=1, le=5)
    completeness_rating: Optional[int] = Field(None, ge=1, le=5)
    quality_rating: Optional[int] = Field(None, ge=1, le=5)
    time_spent_minutes: Optional[int] = Field(None, ge=0)


class UpdateStatusModel(BaseModel):
    """Request model for updating review status"""

    status: ReviewStatus
    notes: Optional[str] = None


class AddCommentModel(BaseModel):
    """Request model for adding a comment"""

    comment_text: str = Field(..., min_length=1)
    parent_comment_id: Optional[str] = None
    highlighted_section: Optional[str] = None
    highlighted_text: Optional[str] = None
    is_internal: bool = False


class ReviewRequestResponse(BaseModel):
    """Response model for review requests"""

    id: str
    organization_id: str
    assessment_id: Optional[str]
    item_type: str
    item_id: str
    item_name: str
    ai_generated_content: Dict[str, Any]
    ai_confidence_score: Optional[float]
    ai_model_version: Optional[str]
    reference_content: Optional[Dict[str, Any]]
    context_data: Optional[Dict[str, Any]]
    status: str
    priority: str
    required_reviewers: int
    approved_count: int
    assigned_to: List[str]
    requested_by: str
    requested_at: datetime
    due_date: Optional[datetime]
    final_decision: Optional[str]
    final_decision_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class ReviewResponse(BaseModel):
    """Response model for reviews"""

    id: str
    review_request_id: str
    reviewer_id: str
    reviewer_name: Optional[str]
    decision: str
    overall_feedback: Optional[str]
    detailed_feedback: Optional[Dict[str, Any]]
    suggested_changes: Optional[Dict[str, Any]]
    accuracy_rating: Optional[int]
    completeness_rating: Optional[int]
    quality_rating: Optional[int]
    time_spent_minutes: Optional[int]
    submitted_at: datetime


class CommentResponse(BaseModel):
    """Response model for comments"""

    id: str
    review_request_id: str
    user_id: str
    user_name: Optional[str]
    comment_text: str
    parent_comment_id: Optional[str]
    thread_id: Optional[str]
    highlighted_section: Optional[str]
    highlighted_text: Optional[str]
    is_internal: bool
    is_resolved: bool
    resolved_at: Optional[datetime]
    created_at: datetime


# ============================================================================
# Review Request Endpoints
# ============================================================================


@router.post("/reviews/requests", response_model=ReviewRequestResponse, status_code=201)
async def create_review_request(
    request: CreateReviewRequestModel,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Create a new review request for AI-generated content

    Creates a review request that requires human validation before
    the AI-generated content can be finalized and used.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        review_request = await service.create_review_request(
            organization_id=auth_context.organization_id,
            requested_by=auth_context.user_id,
            item_type=request.item_type,
            item_id=request.item_id,
            ai_generated_content=request.ai_generated_content,
            item_name=request.item_name,
            assessment_id=request.assessment_id,
            reference_content=request.reference_content,
            context_data=request.context_data,
            ai_confidence_score=request.ai_confidence_score,
            ai_model_version=request.ai_model_version,
            priority=request.priority,
            required_reviewers=request.required_reviewers,
            assigned_to=request.assigned_to,
            due_date=request.due_date,
        )

        return ReviewRequestResponse(**review_request)

    except Exception as e:
        logger.error(f"Failed to create review request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create review request: {str(e)}",
        )


@router.get("/reviews/requests", response_model=List[ReviewRequestResponse])
async def get_review_requests(
    status_filter: Optional[ReviewStatus] = Query(None, alias="status"),
    item_type: Optional[ReviewItemType] = Query(None),
    assessment_id: Optional[str] = Query(None),
    priority: Optional[ReviewPriority] = Query(None),
    overdue_only: bool = Query(False),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Get review requests with optional filters

    Returns a list of review requests for the organization,
    with optional filtering by status, type, priority, etc.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        review_requests = await service.get_review_requests(
            organization_id=auth_context.organization_id,
            status=status_filter,
            item_type=item_type,
            assessment_id=assessment_id,
            priority=priority,
            overdue_only=overdue_only,
            limit=limit,
            offset=offset,
        )

        return [ReviewRequestResponse(**rr) for rr in review_requests]

    except Exception as e:
        logger.error(f"Failed to get review requests: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review requests: {str(e)}",
        )


@router.get("/reviews/requests/{review_request_id}", response_model=ReviewRequestResponse)
async def get_review_request(
    review_request_id: str,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get a specific review request by ID"""
    try:
        service = HITLReviewService(db_pool=pool)
        review_request = await service.get_review_request(review_request_id)

        # Verify organization access
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        return ReviewRequestResponse(**review_request)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get review request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review request: {str(e)}",
        )


@router.post(
    "/reviews/requests/{review_request_id}/assign", response_model=ReviewRequestResponse
)
async def assign_reviewers(
    review_request_id: str,
    request: AssignReviewersModel,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Assign reviewers to a review request

    Assigns one or more reviewers to validate the AI-generated content.
    Reviewers will be notified and can access the review queue.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        # Verify access
        review_request = await service.get_review_request(review_request_id)
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        updated = await service.assign_reviewers(
            review_request_id=review_request_id,
            reviewer_ids=request.reviewer_ids,
            assigned_by=auth_context.user_id,
        )

        return ReviewRequestResponse(**updated)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to assign reviewers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign reviewers: {str(e)}",
        )


@router.patch(
    "/reviews/requests/{review_request_id}/status", response_model=ReviewRequestResponse
)
async def update_review_status(
    review_request_id: str,
    request: UpdateStatusModel,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Update the status of a review request"""
    try:
        service = HITLReviewService(db_pool=pool)

        # Verify access
        review_request = await service.get_review_request(review_request_id)
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        updated = await service.update_review_status(
            review_request_id=review_request_id,
            new_status=request.status,
            user_id=auth_context.user_id,
            notes=request.notes,
        )

        return ReviewRequestResponse(**updated)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update review status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update review status: {str(e)}",
        )


@router.delete("/reviews/requests/{review_request_id}")
async def cancel_review_request(
    review_request_id: str,
    reason: Optional[str] = Query(None),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Cancel a review request"""
    try:
        service = HITLReviewService(db_pool=pool)

        # Verify access
        review_request = await service.get_review_request(review_request_id)
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        await service.cancel_review(
            review_request_id=review_request_id,
            user_id=auth_context.user_id,
            reason=reason,
        )

        return {"message": "Review request cancelled successfully"}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to cancel review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel review: {str(e)}",
        )


# ============================================================================
# Review Submission Endpoints
# ============================================================================


@router.post(
    "/reviews/requests/{review_request_id}/submit", response_model=ReviewResponse
)
async def submit_review(
    review_request_id: str,
    request: SubmitReviewModel,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Submit a review for a review request

    Submits the reviewer's decision, feedback, and ratings.
    If this is the final required review, the request may be auto-approved.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        # Verify access
        review_request = await service.get_review_request(review_request_id)
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        review = await service.submit_review(
            review_request_id=review_request_id,
            reviewer_id=auth_context.user_id,
            decision=request.decision,
            overall_feedback=request.overall_feedback,
            detailed_feedback=request.detailed_feedback,
            suggested_changes=request.suggested_changes,
            accuracy_rating=request.accuracy_rating,
            completeness_rating=request.completeness_rating,
            quality_rating=request.quality_rating,
            time_spent_minutes=request.time_spent_minutes,
        )

        return ReviewResponse(**review)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to submit review: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review: {str(e)}",
        )


@router.get(
    "/reviews/requests/{review_request_id}/reviews", response_model=List[ReviewResponse]
)
async def get_reviews(
    review_request_id: str,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get all submitted reviews for a review request"""
    try:
        service = HITLReviewService(db_pool=pool)

        # Verify access
        review_request = await service.get_review_request(review_request_id)
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        reviews = await service.get_reviews_for_request(review_request_id)
        return [ReviewResponse(**r) for r in reviews]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get reviews: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviews: {str(e)}",
        )


# ============================================================================
# Comment Endpoints
# ============================================================================


@router.post(
    "/reviews/requests/{review_request_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
async def add_comment(
    review_request_id: str,
    request: AddCommentModel,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Add a comment to a review request

    Supports threaded discussions and highlighting specific
    sections of the AI-generated content.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        # Verify access
        review_request = await service.get_review_request(review_request_id)
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        comment = await service.add_comment(
            review_request_id=review_request_id,
            user_id=auth_context.user_id,
            comment_text=request.comment_text,
            parent_comment_id=request.parent_comment_id,
            highlighted_section=request.highlighted_section,
            highlighted_text=request.highlighted_text,
            is_internal=request.is_internal,
        )

        return CommentResponse(**comment)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to add comment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add comment: {str(e)}",
        )


@router.get(
    "/reviews/requests/{review_request_id}/comments",
    response_model=List[CommentResponse],
)
async def get_comments(
    review_request_id: str,
    include_internal: bool = Query(True),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Get all comments for a review request"""
    try:
        service = HITLReviewService(db_pool=pool)

        # Verify access
        review_request = await service.get_review_request(review_request_id)
        if review_request["organization_id"] != auth_context.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this review request",
            )

        comments = await service.get_comments(review_request_id, include_internal)
        return [CommentResponse(**c) for c in comments]

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get comments: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get comments: {str(e)}",
        )


@router.patch("/reviews/comments/{comment_id}/resolve")
async def resolve_comment(
    comment_id: str,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Mark a comment as resolved"""
    try:
        service = HITLReviewService(db_pool=pool)

        comment = await service.resolve_comment(
            comment_id=comment_id, resolved_by=auth_context.user_id
        )

        return {"message": "Comment resolved successfully", "comment": comment}

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to resolve comment: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve comment: {str(e)}",
        )


# ============================================================================
# User Queue and Analytics Endpoints
# ============================================================================


@router.get("/reviews/my-queue", response_model=List[ReviewRequestResponse])
async def get_my_review_queue(
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Get current user's review queue

    Returns all pending reviews assigned to the current user,
    sorted by priority and due date.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        # Get reviews assigned to this user
        queue = await service.get_review_requests(
            organization_id=auth_context.organization_id,
            assigned_to=auth_context.user_id,
            status=ReviewStatus.ASSIGNED,
        )

        # Also get in_review items
        in_review = await service.get_review_requests(
            organization_id=auth_context.organization_id,
            assigned_to=auth_context.user_id,
            status=ReviewStatus.IN_REVIEW,
        )

        all_queue = queue + in_review
        return [ReviewRequestResponse(**rr) for rr in all_queue]

    except Exception as e:
        logger.error(f"Failed to get review queue: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review queue: {str(e)}",
        )


@router.get("/reviews/stats")
async def get_organization_review_stats(
    days: int = Query(30, ge=1, le=365),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Get review statistics for the organization

    Returns metrics like total reviews, approval rates,
    average review time, and AI accuracy.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        stats = await service.get_organization_stats(
            organization_id=auth_context.organization_id,
            start_date=datetime.now() - timedelta(days=days),
            end_date=datetime.now(),
        )

        return stats

    except Exception as e:
        logger.error(f"Failed to get review stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get review stats: {str(e)}",
        )


@router.get("/reviews/my-performance")
async def get_my_performance(
    days: int = Query(30, ge=1, le=365),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """
    Get performance metrics for current user as a reviewer

    Returns stats like total reviews completed, average time,
    and rating scores.
    """
    try:
        service = HITLReviewService(db_pool=pool)

        performance = await service.get_reviewer_performance(
            reviewer_id=auth_context.user_id, days=days
        )

        return performance

    except Exception as e:
        logger.error(f"Failed to get reviewer performance: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get reviewer performance: {str(e)}",
        )


# Import needed for timedelta
from datetime import timedelta
