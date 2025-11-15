"""
AI Budget Management API
Endpoints for configuring budgets and viewing alerts
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import asyncpg

from middleware.auth_middleware import get_auth_context, AuthContext
from services.ai_budget_service import AIBudgetService, BudgetPeriod, AlertLevel

router = APIRouter()

# Dependency to get database pool (will be overridden by app.py)
async def get_db_pool() -> asyncpg.Pool:
    raise NotImplementedError("Database pool dependency not configured")


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class CreateBudgetRequest(BaseModel):
    """Request to create a new budget"""
    budget_limit_usd: float = Field(..., gt=0, description="Maximum allowed spending in USD")
    budget_period: BudgetPeriod = Field(default=BudgetPeriod.MONTHLY, description="Time period for budget")
    warning_threshold_percent: int = Field(default=75, ge=1, le=100, description="Warning alert threshold percentage")
    critical_threshold_percent: int = Field(default=90, ge=1, le=100, description="Critical alert threshold percentage")
    email_alerts_enabled: bool = Field(default=True, description="Enable email notifications")
    slack_webhook_url: Optional[str] = Field(default=None, description="Slack webhook URL for notifications")
    webhook_url: Optional[str] = Field(default=None, description="Custom webhook URL for notifications")
    block_at_limit: bool = Field(default=False, description="Block AI operations when limit is reached")
    assessment_id: Optional[str] = Field(default=None, description="Assessment ID (required for assessment budgets)")


class UpdateBudgetRequest(BaseModel):
    """Request to update an existing budget"""
    budget_limit_usd: Optional[float] = Field(default=None, gt=0)
    warning_threshold_percent: Optional[int] = Field(default=None, ge=1, le=100)
    critical_threshold_percent: Optional[int] = Field(default=None, ge=1, le=100)
    email_alerts_enabled: Optional[bool] = None
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    block_at_limit: Optional[bool] = None


class BudgetResponse(BaseModel):
    """Budget configuration response"""
    id: str
    budget_period: str
    budget_limit_usd: float
    warning_threshold_percent: int
    critical_threshold_percent: int
    email_alerts_enabled: bool
    has_slack_webhook: bool
    has_custom_webhook: bool
    block_at_limit: bool
    assessment_id: Optional[str]
    created_at: str
    updated_at: str


class BudgetStatusResponse(BaseModel):
    """Current budget status response"""
    current_spend_usd: float
    budget_limit_usd: Optional[float]
    percent_used: float
    budget_period: str
    has_budget_configured: bool
    alert_triggered: Optional[bool] = None
    alert_level: Optional[str] = None
    should_block: Optional[bool] = None


class AlertResponse(BaseModel):
    """Budget alert response"""
    id: str
    assessment_id: Optional[str]
    alert_level: str
    budget_period: str
    current_spend_usd: float
    budget_limit_usd: float
    percent_used: float
    period_start: str
    period_end: str
    acknowledged: bool
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]
    notification_sent: bool
    created_at: str


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/budgets", response_model=dict)
async def create_budget(
    request: CreateBudgetRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Create a new AI spending budget

    Configure budget limits and alert thresholds for:
    - Organization-wide spending (daily/weekly/monthly)
    - Per-assessment spending

    When spending reaches thresholds, alerts are automatically triggered
    and notifications sent via configured channels (email, Slack, webhook).
    """
    # Only admins can create budgets
    if auth_context.role not in ['admin', 'owner']:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate thresholds
    if request.warning_threshold_percent >= request.critical_threshold_percent:
        raise HTTPException(
            status_code=400,
            detail="Warning threshold must be less than critical threshold"
        )

    try:
        budget_service = AIBudgetService(db_pool=pool)
        budget_id = await budget_service.create_budget(
            organization_id=auth_context.organization_id,
            budget_limit_usd=request.budget_limit_usd,
            budget_period=request.budget_period,
            warning_threshold_percent=request.warning_threshold_percent,
            critical_threshold_percent=request.critical_threshold_percent,
            email_alerts_enabled=request.email_alerts_enabled,
            slack_webhook_url=request.slack_webhook_url,
            webhook_url=request.webhook_url,
            block_at_limit=request.block_at_limit,
            assessment_id=request.assessment_id,
            created_by=auth_context.user_id
        )

        return {
            "success": True,
            "budget_id": budget_id,
            "message": f"Budget created successfully: ${request.budget_limit_usd} ({request.budget_period.value})"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create budget: {str(e)}")


@router.get("/budgets", response_model=List[BudgetResponse])
async def list_budgets(
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    List all budget configurations for the organization

    Returns all configured budgets including:
    - Organization-wide budgets (daily/weekly/monthly)
    - Assessment-specific budgets
    """
    try:
        budget_service = AIBudgetService(db_pool=pool)
        budgets = await budget_service.get_organization_budgets(
            organization_id=auth_context.organization_id
        )

        return [BudgetResponse(**budget) for budget in budgets]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list budgets: {str(e)}")


@router.patch("/budgets/{budget_id}", response_model=dict)
async def update_budget(
    budget_id: str,
    request: UpdateBudgetRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Update an existing budget configuration

    Allows updating:
    - Budget limits
    - Alert thresholds
    - Notification settings
    - Enforcement options
    """
    # Only admins can update budgets
    if auth_context.role not in ['admin', 'owner']:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate thresholds if both provided
    if (request.warning_threshold_percent is not None and
        request.critical_threshold_percent is not None and
        request.warning_threshold_percent >= request.critical_threshold_percent):
        raise HTTPException(
            status_code=400,
            detail="Warning threshold must be less than critical threshold"
        )

    try:
        budget_service = AIBudgetService(db_pool=pool)
        success = await budget_service.update_budget(
            budget_id=budget_id,
            organization_id=auth_context.organization_id,
            budget_limit_usd=request.budget_limit_usd,
            warning_threshold_percent=request.warning_threshold_percent,
            critical_threshold_percent=request.critical_threshold_percent,
            email_alerts_enabled=request.email_alerts_enabled,
            slack_webhook_url=request.slack_webhook_url,
            webhook_url=request.webhook_url,
            block_at_limit=request.block_at_limit
        )

        if not success:
            raise HTTPException(status_code=404, detail="Budget not found")

        return {
            "success": True,
            "message": "Budget updated successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update budget: {str(e)}")


@router.delete("/budgets/{budget_id}", response_model=dict)
async def delete_budget(
    budget_id: str,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Delete a budget configuration

    Removes the budget and stops monitoring spending for that configuration.
    Historical alerts are preserved.
    """
    # Only admins can delete budgets
    if auth_context.role not in ['admin', 'owner']:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        budget_service = AIBudgetService(db_pool=pool)
        success = await budget_service.delete_budget(
            budget_id=budget_id,
            organization_id=auth_context.organization_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Budget not found")

        return {
            "success": True,
            "message": "Budget deleted successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete budget: {str(e)}")


@router.get("/budgets/status/{period}", response_model=BudgetStatusResponse)
async def get_budget_status(
    period: BudgetPeriod,
    assessment_id: Optional[str] = Query(default=None, description="Assessment ID (for assessment budgets)"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get current budget status for a period

    Returns:
    - Current spending
    - Budget limit (if configured)
    - Percentage used
    - Whether alerts should be triggered
    """
    try:
        budget_service = AIBudgetService(db_pool=pool)

        # Get current spending
        spending = await budget_service.get_current_spending(
            organization_id=auth_context.organization_id,
            budget_period=period,
            assessment_id=assessment_id
        )

        # Check for alerts
        alert_status = await budget_service.check_budget_status(
            organization_id=auth_context.organization_id,
            assessment_id=assessment_id
        )

        return BudgetStatusResponse(
            **spending,
            alert_triggered=alert_status.get('alert_triggered'),
            alert_level=alert_status.get('alert_level'),
            should_block=alert_status.get('should_block')
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get budget status: {str(e)}")


@router.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    unacknowledged_only: bool = Query(default=False, description="Return only unacknowledged alerts"),
    limit: int = Query(default=50, ge=1, le=500, description="Maximum number of alerts to return"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    List budget alerts for the organization

    Returns alerts triggered when spending thresholds are exceeded.
    Can filter to show only unacknowledged alerts.
    """
    try:
        budget_service = AIBudgetService(db_pool=pool)
        alerts = await budget_service.get_alerts(
            organization_id=auth_context.organization_id,
            unacknowledged_only=unacknowledged_only,
            limit=limit
        )

        return [AlertResponse(**alert) for alert in alerts]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list alerts: {str(e)}")


@router.post("/alerts/{alert_id}/acknowledge", response_model=dict)
async def acknowledge_alert(
    alert_id: str,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Acknowledge a budget alert

    Marks the alert as reviewed and records who acknowledged it.
    """
    try:
        budget_service = AIBudgetService(db_pool=pool)
        success = await budget_service.acknowledge_alert(
            alert_id=alert_id,
            organization_id=auth_context.organization_id,
            user_id=auth_context.user_id
        )

        if not success:
            raise HTTPException(status_code=404, detail="Alert not found")

        return {
            "success": True,
            "message": "Alert acknowledged successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to acknowledge alert: {str(e)}")


@router.get("/alerts/summary", response_model=dict)
async def get_alerts_summary(
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get summary of budget alerts

    Returns quick stats for displaying in dashboards:
    - Count of unacknowledged alerts by level
    - Most recent critical alert
    - Total alerts in last 30 days
    """
    try:
        async with pool.acquire() as conn:
            # Count unacknowledged alerts by level
            unack_counts = await conn.fetch(
                """
                SELECT
                    alert_level,
                    COUNT(*) as count
                FROM ai_budget_alerts
                WHERE organization_id = $1
                  AND acknowledged = false
                GROUP BY alert_level
                """,
                auth_context.organization_id
            )

            # Get most recent critical alert
            recent_critical = await conn.fetchrow(
                """
                SELECT
                    id,
                    alert_level,
                    current_spend_usd,
                    budget_limit_usd,
                    percent_used,
                    created_at
                FROM ai_budget_alerts
                WHERE organization_id = $1
                  AND alert_level = 'critical'
                ORDER BY created_at DESC
                LIMIT 1
                """,
                auth_context.organization_id
            )

            # Total alerts in last 30 days
            total_recent = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM ai_budget_alerts
                WHERE organization_id = $1
                  AND created_at >= NOW() - INTERVAL '30 days'
                """,
                auth_context.organization_id
            )

            return {
                "unacknowledged_by_level": {
                    row['alert_level']: row['count']
                    for row in unack_counts
                },
                "recent_critical_alert": {
                    "id": str(recent_critical['id']),
                    "alert_level": recent_critical['alert_level'],
                    "current_spend_usd": float(recent_critical['current_spend_usd']),
                    "budget_limit_usd": float(recent_critical['budget_limit_usd']),
                    "percent_used": float(recent_critical['percent_used']),
                    "created_at": recent_critical['created_at'].isoformat()
                } if recent_critical else None,
                "total_alerts_last_30_days": total_recent
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get alerts summary: {str(e)}")
