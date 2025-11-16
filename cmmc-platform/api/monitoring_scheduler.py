"""
Continuous Monitoring Scheduler
===============================
Automated scheduling for continuous compliance monitoring.

Features:
- Periodic integration runs
- SPRS score recalculation
- Alert rule evaluation
- Evidence expiration checks
- POA&M deadline monitoring
- Compliance drift detection
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import asyncpg
import logging
import json

logger = logging.getLogger(__name__)


class ScheduleInterval(str, Enum):
    """Monitoring schedule intervals."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MonitoringTaskType(str, Enum):
    """Types of monitoring tasks."""
    INTEGRATION_SYNC = "integration_sync"
    SPRS_CALCULATION = "sprs_calculation"
    ALERT_EVALUATION = "alert_evaluation"
    EVIDENCE_EXPIRATION = "evidence_expiration"
    POAM_DEADLINE = "poam_deadline"
    COMPLIANCE_DRIFT = "compliance_drift"


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class MonitoringScheduler:
    """
    Continuous monitoring scheduler.

    Manages periodic execution of compliance monitoring tasks.
    """

    def __init__(self, conn: asyncpg.Connection):
        """
        Initialize monitoring scheduler.

        Args:
            conn: Database connection
        """
        self.conn = conn
        self.running = False

    async def start(self):
        """Start the monitoring scheduler."""
        logger.info("Starting continuous monitoring scheduler")
        self.running = True

        # Start background tasks
        tasks = [
            self._hourly_tasks(),
            self._daily_tasks(),
            self._weekly_tasks()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop(self):
        """Stop the monitoring scheduler."""
        logger.info("Stopping continuous monitoring scheduler")
        self.running = False

    async def _hourly_tasks(self):
        """Execute hourly monitoring tasks."""
        while self.running:
            try:
                logger.info("Running hourly monitoring tasks")

                # 1. Check for integration sync schedules
                await self._run_scheduled_integrations(ScheduleInterval.HOURLY)

                # 2. Evaluate alert rules
                await self._evaluate_alert_rules()

                # Wait for next hour
                await asyncio.sleep(3600)

            except Exception as e:
                logger.error(f"Error in hourly tasks: {str(e)}")
                await asyncio.sleep(60)  # Wait 1 minute on error

    async def _daily_tasks(self):
        """Execute daily monitoring tasks."""
        while self.running:
            try:
                logger.info("Running daily monitoring tasks")

                # 1. Recalculate SPRS scores
                await self._recalculate_all_sprs_scores()

                # 2. Check evidence expiration
                await self._check_evidence_expiration()

                # 3. Check POA&M deadlines
                await self._check_poam_deadlines()

                # 4. Run daily integrations
                await self._run_scheduled_integrations(ScheduleInterval.DAILY)

                # Wait for next day
                await asyncio.sleep(86400)

            except Exception as e:
                logger.error(f"Error in daily tasks: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _weekly_tasks(self):
        """Execute weekly monitoring tasks."""
        while self.running:
            try:
                logger.info("Running weekly monitoring tasks")

                # 1. Detect compliance drift
                await self._detect_compliance_drift()

                # 2. Generate compliance reports
                await self._generate_weekly_reports()

                # 3. Run weekly integrations
                await self._run_scheduled_integrations(ScheduleInterval.WEEKLY)

                # Wait for next week
                await asyncio.sleep(604800)

            except Exception as e:
                logger.error(f"Error in weekly tasks: {str(e)}")
                await asyncio.sleep(3600)  # Wait 1 hour on error

    async def _run_scheduled_integrations(self, interval: ScheduleInterval):
        """Run scheduled integration syncs."""
        integrations = await self.conn.fetch(
            """
            SELECT DISTINCT organization_id, integration_type
            FROM integration_schedules
            WHERE active = TRUE AND interval = $1
            """,
            interval.value
        )

        for integration in integrations:
            try:
                await self._run_integration_sync(
                    integration['organization_id'],
                    integration['integration_type']
                )
            except Exception as e:
                logger.error(f"Integration sync failed: {str(e)}")

    async def _run_integration_sync(
        self,
        organization_id: str,
        integration_type: str
    ):
        """Execute integration sync."""
        logger.info(f"Running {integration_type} sync for org {organization_id}")

        # Get latest assessment for organization
        assessment_id = await self.conn.fetchval(
            """
            SELECT id FROM assessments
            WHERE organization_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """,
            organization_id
        )

        if not assessment_id:
            logger.warning(f"No assessment found for org {organization_id}")
            return

        # Import and run appropriate connector
        if integration_type == "nessus":
            from integrations.nessus_connector import NessusConnector
            # Configure and run Nessus sync
            # connector = NessusConnector(...)
            # await connector.sync(assessment_id, organization_id, self.conn)

        elif integration_type == "splunk":
            from integrations.splunk_connector import SplunkConnector
            # Configure and run Splunk sync

        elif integration_type == "azure":
            from integrations.cloud_connectors import AzurePolicyConnector
            # Configure and run Azure sync

        # Log integration run
        await self.conn.execute(
            """
            INSERT INTO integration_runs
            (integration_type, organization_id, status)
            VALUES ($1, $2, 'scheduled')
            """,
            integration_type,
            organization_id
        )

    async def _recalculate_all_sprs_scores(self):
        """Recalculate SPRS scores for all active assessments."""
        from sprs_calculator import calculate_sprs_score, save_sprs_score

        assessments = await self.conn.fetch(
            """
            SELECT id, organization_id
            FROM assessments
            WHERE status IN ('in_progress', 'under_review')
            """
        )

        for assessment in assessments:
            try:
                score_data = await calculate_sprs_score(str(assessment['id']), self.conn)
                await save_sprs_score(str(assessment['id']), score_data, self.conn)

                logger.info(f"SPRS score calculated: {score_data['score']} for assessment {assessment['id']}")

            except Exception as e:
                logger.error(f"SPRS calculation failed for assessment {assessment['id']}: {str(e)}")

    async def _evaluate_alert_rules(self):
        """Evaluate all active alert rules."""
        rules = await self.conn.fetch(
            """
            SELECT id, rule_name, rule_type, condition, severity, organization_id
            FROM alert_rules
            WHERE active = TRUE
            """
        )

        for rule in rules:
            try:
                triggered = await self._check_alert_rule(rule)

                if triggered:
                    await self._create_alert(
                        organization_id=rule['organization_id'],
                        rule_id=rule['id'],
                        severity=rule['severity'],
                        message=triggered['message'],
                        details=triggered.get('details', {})
                    )

            except Exception as e:
                logger.error(f"Alert rule evaluation failed: {str(e)}")

    async def _check_alert_rule(self, rule: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if an alert rule condition is met.

        Args:
            rule: Alert rule definition

        Returns:
            Alert details if triggered, None otherwise
        """
        rule_type = rule['rule_type']
        condition = rule['condition']

        if rule_type == 'sprs_drop':
            # Check for SPRS score drop
            threshold = condition.get('threshold', 10)
            result = await self.conn.fetchrow(
                """
                SELECT
                    a.id as assessment_id,
                    s1.score as current_score,
                    s2.score as previous_score
                FROM assessments a
                JOIN LATERAL (
                    SELECT score FROM sprs_scores
                    WHERE assessment_id = a.id
                    ORDER BY calculation_date DESC
                    LIMIT 1
                ) s1 ON TRUE
                JOIN LATERAL (
                    SELECT score FROM sprs_scores
                    WHERE assessment_id = a.id
                    ORDER BY calculation_date DESC
                    OFFSET 1 LIMIT 1
                ) s2 ON TRUE
                WHERE a.organization_id = $1
                AND (s2.score - s1.score) >= $2
                """,
                rule['organization_id'],
                threshold
            )

            if result:
                return {
                    "message": f"SPRS score dropped by {result['previous_score'] - result['current_score']} points",
                    "details": {
                        "assessment_id": str(result['assessment_id']),
                        "current_score": result['current_score'],
                        "previous_score": result['previous_score']
                    }
                }

        elif rule_type == 'new_high_findings':
            # Check for new high-severity findings
            count = condition.get('count', 1)
            hours = condition.get('hours', 24)

            result = await self.conn.fetchval(
                """
                SELECT COUNT(*)
                FROM control_findings cf
                JOIN assessments a ON cf.assessment_id = a.id
                WHERE a.organization_id = $1
                AND cf.status = 'Not Met'
                AND cf.created_at >= NOW() - $2::int * INTERVAL '1 hour'
                """,
                rule['organization_id'],
                hours
            )

            if result and result >= count:
                return {
                    "message": f"{result} new 'Not Met' findings in the last {hours} hours",
                    "details": {"count": result, "hours": hours}
                }

        elif rule_type == 'overdue_poam':
            # Check for overdue POA&M items
            result = await self.conn.fetchval(
                """
                SELECT COUNT(*)
                FROM poam_items p
                JOIN assessments a ON p.assessment_id = a.id
                WHERE a.organization_id = $1
                AND p.status != 'completed'
                AND p.estimated_completion_date < CURRENT_DATE
                """,
                rule['organization_id']
            )

            if result and result > 0:
                return {
                    "message": f"{result} POA&M items are overdue",
                    "details": {"count": result}
                }

        return None

    async def _create_alert(
        self,
        organization_id: str,
        rule_id: str,
        severity: str,
        message: str,
        details: Dict[str, Any]
    ):
        """Create an alert."""
        await self.conn.execute(
            """
            INSERT INTO alerts
            (organization_id, rule_id, severity, message, details, status)
            VALUES ($1, $2, $3, $4, $5, 'active')
            """,
            organization_id,
            rule_id,
            severity,
            message,
            json.dumps(details)
        )

        logger.info(f"Alert created: {severity} - {message}")

    async def _check_evidence_expiration(self):
        """Check for expiring evidence."""
        # Evidence older than 1 year should be reviewed
        expiring = await self.conn.fetch(
            """
            SELECT e.id, e.title, e.assessment_id, a.organization_id
            FROM evidence e
            JOIN assessments a ON e.assessment_id = a.id
            WHERE e.collected_date < NOW() - INTERVAL '1 year'
            AND e.status = 'approved'
            """
        )

        for evidence in expiring:
            await self._create_alert(
                organization_id=evidence['organization_id'],
                rule_id=None,
                severity=AlertSeverity.MEDIUM.value,
                message=f"Evidence '{evidence['title']}' is older than 1 year",
                details={
                    "evidence_id": str(evidence['id']),
                    "assessment_id": str(evidence['assessment_id'])
                }
            )

    async def _check_poam_deadlines(self):
        """Check for approaching POA&M deadlines."""
        # Alert 30 days before deadline
        approaching = await self.conn.fetch(
            """
            SELECT p.id, p.poam_id, p.control_id, p.estimated_completion_date,
                   a.organization_id
            FROM poam_items p
            JOIN assessments a ON p.assessment_id = a.id
            WHERE p.status != 'completed'
            AND p.estimated_completion_date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '30 days'
            """
        )

        for poam in approaching:
            days_remaining = (poam['estimated_completion_date'] - datetime.utcnow().date()).days

            await self._create_alert(
                organization_id=poam['organization_id'],
                rule_id=None,
                severity=AlertSeverity.HIGH.value if days_remaining <= 7 else AlertSeverity.MEDIUM.value,
                message=f"POA&M {poam['poam_id']} deadline in {days_remaining} days",
                details={
                    "poam_id": poam['poam_id'],
                    "control_id": poam['control_id'],
                    "deadline": poam['estimated_completion_date'].isoformat()
                }
            )

    async def _detect_compliance_drift(self):
        """Detect compliance drift (controls moving from Met to Not Met)."""
        # Compare current status to status 7 days ago
        drift = await self.conn.fetch(
            """
            WITH current_status AS (
                SELECT cf.id, cf.assessment_id, cf.control_id, cf.status
                FROM control_findings cf
                WHERE cf.updated_at >= NOW() - INTERVAL '7 days'
            ),
            previous_status AS (
                SELECT
                    al.record_id,
                    al.changed_data->>'status' as old_status
                FROM audit_log al
                WHERE al.table_name = 'control_findings'
                AND al.operation = 'UPDATE'
                AND al.changed_at >= NOW() - INTERVAL '14 days'
                AND al.changed_at < NOW() - INTERVAL '7 days'
            )
            SELECT
                cs.assessment_id,
                cs.control_id,
                cs.status as current_status,
                ps.old_status as previous_status,
                a.organization_id
            FROM current_status cs
            JOIN previous_status ps ON cs.id = ps.record_id
            JOIN assessments a ON cs.assessment_id = a.id
            WHERE ps.old_status = 'Met'
            AND cs.status IN ('Not Met', 'Partially Met')
            """
        )

        for item in drift:
            await self._create_alert(
                organization_id=item['organization_id'],
                rule_id=None,
                severity=AlertSeverity.HIGH.value,
                message=f"Compliance drift detected: {item['control_id']} changed from {item['previous_status']} to {item['current_status']}",
                details={
                    "assessment_id": str(item['assessment_id']),
                    "control_id": item['control_id'],
                    "previous_status": item['previous_status'],
                    "current_status": item['current_status']
                }
            )

    async def _generate_weekly_reports(self):
        """Generate weekly compliance reports."""
        organizations = await self.conn.fetch(
            "SELECT id, name FROM organizations WHERE active = TRUE"
        )

        for org in organizations:
            try:
                # Generate report summary
                summary = await self._generate_org_summary(org['id'])

                # Store report
                await self.conn.execute(
                    """
                    INSERT INTO compliance_reports
                    (organization_id, report_type, period_start, period_end, summary)
                    VALUES ($1, 'weekly', NOW() - INTERVAL '7 days', NOW(), $2)
                    """,
                    org['id'],
                    json.dumps(summary)
                )

                logger.info(f"Weekly report generated for {org['name']}")

            except Exception as e:
                logger.error(f"Weekly report generation failed for {org['name']}: {str(e)}")

    async def _generate_org_summary(self, organization_id: str) -> Dict[str, Any]:
        """Generate organization summary for reporting."""
        from monitoring_dashboard import get_dashboard_summary

        summary = await get_dashboard_summary(str(organization_id), self.conn)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "compliance_percentage": summary['compliance']['percentage'],
            "sprs_score": summary['sprs_score']['average'],
            "open_poams": summary['poam']['open'],
            "evidence_count": summary['evidence']['total'],
            "alerts_count": summary['alerts']['count']
        }
