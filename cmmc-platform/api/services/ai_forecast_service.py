"""
AI Cost Forecasting Service
Predict AI costs based on assessment size and historical data
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import asyncpg
import statistics

logger = logging.getLogger(__name__)


class AICostForecaster:
    """
    Service for predicting AI costs based on assessment characteristics

    Uses historical data to forecast costs for new assessments by analyzing:
    - Average cost per control
    - Cost per evidence document
    - Cost per page of documentation
    - CMMC level complexity multipliers
    - Operation type distribution
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize AI cost forecasting service

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

        # Default cost estimates (fallback if no historical data)
        # Based on typical CMMC Level 2 assessment
        self.default_costs = {
            'cost_per_control': 0.15,      # $0.15 per control analysis
            'cost_per_document': 0.02,     # $0.02 per document embedding
            'cost_per_page': 0.001,        # $0.001 per page processed
            'cost_per_rag_query': 0.005,   # $0.005 per RAG search
            'base_setup_cost': 0.50,       # $0.50 base assessment setup
        }

        # CMMC level complexity multipliers
        self.level_multipliers = {
            1: 0.7,   # Level 1 is simpler (fewer controls, less complex)
            2: 1.0,   # Level 2 is baseline
            3: 1.5,   # Level 3 is more complex (more controls, stricter)
        }

    async def forecast_assessment_cost(
        self,
        organization_id: str,
        control_count: int,
        document_count: Optional[int] = None,
        page_count: Optional[int] = None,
        cmmc_level: int = 2,
        expected_rag_queries: Optional[int] = None,
        use_historical_data: bool = True
    ) -> Dict[str, Any]:
        """
        Forecast AI costs for a new assessment

        Args:
            organization_id: Organization ID (for historical data)
            control_count: Number of controls to assess
            document_count: Estimated number of evidence documents
            page_count: Estimated total pages in documentation
            cmmc_level: CMMC level (1, 2, or 3)
            expected_rag_queries: Expected number of RAG searches
            use_historical_data: Use org's historical data if available

        Returns:
            Cost forecast with breakdown and confidence interval
        """
        try:
            # Get historical cost data if available
            if use_historical_data:
                historical_costs = await self._get_historical_costs(organization_id)
            else:
                historical_costs = None

            # Use historical averages or defaults
            if historical_costs and historical_costs['assessment_count'] > 0:
                cost_per_control = historical_costs['avg_cost_per_control']
                cost_per_document = historical_costs['avg_cost_per_document']
                cost_per_page = historical_costs.get('avg_cost_per_page', self.default_costs['cost_per_page'])
                cost_per_rag = historical_costs.get('avg_cost_per_rag', self.default_costs['cost_per_rag_query'])
                data_source = 'historical'
                confidence = 'high' if historical_costs['assessment_count'] >= 3 else 'medium'
            else:
                cost_per_control = self.default_costs['cost_per_control']
                cost_per_document = self.default_costs['cost_per_document']
                cost_per_page = self.default_costs['cost_per_page']
                cost_per_rag = self.default_costs['cost_per_rag_query']
                data_source = 'industry_average'
                confidence = 'low'

            # Apply CMMC level multiplier
            level_multiplier = self.level_multipliers.get(cmmc_level, 1.0)

            # Calculate component costs
            base_cost = self.default_costs['base_setup_cost']

            # Control analysis costs
            control_cost = control_count * cost_per_control * level_multiplier

            # Document processing costs
            document_cost = 0.0
            if document_count:
                document_cost = document_count * cost_per_document

            # Page processing costs
            page_cost = 0.0
            if page_count:
                page_cost = page_count * cost_per_page

            # RAG query costs
            rag_cost = 0.0
            if expected_rag_queries:
                rag_cost = expected_rag_queries * cost_per_rag
            else:
                # Estimate RAG queries as 2x control count (typical usage)
                estimated_rag_queries = control_count * 2
                rag_cost = estimated_rag_queries * cost_per_rag

            # Total estimated cost
            total_estimated_cost = base_cost + control_cost + document_cost + page_cost + rag_cost

            # Calculate confidence interval (±20% for low confidence, ±10% for medium, ±5% for high)
            confidence_ranges = {
                'high': 0.05,
                'medium': 0.10,
                'low': 0.20
            }
            margin = confidence_ranges.get(confidence, 0.20)

            min_cost = total_estimated_cost * (1 - margin)
            max_cost = total_estimated_cost * (1 + margin)

            # Get operation breakdown percentages from historical data
            operation_breakdown = await self._get_operation_breakdown(organization_id, use_historical_data)

            # Calculate breakdown by operation
            breakdown = {
                'setup': {
                    'cost': base_cost,
                    'percentage': (base_cost / total_estimated_cost) * 100 if total_estimated_cost > 0 else 0,
                    'description': 'Base assessment setup and initialization'
                },
                'control_analysis': {
                    'cost': control_cost,
                    'percentage': (control_cost / total_estimated_cost) * 100 if total_estimated_cost > 0 else 0,
                    'description': f'AI analysis of {control_count} controls',
                    'unit_cost': cost_per_control * level_multiplier,
                    'units': control_count
                },
                'document_processing': {
                    'cost': document_cost,
                    'percentage': (document_cost / total_estimated_cost) * 100 if total_estimated_cost > 0 else 0,
                    'description': f'Processing {document_count or 0} evidence documents',
                    'unit_cost': cost_per_document,
                    'units': document_count or 0
                },
                'page_processing': {
                    'cost': page_cost,
                    'percentage': (page_cost / total_estimated_cost) * 100 if total_estimated_cost > 0 else 0,
                    'description': f'Text extraction from {page_count or 0} pages',
                    'unit_cost': cost_per_page,
                    'units': page_count or 0
                },
                'rag_queries': {
                    'cost': rag_cost,
                    'percentage': (rag_cost / total_estimated_cost) * 100 if total_estimated_cost > 0 else 0,
                    'description': f'RAG searches for context (~{expected_rag_queries or control_count * 2} queries)',
                    'unit_cost': cost_per_rag,
                    'units': expected_rag_queries or control_count * 2
                }
            }

            # Get comparable assessments
            similar_assessments = await self._get_similar_assessments(
                organization_id,
                control_count,
                cmmc_level
            )

            return {
                'estimated_cost': round(total_estimated_cost, 2),
                'min_cost': round(min_cost, 2),
                'max_cost': round(max_cost, 2),
                'confidence_level': confidence,
                'confidence_interval': f"±{int(margin * 100)}%",
                'data_source': data_source,
                'breakdown': breakdown,
                'parameters': {
                    'control_count': control_count,
                    'document_count': document_count,
                    'page_count': page_count,
                    'cmmc_level': cmmc_level,
                    'level_multiplier': level_multiplier,
                    'expected_rag_queries': expected_rag_queries or control_count * 2
                },
                'similar_assessments': similar_assessments,
                'recommendations': self._get_cost_recommendations(
                    total_estimated_cost,
                    control_count,
                    document_count,
                    page_count
                ),
                'forecasted_at': datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to forecast assessment cost: {e}")
            raise

    async def _get_historical_costs(
        self,
        organization_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get historical cost averages for the organization"""
        try:
            async with self.db_pool.acquire() as conn:
                # Get assessment-level statistics
                stats = await conn.fetchrow(
                    """
                    WITH assessment_stats AS (
                        SELECT
                            a.id as assessment_id,
                            COUNT(DISTINCT u.control_id) as control_count,
                            COUNT(DISTINCT u.document_id) as document_count,
                            SUM(u.cost_usd) as total_cost,
                            SUM(CASE WHEN u.operation_type = 'analysis' THEN u.cost_usd ELSE 0 END) as analysis_cost,
                            SUM(CASE WHEN u.operation_type = 'embedding' THEN u.cost_usd ELSE 0 END) as embedding_cost,
                            SUM(CASE WHEN u.operation_type = 'rag_query' THEN u.cost_usd ELSE 0 END) as rag_cost
                        FROM assessments a
                        LEFT JOIN ai_usage u ON a.id = u.assessment_id
                        WHERE a.organization_id = $1
                          AND u.id IS NOT NULL
                        GROUP BY a.id
                        HAVING SUM(u.cost_usd) > 0
                    )
                    SELECT
                        COUNT(*) as assessment_count,
                        AVG(total_cost) as avg_total_cost,
                        AVG(total_cost / NULLIF(control_count, 0)) as avg_cost_per_control,
                        AVG(total_cost / NULLIF(document_count, 0)) as avg_cost_per_document,
                        AVG(analysis_cost / NULLIF(control_count, 0)) as avg_analysis_per_control,
                        STDDEV(total_cost) as stddev_cost
                    FROM assessment_stats
                    """,
                    organization_id
                )

                if stats and stats['assessment_count'] > 0:
                    return {
                        'assessment_count': stats['assessment_count'],
                        'avg_total_cost': float(stats['avg_total_cost'] or 0),
                        'avg_cost_per_control': float(stats['avg_cost_per_control'] or self.default_costs['cost_per_control']),
                        'avg_cost_per_document': float(stats['avg_cost_per_document'] or self.default_costs['cost_per_document']),
                        'avg_analysis_per_control': float(stats['avg_analysis_per_control'] or 0),
                        'stddev_cost': float(stats['stddev_cost'] or 0)
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to get historical costs: {e}")
            return None

    async def _get_operation_breakdown(
        self,
        organization_id: str,
        use_historical: bool
    ) -> Dict[str, float]:
        """Get typical percentage breakdown by operation type"""
        if not use_historical:
            # Default breakdown based on industry averages
            return {
                'embedding': 0.15,      # 15% embeddings
                'analysis': 0.70,       # 70% AI analysis
                'rag_query': 0.10,      # 10% RAG queries
                'other': 0.05           # 5% misc
            }

        try:
            async with self.db_pool.acquire() as conn:
                breakdown = await conn.fetch(
                    """
                    SELECT
                        operation_type,
                        SUM(cost_usd) as cost
                    FROM ai_usage
                    WHERE organization_id = $1
                    GROUP BY operation_type
                    """,
                    organization_id
                )

                if breakdown:
                    total = sum(float(row['cost']) for row in breakdown)
                    if total > 0:
                        return {
                            row['operation_type']: float(row['cost']) / total
                            for row in breakdown
                        }

                # Fallback to defaults
                return {
                    'embedding': 0.15,
                    'analysis': 0.70,
                    'rag_query': 0.10,
                    'other': 0.05
                }

        except Exception as e:
            logger.error(f"Failed to get operation breakdown: {e}")
            return {
                'embedding': 0.15,
                'analysis': 0.70,
                'rag_query': 0.10,
                'other': 0.05
            }

    async def _get_similar_assessments(
        self,
        organization_id: str,
        control_count: int,
        cmmc_level: int,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Find similar past assessments for comparison"""
        try:
            async with self.db_pool.acquire() as conn:
                # Find assessments with similar characteristics
                similar = await conn.fetch(
                    """
                    WITH assessment_stats AS (
                        SELECT
                            a.id,
                            a.assessment_name,
                            a.cmmc_level,
                            COUNT(DISTINCT u.control_id) as control_count,
                            SUM(u.cost_usd) as total_cost,
                            MAX(u.created_at) as completed_at
                        FROM assessments a
                        LEFT JOIN ai_usage u ON a.id = u.assessment_id
                        WHERE a.organization_id = $1
                          AND u.id IS NOT NULL
                        GROUP BY a.id, a.assessment_name, a.cmmc_level
                        HAVING SUM(u.cost_usd) > 0
                    )
                    SELECT
                        id,
                        assessment_name,
                        cmmc_level,
                        control_count,
                        total_cost,
                        completed_at,
                        ABS(control_count - $2) as control_diff
                    FROM assessment_stats
                    WHERE cmmc_level = $3
                    ORDER BY control_diff ASC, completed_at DESC
                    LIMIT $4
                    """,
                    organization_id,
                    control_count,
                    cmmc_level,
                    limit
                )

                return [
                    {
                        'id': str(row['id']),
                        'name': row['assessment_name'],
                        'cmmc_level': row['cmmc_level'],
                        'control_count': row['control_count'],
                        'total_cost': float(row['total_cost']),
                        'completed_at': row['completed_at'].isoformat() if row['completed_at'] else None,
                        'similarity': 'high' if abs(row['control_diff']) <= 10 else 'medium' if abs(row['control_diff']) <= 25 else 'low'
                    }
                    for row in similar
                ]

        except Exception as e:
            logger.error(f"Failed to get similar assessments: {e}")
            return []

    def _get_cost_recommendations(
        self,
        estimated_cost: float,
        control_count: int,
        document_count: Optional[int],
        page_count: Optional[int]
    ) -> List[str]:
        """Generate cost optimization recommendations"""
        recommendations = []

        # High cost warning
        if estimated_cost > 50:
            recommendations.append(
                f"High estimated cost (${estimated_cost:.2f}). Consider batching assessments or optimizing evidence."
            )

        # Document efficiency
        if document_count and document_count > 500:
            recommendations.append(
                f"Large document count ({document_count}). Consider pre-filtering or consolidating evidence to reduce processing costs."
            )

        # Page efficiency
        if page_count and page_count > 10000:
            recommendations.append(
                f"Large page count ({page_count}). Consider using document summaries or extracting only relevant sections."
            )

        # Control optimization
        if control_count > 100:
            recommendations.append(
                f"Assessing {control_count} controls. Consider focusing on high-risk controls first to prioritize spending."
            )

        # General tips
        if estimated_cost > 20:
            recommendations.append(
                "Tip: Use cached embeddings and reuse RAG results across similar controls to reduce costs."
            )

        # Budget recommendations
        recommended_budget = estimated_cost * 1.25  # 25% buffer
        recommendations.append(
            f"Recommended budget: ${recommended_budget:.2f} (includes 25% buffer for variations)"
        )

        return recommendations

    async def forecast_monthly_costs(
        self,
        organization_id: str,
        planned_assessments: List[Dict[str, int]],
        historical_months: int = 3
    ) -> Dict[str, Any]:
        """
        Forecast monthly costs based on planned assessments

        Args:
            organization_id: Organization ID
            planned_assessments: List of dicts with control_count, document_count, etc.
            historical_months: Number of months of history to analyze

        Returns:
            Monthly cost forecast with trends
        """
        try:
            # Get historical monthly spending
            async with self.db_pool.acquire() as conn:
                historical = await conn.fetch(
                    """
                    SELECT
                        DATE_TRUNC('month', created_at) as month,
                        SUM(cost_usd) as total_cost,
                        COUNT(DISTINCT assessment_id) as assessment_count
                    FROM ai_usage
                    WHERE organization_id = $1
                      AND created_at >= NOW() - INTERVAL '1 month' * $2
                    GROUP BY DATE_TRUNC('month', created_at)
                    ORDER BY month DESC
                    """,
                    organization_id,
                    historical_months
                )

            # Calculate average monthly spend
            if historical:
                avg_monthly_cost = statistics.mean([float(row['total_cost']) for row in historical])
                avg_assessments_per_month = statistics.mean([row['assessment_count'] for row in historical])
            else:
                avg_monthly_cost = 0
                avg_assessments_per_month = 0

            # Forecast costs for planned assessments
            total_planned_cost = 0
            planned_details = []

            for assessment in planned_assessments:
                forecast = await self.forecast_assessment_cost(
                    organization_id=organization_id,
                    control_count=assessment.get('control_count', 110),
                    document_count=assessment.get('document_count'),
                    page_count=assessment.get('page_count'),
                    cmmc_level=assessment.get('cmmc_level', 2)
                )
                total_planned_cost += forecast['estimated_cost']
                planned_details.append({
                    'assessment': assessment,
                    'estimated_cost': forecast['estimated_cost'],
                    'cost_range': f"${forecast['min_cost']:.2f} - ${forecast['max_cost']:.2f}"
                })

            # Compare with historical average
            if avg_monthly_cost > 0:
                variance = ((total_planned_cost - avg_monthly_cost) / avg_monthly_cost) * 100
                trend = 'increasing' if variance > 10 else 'decreasing' if variance < -10 else 'stable'
            else:
                variance = 0
                trend = 'new'

            return {
                'planned_monthly_cost': round(total_planned_cost, 2),
                'historical_avg_monthly': round(avg_monthly_cost, 2),
                'variance_percentage': round(variance, 1),
                'trend': trend,
                'planned_assessment_count': len(planned_assessments),
                'avg_historical_assessments': round(avg_assessments_per_month, 1),
                'planned_assessments': planned_details,
                'historical_data': [
                    {
                        'month': row['month'].strftime('%Y-%m'),
                        'cost': float(row['total_cost']),
                        'assessment_count': row['assessment_count']
                    }
                    for row in historical
                ] if historical else [],
                'recommendations': self._get_monthly_recommendations(
                    total_planned_cost,
                    avg_monthly_cost,
                    len(planned_assessments)
                )
            }

        except Exception as e:
            logger.error(f"Failed to forecast monthly costs: {e}")
            raise

    def _get_monthly_recommendations(
        self,
        planned_cost: float,
        historical_avg: float,
        planned_count: int
    ) -> List[str]:
        """Generate monthly cost recommendations"""
        recommendations = []

        if planned_cost > historical_avg * 1.5:
            recommendations.append(
                f"Planned costs (${planned_cost:.2f}) are 50%+ higher than historical average (${historical_avg:.2f}). Consider spreading assessments across multiple months."
            )

        if planned_count > 5:
            recommendations.append(
                f"Planning {planned_count} assessments. Consider batching to optimize AI usage and reduce per-assessment overhead."
            )

        if planned_cost > 100:
            recommendations.append(
                "Consider setting a monthly budget alert to monitor spending throughout the month."
            )

        return recommendations
