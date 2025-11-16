"""
Splunk Integration Connector
============================
Integrates with Splunk for log ingestion and security event analysis.

Features:
1. HTTP Event Collector (HEC) for sending events to Splunk
2. SPL (Search Processing Language) query execution
3. Alert retrieval and mapping to CMMC controls
4. Security event correlation
5. Evidence generation from search results

Splunk Integration Modes:
- HEC: Push compliance events to Splunk for centralized logging
- Search API: Pull security alerts and map to CMMC controls
- Alert API: Monitor triggered alerts for control violations

Control Mapping:
- Authentication failures → IA.L2-3.5.1, IA.L2-3.5.7
- Access violations → AC.L2-3.1.1, AC.L2-3.1.2
- Configuration changes → CM.L2-3.4.3, CM.L2-3.4.8
- Security incidents → IR.L2-3.6.1, IR.L2-3.6.2
- Audit log gaps → AU.L2-3.3.1, AU.L2-3.3.2
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import json
from pathlib import Path
import aiohttp
import asyncpg

logger = logging.getLogger(__name__)


class SplunkConnector:
    """
    Splunk connector for bidirectional integration.

    Configuration:
    - splunk_host: Splunk server URL (e.g., https://splunk.example.com:8088)
    - hec_token: HTTP Event Collector token
    - search_token: API token for search operations
    - verify_ssl: Whether to verify SSL certificates (default: True)
    """

    # Control mapping based on security event types
    EVENT_TYPE_TO_CONTROLS = {
        'authentication_failure': ['IA.L2-3.5.1', 'IA.L2-3.5.7', 'IA.L2-3.5.8'],
        'authentication_success': ['IA.L2-3.5.1', 'AU.L2-3.3.1'],
        'access_denied': ['AC.L2-3.1.1', 'AC.L2-3.1.2', 'AU.L2-3.3.1'],
        'privilege_escalation': ['AC.L2-3.1.5', 'AC.L2-3.1.6', 'AU.L2-3.3.2'],
        'configuration_change': ['CM.L2-3.4.3', 'CM.L2-3.4.8', 'AU.L2-3.3.1'],
        'security_incident': ['IR.L2-3.6.1', 'IR.L2-3.6.2', 'AU.L2-3.3.8'],
        'malware_detected': ['SI.L2-3.14.2', 'SI.L2-3.14.4', 'IR.L2-3.6.1'],
        'vulnerability_scan': ['RA.L2-3.11.2', 'RA.L2-3.11.3', 'SI.L2-3.14.1'],
        'audit_log_failure': ['AU.L2-3.3.4', 'AU.L2-3.3.5'],
        'data_exfiltration': ['SC.L2-3.13.1', 'SC.L2-3.13.8', 'IR.L2-3.6.1'],
        'network_intrusion': ['SC.L2-3.13.1', 'SC.L2-3.13.6', 'IR.L2-3.6.1'],
        'failed_backup': ['CP.L2-3.8.9', 'AU.L2-3.3.8'],
        'account_lockout': ['IA.L2-3.5.7', 'AU.L2-3.3.1'],
        'password_change': ['IA.L2-3.5.7', 'IA.L2-3.5.8', 'AU.L2-3.3.1'],
        'file_integrity_violation': ['CM.L2-3.4.2', 'SI.L2-3.14.2', 'AU.L2-3.3.1']
    }

    # Splunk severity to risk level mapping
    SEVERITY_TO_RISK = {
        'critical': 'Critical',
        'high': 'High',
        'medium': 'Medium',
        'low': 'Low',
        'informational': 'Low'
    }

    def __init__(
        self,
        splunk_host: str,
        hec_token: str,
        search_token: Optional[str] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize Splunk connector.

        Args:
            splunk_host: Splunk server URL
            hec_token: HTTP Event Collector token
            search_token: API token for search operations (optional)
            verify_ssl: Whether to verify SSL certificates
        """
        self.splunk_host = splunk_host.rstrip('/')
        self.hec_token = hec_token
        self.search_token = search_token
        self.verify_ssl = verify_ssl
        self.hec_endpoint = f"{self.splunk_host}/services/collector/event"
        self.search_endpoint = f"{self.splunk_host}:8089/services/search/jobs"

    async def send_event_hec(
        self,
        event_data: Dict[str, Any],
        source: str = "cmmc_platform",
        sourcetype: str = "compliance_event",
        index: str = "main"
    ) -> Dict[str, Any]:
        """
        Send event to Splunk via HTTP Event Collector.

        Args:
            event_data: Event data to send
            source: Event source
            sourcetype: Event sourcetype
            index: Splunk index to write to

        Returns:
            Response from Splunk HEC
        """
        payload = {
            "time": int(datetime.utcnow().timestamp()),
            "host": "cmmc-platform",
            "source": source,
            "sourcetype": sourcetype,
            "index": index,
            "event": event_data
        }

        headers = {
            "Authorization": f"Splunk {self.hec_token}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.hec_endpoint,
                    json=payload,
                    headers=headers,
                    ssl=self.verify_ssl
                ) as response:
                    result = await response.json()

                    if response.status == 200:
                        logger.info(f"Event sent to Splunk HEC successfully")
                        return {"status": "success", "response": result}
                    else:
                        logger.error(f"Failed to send event to Splunk HEC: {result}")
                        return {"status": "error", "response": result, "http_status": response.status}

        except Exception as e:
            logger.error(f"Error sending event to Splunk HEC: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def send_compliance_event(
        self,
        assessment_id: str,
        control_id: str,
        event_type: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send compliance event to Splunk for centralized logging.

        Args:
            assessment_id: Assessment UUID
            control_id: Control identifier
            event_type: Type of compliance event
            details: Additional event details

        Returns:
            HEC response
        """
        event_data = {
            "assessment_id": assessment_id,
            "control_id": control_id,
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            **details
        }

        return await self.send_event_hec(
            event_data,
            sourcetype="cmmc_compliance",
            index="compliance"
        )

    async def execute_spl_query(
        self,
        query: str,
        earliest_time: str = "-24h",
        latest_time: str = "now",
        max_results: int = 1000
    ) -> Dict[str, Any]:
        """
        Execute SPL (Search Processing Language) query.

        Args:
            query: SPL query string
            earliest_time: Earliest time for search (e.g., "-24h", "-7d")
            latest_time: Latest time for search
            max_results: Maximum number of results to return

        Returns:
            Query results
        """
        if not self.search_token:
            logger.error("Search token not configured")
            return {"status": "error", "error": "Search token not configured"}

        headers = {
            "Authorization": f"Bearer {self.search_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Create search job
        search_params = {
            "search": query if query.startswith("search") else f"search {query}",
            "earliest_time": earliest_time,
            "latest_time": latest_time,
            "output_mode": "json",
            "max_count": max_results
        }

        try:
            async with aiohttp.ClientSession() as session:
                # Submit search job
                async with session.post(
                    self.search_endpoint,
                    data=search_params,
                    headers=headers,
                    ssl=self.verify_ssl
                ) as response:
                    if response.status != 201:
                        error_text = await response.text()
                        logger.error(f"Failed to create search job: {error_text}")
                        return {"status": "error", "error": error_text}

                    result = await response.json()
                    job_id = result.get("sid")

                    if not job_id:
                        logger.error("No search job ID returned")
                        return {"status": "error", "error": "No job ID returned"}

                logger.info(f"Search job created: {job_id}")

                # Poll for results
                results_url = f"{self.search_endpoint}/{job_id}/results"
                max_wait = 30  # seconds
                poll_interval = 1  # second
                elapsed = 0

                while elapsed < max_wait:
                    async with session.get(
                        f"{self.search_endpoint}/{job_id}",
                        params={"output_mode": "json"},
                        headers=headers,
                        ssl=self.verify_ssl
                    ) as status_response:
                        status_data = await status_response.json()
                        state = status_data.get("entry", [{}])[0].get("content", {}).get("dispatchState")

                        if state == "DONE":
                            # Get results
                            async with session.get(
                                results_url,
                                params={"output_mode": "json", "count": max_results},
                                headers=headers,
                                ssl=self.verify_ssl
                            ) as results_response:
                                results_data = await results_response.json()
                                results = results_data.get("results", [])

                                logger.info(f"Search completed: {len(results)} results")
                                return {
                                    "status": "success",
                                    "job_id": job_id,
                                    "results": results,
                                    "result_count": len(results)
                                }

                        elif state == "FAILED":
                            logger.error(f"Search job failed: {job_id}")
                            return {"status": "error", "error": "Search job failed"}

                    await asyncio.sleep(poll_interval)
                    elapsed += poll_interval

                logger.warning(f"Search job timed out: {job_id}")
                return {"status": "error", "error": "Search timed out"}

        except Exception as e:
            logger.error(f"Error executing SPL query: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def get_security_alerts(
        self,
        earliest_time: str = "-24h",
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve security alerts from Splunk.

        Args:
            earliest_time: Time window for alerts
            severity: Filter by severity (critical, high, medium, low)

        Returns:
            List of security alerts
        """
        # Build SPL query for security alerts
        query = 'index=security sourcetype="alert" | table _time, alert_name, severity, description, src_ip, dest_ip, user'

        if severity:
            query += f' | where severity="{severity}"'

        query += ' | sort -_time'

        result = await self.execute_spl_query(query, earliest_time=earliest_time)

        if result["status"] == "success":
            return result["results"]
        else:
            logger.error(f"Failed to retrieve security alerts: {result.get('error')}")
            return []

    def map_alert_to_controls(self, alert: Dict[str, Any]) -> List[str]:
        """
        Map Splunk alert to CMMC controls.

        Args:
            alert: Splunk alert data

        Returns:
            List of relevant control IDs
        """
        alert_name = alert.get("alert_name", "").lower()
        description = alert.get("description", "").lower()

        # Try to determine event type from alert name and description
        for event_type, controls in self.EVENT_TYPE_TO_CONTROLS.items():
            if event_type.replace("_", " ") in alert_name or event_type.replace("_", " ") in description:
                return controls

        # Default to general audit controls if no specific match
        return ['AU.L2-3.3.1', 'AU.L2-3.3.2']

    async def create_evidence_from_alert(
        self,
        assessment_id: str,
        alert: Dict[str, Any],
        conn: asyncpg.Connection
    ) -> str:
        """
        Create evidence record from Splunk alert.

        Args:
            assessment_id: Assessment UUID
            alert: Splunk alert data
            conn: Database connection

        Returns:
            Evidence UUID
        """
        # Map alert to controls
        control_ids = self.map_alert_to_controls(alert)
        primary_control = control_ids[0] if control_ids else None

        # Determine risk level
        severity = alert.get("severity", "informational").lower()
        risk_level = self.SEVERITY_TO_RISK.get(severity, "Low")

        # Create evidence content
        evidence_content = {
            "source": "Splunk Alert",
            "alert_name": alert.get("alert_name"),
            "severity": alert.get("severity"),
            "description": alert.get("description"),
            "timestamp": alert.get("_time"),
            "src_ip": alert.get("src_ip"),
            "dest_ip": alert.get("dest_ip"),
            "user": alert.get("user"),
            "raw_event": alert
        }

        evidence_title = f"Splunk Alert: {alert.get('alert_name', 'Unknown')}"
        evidence_description = f"Severity: {severity.upper()} - {alert.get('description', 'No description')}"

        # Insert evidence
        evidence_id = await conn.fetchval(
            """
            INSERT INTO evidence
            (assessment_id, control_id, evidence_type, title, description,
             method, content, collection_method, status)
            VALUES ($1, $2, 'log', $3, $4, 'Examine', $5, 'api_splunk', 'approved')
            RETURNING id
            """,
            assessment_id,
            primary_control,
            evidence_title,
            evidence_description,
            json.dumps(evidence_content)
        )

        logger.info(f"Created evidence {evidence_id} from Splunk alert")

        # If high severity, create POA&M
        if severity in ['critical', 'high']:
            await self.create_poam_from_alert(assessment_id, alert, control_ids, evidence_id, conn)

        return str(evidence_id)

    async def create_poam_from_alert(
        self,
        assessment_id: str,
        alert: Dict[str, Any],
        control_ids: List[str],
        evidence_id: str,
        conn: asyncpg.Connection
    ) -> str:
        """
        Create POA&M item from high-severity Splunk alert.

        Args:
            assessment_id: Assessment UUID
            alert: Splunk alert data
            control_ids: Related control IDs
            evidence_id: Associated evidence UUID
            conn: Database connection

        Returns:
            POA&M UUID
        """
        severity = alert.get("severity", "medium").lower()
        risk_level = self.SEVERITY_TO_RISK.get(severity, "Medium")

        # Get finding ID if exists
        finding_id = await conn.fetchval(
            """
            SELECT id FROM control_findings
            WHERE assessment_id = $1 AND control_id = $2
            ORDER BY created_at DESC
            LIMIT 1
            """,
            assessment_id,
            control_ids[0] if control_ids else None
        )

        # Generate POA&M ID
        poam_count = await conn.fetchval(
            "SELECT COUNT(*) FROM poam_items WHERE assessment_id = $1",
            assessment_id
        )
        poam_id = f"POA&M-{str(poam_count + 1).zfill(3)}"

        # Create POA&M
        poam_uuid = await conn.fetchval(
            """
            INSERT INTO poam_items
            (assessment_id, control_id, finding_id, poam_id, weakness_description,
             risk_level, remediation_plan, estimated_completion_date)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
            """,
            assessment_id,
            control_ids[0] if control_ids else None,
            finding_id,
            poam_id,
            f"Splunk alert: {alert.get('alert_name')} - {alert.get('description')}",
            risk_level,
            f"Investigate and remediate {alert.get('alert_name')} alert. Review affected systems and implement corrective actions.",
            datetime.utcnow() + timedelta(days=30 if risk_level == "Critical" else 90)
        )

        logger.info(f"Created POA&M {poam_id} from Splunk alert")
        return str(poam_uuid)

    async def sync_alerts_to_evidence(
        self,
        assessment_id: str,
        organization_id: str,
        conn: asyncpg.Connection,
        earliest_time: str = "-24h"
    ) -> Dict[str, Any]:
        """
        Sync Splunk alerts to evidence records.

        Args:
            assessment_id: Assessment UUID
            organization_id: Organization UUID
            conn: Database connection
            earliest_time: Time window for alerts

        Returns:
            Sync results summary
        """
        logger.info(f"Syncing Splunk alerts for assessment {assessment_id}")

        # Log integration run start
        run_id = await conn.fetchval(
            """
            INSERT INTO integration_runs
            (integration_type, organization_id, status)
            VALUES ('splunk', $1, 'running')
            RETURNING id
            """,
            organization_id
        )

        try:
            # Get alerts from Splunk
            alerts = await self.get_security_alerts(earliest_time=earliest_time)

            evidence_created = 0
            poams_created = 0
            errors = []

            for alert in alerts:
                try:
                    evidence_id = await self.create_evidence_from_alert(assessment_id, alert, conn)
                    evidence_created += 1

                    # Count POA&Ms created (high severity)
                    severity = alert.get("severity", "").lower()
                    if severity in ['critical', 'high']:
                        poams_created += 1

                except Exception as e:
                    logger.error(f"Error processing alert: {str(e)}")
                    errors.append({"alert": alert.get("alert_name"), "error": str(e)})

            # Update integration run
            await conn.execute(
                """
                UPDATE integration_runs
                SET status = $1,
                    records_processed = $2,
                    errors_count = $3,
                    error_details = $4,
                    completed_at = NOW()
                WHERE id = $5
                """,
                "success" if not errors else "failed",
                len(alerts),
                len(errors),
                json.dumps({"errors": errors}) if errors else None,
                run_id
            )

            logger.info(f"Splunk sync completed: {evidence_created} evidence, {poams_created} POA&Ms")

            return {
                "status": "success",
                "run_id": str(run_id),
                "alerts_processed": len(alerts),
                "evidence_created": evidence_created,
                "poams_created": poams_created,
                "errors": errors
            }

        except Exception as e:
            logger.error(f"Splunk sync failed: {str(e)}")

            # Update integration run as failed
            await conn.execute(
                """
                UPDATE integration_runs
                SET status = 'failed',
                    errors_count = 1,
                    error_details = $1,
                    completed_at = NOW()
                WHERE id = $2
                """,
                json.dumps({"error": str(e)}),
                run_id
            )

            return {
                "status": "error",
                "run_id": str(run_id),
                "error": str(e)
            }


# Predefined SPL queries for common compliance checks
COMPLIANCE_QUERIES = {
    "failed_authentication": {
        "query": 'index=security sourcetype="authentication" action=failure | stats count by user, src_ip | where count > 5',
        "controls": ["IA.L2-3.5.1", "IA.L2-3.5.7"],
        "description": "Multiple failed authentication attempts"
    },
    "privileged_access": {
        "query": 'index=security (sourcetype="linux_secure" OR sourcetype="wineventlog") action=sudo OR EventCode=4672 | stats count by user',
        "controls": ["AC.L2-3.1.5", "AC.L2-3.1.6", "AU.L2-3.3.2"],
        "description": "Privileged access activity"
    },
    "configuration_changes": {
        "query": 'index=security sourcetype="config_change" | table _time, host, change_type, user, details',
        "controls": ["CM.L2-3.4.3", "CM.L2-3.4.8"],
        "description": "Configuration changes to critical systems"
    },
    "audit_log_gaps": {
        "query": 'index=security | bucket _time span=1h | stats count by _time | where count=0',
        "controls": ["AU.L2-3.3.4", "AU.L2-3.3.5"],
        "description": "Gaps in audit logging"
    },
    "malware_alerts": {
        "query": 'index=security sourcetype="antivirus" action=blocked | stats count by malware_name, host',
        "controls": ["SI.L2-3.14.2", "SI.L2-3.14.4"],
        "description": "Malware detection events"
    }
}
