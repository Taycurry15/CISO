"""
Integration Hub API
Manage third-party integrations, webhooks, and API keys
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid
import hashlib
import secrets

from database import Database
from services.integration_service import IntegrationService

router = APIRouter()
db = Database()


# Enums
class IntegrationCategory(str, Enum):
    CLOUD = "cloud"
    SECURITY = "security"
    TICKETING = "ticketing"
    SSO = "sso"
    OTHER = "other"


class IntegrationStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    PENDING = "pending"


# Request/Response Models
class IntegrationProvider(BaseModel):
    id: str
    name: str
    category: IntegrationCategory
    description: Optional[str] = None
    logo_url: Optional[str] = None
    documentation_url: Optional[str] = None
    is_active: bool = True


class CreateIntegrationRequest(BaseModel):
    provider_id: str = Field(..., description="Provider ID (aws, azure, gcp, etc.)")
    name: str = Field(..., description="Integration name")
    configuration: Dict[str, Any] = Field(default_factory=dict)
    credentials: Dict[str, str] = Field(..., description="Provider credentials")
    auto_sync_enabled: bool = True
    sync_frequency_minutes: int = Field(default=60, ge=5, le=1440)


class UpdateIntegrationRequest(BaseModel):
    name: Optional[str] = None
    configuration: Optional[Dict[str, Any]] = None
    credentials: Optional[Dict[str, str]] = None
    auto_sync_enabled: Optional[bool] = None
    sync_frequency_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    status: Optional[IntegrationStatus] = None


class IntegrationResponse(BaseModel):
    id: str
    organization_id: str
    provider_id: str
    provider_name: str
    name: str
    status: IntegrationStatus
    configuration: Dict[str, Any]
    last_sync_at: Optional[datetime] = None
    last_sync_status: Optional[str] = None
    sync_frequency_minutes: int
    auto_sync_enabled: bool
    created_at: datetime
    updated_at: datetime


class CreateWebhookRequest(BaseModel):
    name: str
    url: HttpUrl
    events: List[str] = Field(..., description="Event types to trigger webhook")
    headers: Dict[str, str] = Field(default_factory=dict)
    retry_count: int = Field(default=3, ge=0, le=10)
    timeout_seconds: int = Field(default=30, ge=5, le=120)


class WebhookResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    url: str
    secret: str
    events: List[str]
    is_active: bool
    headers: Dict[str, str]
    retry_count: int
    timeout_seconds: int
    created_at: datetime


class CreateAPIKeyRequest(BaseModel):
    name: str
    permissions: List[str] = Field(..., description="API permissions (read:assessments, etc.)")
    rate_limit_per_minute: int = Field(default=100, ge=10, le=1000)
    expires_at: Optional[datetime] = None


class APIKeyResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    key: Optional[str] = None  # Only returned on creation
    key_prefix: str
    permissions: List[str]
    rate_limit_per_minute: int
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool
    created_at: datetime


class CloudResourceResponse(BaseModel):
    id: str
    provider: str
    resource_type: str
    resource_id: str
    resource_name: Optional[str] = None
    region: Optional[str] = None
    tags: Dict[str, Any]
    compliance_status: Optional[str] = None
    last_scanned_at: Optional[datetime] = None


class SecurityFindingResponse(BaseModel):
    id: str
    finding_id: str
    title: str
    description: Optional[str] = None
    severity: str
    status: str
    affected_resource: Optional[str] = None
    cvss_score: Optional[float] = None
    cve_ids: List[str]
    remediation: Optional[str] = None
    first_seen_at: datetime
    last_seen_at: datetime


# ============================================================================
# INTEGRATION PROVIDERS
# ============================================================================

@router.get("/integrations/providers", response_model=List[IntegrationProvider])
async def list_integration_providers(
    category: Optional[IntegrationCategory] = None
):
    """List all available integration providers"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM integration_providers WHERE is_active = true"
        params = []

        if category:
            query += " AND category = $1"
            params.append(category.value)

        query += " ORDER BY name"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


# ============================================================================
# ORGANIZATION INTEGRATIONS
# ============================================================================

@router.post("/integrations", response_model=IntegrationResponse)
async def create_integration(
    request: CreateIntegrationRequest,
    organization_id: str = "test-org-id",  # From auth
    user_id: str = "test-user-id",  # From auth
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Create a new integration"""
    integration_service = IntegrationService(db)

    integration_id = str(uuid.uuid4())

    # Encrypt credentials
    credentials_encrypted = integration_service.encrypt_credentials(
        request.credentials
    )

    pool = db.get_pool()
    async with pool.acquire() as conn:
        # Verify provider exists
        provider = await conn.fetchrow(
            "SELECT * FROM integration_providers WHERE id = $1",
            request.provider_id
        )
        if not provider:
            raise HTTPException(status_code=404, detail="Provider not found")

        # Create integration
        row = await conn.fetchrow("""
            INSERT INTO organization_integrations (
                id, organization_id, provider_id, name, status,
                configuration, credentials_encrypted, sync_frequency_minutes,
                auto_sync_enabled, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """, integration_id, organization_id, request.provider_id, request.name,
            "pending", request.configuration, credentials_encrypted,
            request.sync_frequency_minutes, request.auto_sync_enabled, user_id)

        # Test connection in background
        background_tasks.add_task(
            integration_service.test_connection,
            integration_id
        )

        return {
            **dict(row),
            "provider_name": provider["name"]
        }


@router.get("/integrations", response_model=List[IntegrationResponse])
async def list_integrations(
    organization_id: str = "test-org-id",  # From auth
    provider_id: Optional[str] = None,
    status: Optional[IntegrationStatus] = None
):
    """List organization integrations"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        query = """
            SELECT i.*, p.name as provider_name
            FROM organization_integrations i
            JOIN integration_providers p ON i.provider_id = p.id
            WHERE i.organization_id = $1
        """
        params = [organization_id]

        if provider_id:
            query += f" AND i.provider_id = ${len(params) + 1}"
            params.append(provider_id)

        if status:
            query += f" AND i.status = ${len(params) + 1}"
            params.append(status.value)

        query += " ORDER BY i.created_at DESC"

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


@router.get("/integrations/{integration_id}", response_model=IntegrationResponse)
async def get_integration(
    integration_id: str,
    organization_id: str = "test-org-id"  # From auth
):
    """Get integration details"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT i.*, p.name as provider_name
            FROM organization_integrations i
            JOIN integration_providers p ON i.provider_id = p.id
            WHERE i.id = $1 AND i.organization_id = $2
        """, integration_id, organization_id)

        if not row:
            raise HTTPException(status_code=404, detail="Integration not found")

        return dict(row)


@router.put("/integrations/{integration_id}", response_model=IntegrationResponse)
async def update_integration(
    integration_id: str,
    request: UpdateIntegrationRequest,
    organization_id: str = "test-org-id"  # From auth
):
    """Update integration configuration"""
    integration_service = IntegrationService(db)

    pool = db.get_pool()
    async with pool.acquire() as conn:
        # Check if exists
        existing = await conn.fetchrow("""
            SELECT * FROM organization_integrations
            WHERE id = $1 AND organization_id = $2
        """, integration_id, organization_id)

        if not existing:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Build update query
        updates = []
        params = []
        param_index = 1

        if request.name is not None:
            updates.append(f"name = ${param_index}")
            params.append(request.name)
            param_index += 1

        if request.configuration is not None:
            updates.append(f"configuration = ${param_index}")
            params.append(request.configuration)
            param_index += 1

        if request.credentials is not None:
            encrypted = integration_service.encrypt_credentials(request.credentials)
            updates.append(f"credentials_encrypted = ${param_index}")
            params.append(encrypted)
            param_index += 1

        if request.status is not None:
            updates.append(f"status = ${param_index}")
            params.append(request.status.value)
            param_index += 1

        if request.auto_sync_enabled is not None:
            updates.append(f"auto_sync_enabled = ${param_index}")
            params.append(request.auto_sync_enabled)
            param_index += 1

        if request.sync_frequency_minutes is not None:
            updates.append(f"sync_frequency_minutes = ${param_index}")
            params.append(request.sync_frequency_minutes)
            param_index += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")

        updates.append(f"updated_at = ${param_index}")
        params.append(datetime.utcnow())
        param_index += 1

        params.append(integration_id)
        params.append(organization_id)

        query = f"""
            UPDATE organization_integrations
            SET {', '.join(updates)}
            WHERE id = ${param_index - 1} AND organization_id = ${param_index}
            RETURNING *
        """

        row = await conn.fetchrow(query, *params)

        # Get provider name
        provider = await conn.fetchrow(
            "SELECT name FROM integration_providers WHERE id = $1",
            row["provider_id"]
        )

        return {**dict(row), "provider_name": provider["name"]}


@router.delete("/integrations/{integration_id}")
async def delete_integration(
    integration_id: str,
    organization_id: str = "test-org-id"  # From auth
):
    """Delete an integration"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM organization_integrations
            WHERE id = $1 AND organization_id = $2
        """, integration_id, organization_id)

        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Integration not found")

        return {"message": "Integration deleted"}


@router.post("/integrations/{integration_id}/sync")
async def trigger_sync(
    integration_id: str,
    organization_id: str = "test-org-id",  # From auth
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """Manually trigger integration sync"""
    integration_service = IntegrationService(db)

    pool = db.get_pool()
    async with pool.acquire() as conn:
        integration = await conn.fetchrow("""
            SELECT * FROM organization_integrations
            WHERE id = $1 AND organization_id = $2
        """, integration_id, organization_id)

        if not integration:
            raise HTTPException(status_code=404, detail="Integration not found")

        # Trigger sync in background
        background_tasks.add_task(
            integration_service.sync_integration,
            integration_id
        )

        return {"message": "Sync triggered", "integration_id": integration_id}


# ============================================================================
# WEBHOOKS
# ============================================================================

@router.post("/webhooks", response_model=WebhookResponse)
async def create_webhook(
    request: CreateWebhookRequest,
    organization_id: str = "test-org-id",  # From auth
    user_id: str = "test-user-id"  # From auth
):
    """Create a new webhook"""
    webhook_id = str(uuid.uuid4())
    secret = secrets.token_urlsafe(32)

    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO webhooks (
                id, organization_id, name, url, secret, events,
                headers, retry_count, timeout_seconds, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING *
        """, webhook_id, organization_id, request.name, str(request.url),
            secret, request.events, request.headers, request.retry_count,
            request.timeout_seconds, user_id)

        return dict(row)


@router.get("/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    organization_id: str = "test-org-id"  # From auth
):
    """List organization webhooks"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM webhooks
            WHERE organization_id = $1
            ORDER BY created_at DESC
        """, organization_id)

        return [dict(row) for row in rows]


@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    organization_id: str = "test-org-id"  # From auth
):
    """Delete a webhook"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM webhooks
            WHERE id = $1 AND organization_id = $2
        """, webhook_id, organization_id)

        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="Webhook not found")

        return {"message": "Webhook deleted"}


# ============================================================================
# API KEYS
# ============================================================================

@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    request: CreateAPIKeyRequest,
    organization_id: str = "test-org-id",  # From auth
    user_id: str = "test-user-id"  # From auth
):
    """Create a new API key"""
    # Generate API key
    key = f"cmmc_{secrets.token_urlsafe(32)}"
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    key_prefix = key[:12] + "..."

    api_key_id = str(uuid.uuid4())

    pool = db.get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO api_keys (
                id, organization_id, name, key_hash, key_prefix,
                permissions, rate_limit_per_minute, expires_at, created_by
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            RETURNING *
        """, api_key_id, organization_id, request.name, key_hash, key_prefix,
            request.permissions, request.rate_limit_per_minute, request.expires_at, user_id)

        response = dict(row)
        response["key"] = key  # Only shown once
        return response


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    organization_id: str = "test-org-id"  # From auth
):
    """List organization API keys"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT * FROM api_keys
            WHERE organization_id = $1
            ORDER BY created_at DESC
        """, organization_id)

        return [dict(row) for row in rows]


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    organization_id: str = "test-org-id"  # From auth
):
    """Revoke an API key"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute("""
            DELETE FROM api_keys
            WHERE id = $1 AND organization_id = $2
        """, key_id, organization_id)

        if result == "DELETE 0":
            raise HTTPException(status_code=404, detail="API key not found")

        return {"message": "API key revoked"}


# ============================================================================
# CLOUD RESOURCES
# ============================================================================

@router.get("/cloud-resources", response_model=List[CloudResourceResponse])
async def list_cloud_resources(
    organization_id: str = "test-org-id",  # From auth
    provider: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 100
):
    """List cloud resources synced from integrations"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM cloud_resources WHERE organization_id = $1"
        params = [organization_id]

        if provider:
            query += f" AND provider = ${len(params) + 1}"
            params.append(provider)

        if resource_type:
            query += f" AND resource_type = ${len(params) + 1}"
            params.append(resource_type)

        query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]


# ============================================================================
# SECURITY FINDINGS
# ============================================================================

@router.get("/security-findings", response_model=List[SecurityFindingResponse])
async def list_security_findings(
    organization_id: str = "test-org-id",  # From auth
    severity: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100
):
    """List security findings from integrated tools"""
    pool = db.get_pool()
    async with pool.acquire() as conn:
        query = "SELECT * FROM security_findings WHERE organization_id = $1"
        params = [organization_id]

        if severity:
            query += f" AND severity = ${len(params) + 1}"
            params.append(severity)

        if status:
            query += f" AND status = ${len(params) + 1}"
            params.append(status)

        query += f" ORDER BY first_seen_at DESC LIMIT ${len(params) + 1}"
        params.append(limit)

        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
