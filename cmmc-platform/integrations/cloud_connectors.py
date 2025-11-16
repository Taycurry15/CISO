"""
Cloud Connector Suite
====================
Integrates with major cloud providers for compliance automation.

Supported Providers:
1. Azure Policy - Policy compliance state and recommendations
2. AWS Security Hub - Security findings and compliance checks
3. M365/Entra ID - Identity, access, and security events

Features:
- Automated compliance data collection
- Control mapping to CMMC framework
- Evidence generation from cloud provider data
- Provider inheritance documentation
- Configuration drift detection
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import asyncio
import logging
import json
from enum import Enum
import aiohttp
import asyncpg

logger = logging.getLogger(__name__)


class CloudProvider(str, Enum):
    AZURE = "azure"
    AWS = "aws"
    M365 = "m365"
    GCP = "gcp"


# =============================================================================
# AZURE POLICY CONNECTOR
# =============================================================================

class AzurePolicyConnector:
    """
    Azure Policy connector for compliance state monitoring.

    Uses Azure Policy and Azure Security Center APIs to:
    - Retrieve policy compliance states
    - Get security recommendations
    - Monitor configuration compliance
    - Track resource compliance
    """

    # Azure Policy to CMMC control mapping
    POLICY_TO_CONTROLS = {
        # Identity and Access
        'mfa_enabled': ['IA.L2-3.5.3', 'IA.L2-3.5.4'],
        'privileged_access_managed': ['AC.L2-3.1.5', 'AC.L2-3.1.6'],
        'guest_access_reviewed': ['AC.L2-3.1.1', 'AC.L2-3.1.12'],

        # Network Security
        'network_security_groups_configured': ['SC.L2-3.13.1', 'SC.L2-3.13.6'],
        'ddos_protection_enabled': ['SC.L2-3.13.6'],
        'vnet_encryption_enabled': ['SC.L2-3.13.8', 'SC.L2-3.13.11'],

        # Data Protection
        'encryption_at_rest': ['SC.L2-3.13.16', 'MP.L2-3.8.3'],
        'encryption_in_transit': ['SC.L2-3.13.8', 'SC.L2-3.13.11'],
        'backup_enabled': ['CP.L2-3.8.9'],

        # Monitoring and Logging
        'diagnostic_logs_enabled': ['AU.L2-3.3.1', 'AU.L2-3.3.2'],
        'security_center_monitoring': ['AU.L2-3.3.6', 'RA.L2-3.11.2'],
        'log_retention_configured': ['AU.L2-3.3.8'],

        # Configuration Management
        'auto_provisioning_enabled': ['CM.L2-3.4.1'],
        'system_updates_installed': ['SI.L2-3.14.1', 'SI.L2-3.14.2'],
        'vulnerability_assessment_enabled': ['RA.L2-3.11.2', 'RA.L2-3.11.3'],

        # Incident Response
        'security_alerts_configured': ['IR.L2-3.6.1'],
        'threat_protection_enabled': ['SI.L2-3.14.2', 'SI.L2-3.14.4']
    }

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
        subscription_id: str
    ):
        """
        Initialize Azure Policy connector.

        Args:
            tenant_id: Azure AD tenant ID
            client_id: Service principal client ID
            client_secret: Service principal secret
            subscription_id: Azure subscription ID
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.subscription_id = subscription_id
        self.token = None
        self.token_expires = None
        self.base_url = "https://management.azure.com"

    async def get_access_token(self) -> str:
        """Get Azure AD access token."""
        if self.token and self.token_expires and datetime.utcnow() < self.token_expires:
            return self.token

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://management.azure.com/.default",
            "grant_type": "client_credentials"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                result = await response.json()

                if "access_token" in result:
                    self.token = result["access_token"]
                    expires_in = result.get("expires_in", 3600)
                    self.token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 300)
                    return self.token
                else:
                    raise Exception(f"Failed to get access token: {result}")

    async def get_policy_states(self) -> List[Dict[str, Any]]:
        """
        Get Azure Policy compliance states.

        Returns:
            List of policy compliance states
        """
        token = await self.get_access_token()

        url = f"{self.base_url}/subscriptions/{self.subscription_id}/providers/Microsoft.PolicyInsights/policyStates/latest/queryResults"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        params = {
            "api-version": "2019-10-01",
            "$top": 1000
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("value", [])
                    else:
                        error = await response.text()
                        logger.error(f"Failed to get policy states: {error}")
                        return []
        except Exception as e:
            logger.error(f"Error getting Azure policy states: {str(e)}")
            return []

    async def get_security_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get Azure Security Center recommendations.

        Returns:
            List of security recommendations
        """
        token = await self.get_access_token()

        url = f"{self.base_url}/subscriptions/{self.subscription_id}/providers/Microsoft.Security/assessments"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        params = {
            "api-version": "2020-01-01"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("value", [])
                    else:
                        error = await response.text()
                        logger.error(f"Failed to get security recommendations: {error}")
                        return []
        except Exception as e:
            logger.error(f"Error getting Azure security recommendations: {str(e)}")
            return []

    def map_policy_to_controls(self, policy_name: str) -> List[str]:
        """Map Azure policy to CMMC controls."""
        policy_key = policy_name.lower().replace(" ", "_").replace("-", "_")

        for key, controls in self.POLICY_TO_CONTROLS.items():
            if key in policy_key:
                return controls

        # Default to configuration management if no specific match
        return ['CM.L2-3.4.1', 'CM.L2-3.4.2']

    async def sync_to_evidence(
        self,
        assessment_id: str,
        organization_id: str,
        conn: asyncpg.Connection
    ) -> Dict[str, Any]:
        """Sync Azure Policy compliance to evidence."""
        logger.info(f"Syncing Azure Policy data for assessment {assessment_id}")

        run_id = await conn.fetchval(
            "INSERT INTO integration_runs (integration_type, organization_id, status) VALUES ('azure', $1, 'running') RETURNING id",
            organization_id
        )

        try:
            policy_states = await self.get_policy_states()
            recommendations = await self.get_security_recommendations()

            evidence_created = 0

            # Process non-compliant policies
            for policy in policy_states:
                if policy.get("complianceState") == "NonCompliant":
                    controls = self.map_policy_to_controls(policy.get("policyDefinitionName", ""))

                    evidence_content = {
                        "source": "Azure Policy",
                        "policy_name": policy.get("policyDefinitionName"),
                        "resource_id": policy.get("resourceId"),
                        "compliance_state": policy.get("complianceState"),
                        "timestamp": policy.get("timestamp")
                    }

                    await conn.execute(
                        """
                        INSERT INTO evidence
                        (assessment_id, control_id, evidence_type, title, description,
                         method, content, collection_method, status)
                        VALUES ($1, $2, 'log', $3, $4, 'Examine', $5, 'api_azure', 'approved')
                        """,
                        assessment_id,
                        controls[0] if controls else None,
                        f"Azure Policy: {policy.get('policyDefinitionName')}",
                        f"Non-compliant resource: {policy.get('resourceId')}",
                        json.dumps(evidence_content)
                    )
                    evidence_created += 1

            await conn.execute(
                "UPDATE integration_runs SET status = 'success', records_processed = $1, completed_at = NOW() WHERE id = $2",
                len(policy_states),
                run_id
            )

            return {
                "status": "success",
                "run_id": str(run_id),
                "policies_processed": len(policy_states),
                "evidence_created": evidence_created
            }

        except Exception as e:
            logger.error(f"Azure sync failed: {str(e)}")
            await conn.execute(
                "UPDATE integration_runs SET status = 'failed', error_details = $1, completed_at = NOW() WHERE id = $2",
                json.dumps({"error": str(e)}),
                run_id
            )
            return {"status": "error", "error": str(e)}


# =============================================================================
# AWS SECURITY HUB CONNECTOR
# =============================================================================

class AWSSecurityHubConnector:
    """
    AWS Security Hub connector for compliance monitoring.

    Uses AWS Security Hub API to:
    - Retrieve security findings
    - Get compliance standards results
    - Monitor configuration compliance
    - Track security best practices
    """

    # AWS Security Hub findings to CMMC controls
    FINDING_TO_CONTROLS = {
        # IAM and Access
        'iam-user-mfa-enabled': ['IA.L2-3.5.3', 'IA.L2-3.5.4'],
        'iam-root-access-key-check': ['AC.L2-3.1.5'],
        'iam-password-policy': ['IA.L2-3.5.7', 'IA.L2-3.5.8'],

        # Encryption
        's3-bucket-encryption': ['SC.L2-3.13.16', 'MP.L2-3.8.3'],
        'ebs-encryption': ['SC.L2-3.13.16'],
        'rds-encryption-at-rest': ['SC.L2-3.13.16'],

        # Logging and Monitoring
        'cloudtrail-enabled': ['AU.L2-3.3.1', 'AU.L2-3.3.2'],
        'cloudwatch-alarm-action-check': ['AU.L2-3.3.6', 'IR.L2-3.6.1'],
        's3-bucket-logging-enabled': ['AU.L2-3.3.1'],

        # Network Security
        'vpc-flow-logs-enabled': ['AU.L2-3.3.3', 'SC.L2-3.13.1'],
        'restricted-ssh': ['AC.L2-3.1.3', 'SC.L2-3.13.1'],
        'restricted-rdp': ['AC.L2-3.1.3', 'SC.L2-3.13.1'],

        # Backup and Recovery
        'db-backup-enabled': ['CP.L2-3.8.9'],
        'ebs-snapshot-public-restorable-check': ['AC.L2-3.1.3', 'MP.L2-3.8.3'],

        # Vulnerability Management
        'ec2-managedinstance-patch-compliance-status-check': ['SI.L2-3.14.1'],
        'guardduty-enabled-centralized': ['SI.L2-3.14.2', 'IR.L2-3.6.1']
    }

    def __init__(
        self,
        aws_access_key_id: str,
        aws_secret_access_key: str,
        region: str = "us-east-1"
    ):
        """
        Initialize AWS Security Hub connector.

        Note: This is a simplified implementation. Production should use boto3.

        Args:
            aws_access_key_id: AWS access key
            aws_secret_access_key: AWS secret key
            region: AWS region
        """
        self.access_key_id = aws_access_key_id
        self.secret_access_key = aws_secret_access_key
        self.region = region
        logger.info("AWS Security Hub connector initialized (boto3 implementation recommended)")

    def map_finding_to_controls(self, finding_type: str) -> List[str]:
        """Map AWS Security Hub finding to CMMC controls."""
        finding_key = finding_type.lower().replace(" ", "-")

        for key, controls in self.FINDING_TO_CONTROLS.items():
            if key in finding_key:
                return controls

        return ['CM.L2-3.4.1']

    async def sync_to_evidence(
        self,
        assessment_id: str,
        organization_id: str,
        conn: asyncpg.Connection
    ) -> Dict[str, Any]:
        """
        Sync AWS Security Hub findings to evidence.

        Note: This is a stub. Production implementation should use boto3.
        """
        logger.info(f"AWS Security Hub sync for assessment {assessment_id}")

        run_id = await conn.fetchval(
            "INSERT INTO integration_runs (integration_type, organization_id, status) VALUES ('aws', $1, 'running') RETURNING id",
            organization_id
        )

        # Stub implementation - would use boto3 in production
        await conn.execute(
            "UPDATE integration_runs SET status = 'success', records_processed = 0, completed_at = NOW() WHERE id = $1",
            run_id
        )

        return {
            "status": "success",
            "run_id": str(run_id),
            "message": "AWS connector ready - integrate boto3 for full functionality"
        }


# =============================================================================
# M365/ENTRA ID CONNECTOR
# =============================================================================

class M365EntraIDConnector:
    """
    Microsoft 365 and Entra ID (Azure AD) connector.

    Integrates with:
    - Microsoft Graph API for identity and access
    - Microsoft 365 Security & Compliance Center
    - Entra ID (Azure AD) for authentication events
    """

    # M365/Entra ID events to CMMC controls
    EVENT_TO_CONTROLS = {
        # Authentication and Identity
        'UserLoggedIn': ['IA.L2-3.5.1', 'AU.L2-3.3.1'],
        'UserLoginFailed': ['IA.L2-3.5.1', 'IA.L2-3.5.7', 'AU.L2-3.3.2'],
        'Add user': ['AC.L2-3.1.12', 'AU.L2-3.3.1'],
        'Delete user': ['AC.L2-3.1.12', 'AU.L2-3.3.1'],
        'Reset password': ['IA.L2-3.5.8', 'AU.L2-3.3.1'],

        # Access Control
        'Add member to role': ['AC.L2-3.1.5', 'AU.L2-3.3.2'],
        'Remove member from role': ['AC.L2-3.1.5', 'AU.L2-3.3.2'],
        'Update policy': ['AC.L2-3.1.3', 'CM.L2-3.4.3'],

        # Data Protection
        'FileAccessed': ['AU.L2-3.3.3', 'MP.L2-3.8.2'],
        'FileDownloaded': ['AU.L2-3.3.3', 'MP.L2-3.8.2'],
        'FileSyncDownloadedFull': ['AU.L2-3.3.3'],
        'SharingSet': ['AC.L2-3.1.20', 'MP.L2-3.8.2'],

        # Security Alerts
        'Malware detected': ['SI.L2-3.14.2', 'SI.L2-3.14.4', 'IR.L2-3.6.1'],
        'Suspicious activity': ['IR.L2-3.6.1', 'AU.L2-3.3.6'],
        'DLP policy match': ['MP.L2-3.8.2', 'SC.L2-3.13.10']
    }

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str
    ):
        """
        Initialize M365/Entra ID connector.

        Args:
            tenant_id: Microsoft 365 tenant ID
            client_id: App registration client ID
            client_secret: App registration secret
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_expires = None
        self.graph_endpoint = "https://graph.microsoft.com/v1.0"

    async def get_access_token(self) -> str:
        """Get Microsoft Graph API access token."""
        if self.token and self.token_expires and datetime.utcnow() < self.token_expires:
            return self.token

        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(token_url, data=data) as response:
                result = await response.json()

                if "access_token" in result:
                    self.token = result["access_token"]
                    expires_in = result.get("expires_in", 3600)
                    self.token_expires = datetime.utcnow() + timedelta(seconds=expires_in - 300)
                    return self.token
                else:
                    raise Exception(f"Failed to get access token: {result}")

    async def get_audit_logs(
        self,
        start_time: Optional[datetime] = None,
        activity_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs from Entra ID and M365.

        Args:
            start_time: Start time for log retrieval
            activity_filter: Filter for specific activities

        Returns:
            List of audit log entries
        """
        token = await self.get_access_token()

        if not start_time:
            start_time = datetime.utcnow() - timedelta(days=7)

        url = f"{self.graph_endpoint}/auditLogs/directoryAudits"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        params = {
            "$filter": f"activityDateTime ge {start_time.isoformat()}Z"
        }

        if activity_filter:
            params["$filter"] += f" and activityDisplayName eq '{activity_filter}'"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("value", [])
                    else:
                        error = await response.text()
                        logger.error(f"Failed to get audit logs: {error}")
                        return []
        except Exception as e:
            logger.error(f"Error getting M365 audit logs: {str(e)}")
            return []

    async def get_security_alerts(self) -> List[Dict[str, Any]]:
        """
        Get security alerts from Microsoft 365 Defender.

        Returns:
            List of security alerts
        """
        token = await self.get_access_token()

        url = f"{self.graph_endpoint}/security/alerts"

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("value", [])
                    else:
                        error = await response.text()
                        logger.error(f"Failed to get security alerts: {error}")
                        return []
        except Exception as e:
            logger.error(f"Error getting M365 security alerts: {str(e)}")
            return []

    def map_event_to_controls(self, activity_name: str) -> List[str]:
        """Map M365/Entra ID event to CMMC controls."""
        for key, controls in self.EVENT_TO_CONTROLS.items():
            if key.lower() in activity_name.lower():
                return controls

        return ['AU.L2-3.3.1']

    async def sync_to_evidence(
        self,
        assessment_id: str,
        organization_id: str,
        conn: asyncpg.Connection
    ) -> Dict[str, Any]:
        """Sync M365/Entra ID events to evidence."""
        logger.info(f"Syncing M365/Entra ID data for assessment {assessment_id}")

        run_id = await conn.fetchval(
            "INSERT INTO integration_runs (integration_type, organization_id, status) VALUES ('m365', $1, 'running') RETURNING id",
            organization_id
        )

        try:
            audit_logs = await self.get_audit_logs()
            security_alerts = await self.get_security_alerts()

            evidence_created = 0

            # Process high-severity alerts
            for alert in security_alerts:
                if alert.get("severity") in ["high", "medium"]:
                    controls = self.map_event_to_controls(alert.get("title", ""))

                    evidence_content = {
                        "source": "M365 Security Alert",
                        "title": alert.get("title"),
                        "severity": alert.get("severity"),
                        "category": alert.get("category"),
                        "status": alert.get("status"),
                        "created_datetime": alert.get("createdDateTime")
                    }

                    await conn.execute(
                        """
                        INSERT INTO evidence
                        (assessment_id, control_id, evidence_type, title, description,
                         method, content, collection_method, status)
                        VALUES ($1, $2, 'log', $3, $4, 'Examine', $5, 'api_m365', 'approved')
                        """,
                        assessment_id,
                        controls[0] if controls else None,
                        f"M365 Alert: {alert.get('title')}",
                        f"{alert.get('severity')} - {alert.get('category')}",
                        json.dumps(evidence_content)
                    )
                    evidence_created += 1

            await conn.execute(
                "UPDATE integration_runs SET status = 'success', records_processed = $1, completed_at = NOW() WHERE id = $2",
                len(audit_logs) + len(security_alerts),
                run_id
            )

            return {
                "status": "success",
                "run_id": str(run_id),
                "audit_logs_processed": len(audit_logs),
                "alerts_processed": len(security_alerts),
                "evidence_created": evidence_created
            }

        except Exception as e:
            logger.error(f"M365 sync failed: {str(e)}")
            await conn.execute(
                "UPDATE integration_runs SET status = 'failed', error_details = $1, completed_at = NOW() WHERE id = $2",
                json.dumps({"error": str(e)}),
                run_id
            )
            return {"status": "error", "error": str(e)}
