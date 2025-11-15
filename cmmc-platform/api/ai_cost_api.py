"""
AI Cost Tracking API
Endpoints for viewing AI usage and costs
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import asyncpg

from middleware.auth_middleware import get_auth_context, AuthContext
from services.ai_cost_service import AICostService

router = APIRouter()

# Dependency to get database pool (will be overridden by app.py)
async def get_db_pool() -> asyncpg.Pool:
    raise NotImplementedError("Database pool dependency not configured")


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UsageRecord(BaseModel):
    """Single AI usage record"""
    id: str
    user_id: str
    assessment_id: Optional[str]
    control_id: Optional[str]
    operation_type: str
    model_name: str
    provider: str
    total_tokens: int
    cost_usd: float
    response_time_ms: Optional[int]
    created_at: str


class CostBreakdown(BaseModel):
    """Cost breakdown by operation type"""
    operation_type: str
    model_name: str
    count: int
    tokens: int
    cost_usd: float


class AssessmentCostResponse(BaseModel):
    """AI costs for a specific assessment"""
    assessment_id: str
    total_operations: int
    total_tokens: int
    total_cost_usd: float
    first_operation: Optional[datetime]
    last_operation: Optional[datetime]
    breakdown: List[CostBreakdown]


class DailyCost(BaseModel):
    """Daily cost summary"""
    date: str
    operations: int
    tokens: int
    cost_usd: float


class OperationCost(BaseModel):
    """Cost by operation type"""
    operation_type: str
    count: int
    tokens: int
    cost_usd: float


class OrganizationCostResponse(BaseModel):
    """Organization-wide AI costs"""
    organization_id: str
    period: Dict[str, str]
    summary: Dict[str, Any]
    daily_breakdown: List[DailyCost]
    operation_breakdown: List[OperationCost]


class RecentUsageResponse(BaseModel):
    """Recent AI usage records"""
    records: List[UsageRecord]
    total_count: int


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/costs/assessment/{assessment_id}", response_model=AssessmentCostResponse)
async def get_assessment_costs(
    assessment_id: str,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get AI costs for a specific assessment

    Returns detailed breakdown of AI usage and costs for an assessment,
    including:
    - Total operations, tokens, and costs
    - Breakdown by operation type (embedding, analysis, etc.)
    - First and last operation timestamps
    """
    try:
        # Verify assessment belongs to user's organization
        async with pool.acquire() as conn:
            assessment = await conn.fetchrow(
                """
                SELECT organization_id
                FROM assessments
                WHERE id = $1
                """,
                assessment_id
            )

            if not assessment:
                raise HTTPException(status_code=404, detail="Assessment not found")

            if str(assessment['organization_id']) != auth_context.organization_id:
                raise HTTPException(status_code=403, detail="Access denied")

        # Get costs
        cost_service = AICostService(db_pool=pool)
        costs = await cost_service.get_assessment_costs(
            assessment_id=assessment_id,
            organization_id=auth_context.organization_id
        )

        return AssessmentCostResponse(**costs)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get assessment costs: {str(e)}")


@router.get("/costs/organization", response_model=OrganizationCostResponse)
async def get_organization_costs(
    start_date: Optional[datetime] = Query(None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[datetime] = Query(None, description="End date (defaults to now)"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get organization-wide AI costs

    Returns aggregated AI usage and costs for the entire organization,
    including:
    - Total summary for the period
    - Daily breakdown
    - Breakdown by operation type
    """
    try:
        cost_service = AICostService(db_pool=pool)
        costs = await cost_service.get_organization_costs(
            organization_id=auth_context.organization_id,
            start_date=start_date,
            end_date=end_date
        )

        return OrganizationCostResponse(**costs)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get organization costs: {str(e)}")


@router.get("/costs/usage", response_model=RecentUsageResponse)
async def get_recent_usage(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get recent AI usage records

    Returns a list of recent AI API calls with details including:
    - Operation type and model used
    - Token usage and cost
    - Response time
    - Timestamp
    """
    try:
        cost_service = AICostService(db_pool=pool)
        records = await cost_service.get_recent_usage(
            organization_id=auth_context.organization_id,
            limit=limit
        )

        return RecentUsageResponse(
            records=[UsageRecord(**record) for record in records],
            total_count=len(records)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get recent usage: {str(e)}")


@router.get("/costs/summary")
async def get_cost_summary(
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get quick cost summary for dashboard

    Returns high-level cost metrics:
    - Today's costs
    - This month's costs
    - Average cost per assessment
    - Total operations
    """
    try:
        async with pool.acquire() as conn:
            # Today's costs
            today_costs = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as operations,
                    COALESCE(SUM(total_tokens), 0) as tokens,
                    COALESCE(SUM(cost_usd), 0) as cost_usd
                FROM ai_usage
                WHERE organization_id = $1
                  AND created_at >= CURRENT_DATE
                """,
                auth_context.organization_id
            )

            # This month's costs
            month_costs = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as operations,
                    COALESCE(SUM(total_tokens), 0) as tokens,
                    COALESCE(SUM(cost_usd), 0) as cost_usd
                FROM ai_usage
                WHERE organization_id = $1
                  AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
                """,
                auth_context.organization_id
            )

            # Average cost per assessment (assessments with AI usage)
            avg_assessment_cost = await conn.fetchrow(
                """
                SELECT
                    COUNT(DISTINCT assessment_id) as assessment_count,
                    COALESCE(AVG(total_cost), 0) as avg_cost_usd
                FROM (
                    SELECT
                        assessment_id,
                        SUM(cost_usd) as total_cost
                    FROM ai_usage
                    WHERE organization_id = $1
                      AND assessment_id IS NOT NULL
                    GROUP BY assessment_id
                ) as assessment_costs
                """,
                auth_context.organization_id
            )

            # Most used models
            top_models = await conn.fetch(
                """
                SELECT
                    model_name,
                    COUNT(*) as usage_count,
                    SUM(cost_usd) as total_cost_usd
                FROM ai_usage
                WHERE organization_id = $1
                  AND created_at >= DATE_TRUNC('month', CURRENT_DATE)
                GROUP BY model_name
                ORDER BY usage_count DESC
                LIMIT 5
                """,
                auth_context.organization_id
            )

            return {
                "today": {
                    "operations": today_costs['operations'],
                    "tokens": today_costs['tokens'],
                    "cost_usd": float(today_costs['cost_usd'])
                },
                "this_month": {
                    "operations": month_costs['operations'],
                    "tokens": month_costs['tokens'],
                    "cost_usd": float(month_costs['cost_usd'])
                },
                "average_per_assessment": {
                    "assessment_count": avg_assessment_cost['assessment_count'],
                    "avg_cost_usd": float(avg_assessment_cost['avg_cost_usd'])
                },
                "top_models": [
                    {
                        "model_name": row['model_name'],
                        "usage_count": row['usage_count'],
                        "total_cost_usd": float(row['total_cost_usd'])
                    }
                    for row in top_models
                ]
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cost summary: {str(e)}")


@router.post("/costs/refresh-summary")
async def refresh_cost_summary(
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Refresh the materialized view for daily cost summaries

    Call this endpoint to update the cached cost summaries.
    Useful after bulk operations or for generating fresh reports.

    Requires admin role.
    """
    if auth_context.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        async with pool.acquire() as conn:
            await conn.execute("SELECT refresh_ai_cost_daily_summary()")

        return {
            "success": True,
            "message": "Cost summary refreshed successfully"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh summary: {str(e)}")
