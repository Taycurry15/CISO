"""
Dashboard Analytics Service

Provides real-time analytics, metrics, and insights for CMMC assessments.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncpg

logger = logging.getLogger(__name__)


@dataclass
class AssessmentOverview:
    """High-level assessment statistics"""
    total_assessments: int
    active_assessments: int
    completed_assessments: int
    draft_assessments: int
    in_progress_assessments: int
    avg_completion_percentage: float
    avg_confidence_score: float
    total_evidence_collected: int


@dataclass
class ControlCompliance:
    """Control compliance metrics"""
    total_controls: int
    controls_met: int
    controls_not_met: int
    controls_partial: int
    controls_na: int
    compliance_percentage: float
    by_domain: Dict[str, Dict[str, int]]
    high_risk_controls: List[Dict[str, Any]]


@dataclass
class ProgressMetrics:
    """Assessment progress over time"""
    date: str
    controls_analyzed: int
    evidence_uploaded: int
    completion_percentage: float


@dataclass
class TeamPerformance:
    """Team productivity metrics"""
    assessor_name: str
    controls_analyzed: int
    evidence_collected: int
    avg_confidence_score: float
    assessments_active: int


@dataclass
class SavingsCalculation:
    """Cost and time savings from automation"""
    manual_hours: float
    automated_hours: float
    hours_saved: float
    cost_savings: float
    provider_inheritance_hours: float
    ai_analysis_hours: float
    report_generation_hours: float


class DashboardService:
    """
    Dashboard Analytics Service

    Provides comprehensive analytics and metrics for assessments,
    controls, evidence, and team performance.
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize dashboard service

        Args:
            db_pool: Database connection pool
        """
        self.db_pool = db_pool

    async def get_assessment_overview(
        self,
        organization_id: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> AssessmentOverview:
        """
        Get high-level assessment overview

        Args:
            organization_id: Filter by organization
            date_from: Filter assessments created after this date
            date_to: Filter assessments created before this date

        Returns:
            AssessmentOverview with statistics
        """
        async with self.db_pool.acquire() as conn:
            # Build query with filters
            query = """
                SELECT
                    COUNT(*) as total_assessments,
                    COUNT(*) FILTER (WHERE status NOT IN ('Completed', 'Archived')) as active_assessments,
                    COUNT(*) FILTER (WHERE status = 'Completed') as completed_assessments,
                    COUNT(*) FILTER (WHERE status = 'Draft') as draft_assessments,
                    COUNT(*) FILTER (WHERE status = 'In Progress') as in_progress_assessments
                FROM assessments
                WHERE 1=1
            """

            params = []
            param_count = 0

            if organization_id:
                param_count += 1
                query += f" AND organization_id = ${param_count}"
                params.append(organization_id)

            if date_from:
                param_count += 1
                query += f" AND created_at >= ${param_count}"
                params.append(date_from)

            if date_to:
                param_count += 1
                query += f" AND created_at <= ${param_count}"
                params.append(date_to)

            stats = await conn.fetchrow(query, *params)

            # Get progress metrics
            progress_query = """
                SELECT
                    AVG(
                        CASE
                            WHEN total_controls > 0
                            THEN (analyzed::FLOAT / total_controls * 100)
                            ELSE 0
                        END
                    ) as avg_completion,
                    AVG(avg_confidence) as avg_confidence
                FROM (
                    SELECT
                        cf.assessment_id,
                        COUNT(*) as total_controls,
                        COUNT(*) FILTER (WHERE cf.status != 'Not Assessed') as analyzed,
                        AVG(cf.ai_confidence_score) FILTER (WHERE cf.ai_confidence_score IS NOT NULL) as avg_confidence
                    FROM control_findings cf
                    JOIN assessments a ON cf.assessment_id = a.id
                    WHERE a.status NOT IN ('Archived')
            """

            if organization_id:
                progress_query += f" AND a.organization_id = ${len(params) + 1}"
                params.append(organization_id)

            progress_query += " GROUP BY cf.assessment_id) subq"

            progress = await conn.fetchrow(progress_query, *params)

            # Get total evidence
            evidence_query = """
                SELECT COUNT(*) as total_evidence
                FROM evidence e
                JOIN assessments a ON e.assessment_id = a.id
                WHERE 1=1
            """

            evidence_params = []
            if organization_id:
                evidence_query += " AND a.organization_id = $1"
                evidence_params.append(organization_id)

            evidence_stats = await conn.fetchrow(evidence_query, *evidence_params)

            return AssessmentOverview(
                total_assessments=stats['total_assessments'],
                active_assessments=stats['active_assessments'],
                completed_assessments=stats['completed_assessments'],
                draft_assessments=stats['draft_assessments'],
                in_progress_assessments=stats['in_progress_assessments'],
                avg_completion_percentage=round(float(progress['avg_completion'] or 0), 1),
                avg_confidence_score=round(float(progress['avg_confidence'] or 0), 2),
                total_evidence_collected=evidence_stats['total_evidence']
            )

    async def get_control_compliance(
        self,
        assessment_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> ControlCompliance:
        """
        Get control compliance metrics

        Args:
            assessment_id: Filter by specific assessment
            organization_id: Filter by organization

        Returns:
            ControlCompliance with detailed metrics
        """
        async with self.db_pool.acquire() as conn:
            # Build query
            query = """
                SELECT
                    COUNT(*) as total_controls,
                    COUNT(*) FILTER (WHERE cf.status = 'Met') as controls_met,
                    COUNT(*) FILTER (WHERE cf.status = 'Not Met') as controls_not_met,
                    COUNT(*) FILTER (WHERE cf.status = 'Partially Met') as controls_partial,
                    COUNT(*) FILTER (WHERE cf.status = 'Not Applicable') as controls_na
                FROM control_findings cf
                JOIN assessments a ON cf.assessment_id = a.id
                WHERE cf.status != 'Not Assessed'
            """

            params = []
            param_count = 0

            if assessment_id:
                param_count += 1
                query += f" AND cf.assessment_id = ${param_count}"
                params.append(assessment_id)

            if organization_id:
                param_count += 1
                query += f" AND a.organization_id = ${param_count}"
                params.append(organization_id)

            stats = await conn.fetchrow(query, *params)

            # Calculate compliance percentage
            total = stats['total_controls']
            met = stats['controls_met']
            compliance_pct = (met / total * 100) if total > 0 else 0

            # Get by domain
            domain_query = """
                SELECT
                    cd.name as domain,
                    COUNT(*) as total,
                    COUNT(*) FILTER (WHERE cf.status = 'Met') as met,
                    COUNT(*) FILTER (WHERE cf.status = 'Not Met') as not_met,
                    COUNT(*) FILTER (WHERE cf.status = 'Partially Met') as partial
                FROM control_findings cf
                JOIN controls c ON cf.control_id = c.id
                JOIN control_domains cd ON c.domain_id = cd.id
                JOIN assessments a ON cf.assessment_id = a.id
                WHERE cf.status != 'Not Assessed'
            """

            domain_params = []
            domain_param_count = 0

            if assessment_id:
                domain_param_count += 1
                domain_query += f" AND cf.assessment_id = ${domain_param_count}"
                domain_params.append(assessment_id)

            if organization_id:
                domain_param_count += 1
                domain_query += f" AND a.organization_id = ${domain_param_count}"
                domain_params.append(organization_id)

            domain_query += " GROUP BY cd.name ORDER BY cd.name"

            domain_stats = await conn.fetch(domain_query, *domain_params)

            by_domain = {}
            for row in domain_stats:
                by_domain[row['domain']] = {
                    'total': row['total'],
                    'met': row['met'],
                    'not_met': row['not_met'],
                    'partial': row['partial'],
                    'compliance_pct': round((row['met'] / row['total'] * 100) if row['total'] > 0 else 0, 1)
                }

            # Get high-risk controls (Not Met in critical domains)
            high_risk_query = """
                SELECT
                    cf.control_id,
                    c.title,
                    cd.name as domain,
                    cf.status,
                    cf.ai_confidence_score
                FROM control_findings cf
                JOIN controls c ON cf.control_id = c.id
                JOIN control_domains cd ON c.domain_id = cd.id
                JOIN assessments a ON cf.assessment_id = a.id
                WHERE cf.status IN ('Not Met', 'Partially Met')
                  AND cd.name IN ('AC', 'IA', 'SC', 'AU')
            """

            high_risk_params = []
            high_risk_param_count = 0

            if assessment_id:
                high_risk_param_count += 1
                high_risk_query += f" AND cf.assessment_id = ${high_risk_param_count}"
                high_risk_params.append(assessment_id)

            if organization_id:
                high_risk_param_count += 1
                high_risk_query += f" AND a.organization_id = ${high_risk_param_count}"
                high_risk_params.append(organization_id)

            high_risk_query += " ORDER BY cf.status DESC, cd.name, cf.control_id LIMIT 10"

            high_risk = await conn.fetch(high_risk_query, *high_risk_params)

            high_risk_controls = [
                {
                    'control_id': row['control_id'],
                    'title': row['title'],
                    'domain': row['domain'],
                    'status': row['status'],
                    'confidence_score': float(row['ai_confidence_score']) if row['ai_confidence_score'] else None
                }
                for row in high_risk
            ]

            return ControlCompliance(
                total_controls=total,
                controls_met=met,
                controls_not_met=stats['controls_not_met'],
                controls_partial=stats['controls_partial'],
                controls_na=stats['controls_na'],
                compliance_percentage=round(compliance_pct, 1),
                by_domain=by_domain,
                high_risk_controls=high_risk_controls
            )

    async def get_progress_over_time(
        self,
        assessment_id: str,
        days: int = 30
    ) -> List[ProgressMetrics]:
        """
        Get assessment progress over time

        Args:
            assessment_id: Assessment ID
            days: Number of days to look back

        Returns:
            List of daily progress metrics
        """
        async with self.db_pool.acquire() as conn:
            # Get assessment start date
            assessment = await conn.fetchrow(
                "SELECT start_date FROM assessments WHERE id = $1",
                assessment_id
            )

            if not assessment or not assessment['start_date']:
                return []

            start_date = assessment['start_date']
            end_date = datetime.utcnow()

            # Generate daily metrics
            # This is a simplified version - in production, you'd track changes over time
            # For now, we'll show current state projected over time

            progress_data = []
            current_day = start_date

            while current_day <= end_date:
                # Get stats for this day
                # In real implementation, you'd track historical data
                stats = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status != 'Not Assessed') as analyzed
                    FROM control_findings
                    WHERE assessment_id = $1
                """, assessment_id)

                evidence_count = await conn.fetchval("""
                    SELECT COUNT(*)
                    FROM evidence
                    WHERE assessment_id = $1
                      AND collection_date <= $2
                """, assessment_id, current_day)

                completion_pct = (stats['analyzed'] / stats['total'] * 100) if stats['total'] > 0 else 0

                progress_data.append(ProgressMetrics(
                    date=current_day.strftime('%Y-%m-%d'),
                    controls_analyzed=stats['analyzed'],
                    evidence_uploaded=evidence_count,
                    completion_percentage=round(completion_pct, 1)
                ))

                current_day += timedelta(days=1)

            return progress_data[-days:]  # Return last N days

    async def get_evidence_statistics(
        self,
        assessment_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive evidence statistics

        Args:
            assessment_id: Filter by assessment
            organization_id: Filter by organization

        Returns:
            Dictionary with evidence statistics
        """
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT
                    COUNT(*) as total_evidence,
                    COUNT(DISTINCT evidence_type) as evidence_types,
                    SUM(file_size) as total_size,
                    AVG(file_size) as avg_size,
                    COUNT(DISTINCT ecl.control_id) as controls_with_evidence
                FROM evidence e
                LEFT JOIN evidence_control_links ecl ON e.id = ecl.evidence_id
                JOIN assessments a ON e.assessment_id = a.id
                WHERE 1=1
            """

            params = []
            param_count = 0

            if assessment_id:
                param_count += 1
                query += f" AND e.assessment_id = ${param_count}"
                params.append(assessment_id)

            if organization_id:
                param_count += 1
                query += f" AND a.organization_id = ${param_count}"
                params.append(organization_id)

            stats = await conn.fetchrow(query, *params)

            # By type
            type_query = """
                SELECT evidence_type, COUNT(*) as count
                FROM evidence e
                JOIN assessments a ON e.assessment_id = a.id
                WHERE 1=1
            """

            type_params = []
            type_param_count = 0

            if assessment_id:
                type_param_count += 1
                type_query += f" AND e.assessment_id = ${type_param_count}"
                type_params.append(assessment_id)

            if organization_id:
                type_param_count += 1
                type_query += f" AND a.organization_id = ${type_param_count}"
                type_params.append(organization_id)

            type_query += " GROUP BY evidence_type ORDER BY count DESC"

            by_type = await conn.fetch(type_query, *type_params)

            # By method
            method_query = """
                SELECT method, COUNT(*) as count
                FROM evidence e
                JOIN assessments a ON e.assessment_id = a.id,
                UNNEST(e.assessment_methods) as method
                WHERE 1=1
            """

            method_params = []
            method_param_count = 0

            if assessment_id:
                method_param_count += 1
                method_query += f" AND e.assessment_id = ${method_param_count}"
                method_params.append(assessment_id)

            if organization_id:
                method_param_count += 1
                method_query += f" AND a.organization_id = ${method_param_count}"
                method_params.append(organization_id)

            method_query += " GROUP BY method ORDER BY count DESC"

            by_method = await conn.fetch(method_query, *method_params)

            return {
                'total_evidence': stats['total_evidence'],
                'evidence_types': stats['evidence_types'],
                'total_size_bytes': stats['total_size'] or 0,
                'avg_size_bytes': int(stats['avg_size']) if stats['avg_size'] else 0,
                'controls_with_evidence': stats['controls_with_evidence'] or 0,
                'by_type': {row['evidence_type']: row['count'] for row in by_type},
                'by_method': {row['method']: row['count'] for row in by_method}
            }

    async def calculate_savings(
        self,
        assessment_id: str,
        hourly_rate: float = 200.0
    ) -> SavingsCalculation:
        """
        Calculate time and cost savings from automation

        Args:
            assessment_id: Assessment ID
            hourly_rate: Assessor hourly rate (default $200)

        Returns:
            SavingsCalculation with detailed breakdown
        """
        async with self.db_pool.acquire() as conn:
            # Get assessment details
            assessment = await conn.fetchrow("""
                SELECT scope FROM assessments WHERE id = $1
            """, assessment_id)

            if not assessment:
                raise ValueError(f"Assessment {assessment_id} not found")

            import json
            scope = json.loads(assessment['scope']) if isinstance(assessment['scope'], str) else assessment['scope']

            # Get control counts
            stats = await conn.fetchrow("""
                SELECT
                    COUNT(*) as total_controls,
                    COUNT(*) FILTER (WHERE status != 'Not Assessed') as analyzed
                FROM control_findings
                WHERE assessment_id = $1
            """, assessment_id)

            total_controls = stats['total_controls']

            # Manual effort estimates
            manual_hours_per_control = 2.0  # 2 hours per control manually
            manual_hours = total_controls * manual_hours_per_control

            # Automated effort
            # - Provider inheritance (from provider service)
            provider_inheritance_hours = 0.0
            if scope.get('cloud_providers'):
                # Estimate based on provider coverage (~38% coverage, ~70 hours saved)
                provider_inheritance_hours = total_controls * 0.38 * manual_hours_per_control

            # - AI analysis (4-6 minutes for all 110 controls vs. manual review)
            ai_analysis_hours = manual_hours - (total_controls * 0.1)  # AI saves ~90% of time

            # - Report generation (SSP + POA&M: seconds vs. 48-96 hours)
            report_generation_hours = 48.0  # Manual SSP/POA&M effort

            # Total automated hours
            automated_hours = manual_hours - provider_inheritance_hours - ai_analysis_hours + report_generation_hours
            automated_hours = max(0.5, automated_hours)  # At least 30 minutes

            # Calculate savings
            hours_saved = manual_hours - automated_hours
            cost_savings = hours_saved * hourly_rate

            return SavingsCalculation(
                manual_hours=round(manual_hours, 1),
                automated_hours=round(automated_hours, 1),
                hours_saved=round(hours_saved, 1),
                cost_savings=round(cost_savings, 2),
                provider_inheritance_hours=round(provider_inheritance_hours, 1),
                ai_analysis_hours=round(ai_analysis_hours * 0.9, 1),  # AI saves 90%
                report_generation_hours=report_generation_hours
            )

    async def get_recent_activity(
        self,
        organization_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get recent activity feed

        Args:
            organization_id: Filter by organization
            limit: Maximum items to return

        Returns:
            List of recent activities
        """
        async with self.db_pool.acquire() as conn:
            # Get recent evidence uploads
            evidence_query = """
                SELECT
                    'evidence_upload' as activity_type,
                    e.created_at as timestamp,
                    e.title as description,
                    a.id as assessment_id,
                    e.collected_by as actor
                FROM evidence e
                JOIN assessments a ON e.assessment_id = a.id
                WHERE 1=1
            """

            params = []
            if organization_id:
                evidence_query += " AND a.organization_id = $1"
                params.append(organization_id)

            evidence_query += f" ORDER BY e.created_at DESC LIMIT {limit}"

            activities = await conn.fetch(evidence_query, *params)

            return [
                {
                    'activity_type': row['activity_type'],
                    'timestamp': row['timestamp'].isoformat(),
                    'description': row['description'],
                    'assessment_id': str(row['assessment_id']),
                    'actor': row['actor']
                }
                for row in activities
            ]
