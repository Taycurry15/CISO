"""
AI Cost Tracking Service
Logs all AI API calls for cost monitoring and analytics
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import asyncpg

logger = logging.getLogger(__name__)


class AICostService:
    """
    Service for tracking AI usage and costs

    Logs every AI API call with:
    - Token usage (input/output/total)
    - Cost in USD
    - Operation type (embedding, analysis, etc.)
    - Associated entities (user, assessment, control)
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize AI cost tracking service

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    async def log_usage(
        self,
        organization_id: str,
        user_id: str,
        operation_type: str,
        model_name: str,
        provider: str,
        total_tokens: int,
        cost_usd: float,
        assessment_id: Optional[str] = None,
        control_id: Optional[str] = None,
        document_id: Optional[str] = None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        request_id: Optional[str] = None,
        response_time_ms: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an AI API usage event

        Args:
            organization_id: Organization ID
            user_id: User who triggered the operation
            operation_type: Type of operation (embedding, analysis, rag_query, etc.)
            model_name: AI model used (e.g., 'gpt-4-turbo-preview')
            provider: AI provider (openai, anthropic)
            total_tokens: Total tokens used
            cost_usd: Cost in USD
            assessment_id: Optional assessment ID
            control_id: Optional control ID
            document_id: Optional document ID
            input_tokens: Input tokens (for chat/completion models)
            output_tokens: Output tokens (for chat/completion models)
            request_id: Provider's request ID
            response_time_ms: Response time in milliseconds
            metadata: Additional context (JSON)

        Returns:
            Usage record ID
        """
        try:
            async with self.db_pool.acquire() as conn:
                usage_id = await conn.fetchval(
                    """
                    INSERT INTO ai_usage (
                        organization_id,
                        user_id,
                        assessment_id,
                        control_id,
                        document_id,
                        operation_type,
                        model_name,
                        provider,
                        input_tokens,
                        output_tokens,
                        total_tokens,
                        cost_usd,
                        request_id,
                        response_time_ms,
                        metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    RETURNING id
                    """,
                    organization_id,
                    user_id,
                    assessment_id,
                    control_id,
                    document_id,
                    operation_type,
                    model_name,
                    provider,
                    input_tokens,
                    output_tokens,
                    total_tokens,
                    Decimal(str(cost_usd)),  # Convert to Decimal for precision
                    request_id,
                    response_time_ms,
                    metadata or {}
                )

                logger.info(
                    f"Logged AI usage: {operation_type} with {model_name} "
                    f"({total_tokens} tokens, ${cost_usd:.6f})"
                )

                return str(usage_id)

        except Exception as e:
            logger.error(f"Failed to log AI usage: {e}")
            # Don't raise - cost tracking failure shouldn't break AI features
            return None

    async def get_assessment_costs(
        self,
        assessment_id: str,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get AI costs for a specific assessment

        Args:
            assessment_id: Assessment ID
            organization_id: Organization ID (for access control)

        Returns:
            Cost summary with breakdown by operation type
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Overall summary
                summary = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as operation_count,
                        SUM(total_tokens) as total_tokens,
                        SUM(cost_usd) as total_cost_usd,
                        MIN(created_at) as first_operation,
                        MAX(created_at) as last_operation
                    FROM ai_usage
                    WHERE assessment_id = $1 AND organization_id = $2
                    """,
                    assessment_id,
                    organization_id
                )

                # Breakdown by operation type
                breakdown = await conn.fetch(
                    """
                    SELECT
                        operation_type,
                        model_name,
                        COUNT(*) as count,
                        SUM(total_tokens) as tokens,
                        SUM(cost_usd) as cost_usd
                    FROM ai_usage
                    WHERE assessment_id = $1 AND organization_id = $2
                    GROUP BY operation_type, model_name
                    ORDER BY cost_usd DESC
                    """,
                    assessment_id,
                    organization_id
                )

                return {
                    "assessment_id": assessment_id,
                    "total_operations": summary['operation_count'],
                    "total_tokens": summary['total_tokens'],
                    "total_cost_usd": float(summary['total_cost_usd'] or 0),
                    "first_operation": summary['first_operation'],
                    "last_operation": summary['last_operation'],
                    "breakdown": [
                        {
                            "operation_type": row['operation_type'],
                            "model_name": row['model_name'],
                            "count": row['count'],
                            "tokens": row['tokens'],
                            "cost_usd": float(row['cost_usd'])
                        }
                        for row in breakdown
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to get assessment costs: {e}")
            raise

    async def get_organization_costs(
        self,
        organization_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get AI costs for an organization

        Args:
            organization_id: Organization ID
            start_date: Optional start date (defaults to 30 days ago)
            end_date: Optional end date (defaults to now)

        Returns:
            Cost summary with daily breakdown
        """
        if start_date is None:
            start_date = datetime.utcnow() - timedelta(days=30)
        if end_date is None:
            end_date = datetime.utcnow()

        try:
            async with self.db_pool.acquire() as conn:
                # Overall summary
                summary = await conn.fetchrow(
                    """
                    SELECT
                        COUNT(*) as operation_count,
                        SUM(total_tokens) as total_tokens,
                        SUM(cost_usd) as total_cost_usd
                    FROM ai_usage
                    WHERE organization_id = $1
                      AND created_at >= $2
                      AND created_at <= $3
                    """,
                    organization_id,
                    start_date,
                    end_date
                )

                # Daily breakdown
                daily = await conn.fetch(
                    """
                    SELECT
                        DATE(created_at) as date,
                        COUNT(*) as operations,
                        SUM(total_tokens) as tokens,
                        SUM(cost_usd) as cost_usd
                    FROM ai_usage
                    WHERE organization_id = $1
                      AND created_at >= $2
                      AND created_at <= $3
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                    """,
                    organization_id,
                    start_date,
                    end_date
                )

                # Breakdown by operation type
                operations = await conn.fetch(
                    """
                    SELECT
                        operation_type,
                        COUNT(*) as count,
                        SUM(total_tokens) as tokens,
                        SUM(cost_usd) as cost_usd
                    FROM ai_usage
                    WHERE organization_id = $1
                      AND created_at >= $2
                      AND created_at <= $3
                    GROUP BY operation_type
                    ORDER BY cost_usd DESC
                    """,
                    organization_id,
                    start_date,
                    end_date
                )

                return {
                    "organization_id": organization_id,
                    "period": {
                        "start": start_date.isoformat(),
                        "end": end_date.isoformat()
                    },
                    "summary": {
                        "total_operations": summary['operation_count'],
                        "total_tokens": summary['total_tokens'],
                        "total_cost_usd": float(summary['total_cost_usd'] or 0)
                    },
                    "daily_breakdown": [
                        {
                            "date": row['date'].isoformat(),
                            "operations": row['operations'],
                            "tokens": row['tokens'],
                            "cost_usd": float(row['cost_usd'])
                        }
                        for row in daily
                    ],
                    "operation_breakdown": [
                        {
                            "operation_type": row['operation_type'],
                            "count": row['count'],
                            "tokens": row['tokens'],
                            "cost_usd": float(row['cost_usd'])
                        }
                        for row in operations
                    ]
                }

        except Exception as e:
            logger.error(f"Failed to get organization costs: {e}")
            raise

    async def get_recent_usage(
        self,
        organization_id: str,
        limit: int = 100
    ) -> list:
        """
        Get recent AI usage records

        Args:
            organization_id: Organization ID
            limit: Maximum number of records to return

        Returns:
            List of recent usage records
        """
        try:
            async with self.db_pool.acquire() as conn:
                records = await conn.fetch(
                    """
                    SELECT
                        id,
                        user_id,
                        assessment_id,
                        control_id,
                        operation_type,
                        model_name,
                        provider,
                        total_tokens,
                        cost_usd,
                        response_time_ms,
                        created_at
                    FROM ai_usage
                    WHERE organization_id = $1
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    organization_id,
                    limit
                )

                return [
                    {
                        "id": str(row['id']),
                        "user_id": str(row['user_id']),
                        "assessment_id": str(row['assessment_id']) if row['assessment_id'] else None,
                        "control_id": row['control_id'],
                        "operation_type": row['operation_type'],
                        "model_name": row['model_name'],
                        "provider": row['provider'],
                        "total_tokens": row['total_tokens'],
                        "cost_usd": float(row['cost_usd']),
                        "response_time_ms": row['response_time_ms'],
                        "created_at": row['created_at'].isoformat()
                    }
                    for row in records
                ]

        except Exception as e:
            logger.error(f"Failed to get recent usage: {e}")
            raise

    def calculate_cost(
        self,
        model_name: str,
        total_tokens: int,
        input_tokens: int = 0,
        output_tokens: int = 0
    ) -> float:
        """
        Calculate cost for AI operation based on model pricing

        Args:
            model_name: Model name
            total_tokens: Total tokens used
            input_tokens: Input tokens (for models with different pricing)
            output_tokens: Output tokens (for models with different pricing)

        Returns:
            Cost in USD
        """
        # Pricing per 1M tokens (as of 2024)
        pricing = {
            # OpenAI Embeddings
            "text-embedding-ada-002": 0.0001,
            "text-embedding-3-small": 0.00002,
            "text-embedding-3-large": 0.00013,

            # OpenAI GPT-4
            "gpt-4-turbo-preview": {
                "input": 0.01,
                "output": 0.03
            },
            "gpt-4": {
                "input": 0.03,
                "output": 0.06
            },

            # OpenAI GPT-3.5
            "gpt-3.5-turbo": {
                "input": 0.0005,
                "output": 0.0015
            },

            # Anthropic Claude
            "claude-3-5-sonnet-20241022": {
                "input": 0.003,
                "output": 0.015
            },
            "claude-3-opus-20240229": {
                "input": 0.015,
                "output": 0.075
            }
        }

        model_pricing = pricing.get(model_name, 0.0001)

        if isinstance(model_pricing, dict):
            # Different pricing for input/output
            input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
            output_cost = (output_tokens / 1_000_000) * model_pricing["output"]
            return input_cost + output_cost
        else:
            # Single price per token
            return (total_tokens / 1_000_000) * model_pricing
