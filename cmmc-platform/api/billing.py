"""
Billing Integration (Stripe)
============================
Stripe integration for subscription management and billing.

Features:
- Subscription plans (Starter, Professional, Enterprise)
- Usage-based billing
- Payment method management
- Invoice generation
- Subscription upgrades/downgrades
- Trial management
- Webhook handling for Stripe events
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from enum import Enum
import asyncpg
import logging
import json
import os

logger = logging.getLogger(__name__)

# Stripe configuration (would use actual stripe library in production)
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_...")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_test_...")


class SubscriptionPlan(str, Enum):
    """Subscription plan tiers."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    TRIAL = "trial"


class SubscriptionStatus(str, Enum):
    """Subscription status."""
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class BillingInterval(str, Enum):
    """Billing interval."""
    MONTHLY = "monthly"
    ANNUAL = "annual"


# =============================================================================
# PRICING PLANS
# =============================================================================

PRICING_PLANS = {
    SubscriptionPlan.STARTER: {
        "name": "Starter",
        "description": "For small organizations starting their CMMC journey",
        "monthly_price": 299,
        "annual_price": 2990,  # ~$250/month
        "features": [
            "1 active assessment",
            "Up to 5 users",
            "CMMC Level 1 & 2",
            "Evidence management",
            "SSP/POA&M generation",
            "Email support"
        ],
        "limits": {
            "assessments": 1,
            "users": 5,
            "max_cmmc_level": 2,
            "integrations": 2,
            "storage_gb": 10
        }
    },
    SubscriptionPlan.PROFESSIONAL: {
        "name": "Professional",
        "description": "For growing organizations with advanced compliance needs",
        "monthly_price": 799,
        "annual_price": 7990,  # ~$665/month
        "features": [
            "5 active assessments",
            "Up to 25 users",
            "All CMMC Levels (1-3)",
            "Full integration suite",
            "API access",
            "Priority support",
            "White-labeling",
            "Custom controls"
        ],
        "limits": {
            "assessments": 5,
            "users": 25,
            "max_cmmc_level": 3,
            "integrations": 10,
            "storage_gb": 100
        }
    },
    SubscriptionPlan.ENTERPRISE: {
        "name": "Enterprise",
        "description": "For large organizations and MSPs",
        "monthly_price": 2499,
        "annual_price": 24990,  # ~$2082/month
        "features": [
            "Unlimited assessments",
            "Unlimited users",
            "All CMMC Levels",
            "Unlimited integrations",
            "Dedicated support",
            "SLA guarantees",
            "Custom deployment",
            "C3PAO workflow",
            "Multi-organization management"
        ],
        "limits": {
            "assessments": -1,  # unlimited
            "users": -1,
            "max_cmmc_level": 3,
            "integrations": -1,
            "storage_gb": -1
        }
    }
}


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class CreateSubscriptionRequest(BaseModel):
    """Create subscription request."""
    plan: SubscriptionPlan
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    payment_method_id: Optional[str] = None
    trial_days: int = 14


class UpdateSubscriptionRequest(BaseModel):
    """Update subscription request."""
    plan: Optional[SubscriptionPlan] = None
    billing_interval: Optional[BillingInterval] = None


class PaymentMethodRequest(BaseModel):
    """Add payment method request."""
    stripe_payment_method_id: str
    set_as_default: bool = True


# =============================================================================
# BILLING SERVICE
# =============================================================================

class BillingService:
    """Billing service for Stripe integration."""

    def __init__(self, conn: asyncpg.Connection):
        """Initialize billing service."""
        self.conn = conn

    async def create_subscription(
        self,
        organization_id: str,
        request: CreateSubscriptionRequest
    ) -> Dict[str, Any]:
        """
        Create a new subscription.

        Args:
            organization_id: Organization UUID
            request: Subscription creation request

        Returns:
            Subscription details
        """
        plan_details = PRICING_PLANS[request.plan]

        # Calculate price based on interval
        price = plan_details['monthly_price'] if request.billing_interval == BillingInterval.MONTHLY else plan_details['annual_price']

        # In production, create Stripe subscription here
        # stripe_subscription = stripe.Subscription.create(...)

        # For now, create local subscription record
        trial_end = datetime.utcnow() + timedelta(days=request.trial_days) if request.trial_days > 0 else None

        subscription_id = await self.conn.fetchval(
            """
            INSERT INTO subscriptions
            (organization_id, plan, billing_interval, status, price_cents,
             trial_end, current_period_start, current_period_end)
            VALUES ($1, $2, $3, $4, $5, $6, NOW(), NOW() + INTERVAL '1 month')
            RETURNING id
            """,
            organization_id,
            request.plan.value,
            request.billing_interval.value,
            SubscriptionStatus.TRIALING.value if trial_end else SubscriptionStatus.ACTIVE.value,
            price,
            trial_end
        )

        # Store payment method if provided
        if request.payment_method_id:
            await self._add_payment_method(
                organization_id,
                request.payment_method_id,
                set_as_default=True
            )

        logger.info(f"Subscription created: {subscription_id} for org {organization_id}")

        return {
            "id": str(subscription_id),
            "organization_id": organization_id,
            "plan": request.plan.value,
            "billing_interval": request.billing_interval.value,
            "status": SubscriptionStatus.TRIALING.value if trial_end else SubscriptionStatus.ACTIVE.value,
            "price": price / 100,  # Convert cents to dollars
            "trial_end": trial_end.isoformat() if trial_end else None,
            "features": plan_details['features'],
            "limits": plan_details['limits']
        }

    async def get_subscription(
        self,
        organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get current subscription for organization.

        Args:
            organization_id: Organization UUID

        Returns:
            Subscription details or None
        """
        subscription = await self.conn.fetchrow(
            """
            SELECT
                id, plan, billing_interval, status, price_cents,
                trial_end, current_period_start, current_period_end,
                canceled_at, created_at
            FROM subscriptions
            WHERE organization_id = $1
            AND status != 'canceled'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            organization_id
        )

        if not subscription:
            return None

        plan_details = PRICING_PLANS.get(SubscriptionPlan(subscription['plan']))

        # Get usage statistics
        usage = await self._get_usage_statistics(organization_id)

        return {
            "id": str(subscription['id']),
            "plan": subscription['plan'],
            "plan_name": plan_details['name'] if plan_details else subscription['plan'],
            "billing_interval": subscription['billing_interval'],
            "status": subscription['status'],
            "price": subscription['price_cents'] / 100,
            "trial_end": subscription['trial_end'].isoformat() if subscription['trial_end'] else None,
            "current_period_start": subscription['current_period_start'].isoformat(),
            "current_period_end": subscription['current_period_end'].isoformat(),
            "canceled_at": subscription['canceled_at'].isoformat() if subscription['canceled_at'] else None,
            "features": plan_details['features'] if plan_details else [],
            "limits": plan_details['limits'] if plan_details else {},
            "usage": usage
        }

    async def update_subscription(
        self,
        organization_id: str,
        request: UpdateSubscriptionRequest
    ) -> Dict[str, Any]:
        """
        Update subscription (upgrade/downgrade).

        Args:
            organization_id: Organization UUID
            request: Update request

        Returns:
            Updated subscription details
        """
        current_subscription = await self.get_subscription(organization_id)

        if not current_subscription:
            raise ValueError("No active subscription found")

        # Build update query
        updates = {}
        if request.plan:
            plan_details = PRICING_PLANS[request.plan]
            updates['plan'] = request.plan.value

            # Update price based on plan and interval
            billing_interval = request.billing_interval or current_subscription['billing_interval']
            price = plan_details['monthly_price'] if billing_interval == 'monthly' else plan_details['annual_price']
            updates['price_cents'] = price

        if request.billing_interval:
            updates['billing_interval'] = request.billing_interval.value

            # Recalculate price if plan stays the same
            if not request.plan:
                plan = SubscriptionPlan(current_subscription['plan'])
                plan_details = PRICING_PLANS[plan]
                price = plan_details['monthly_price'] if request.billing_interval == BillingInterval.MONTHLY else plan_details['annual_price']
                updates['price_cents'] = price

        if not updates:
            return current_subscription

        # In production, update Stripe subscription here
        # stripe.Subscription.modify(...)

        # Update local record
        set_clause = ', '.join([f"{k} = ${i+2}" for i, k in enumerate(updates.keys())])
        values = [current_subscription['id']] + list(updates.values())

        await self.conn.execute(
            f"UPDATE subscriptions SET {set_clause}, updated_at = NOW() WHERE id = $1",
            *values
        )

        logger.info(f"Subscription updated: {current_subscription['id']}")

        return await self.get_subscription(organization_id)

    async def cancel_subscription(
        self,
        organization_id: str,
        immediate: bool = False
    ) -> Dict[str, Any]:
        """
        Cancel subscription.

        Args:
            organization_id: Organization UUID
            immediate: Cancel immediately or at period end

        Returns:
            Cancellation details
        """
        current_subscription = await self.get_subscription(organization_id)

        if not current_subscription:
            raise ValueError("No active subscription found")

        # In production, cancel Stripe subscription
        # stripe.Subscription.delete(...) or modify with cancel_at_period_end

        if immediate:
            await self.conn.execute(
                """
                UPDATE subscriptions
                SET status = 'canceled', canceled_at = NOW()
                WHERE id = $1
                """,
                current_subscription['id']
            )
        else:
            await self.conn.execute(
                """
                UPDATE subscriptions
                SET canceled_at = current_period_end
                WHERE id = $1
                """,
                current_subscription['id']
            )

        logger.info(f"Subscription canceled: {current_subscription['id']}")

        return {
            "subscription_id": current_subscription['id'],
            "status": "canceled" if immediate else "canceling",
            "canceled_at": datetime.utcnow().isoformat() if immediate else current_subscription['current_period_end'],
            "access_until": current_subscription['current_period_end']
        }

    async def _add_payment_method(
        self,
        organization_id: str,
        stripe_payment_method_id: str,
        set_as_default: bool = True
    ) -> str:
        """Add payment method."""
        payment_method_id = await self.conn.fetchval(
            """
            INSERT INTO payment_methods
            (organization_id, stripe_payment_method_id, is_default)
            VALUES ($1, $2, $3)
            RETURNING id
            """,
            organization_id,
            stripe_payment_method_id,
            set_as_default
        )

        if set_as_default:
            # Unset other default payment methods
            await self.conn.execute(
                """
                UPDATE payment_methods
                SET is_default = FALSE
                WHERE organization_id = $1 AND id != $2
                """,
                organization_id,
                payment_method_id
            )

        return str(payment_method_id)

    async def get_invoices(
        self,
        organization_id: str,
        limit: int = 12
    ) -> List[Dict[str, Any]]:
        """
        Get invoices for organization.

        Args:
            organization_id: Organization UUID
            limit: Number of invoices to return

        Returns:
            List of invoices
        """
        invoices = await self.conn.fetch(
            """
            SELECT
                id, invoice_number, amount_cents, status,
                period_start, period_end, due_date, paid_at,
                invoice_pdf_url, created_at
            FROM invoices
            WHERE organization_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            organization_id,
            limit
        )

        return [
            {
                "id": str(invoice['id']),
                "invoice_number": invoice['invoice_number'],
                "amount": invoice['amount_cents'] / 100,
                "status": invoice['status'],
                "period_start": invoice['period_start'].isoformat(),
                "period_end": invoice['period_end'].isoformat(),
                "due_date": invoice['due_date'].isoformat() if invoice['due_date'] else None,
                "paid_at": invoice['paid_at'].isoformat() if invoice['paid_at'] else None,
                "pdf_url": invoice['invoice_pdf_url'],
                "created_at": invoice['created_at'].isoformat()
            }
            for invoice in invoices
        ]

    async def _get_usage_statistics(
        self,
        organization_id: str
    ) -> Dict[str, Any]:
        """Get usage statistics for billing."""
        # Get current counts
        assessments_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM assessments WHERE organization_id = $1",
            organization_id
        )

        users_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM users WHERE organization_id = $1 AND active = TRUE",
            organization_id
        )

        integrations_count = await self.conn.fetchval(
            "SELECT COUNT(*) FROM integration_credentials WHERE organization_id = $1 AND active = TRUE",
            organization_id
        )

        # Estimate storage usage (placeholder)
        storage_gb = await self.conn.fetchval(
            """
            SELECT COALESCE(SUM(file_size_bytes), 0) / 1073741824.0
            FROM evidence e
            JOIN assessments a ON e.assessment_id = a.id
            WHERE a.organization_id = $1
            """,
            organization_id
        ) or 0

        return {
            "assessments": assessments_count,
            "users": users_count,
            "integrations": integrations_count,
            "storage_gb": round(storage_gb, 2)
        }

    async def check_limits(
        self,
        organization_id: str,
        resource_type: str
    ) -> bool:
        """
        Check if organization is within subscription limits.

        Args:
            organization_id: Organization UUID
            resource_type: Type of resource (assessments, users, etc.)

        Returns:
            True if within limits, False otherwise
        """
        subscription = await self.get_subscription(organization_id)

        if not subscription:
            return False

        limits = subscription['limits']
        usage = subscription['usage']

        # -1 means unlimited
        limit = limits.get(resource_type, 0)
        if limit == -1:
            return True

        current_usage = usage.get(resource_type, 0)

        return current_usage < limit

    async def handle_stripe_webhook(
        self,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> bool:
        """
        Handle Stripe webhook events.

        Args:
            event_type: Stripe event type
            event_data: Event data from Stripe

        Returns:
            Success status
        """
        logger.info(f"Processing Stripe webhook: {event_type}")

        try:
            if event_type == "invoice.paid":
                await self._handle_invoice_paid(event_data)
            elif event_type == "invoice.payment_failed":
                await self._handle_payment_failed(event_data)
            elif event_type == "customer.subscription.updated":
                await self._handle_subscription_updated(event_data)
            elif event_type == "customer.subscription.deleted":
                await self._handle_subscription_deleted(event_data)
            else:
                logger.warning(f"Unhandled webhook event: {event_type}")

            return True

        except Exception as e:
            logger.error(f"Error handling webhook {event_type}: {str(e)}")
            return False

    async def _handle_invoice_paid(self, event_data: Dict[str, Any]):
        """Handle successful invoice payment."""
        # Update invoice status
        # Send confirmation email
        pass

    async def _handle_payment_failed(self, event_data: Dict[str, Any]):
        """Handle failed payment."""
        # Update subscription status to past_due
        # Send payment failure notification
        pass

    async def _handle_subscription_updated(self, event_data: Dict[str, Any]):
        """Handle subscription update from Stripe."""
        # Sync subscription status with Stripe
        pass

    async def _handle_subscription_deleted(self, event_data: Dict[str, Any]):
        """Handle subscription cancellation."""
        # Mark subscription as canceled
        # Trigger offboarding workflow
        pass
