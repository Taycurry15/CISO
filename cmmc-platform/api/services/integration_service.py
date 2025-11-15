"""
Integration Service
Handles syncing data from cloud providers and security tools
"""

import asyncio
import json
import hashlib
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from cryptography.fernet import Fernet
import base64

logger = logging.getLogger(__name__)


class IntegrationService:
    """Service for managing third-party integrations"""

    def __init__(self, database):
        self.db = database
        # In production, load from secure key storage
        self.encryption_key = Fernet.generate_key()
        self.cipher = Fernet(self.encryption_key)

    def encrypt_credentials(self, credentials: Dict[str, str]) -> str:
        """Encrypt integration credentials"""
        try:
            json_str = json.dumps(credentials)
            encrypted = self.cipher.encrypt(json_str.encode())
            return base64.b64encode(encrypted).decode()
        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise

    def decrypt_credentials(self, encrypted_credentials: str) -> Dict[str, str]:
        """Decrypt integration credentials"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_credentials.encode())
            decrypted = self.cipher.decrypt(encrypted_bytes)
            return json.loads(decrypted.decode())
        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise

    async def test_connection(self, integration_id: str) -> bool:
        """Test connection to integration provider"""
        pool = self.db.get_pool()
        async with pool.acquire() as conn:
            integration = await conn.fetchrow("""
                SELECT * FROM organization_integrations
                WHERE id = $1
            """, integration_id)

            if not integration:
                return False

            try:
                credentials = self.decrypt_credentials(
                    integration["credentials_encrypted"]
                )

                # Test based on provider
                provider_id = integration["provider_id"]

                if provider_id == "aws":
                    success = await self._test_aws_connection(credentials)
                elif provider_id == "azure":
                    success = await self._test_azure_connection(credentials)
                elif provider_id == "gcp":
                    success = await self._test_gcp_connection(credentials)
                else:
                    # Generic test
                    success = True

                # Update status
                status = "active" if success else "error"
                await conn.execute("""
                    UPDATE organization_integrations
                    SET status = $1, updated_at = $2
                    WHERE id = $3
                """, status, datetime.utcnow(), integration_id)

                return success

            except Exception as e:
                logger.error(f"Connection test failed for {integration_id}: {e}")
                await conn.execute("""
                    UPDATE organization_integrations
                    SET status = 'error', last_sync_error = $1, updated_at = $2
                    WHERE id = $3
                """, str(e), datetime.utcnow(), integration_id)
                return False

    async def sync_integration(self, integration_id: str) -> Dict[str, Any]:
        """Sync data from integration provider"""
        sync_log_id = None
        started_at = datetime.utcnow()

        pool = self.db.get_pool()
        async with pool.acquire() as conn:
            try:
                integration = await conn.fetchrow("""
                    SELECT * FROM organization_integrations
                    WHERE id = $1
                """, integration_id)

                if not integration:
                    return {"status": "error", "message": "Integration not found"}

                # Create sync log
                sync_log_id = await conn.fetchval("""
                    INSERT INTO integration_sync_logs (
                        integration_id, sync_type, status, started_at
                    ) VALUES ($1, 'manual', 'running', $2)
                    RETURNING id
                """, integration_id, started_at)

                credentials = self.decrypt_credentials(
                    integration["credentials_encrypted"]
                )

                # Sync based on provider
                provider_id = integration["provider_id"]
                result = {"items_synced": 0, "items_failed": 0}

                if provider_id == "aws":
                    result = await self._sync_aws(integration, credentials)
                elif provider_id == "azure":
                    result = await self._sync_azure(integration, credentials)
                elif provider_id == "gcp":
                    result = await self._sync_gcp(integration, credentials)
                elif provider_id in ["tenable", "qualys"]:
                    result = await self._sync_security_findings(integration, credentials)

                # Update sync log
                completed_at = datetime.utcnow()
                duration = (completed_at - started_at).total_seconds()

                await conn.execute("""
                    UPDATE integration_sync_logs
                    SET status = 'success', items_synced = $1, items_failed = $2,
                        completed_at = $3, duration_seconds = $4
                    WHERE id = $5
                """, result["items_synced"], result["items_failed"],
                    completed_at, int(duration), sync_log_id)

                # Update integration
                await conn.execute("""
                    UPDATE organization_integrations
                    SET last_sync_at = $1, last_sync_status = 'success', updated_at = $2
                    WHERE id = $3
                """, completed_at, datetime.utcnow(), integration_id)

                return {
                    "status": "success",
                    "items_synced": result["items_synced"],
                    "items_failed": result["items_failed"],
                    "duration_seconds": int(duration)
                }

            except Exception as e:
                logger.error(f"Sync failed for {integration_id}: {e}")

                if sync_log_id:
                    completed_at = datetime.utcnow()
                    duration = (completed_at - started_at).total_seconds()

                    await conn.execute("""
                        UPDATE integration_sync_logs
                        SET status = 'failed', error_message = $1,
                            completed_at = $2, duration_seconds = $3
                        WHERE id = $4
                    """, str(e), completed_at, int(duration), sync_log_id)

                await conn.execute("""
                    UPDATE organization_integrations
                    SET last_sync_status = 'failed', last_sync_error = $1,
                        updated_at = $2
                    WHERE id = $3
                """, str(e), datetime.utcnow(), integration_id)

                return {"status": "error", "message": str(e)}

    # ========================================================================
    # Provider-specific implementations
    # ========================================================================

    async def _test_aws_connection(self, credentials: Dict[str, str]) -> bool:
        """Test AWS connection using boto3"""
        try:
            # In production: import boto3 and test
            # client = boto3.client(
            #     'sts',
            #     aws_access_key_id=credentials['access_key_id'],
            #     aws_secret_access_key=credentials['secret_access_key']
            # )
            # client.get_caller_identity()
            logger.info("AWS connection test (simulated)")
            return True
        except Exception as e:
            logger.error(f"AWS connection failed: {e}")
            return False

    async def _test_azure_connection(self, credentials: Dict[str, str]) -> bool:
        """Test Azure connection"""
        try:
            # In production: use Azure SDK
            logger.info("Azure connection test (simulated)")
            return True
        except Exception as e:
            logger.error(f"Azure connection failed: {e}")
            return False

    async def _test_gcp_connection(self, credentials: Dict[str, str]) -> bool:
        """Test GCP connection"""
        try:
            # In production: use Google Cloud SDK
            logger.info("GCP connection test (simulated)")
            return True
        except Exception as e:
            logger.error(f"GCP connection failed: {e}")
            return False

    async def _sync_aws(
        self,
        integration: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, int]:
        """Sync AWS resources"""
        items_synced = 0
        items_failed = 0

        pool = self.db.get_pool()
        async with pool.acquire() as conn:
            try:
                # In production: Use boto3 to enumerate resources
                # Example: EC2 instances, RDS databases, S3 buckets, etc.

                # Simulated data
                resources = [
                    {
                        "resource_type": "ec2_instance",
                        "resource_id": "i-1234567890abcdef0",
                        "resource_name": "web-server-1",
                        "region": "us-east-1",
                        "tags": {"Environment": "Production", "Owner": "DevOps"},
                        "metadata": {"instance_type": "t3.medium", "state": "running"}
                    },
                    {
                        "resource_type": "rds_instance",
                        "resource_id": "database-1",
                        "resource_name": "prod-database",
                        "region": "us-east-1",
                        "tags": {"Environment": "Production"},
                        "metadata": {"engine": "postgres", "version": "15.2"}
                    }
                ]

                for resource in resources:
                    try:
                        await conn.execute("""
                            INSERT INTO cloud_resources (
                                organization_id, integration_id, provider, resource_type,
                                resource_id, resource_name, region, tags, metadata
                            ) VALUES ($1, $2, 'aws', $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (organization_id, provider, resource_id)
                            DO UPDATE SET
                                resource_name = EXCLUDED.resource_name,
                                tags = EXCLUDED.tags,
                                metadata = EXCLUDED.metadata,
                                updated_at = NOW()
                        """, integration["organization_id"], integration["id"],
                            resource["resource_type"], resource["resource_id"],
                            resource["resource_name"], resource["region"],
                            resource["tags"], resource["metadata"])

                        items_synced += 1
                    except Exception as e:
                        logger.error(f"Failed to sync AWS resource: {e}")
                        items_failed += 1

            except Exception as e:
                logger.error(f"AWS sync failed: {e}")
                items_failed += 1

        return {"items_synced": items_synced, "items_failed": items_failed}

    async def _sync_azure(
        self,
        integration: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, int]:
        """Sync Azure resources"""
        # Similar to AWS but for Azure resources
        logger.info("Azure sync (simulated)")
        return {"items_synced": 0, "items_failed": 0}

    async def _sync_gcp(
        self,
        integration: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, int]:
        """Sync GCP resources"""
        # Similar to AWS but for GCP resources
        logger.info("GCP sync (simulated)")
        return {"items_synced": 0, "items_failed": 0}

    async def _sync_security_findings(
        self,
        integration: Dict[str, Any],
        credentials: Dict[str, str]
    ) -> Dict[str, int]:
        """Sync security findings from vulnerability scanners"""
        items_synced = 0
        items_failed = 0

        pool = self.db.get_pool()
        async with pool.acquire() as conn:
            try:
                # In production: Call scanner API (Tenable, Qualys, etc.)

                # Simulated findings
                findings = [
                    {
                        "finding_id": "CVE-2024-1234",
                        "title": "Critical SQL Injection Vulnerability",
                        "description": "SQL injection vulnerability in web application",
                        "severity": "critical",
                        "status": "open",
                        "affected_resource": "web-app-1",
                        "cvss_score": 9.8,
                        "cve_ids": ["CVE-2024-1234"],
                        "remediation": "Update to version 2.0.1 or later"
                    }
                ]

                for finding in findings:
                    try:
                        await conn.execute("""
                            INSERT INTO security_findings (
                                organization_id, integration_id, finding_id, title,
                                description, severity, status, affected_resource,
                                cvss_score, cve_ids, remediation
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
                            ON CONFLICT (organization_id, integration_id, finding_id)
                            DO UPDATE SET
                                title = EXCLUDED.title,
                                description = EXCLUDED.description,
                                severity = EXCLUDED.severity,
                                status = EXCLUDED.status,
                                last_seen_at = NOW(),
                                updated_at = NOW()
                        """, integration["organization_id"], integration["id"],
                            finding["finding_id"], finding["title"],
                            finding["description"], finding["severity"],
                            finding["status"], finding.get("affected_resource"),
                            finding.get("cvss_score"), finding.get("cve_ids", []),
                            finding.get("remediation"))

                        items_synced += 1
                    except Exception as e:
                        logger.error(f"Failed to sync finding: {e}")
                        items_failed += 1

            except Exception as e:
                logger.error(f"Security findings sync failed: {e}")
                items_failed += 1

        return {"items_synced": items_synced, "items_failed": items_failed}
