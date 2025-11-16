"""
Continuous Monitoring Dashboard
================================
Provides real-time compliance monitoring and analytics capabilities.

Features:
- Dashboard summary with key metrics
- Control compliance tracking
- Recent activity feed
- Risk metrics and trends
- Integration status monitoring
- Evidence statistics
- Alert notifications
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncpg
import logging

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, Enum):
    COMPLIANCE_DROP = "compliance_drop"
    NEW_VULNERABILITY = "new_vulnerability"
    EVIDENCE_EXPIRED = "evidence_expired"
    INTEGRATION_FAILURE = "integration_failure"
    POA_M_OVERDUE = "poam_overdue"
    CONTROL_NOT_MET = "control_not_met"


async def get_dashboard_summary(
    organization_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Get high-level dashboard summary for an organization.

    Returns:
        Dashboard summary including:
        - Total assessments
        - Active assessments
        - Overall SPRS score
        - Control compliance percentage
        - Evidence count
        - Open POA&M items
        - Recent alerts
    """
    logger.info(f"Generating dashboard summary for organization {organization_id}")

    # Get assessment statistics
    assessment_stats = await conn.fetchrow(
        """
        SELECT
            COUNT(*) as total_assessments,
            COUNT(*) FILTER (WHERE status IN ('in_progress', 'under_review')) as active_assessments,
            COUNT(*) FILTER (WHERE status = 'complete') as completed_assessments
        FROM assessments
        WHERE organization_id = $1
        """,
        organization_id
    )

    # Get latest SPRS score across all assessments
    latest_sprs = await conn.fetchrow(
        """
        SELECT
            AVG(s.score) as avg_score,
            MAX(s.score) as max_score,
            MIN(s.score) as min_score
        FROM sprs_scores s
        JOIN assessments a ON s.assessment_id = a.id
        WHERE a.organization_id = $1
            AND s.calculation_date >= NOW() - INTERVAL '30 days'
        """,
        organization_id
    )

    # Get control compliance statistics
    control_stats = await conn.fetchrow(
        """
        SELECT
            COUNT(*) as total_findings,
            COUNT(*) FILTER (WHERE status = 'Met') as met,
            COUNT(*) FILTER (WHERE status = 'Partially Met') as partially_met,
            COUNT(*) FILTER (WHERE status = 'Not Met') as not_met,
            COUNT(*) FILTER (WHERE status = 'Not Assessed') as not_assessed
        FROM control_findings cf
        JOIN assessments a ON cf.assessment_id = a.id
        WHERE a.organization_id = $1
        """,
        organization_id
    )

    # Calculate compliance percentage
    total_findings = control_stats['total_findings'] or 0
    met = control_stats['met'] or 0
    partially_met = control_stats['partially_met'] or 0

    compliance_percentage = 0.0
    if total_findings > 0:
        compliance_percentage = ((met + (partially_met * 0.5)) / total_findings) * 100

    # Get evidence statistics
    evidence_stats = await conn.fetchrow(
        """
        SELECT
            COUNT(*) as total_evidence,
            COUNT(*) FILTER (WHERE status = 'approved') as approved,
            COUNT(*) FILTER (WHERE status = 'pending_review') as pending,
            COUNT(*) FILTER (WHERE status = 'rejected') as rejected
        FROM evidence e
        JOIN assessments a ON e.assessment_id = a.id
        WHERE a.organization_id = $1
        """,
        organization_id
    )

    # Get POA&M statistics
    poam_stats = await conn.fetchrow(
        """
        SELECT
            COUNT(*) as total_poams,
            COUNT(*) FILTER (WHERE status = 'open') as open,
            COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress,
            COUNT(*) FILTER (WHERE status = 'completed') as completed,
            COUNT(*) FILTER (WHERE estimated_completion_date < CURRENT_DATE AND status != 'completed') as overdue
        FROM poam_items p
        JOIN assessments a ON p.assessment_id = a.id
        WHERE a.organization_id = $1
        """,
        organization_id
    )

    # Get recent alerts (last 7 days)
    recent_alerts = await get_recent_alerts(organization_id, conn, days=7)

    return {
        'organization_id': organization_id,
        'timestamp': datetime.utcnow().isoformat(),
        'assessments': {
            'total': assessment_stats['total_assessments'] or 0,
            'active': assessment_stats['active_assessments'] or 0,
            'completed': assessment_stats['completed_assessments'] or 0
        },
        'sprs_score': {
            'average': round(float(latest_sprs['avg_score'] or 0), 2),
            'highest': latest_sprs['max_score'] or 0,
            'lowest': latest_sprs['min_score'] or 0
        },
        'compliance': {
            'percentage': round(compliance_percentage, 2),
            'total_controls': total_findings,
            'met': met,
            'partially_met': partially_met,
            'not_met': control_stats['not_met'] or 0,
            'not_assessed': control_stats['not_assessed'] or 0
        },
        'evidence': {
            'total': evidence_stats['total_evidence'] or 0,
            'approved': evidence_stats['approved'] or 0,
            'pending': evidence_stats['pending'] or 0,
            'rejected': evidence_stats['rejected'] or 0
        },
        'poam': {
            'total': poam_stats['total_poams'] or 0,
            'open': poam_stats['open'] or 0,
            'in_progress': poam_stats['in_progress'] or 0,
            'completed': poam_stats['completed'] or 0,
            'overdue': poam_stats['overdue'] or 0
        },
        'alerts': {
            'count': len(recent_alerts),
            'recent': recent_alerts[:5]  # Top 5 recent alerts
        }
    }


async def get_control_compliance_overview(
    assessment_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Get detailed control compliance overview for an assessment.

    Returns:
        Control compliance breakdown by family and domain
    """
    logger.info(f"Getting control compliance overview for assessment {assessment_id}")

    # Get compliance by family
    family_compliance = await conn.fetch(
        """
        SELECT
            c.family,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE cf.status = 'Met') as met,
            COUNT(*) FILTER (WHERE cf.status = 'Partially Met') as partially_met,
            COUNT(*) FILTER (WHERE cf.status = 'Not Met') as not_met,
            COUNT(*) FILTER (WHERE cf.status = 'Not Assessed') as not_assessed
        FROM controls c
        LEFT JOIN control_findings cf ON c.id = cf.control_id AND cf.assessment_id = $1
        WHERE c.framework = 'NIST 800-171'
        GROUP BY c.family
        ORDER BY c.family
        """,
        assessment_id
    )

    families = []
    for row in family_compliance:
        total = row['total'] or 0
        met = row['met'] or 0
        partially_met = row['partially_met'] or 0

        compliance_pct = 0.0
        if total > 0:
            compliance_pct = ((met + (partially_met * 0.5)) / total) * 100

        families.append({
            'family': row['family'],
            'total': total,
            'met': met,
            'partially_met': partially_met,
            'not_met': row['not_met'] or 0,
            'not_assessed': row['not_assessed'] or 0,
            'compliance_percentage': round(compliance_pct, 2)
        })

    # Get top non-compliant controls
    non_compliant = await conn.fetch(
        """
        SELECT
            cf.control_id,
            c.title,
            c.family,
            cf.status,
            cf.ai_confidence_score,
            EXISTS(SELECT 1 FROM poam_items WHERE finding_id = cf.id) as has_poam
        FROM control_findings cf
        JOIN controls c ON cf.control_id = c.id
        WHERE cf.assessment_id = $1
            AND cf.status IN ('Not Met', 'Partially Met')
        ORDER BY
            CASE cf.status
                WHEN 'Not Met' THEN 1
                WHEN 'Partially Met' THEN 2
            END,
            cf.ai_confidence_score DESC
        LIMIT 10
        """,
        assessment_id
    )

    return {
        'assessment_id': assessment_id,
        'timestamp': datetime.utcnow().isoformat(),
        'family_breakdown': families,
        'top_non_compliant_controls': [
            {
                'control_id': row['control_id'],
                'title': row['title'],
                'family': row['family'],
                'status': row['status'],
                'confidence': row['ai_confidence_score'],
                'has_poam': row['has_poam']
            }
            for row in non_compliant
        ]
    }


async def get_recent_activity(
    organization_id: str,
    conn: asyncpg.Connection,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Get recent activity feed for an organization.

    Returns:
        List of recent activities across assessments, evidence, and findings
    """
    logger.info(f"Getting recent activity for organization {organization_id}")

    # Get recent audit log entries
    activities = await conn.fetch(
        """
        SELECT
            al.id,
            al.table_name,
            al.operation,
            al.changed_data,
            al.changed_at,
            u.email as user_email
        FROM audit_log al
        LEFT JOIN users u ON al.changed_by = u.id
        JOIN assessments a ON (
            (al.table_name = 'evidence' AND (al.changed_data->>'assessment_id')::uuid = a.id)
            OR (al.table_name = 'control_findings' AND (al.changed_data->>'assessment_id')::uuid = a.id)
            OR (al.table_name = 'poam_items' AND (al.changed_data->>'assessment_id')::uuid = a.id)
        )
        WHERE a.organization_id = $1
        ORDER BY al.changed_at DESC
        LIMIT $2
        """,
        organization_id,
        limit
    )

    activity_feed = []
    for activity in activities:
        activity_feed.append({
            'id': str(activity['id']),
            'type': activity['table_name'],
            'operation': activity['operation'],
            'user': activity['user_email'] or 'System',
            'timestamp': activity['changed_at'].isoformat(),
            'details': activity['changed_data']
        })

    return activity_feed


async def get_integration_status(
    organization_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Get status of all integrations for an organization.

    Returns:
        Integration status including last run time, success rate, and errors
    """
    logger.info(f"Getting integration status for organization {organization_id}")

    # Get integration statistics
    integration_stats = await conn.fetch(
        """
        SELECT
            integration_type,
            COUNT(*) as total_runs,
            COUNT(*) FILTER (WHERE status = 'success') as successful,
            COUNT(*) FILTER (WHERE status = 'failed') as failed,
            MAX(started_at) as last_run,
            SUM(records_processed) as total_records_processed,
            SUM(errors_count) as total_errors
        FROM integration_runs
        WHERE organization_id = $1
        GROUP BY integration_type
        ORDER BY last_run DESC
        """,
        organization_id
    )

    integrations = []
    for stat in integration_stats:
        total = stat['total_runs'] or 0
        successful = stat['successful'] or 0

        success_rate = 0.0
        if total > 0:
            success_rate = (successful / total) * 100

        # Determine health status
        health = 'healthy'
        if success_rate < 50:
            health = 'critical'
        elif success_rate < 75:
            health = 'degraded'
        elif success_rate < 95:
            health = 'warning'

        integrations.append({
            'type': stat['integration_type'],
            'total_runs': total,
            'successful': successful,
            'failed': stat['failed'] or 0,
            'success_rate': round(success_rate, 2),
            'last_run': stat['last_run'].isoformat() if stat['last_run'] else None,
            'total_records_processed': stat['total_records_processed'] or 0,
            'total_errors': stat['total_errors'] or 0,
            'health': health
        })

    return {
        'organization_id': organization_id,
        'timestamp': datetime.utcnow().isoformat(),
        'integrations': integrations
    }


async def get_risk_metrics(
    assessment_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Get risk metrics for an assessment.

    Returns:
        Risk metrics including:
        - Risk score distribution
        - Critical findings
        - Overdue POA&Ms
        - High-risk controls
    """
    logger.info(f"Getting risk metrics for assessment {assessment_id}")

    # Get POA&M risk distribution
    poam_risk = await conn.fetch(
        """
        SELECT
            risk_level,
            COUNT(*) as count
        FROM poam_items
        WHERE assessment_id = $1
        GROUP BY risk_level
        """,
        assessment_id
    )

    risk_distribution = {
        'Critical': 0,
        'High': 0,
        'Medium': 0,
        'Low': 0
    }
    for row in poam_risk:
        if row['risk_level'] in risk_distribution:
            risk_distribution[row['risk_level']] = row['count']

    # Get critical findings
    critical_findings = await conn.fetch(
        """
        SELECT
            cf.control_id,
            c.title,
            cf.status,
            cf.assessor_narrative
        FROM control_findings cf
        JOIN controls c ON cf.control_id = c.id
        WHERE cf.assessment_id = $1
            AND cf.status = 'Not Met'
            AND EXISTS(
                SELECT 1 FROM poam_items p
                WHERE p.finding_id = cf.id AND p.risk_level = 'Critical'
            )
        LIMIT 10
        """,
        assessment_id
    )

    # Get overdue POA&Ms
    overdue_poams = await conn.fetch(
        """
        SELECT
            poam_id,
            control_id,
            weakness_description,
            risk_level,
            estimated_completion_date,
            CURRENT_DATE - estimated_completion_date as days_overdue
        FROM poam_items
        WHERE assessment_id = $1
            AND status != 'completed'
            AND estimated_completion_date < CURRENT_DATE
        ORDER BY estimated_completion_date ASC
        LIMIT 10
        """,
        assessment_id
    )

    # Calculate overall risk score (0-100, higher is riskier)
    total_risk = (
        risk_distribution['Critical'] * 4 +
        risk_distribution['High'] * 3 +
        risk_distribution['Medium'] * 2 +
        risk_distribution['Low'] * 1
    )
    max_possible_risk = 110 * 4  # 110 controls * max weight
    risk_score = (total_risk / max_possible_risk) * 100 if max_possible_risk > 0 else 0

    return {
        'assessment_id': assessment_id,
        'timestamp': datetime.utcnow().isoformat(),
        'risk_score': round(risk_score, 2),
        'risk_distribution': risk_distribution,
        'critical_findings': [
            {
                'control_id': row['control_id'],
                'title': row['title'],
                'status': row['status'],
                'narrative': row['assessor_narrative']
            }
            for row in critical_findings
        ],
        'overdue_poams': [
            {
                'poam_id': row['poam_id'],
                'control_id': row['control_id'],
                'description': row['weakness_description'],
                'risk_level': row['risk_level'],
                'due_date': row['estimated_completion_date'].isoformat(),
                'days_overdue': row['days_overdue']
            }
            for row in overdue_poams
        ]
    }


async def get_recent_alerts(
    organization_id: str,
    conn: asyncpg.Connection,
    days: int = 7
) -> List[Dict[str, Any]]:
    """
    Get recent alerts for an organization.

    This is a placeholder for a full alert system.
    In production, alerts would be generated by:
    - Scheduled monitoring jobs
    - Webhook triggers from integrations
    - Compliance threshold violations
    """
    logger.info(f"Getting recent alerts for organization {organization_id} (last {days} days)")

    alerts = []

    # Check for overdue POA&Ms
    overdue_poams = await conn.fetch(
        """
        SELECT
            p.poam_id,
            p.control_id,
            p.risk_level,
            p.estimated_completion_date,
            a.id as assessment_id
        FROM poam_items p
        JOIN assessments a ON p.assessment_id = a.id
        WHERE a.organization_id = $1
            AND p.status != 'completed'
            AND p.estimated_completion_date < CURRENT_DATE
            AND p.estimated_completion_date >= CURRENT_DATE - $2::int
        """,
        organization_id,
        days
    )

    for poam in overdue_poams:
        severity = AlertSeverity.CRITICAL if poam['risk_level'] == 'Critical' else AlertSeverity.HIGH
        alerts.append({
            'type': AlertType.POA_M_OVERDUE.value,
            'severity': severity.value,
            'message': f"POA&M {poam['poam_id']} for control {poam['control_id']} is overdue",
            'details': {
                'poam_id': poam['poam_id'],
                'control_id': poam['control_id'],
                'risk_level': poam['risk_level'],
                'due_date': poam['estimated_completion_date'].isoformat()
            },
            'timestamp': datetime.utcnow().isoformat()
        })

    # Check for failed integrations
    failed_integrations = await conn.fetch(
        """
        SELECT
            integration_type,
            error_details,
            started_at
        FROM integration_runs
        WHERE organization_id = $1
            AND status = 'failed'
            AND started_at >= NOW() - $2::int * INTERVAL '1 day'
        ORDER BY started_at DESC
        LIMIT 10
        """,
        organization_id,
        days
    )

    for integration in failed_integrations:
        alerts.append({
            'type': AlertType.INTEGRATION_FAILURE.value,
            'severity': AlertSeverity.MEDIUM.value,
            'message': f"Integration {integration['integration_type']} failed",
            'details': {
                'integration_type': integration['integration_type'],
                'error': integration['error_details'],
                'timestamp': integration['started_at'].isoformat()
            },
            'timestamp': integration['started_at'].isoformat()
        })

    # Check for new "Not Met" findings
    new_not_met = await conn.fetch(
        """
        SELECT
            cf.control_id,
            c.title,
            cf.created_at,
            a.id as assessment_id
        FROM control_findings cf
        JOIN controls c ON cf.control_id = c.id
        JOIN assessments a ON cf.assessment_id = a.id
        WHERE a.organization_id = $1
            AND cf.status = 'Not Met'
            AND cf.created_at >= NOW() - $2::int * INTERVAL '1 day'
        ORDER BY cf.created_at DESC
        LIMIT 10
        """,
        organization_id,
        days
    )

    for finding in new_not_met:
        alerts.append({
            'type': AlertType.CONTROL_NOT_MET.value,
            'severity': AlertSeverity.HIGH.value,
            'message': f"Control {finding['control_id']} marked as Not Met",
            'details': {
                'control_id': finding['control_id'],
                'title': finding['title'],
                'assessment_id': str(finding['assessment_id'])
            },
            'timestamp': finding['created_at'].isoformat()
        })

    # Sort alerts by timestamp (newest first)
    alerts.sort(key=lambda x: x['timestamp'], reverse=True)

    return alerts


async def get_evidence_statistics(
    assessment_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Get detailed evidence statistics for an assessment.

    Returns:
        Evidence statistics including:
        - Total count by type
        - Collection method breakdown
        - Status distribution
        - Recent uploads
    """
    logger.info(f"Getting evidence statistics for assessment {assessment_id}")

    # Get evidence by type
    by_type = await conn.fetch(
        """
        SELECT
            evidence_type,
            COUNT(*) as count
        FROM evidence
        WHERE assessment_id = $1
        GROUP BY evidence_type
        """,
        assessment_id
    )

    # Get evidence by collection method
    by_method = await conn.fetch(
        """
        SELECT
            collection_method,
            COUNT(*) as count
        FROM evidence
        WHERE assessment_id = $1
        GROUP BY collection_method
        """,
        assessment_id
    )

    # Get evidence by status
    by_status = await conn.fetch(
        """
        SELECT
            status,
            COUNT(*) as count
        FROM evidence
        WHERE assessment_id = $1
        GROUP BY status
        """,
        assessment_id
    )

    # Get recent uploads
    recent_uploads = await conn.fetch(
        """
        SELECT
            id,
            title,
            evidence_type,
            collected_date,
            status
        FROM evidence
        WHERE assessment_id = $1
        ORDER BY collected_date DESC
        LIMIT 10
        """,
        assessment_id
    )

    return {
        'assessment_id': assessment_id,
        'timestamp': datetime.utcnow().isoformat(),
        'by_type': {row['evidence_type']: row['count'] for row in by_type},
        'by_collection_method': {row['collection_method']: row['count'] for row in by_method},
        'by_status': {row['status']: row['count'] for row in by_status},
        'recent_uploads': [
            {
                'id': str(row['id']),
                'title': row['title'],
                'type': row['evidence_type'],
                'collected_date': row['collected_date'].isoformat(),
                'status': row['status']
            }
            for row in recent_uploads
        ]
    }
