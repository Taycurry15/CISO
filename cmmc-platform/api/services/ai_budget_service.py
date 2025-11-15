"""
AI Budget Alert Service
Manages AI spending budgets and automated alerts
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
import asyncpg
import aiohttp

logger = logging.getLogger(__name__)


class BudgetPeriod(str, Enum):
    """Budget period types"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ASSESSMENT = "assessment"


class AlertLevel(str, Enum):
    """Alert severity levels"""
    WARNING = "warning"
    CRITICAL = "critical"
    LIMIT_REACHED = "limit_reached"
    RESOLVED = "resolved"


class AIBudgetService:
    """
    Service for managing AI spending budgets and alerts

    Features:
    - Create and manage budget limits (daily/weekly/monthly/per-assessment)
    - Automatic alert triggers at configurable thresholds
    - Multi-channel notifications (email, Slack, webhook)
    - Optional spending enforcement (block at limit)
    - Alert acknowledgment and resolution
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize AI budget service

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    async def create_budget(
        self,
        organization_id: str,
        budget_limit_usd: float,
        budget_period: BudgetPeriod = BudgetPeriod.MONTHLY,
        warning_threshold_percent: int = 75,
        critical_threshold_percent: int = 90,
        email_alerts_enabled: bool = True,
        slack_webhook_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        block_at_limit: bool = False,
        assessment_id: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> str:
        """
        Create a new budget configuration

        Args:
            organization_id: Organization ID
            budget_limit_usd: Maximum allowed spending
            budget_period: Time period for budget (daily/weekly/monthly/assessment)
            warning_threshold_percent: Warning alert at this percentage (default: 75%)
            critical_threshold_percent: Critical alert at this percentage (default: 90%)
            email_alerts_enabled: Enable email notifications
            slack_webhook_url: Optional Slack webhook for notifications
            webhook_url: Optional custom webhook for notifications
            block_at_limit: Block AI operations when limit is reached
            assessment_id: Optional assessment ID for assessment-specific budgets
            created_by: User who created the budget

        Returns:
            Budget setting ID
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Validate assessment-specific budget
                if budget_period == BudgetPeriod.ASSESSMENT and not assessment_id:
                    raise ValueError("assessment_id required for assessment budget period")

                if budget_period != BudgetPeriod.ASSESSMENT and assessment_id:
                    raise ValueError("assessment_id only valid for assessment budget period")

                budget_id = await conn.fetchval(
                    """
                    INSERT INTO ai_budget_settings (
                        organization_id,
                        budget_period,
                        budget_limit_usd,
                        warning_threshold_percent,
                        critical_threshold_percent,
                        email_alerts_enabled,
                        slack_webhook_url,
                        webhook_url,
                        block_at_limit,
                        assessment_id,
                        created_by
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                    RETURNING id
                    """,
                    organization_id,
                    budget_period.value,
                    Decimal(str(budget_limit_usd)),
                    warning_threshold_percent,
                    critical_threshold_percent,
                    email_alerts_enabled,
                    slack_webhook_url,
                    webhook_url,
                    block_at_limit,
                    assessment_id,
                    created_by
                )

                logger.info(
                    f"Created {budget_period.value} budget for org {organization_id}: "
                    f"${budget_limit_usd} (warn: {warning_threshold_percent}%, critical: {critical_threshold_percent}%)"
                )

                return str(budget_id)

        except Exception as e:
            logger.error(f"Failed to create budget: {e}")
            raise

    async def update_budget(
        self,
        budget_id: str,
        organization_id: str,
        budget_limit_usd: Optional[float] = None,
        warning_threshold_percent: Optional[int] = None,
        critical_threshold_percent: Optional[int] = None,
        email_alerts_enabled: Optional[bool] = None,
        slack_webhook_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        block_at_limit: Optional[bool] = None
    ) -> bool:
        """
        Update an existing budget configuration

        Args:
            budget_id: Budget setting ID
            organization_id: Organization ID (for access control)
            budget_limit_usd: New budget limit
            warning_threshold_percent: New warning threshold
            critical_threshold_percent: New critical threshold
            email_alerts_enabled: Enable/disable email alerts
            slack_webhook_url: Update Slack webhook URL
            webhook_url: Update custom webhook URL
            block_at_limit: Enable/disable blocking at limit

        Returns:
            True if updated successfully
        """
        try:
            # Build dynamic update query
            updates = []
            params = [budget_id, organization_id]
            param_count = 2

            if budget_limit_usd is not None:
                param_count += 1
                updates.append(f"budget_limit_usd = ${param_count}")
                params.append(Decimal(str(budget_limit_usd)))

            if warning_threshold_percent is not None:
                param_count += 1
                updates.append(f"warning_threshold_percent = ${param_count}")
                params.append(warning_threshold_percent)

            if critical_threshold_percent is not None:
                param_count += 1
                updates.append(f"critical_threshold_percent = ${param_count}")
                params.append(critical_threshold_percent)

            if email_alerts_enabled is not None:
                param_count += 1
                updates.append(f"email_alerts_enabled = ${param_count}")
                params.append(email_alerts_enabled)

            if slack_webhook_url is not None:
                param_count += 1
                updates.append(f"slack_webhook_url = ${param_count}")
                params.append(slack_webhook_url)

            if webhook_url is not None:
                param_count += 1
                updates.append(f"webhook_url = ${param_count}")
                params.append(webhook_url)

            if block_at_limit is not None:
                param_count += 1
                updates.append(f"block_at_limit = ${param_count}")
                params.append(block_at_limit)

            if not updates:
                logger.warning("No fields to update")
                return False

            query = f"""
                UPDATE ai_budget_settings
                SET {', '.join(updates)}
                WHERE id = $1 AND organization_id = $2
            """

            async with self.db_pool.acquire() as conn:
                result = await conn.execute(query, *params)
                return result == "UPDATE 1"

        except Exception as e:
            logger.error(f"Failed to update budget: {e}")
            raise

    async def delete_budget(
        self,
        budget_id: str,
        organization_id: str
    ) -> bool:
        """
        Delete a budget configuration

        Args:
            budget_id: Budget setting ID
            organization_id: Organization ID (for access control)

        Returns:
            True if deleted successfully
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM ai_budget_settings
                    WHERE id = $1 AND organization_id = $2
                    """,
                    budget_id,
                    organization_id
                )
                return result == "DELETE 1"

        except Exception as e:
            logger.error(f"Failed to delete budget: {e}")
            raise

    async def get_organization_budgets(
        self,
        organization_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get all budget configurations for an organization

        Args:
            organization_id: Organization ID

        Returns:
            List of budget configurations
        """
        try:
            async with self.db_pool.acquire() as conn:
                budgets = await conn.fetch(
                    """
                    SELECT
                        id,
                        budget_period,
                        budget_limit_usd,
                        warning_threshold_percent,
                        critical_threshold_percent,
                        email_alerts_enabled,
                        slack_webhook_url IS NOT NULL as has_slack_webhook,
                        webhook_url IS NOT NULL as has_custom_webhook,
                        block_at_limit,
                        assessment_id,
                        created_at,
                        updated_at
                    FROM ai_budget_settings
                    WHERE organization_id = $1
                    ORDER BY created_at DESC
                    """,
                    organization_id
                )

                return [
                    {
                        "id": str(row['id']),
                        "budget_period": row['budget_period'],
                        "budget_limit_usd": float(row['budget_limit_usd']),
                        "warning_threshold_percent": row['warning_threshold_percent'],
                        "critical_threshold_percent": row['critical_threshold_percent'],
                        "email_alerts_enabled": row['email_alerts_enabled'],
                        "has_slack_webhook": row['has_slack_webhook'],
                        "has_custom_webhook": row['has_custom_webhook'],
                        "block_at_limit": row['block_at_limit'],
                        "assessment_id": str(row['assessment_id']) if row['assessment_id'] else None,
                        "created_at": row['created_at'].isoformat(),
                        "updated_at": row['updated_at'].isoformat()
                    }
                    for row in budgets
                ]

        except Exception as e:
            logger.error(f"Failed to get organization budgets: {e}")
            raise

    async def check_budget_status(
        self,
        organization_id: str,
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Check current budget status and trigger alerts if needed

        Args:
            organization_id: Organization ID
            assessment_id: Optional assessment ID

        Returns:
            Budget status with current spending and alerts
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Call stored procedure to check and trigger alerts
                result = await conn.fetchrow(
                    """
                    SELECT * FROM check_budget_alerts($1, $2)
                    """,
                    organization_id,
                    assessment_id
                )

                if result and result['alert_triggered']:
                    # Alert was triggered - send notifications
                    await self._send_alert_notifications(
                        organization_id=organization_id,
                        alert_level=result['alert_level'],
                        percent_used=float(result['percent_used']),
                        current_spend=float(result['current_spend']),
                        budget_limit=float(result['budget_limit']),
                        assessment_id=assessment_id
                    )

                    return {
                        "alert_triggered": True,
                        "alert_level": result['alert_level'],
                        "percent_used": float(result['percent_used']),
                        "current_spend_usd": float(result['current_spend']),
                        "budget_limit_usd": float(result['budget_limit']),
                        "should_block": result['alert_level'] == 'limit_reached'
                    }
                else:
                    return {
                        "alert_triggered": False,
                        "should_block": False
                    }

        except Exception as e:
            logger.error(f"Failed to check budget status: {e}")
            # Don't raise - budget checks shouldn't break AI operations
            return {
                "alert_triggered": False,
                "should_block": False,
                "error": str(e)
            }

    async def get_current_spending(
        self,
        organization_id: str,
        budget_period: BudgetPeriod,
        assessment_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get current spending for a budget period

        Args:
            organization_id: Organization ID
            budget_period: Budget period to check
            assessment_id: Optional assessment ID

        Returns:
            Current spending information
        """
        try:
            async with self.db_pool.acquire() as conn:
                current_spend = await conn.fetchval(
                    """
                    SELECT get_period_spending($1, $2, $3)
                    """,
                    organization_id,
                    budget_period.value,
                    assessment_id
                )

                # Get budget limit if configured
                budget_limit = await conn.fetchval(
                    """
                    SELECT budget_limit_usd
                    FROM ai_budget_settings
                    WHERE organization_id = $1
                      AND budget_period = $2
                      AND (
                          (assessment_id IS NULL AND $3::UUID IS NULL) OR
                          (assessment_id = $3)
                      )
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    organization_id,
                    budget_period.value,
                    assessment_id
                )

                percent_used = 0.0
                if budget_limit and budget_limit > 0:
                    percent_used = (float(current_spend) / float(budget_limit)) * 100

                return {
                    "current_spend_usd": float(current_spend or 0),
                    "budget_limit_usd": float(budget_limit) if budget_limit else None,
                    "percent_used": percent_used,
                    "budget_period": budget_period.value,
                    "has_budget_configured": budget_limit is not None
                }

        except Exception as e:
            logger.error(f"Failed to get current spending: {e}")
            raise

    async def get_alerts(
        self,
        organization_id: str,
        unacknowledged_only: bool = False,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get budget alerts for an organization

        Args:
            organization_id: Organization ID
            unacknowledged_only: Return only unacknowledged alerts
            limit: Maximum number of alerts to return

        Returns:
            List of budget alerts
        """
        try:
            async with self.db_pool.acquire() as conn:
                query = """
                    SELECT
                        id,
                        assessment_id,
                        alert_level,
                        budget_period,
                        current_spend_usd,
                        budget_limit_usd,
                        percent_used,
                        period_start,
                        period_end,
                        acknowledged,
                        acknowledged_by,
                        acknowledged_at,
                        notification_sent,
                        created_at
                    FROM ai_budget_alerts
                    WHERE organization_id = $1
                """

                if unacknowledged_only:
                    query += " AND acknowledged = false"

                query += " ORDER BY created_at DESC LIMIT $2"

                alerts = await conn.fetch(query, organization_id, limit)

                return [
                    {
                        "id": str(row['id']),
                        "assessment_id": str(row['assessment_id']) if row['assessment_id'] else None,
                        "alert_level": row['alert_level'],
                        "budget_period": row['budget_period'],
                        "current_spend_usd": float(row['current_spend_usd']),
                        "budget_limit_usd": float(row['budget_limit_usd']),
                        "percent_used": float(row['percent_used']),
                        "period_start": row['period_start'].isoformat(),
                        "period_end": row['period_end'].isoformat(),
                        "acknowledged": row['acknowledged'],
                        "acknowledged_by": str(row['acknowledged_by']) if row['acknowledged_by'] else None,
                        "acknowledged_at": row['acknowledged_at'].isoformat() if row['acknowledged_at'] else None,
                        "notification_sent": row['notification_sent'],
                        "created_at": row['created_at'].isoformat()
                    }
                    for row in alerts
                ]

        except Exception as e:
            logger.error(f"Failed to get alerts: {e}")
            raise

    async def acknowledge_alert(
        self,
        alert_id: str,
        organization_id: str,
        user_id: str
    ) -> bool:
        """
        Acknowledge a budget alert

        Args:
            alert_id: Alert ID
            organization_id: Organization ID (for access control)
            user_id: User acknowledging the alert

        Returns:
            True if acknowledged successfully
        """
        try:
            async with self.db_pool.acquire() as conn:
                result = await conn.execute(
                    """
                    UPDATE ai_budget_alerts
                    SET acknowledged = true,
                        acknowledged_by = $3,
                        acknowledged_at = NOW()
                    WHERE id = $1 AND organization_id = $2
                    """,
                    alert_id,
                    organization_id,
                    user_id
                )
                return result == "UPDATE 1"

        except Exception as e:
            logger.error(f"Failed to acknowledge alert: {e}")
            raise

    async def _send_alert_notifications(
        self,
        organization_id: str,
        alert_level: str,
        percent_used: float,
        current_spend: float,
        budget_limit: float,
        assessment_id: Optional[str] = None
    ):
        """
        Send notifications for budget alerts

        Args:
            organization_id: Organization ID
            alert_level: Alert severity level
            percent_used: Percentage of budget used
            current_spend: Current spending amount
            budget_limit: Budget limit
            assessment_id: Optional assessment ID
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Get notification settings
                settings = await conn.fetchrow(
                    """
                    SELECT
                        email_alerts_enabled,
                        slack_webhook_url,
                        webhook_url
                    FROM ai_budget_settings
                    WHERE organization_id = $1
                      AND (
                          (assessment_id IS NULL AND $2::UUID IS NULL) OR
                          (assessment_id = $2)
                      )
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    organization_id,
                    assessment_id
                )

                if not settings:
                    return

                channels_notified = []

                # Send Slack notification
                if settings['slack_webhook_url']:
                    success = await self._send_slack_notification(
                        webhook_url=settings['slack_webhook_url'],
                        alert_level=alert_level,
                        percent_used=percent_used,
                        current_spend=current_spend,
                        budget_limit=budget_limit
                    )
                    if success:
                        channels_notified.append('slack')

                # Send custom webhook notification
                if settings['webhook_url']:
                    success = await self._send_webhook_notification(
                        webhook_url=settings['webhook_url'],
                        organization_id=organization_id,
                        alert_level=alert_level,
                        percent_used=percent_used,
                        current_spend=current_spend,
                        budget_limit=budget_limit,
                        assessment_id=assessment_id
                    )
                    if success:
                        channels_notified.append('webhook')

                # Email notifications would be implemented here
                # if settings['email_alerts_enabled']:
                #     await self._send_email_notification(...)

                logger.info(
                    f"Sent {alert_level} budget alert for org {organization_id}: "
                    f"{percent_used:.1f}% (${current_spend:.2f}/${budget_limit:.2f}) "
                    f"via {channels_notified}"
                )

        except Exception as e:
            logger.error(f"Failed to send alert notifications: {e}")
            # Don't raise - notification failures shouldn't break the flow

    async def _send_slack_notification(
        self,
        webhook_url: str,
        alert_level: str,
        percent_used: float,
        current_spend: float,
        budget_limit: float
    ) -> bool:
        """Send Slack notification via webhook"""
        try:
            # Color based on alert level
            colors = {
                'warning': '#FFA500',  # Orange
                'critical': '#FF0000',  # Red
                'limit_reached': '#8B0000'  # Dark red
            }

            message = {
                "attachments": [
                    {
                        "color": colors.get(alert_level, '#808080'),
                        "title": f"⚠️ AI Budget Alert: {alert_level.upper()}",
                        "text": (
                            f"Your AI spending has reached *{percent_used:.1f}%* of the budget limit.\n\n"
                            f"*Current Spend:* ${current_spend:.2f}\n"
                            f"*Budget Limit:* ${budget_limit:.2f}\n"
                            f"*Remaining:* ${budget_limit - current_spend:.2f}"
                        ),
                        "footer": "CMMC Platform AI Cost Tracking",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=message, timeout=10) as resp:
                    return resp.status == 200

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            return False

    async def _send_webhook_notification(
        self,
        webhook_url: str,
        organization_id: str,
        alert_level: str,
        percent_used: float,
        current_spend: float,
        budget_limit: float,
        assessment_id: Optional[str] = None
    ) -> bool:
        """Send custom webhook notification"""
        try:
            payload = {
                "event": "ai_budget_alert",
                "organization_id": organization_id,
                "assessment_id": assessment_id,
                "alert_level": alert_level,
                "budget_status": {
                    "current_spend_usd": current_spend,
                    "budget_limit_usd": budget_limit,
                    "percent_used": percent_used,
                    "remaining_usd": budget_limit - current_spend
                },
                "timestamp": datetime.utcnow().isoformat()
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(webhook_url, json=payload, timeout=10) as resp:
                    return resp.status in [200, 201, 202, 204]

        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return False
