# User Management & RBAC System

Complete authentication, authorization, and multi-tenant user management for the CMMC Compliance Platform.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Security Features](#security-features)
- [User Roles](#user-roles)
- [API Endpoints](#api-endpoints)
- [Authentication Flow](#authentication-flow)
- [RBAC Implementation](#rbac-implementation)
- [Multi-Tenant Isolation](#multi-tenant-isolation)
- [Code Examples](#code-examples)
- [Testing](#testing)

## Overview

The user management system provides:

- **Secure Authentication**: JWT-based authentication with bcrypt password hashing
- **Role-Based Access Control (RBAC)**: 4 roles with hierarchical permissions
- **Multi-Tenant Support**: Organization-based data isolation
- **Token Management**: Access tokens (1 hour) and refresh tokens (30 days)
- **User Lifecycle**: Registration, login, profile management, password changes
- **Admin Tools**: User and organization management for administrators

## Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                      User Management                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │
│  │  User API    │  │  Services    │  │   Middleware    │  │
│  │              │  │              │  │                 │  │
│  │ - Register   │  │ - UserSvc    │  │ - Auth Context │  │
│  │ - Login      │  │ - AuthSvc    │  │ - require_role │  │
│  │ - Profile    │  │ - OrgSvc     │  │ - permissions  │  │
│  │ - Admin      │  │              │  │ - isolation    │  │
│  └──────────────┘  └──────────────┘  └─────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Database (PostgreSQL)                    │  │
│  │                                                       │  │
│  │  users table          organizations table            │  │
│  │  - id (UUID)          - id (UUID)                    │  │
│  │  - organization_id    - name                         │  │
│  │  - email (unique)     - type (SMB, Enterprise...)    │  │
│  │  - password_hash      - status (Active, Trial...)    │  │
│  │  - role               - contact info                 │  │
│  │  - status                                            │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
api/
├── user_api.py                      # User management REST API
├── services/
│   ├── user_service.py              # User CRUD and authentication
│   ├── auth_service.py              # JWT token management
│   └── organization_service.py      # Multi-tenant organizations
├── middleware/
│   └── auth_middleware.py           # RBAC and permission checking
└── tests/
    └── test_user_management.py      # Comprehensive tests
```

## Security Features

### 1. Password Security

- **bcrypt Hashing**: Passwords hashed with bcrypt (12 rounds)
- **Salted**: Each password has unique salt
- **Never Stored Plaintext**: Original passwords never stored
- **Strength Requirements**: 8+ chars, uppercase, lowercase, digit

```python
# Password hashing
password = "SecurePass123"
salt = bcrypt.gensalt()
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)

# Password verification
is_valid = bcrypt.checkpw(password.encode('utf-8'), hashed)
```

### 2. JWT Token Security

- **HS256 Algorithm**: HMAC with SHA-256
- **Short-Lived Access Tokens**: 1 hour expiration
- **Long-Lived Refresh Tokens**: 30 days expiration
- **Token Type Enforcement**: Access vs refresh tokens validated
- **Secret Key Protection**: Loaded from environment variables

```python
# Token payload
{
    "sub": "user-123",              # Subject (user ID)
    "org_id": "org-456",            # Organization ID
    "email": "user@example.com",    # User email
    "role": "Assessor",             # User role
    "type": "access",               # Token type
    "iat": 1234567890,              # Issued at
    "exp": 1234571490               # Expires at (1 hour)
}
```

### 3. Multi-Tenant Isolation

- **Organization-Based**: All data scoped to organization_id
- **Automatic Filtering**: Users only see their organization's data
- **Cross-Org Prevention**: API enforces organization boundaries
- **Admin Restrictions**: Admins can only manage their own organization

## User Roles

### Role Hierarchy

```
Admin > Assessor > Auditor > Viewer
  4        3          2        1
```

### Role Permissions

#### Admin (Level 4)
- **Full Control**: All permissions
- **User Management**: Create, update, delete users
- **Organization Management**: Update organization settings
- **Assessment Management**: Full CRUD on assessments
- **Evidence Management**: Full CRUD on evidence
- **Report Generation**: Generate all reports

#### Assessor (Level 3)
- **Assessment CRUD**: Create, read, update assessments
- **Evidence CRUD**: Create, read, update, delete evidence
- **Control Updates**: Update control findings
- **Report Generation**: Generate reports
- **Read-Only Users**: View user list

#### Auditor (Level 2)
- **Read-Only Assessments**: View all assessments
- **Read-Only Evidence**: View all evidence
- **Read-Only Controls**: View all controls
- **Report Generation**: Generate audit reports
- **Read-Only Users**: View user list

#### Viewer (Level 1)
- **Read-Only Assigned**: View assigned assessments only
- **Read-Only Evidence**: View evidence for assigned assessments
- **Read-Only Controls**: View controls for assigned assessments
- **Read-Only Reports**: View generated reports

### Permission Mapping

```python
permissions = {
    'assessment': ['read', 'create', 'update', 'delete'],
    'evidence': ['read', 'create', 'update', 'delete'],
    'control': ['read', 'update'],
    'report': ['read', 'create'],
    'user': ['read', 'create', 'update', 'delete'],
    'organization': ['read', 'update']
}
```

## API Endpoints

### Authentication Endpoints

#### POST /api/v1/auth/register
Register new user and organization.

**Request:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123",
    "full_name": "John Doe",
    "organization_name": "Acme Corp",
    "organization_type": "SMB",
    "phone": "555-0100"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

#### POST /api/v1/auth/login
Authenticate user.

**Request:**
```json
{
    "email": "user@example.com",
    "password": "SecurePass123"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

#### POST /api/v1/auth/refresh
Refresh access token.

**Request:**
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 3600
}
```

### User Profile Endpoints

#### GET /api/v1/users/me
Get current user profile.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Response:**
```json
{
    "id": "user-123",
    "organization_id": "org-456",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "Assessor",
    "status": "Active",
    "phone": "555-0100",
    "job_title": "Security Engineer",
    "email_verified": true,
    "last_login": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
}
```

#### PUT /api/v1/users/me
Update current user profile.

**Request:**
```json
{
    "full_name": "John Smith",
    "phone": "555-0200",
    "job_title": "Senior Security Engineer"
}
```

#### PUT /api/v1/users/me/password
Change password.

**Request:**
```json
{
    "current_password": "OldPass123",
    "new_password": "NewPass456"
}
```

#### GET /api/v1/users/me/permissions
Get current user permissions.

**Response:**
```json
{
    "user_id": "user-123",
    "role": "Assessor",
    "permissions": [
        "assessment:read",
        "assessment:create",
        "assessment:update",
        "evidence:read",
        "evidence:create",
        "evidence:update",
        "evidence:delete",
        "control:read",
        "control:update",
        "report:read",
        "report:create"
    ]
}
```

### User Management Endpoints (Admin Only)

#### GET /api/v1/users
List users with filtering and pagination.

**Query Parameters:**
- `organization_id` (optional): Filter by organization
- `role` (optional): Filter by role
- `status` (optional): Filter by status
- `limit` (default: 50, max: 100)
- `offset` (default: 0)

**Response:**
```json
[
    {
        "id": "user-123",
        "organization_id": "org-456",
        "email": "user1@example.com",
        "full_name": "John Doe",
        "role": "Assessor",
        "status": "Active",
        ...
    },
    {
        "id": "user-124",
        "organization_id": "org-456",
        "email": "user2@example.com",
        "full_name": "Jane Smith",
        "role": "Viewer",
        "status": "Active",
        ...
    }
]
```

#### POST /api/v1/users
Create new user (admin only).

**Request:**
```json
{
    "organization_id": "org-456",
    "email": "newuser@example.com",
    "password": "SecurePass123",
    "full_name": "New User",
    "role": "Viewer",
    "phone": "555-0300",
    "job_title": "Analyst"
}
```

#### GET /api/v1/users/{user_id}
Get user by ID.

#### PUT /api/v1/users/{user_id}
Update user (admin can change role, status).

**Request:**
```json
{
    "full_name": "Updated Name",
    "role": "Assessor",
    "status": "Active",
    "phone": "555-0400",
    "job_title": "Lead Analyst"
}
```

#### DELETE /api/v1/users/{user_id}
Soft delete user (sets status to Inactive).

### Organization Management Endpoints (Admin Only)

#### GET /api/v1/organizations
List organizations.

#### GET /api/v1/organizations/{org_id}
Get organization by ID.

#### PUT /api/v1/organizations/{org_id}
Update organization.

**Request:**
```json
{
    "name": "Updated Company Name",
    "organization_type": "Enterprise",
    "status": "Active",
    "address": "456 New St",
    "phone": "555-0500",
    "email": "contact@updated.com"
}
```

#### GET /api/v1/organizations/{org_id}/stats
Get organization statistics.

**Response:**
```json
{
    "organization_id": "org-456",
    "active_users": 12,
    "total_assessments": 25,
    "completed_assessments": 18,
    "total_evidence": 342
}
```

## Authentication Flow

### Registration Flow

```
┌──────┐                  ┌──────┐                  ┌──────┐
│Client│                  │ API  │                  │  DB  │
└──┬───┘                  └──┬───┘                  └──┬───┘
   │                         │                         │
   │ POST /auth/register     │                         │
   │ {email, password, ...}  │                         │
   ├────────────────────────>│                         │
   │                         │                         │
   │                         │ Hash password (bcrypt)  │
   │                         │                         │
   │                         │ INSERT organizations    │
   │                         ├────────────────────────>│
   │                         │                         │
   │                         │ INSERT users            │
   │                         ├────────────────────────>│
   │                         │                         │
   │                         │ Generate JWT tokens     │
   │                         │                         │
   │ 201 Created             │                         │
   │ {access_token, ...}     │                         │
   │<────────────────────────┤                         │
   │                         │                         │
```

### Login Flow

```
┌──────┐                  ┌──────┐                  ┌──────┐
│Client│                  │ API  │                  │  DB  │
└──┬───┘                  └──┬───┘                  └──┬───┘
   │                         │                         │
   │ POST /auth/login        │                         │
   │ {email, password}       │                         │
   ├────────────────────────>│                         │
   │                         │                         │
   │                         │ SELECT user by email    │
   │                         ├────────────────────────>│
   │                         │<────────────────────────┤
   │                         │                         │
   │                         │ Verify password (bcrypt)│
   │                         │                         │
   │                         │ UPDATE last_login       │
   │                         ├────────────────────────>│
   │                         │                         │
   │                         │ Generate JWT tokens     │
   │                         │                         │
   │ 200 OK                  │                         │
   │ {access_token, ...}     │                         │
   │<────────────────────────┤                         │
   │                         │                         │
```

### Authenticated Request Flow

```
┌──────┐                  ┌──────────┐               ┌──────┐
│Client│                  │Middleware│               │ API  │
└──┬───┘                  └────┬─────┘               └──┬───┘
   │                           │                        │
   │ GET /assessments          │                        │
   │ Authorization: Bearer ... │                        │
   ├──────────────────────────>│                        │
   │                           │                        │
   │                           │ Extract token          │
   │                           │ Verify JWT signature   │
   │                           │ Check expiration       │
   │                           │ Get user from DB       │
   │                           │ Check user status      │
   │                           │ Create AuthContext     │
   │                           │                        │
   │                           │ AuthContext            │
   │                           ├───────────────────────>│
   │                           │                        │
   │                           │                        │ Check permissions
   │                           │                        │ Filter by org_id
   │                           │                        │ Execute query
   │                           │                        │
   │                           │        Response        │
   │<──────────────────────────┴────────────────────────┤
   │                                                    │
```

### Token Refresh Flow

```
┌──────┐                  ┌──────┐                  ┌──────┐
│Client│                  │ API  │                  │  DB  │
└──┬───┘                  └──┬───┘                  └──┬───┘
   │                         │                         │
   │ Access token expired    │                         │
   │ (401 Unauthorized)      │                         │
   │                         │                         │
   │ POST /auth/refresh      │                         │
   │ {refresh_token}         │                         │
   ├────────────────────────>│                         │
   │                         │                         │
   │                         │ Verify refresh token    │
   │                         │                         │
   │                         │ SELECT user by ID       │
   │                         ├────────────────────────>│
   │                         │<────────────────────────┤
   │                         │                         │
   │                         │ Check user still active │
   │                         │                         │
   │                         │ Generate new tokens     │
   │                         │                         │
   │ 200 OK                  │                         │
   │ {access_token, ...}     │                         │
   │<────────────────────────┤                         │
   │                         │                         │
   │ Continue with new token │                         │
   │                         │                         │
```

## RBAC Implementation

### Using Role-Based Protection

```python
from fastapi import APIRouter, Depends
from middleware.auth_middleware import (
    require_admin,
    require_assessor,
    require_auth,
    AuthContext
)

router = APIRouter()

# Require any authenticated user
@router.get("/public-data")
async def get_public_data(
    auth: AuthContext = require_auth
):
    return {"message": f"Hello {auth.email}"}

# Require assessor or admin role
@router.post("/assessments")
async def create_assessment(
    auth: AuthContext = Depends(require_assessor)
):
    # Only Assessor and Admin can create
    return {"created_by": auth.user_id}

# Require admin role only
@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    auth: AuthContext = Depends(require_admin)
):
    # Only Admin can delete users
    return {"deleted": user_id}
```

### Using Permission-Based Protection

```python
from middleware.auth_middleware import require_permission

# Require specific permission
@router.put("/assessments/{id}")
async def update_assessment(
    id: str,
    auth: AuthContext = Depends(require_permission("assessment:update"))
):
    # Check if assessment belongs to user's organization
    auth.require_same_organization(assessment.organization_id)

    return {"updated": id}

# Require multiple possible permissions
@router.get("/reports/{id}")
async def get_report(
    id: str,
    auth: AuthContext = Depends(
        require_permission("report:read", "report:create")
    )
):
    return {"report_id": id}
```

### Custom Permission Checks

```python
from middleware.auth_middleware import get_auth_context

@router.post("/assessments/{id}/evidence")
async def upload_evidence(
    id: str,
    file: UploadFile,
    auth: AuthContext = Depends(get_auth_context)
):
    # Manual permission check
    if not auth.has_permission("evidence:create"):
        raise HTTPException(
            status_code=403,
            detail="Cannot upload evidence"
        )

    # Check organization isolation
    assessment = await get_assessment(id)
    auth.require_same_organization(assessment.organization_id)

    # Upload evidence
    return {"uploaded": file.filename}
```

## Multi-Tenant Isolation

### Automatic Organization Filtering

All queries automatically filter by organization_id:

```python
# In user service
async def list_users(self, organization_id: str, ...):
    """List users - automatically filtered to organization"""
    query = """
        SELECT * FROM users
        WHERE organization_id = $1
        AND status = 'Active'
    """
    users = await conn.fetch(query, organization_id)
    return users
```

### Preventing Cross-Organization Access

```python
from middleware.auth_middleware import OrganizationIsolation

# Create middleware
org_isolation = OrganizationIsolation()

@router.get("/assessments/{id}")
async def get_assessment(
    id: str,
    auth: AuthContext = Depends(get_auth_context)
):
    # Get assessment
    assessment = await assessment_service.get_assessment(id)

    if not assessment:
        raise HTTPException(status_code=404, detail="Not found")

    # Verify same organization
    auth.require_same_organization(assessment['organization_id'])

    return assessment
```

## Code Examples

### Complete Registration Example

```python
import httpx

# Register new user and organization
async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/auth/register",
        json={
            "email": "admin@newcompany.com",
            "password": "SecurePass123!",
            "full_name": "Company Admin",
            "organization_name": "New Company Inc",
            "organization_type": "Enterprise",
            "phone": "555-1234"
        }
    )

    tokens = response.json()
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    print(f"Registered! Access token: {access_token[:20]}...")
```

### Complete Login and API Call Example

```python
# Login
async with httpx.AsyncClient() as client:
    # Step 1: Login
    login_response = await client.post(
        "http://localhost:8000/api/v1/auth/login",
        json={
            "email": "admin@newcompany.com",
            "password": "SecurePass123!"
        }
    )

    tokens = login_response.json()
    access_token = tokens["access_token"]

    # Step 2: Make authenticated request
    headers = {"Authorization": f"Bearer {access_token}"}

    profile_response = await client.get(
        "http://localhost:8000/api/v1/users/me",
        headers=headers
    )

    profile = profile_response.json()
    print(f"Logged in as: {profile['full_name']} ({profile['role']})")

    # Step 3: Create assessment (if has permission)
    assessment_response = await client.post(
        "http://localhost:8000/api/v1/assessments",
        headers=headers,
        json={
            "name": "Q1 2024 Assessment",
            "assessment_type": "CMMC_L2",
            "scope": {
                "level": 2,
                "domains": ["all"],
                "cloud_providers": ["Microsoft365", "Azure"]
            }
        }
    )

    assessment = assessment_response.json()
    print(f"Created assessment: {assessment['id']}")
```

### Token Refresh Example

```python
async def make_api_call(access_token, refresh_token):
    """Make API call with automatic token refresh"""
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        # Try API call
        response = await client.get(
            "http://localhost:8000/api/v1/assessments",
            headers=headers
        )

        # If token expired, refresh and retry
        if response.status_code == 401:
            # Refresh token
            refresh_response = await client.post(
                "http://localhost:8000/api/v1/auth/refresh",
                json={"refresh_token": refresh_token}
            )

            new_tokens = refresh_response.json()
            access_token = new_tokens["access_token"]
            refresh_token = new_tokens["refresh_token"]

            # Retry with new token
            headers = {"Authorization": f"Bearer {access_token}"}
            response = await client.get(
                "http://localhost:8000/api/v1/assessments",
                headers=headers
            )

        return response.json(), access_token, refresh_token
```

## Testing

### Run All Tests

```bash
cd api
pytest tests/test_user_management.py -v
```

### Run Specific Test Categories

```bash
# Test user service
pytest tests/test_user_management.py::TestUserService -v

# Test auth service
pytest tests/test_user_management.py::TestAuthService -v

# Test RBAC
pytest tests/test_user_management.py::TestRoleBasedAccess -v

# Test security
pytest tests/test_user_management.py::TestSecurity -v
```

### Test Coverage

```bash
pytest tests/test_user_management.py --cov=services --cov=middleware --cov-report=html
```

### Manual API Testing

```bash
# Start API server
uvicorn main:app --reload

# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123",
    "full_name": "Test User",
    "organization_name": "Test Org"
  }'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "SecurePass123"
  }'

# Get profile (use token from login)
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <access_token>"
```

## Environment Configuration

### Required Environment Variables

```bash
# .env file
JWT_SECRET_KEY=your-super-secret-jwt-key-min-32-chars
DATABASE_URL=postgresql://user:pass@localhost:5432/cmmc_db
```

### Generate Secure Secret Key

```python
import secrets

# Generate random 64-character hex string
secret_key = secrets.token_hex(32)
print(f"JWT_SECRET_KEY={secret_key}")
```

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,  -- Admin, Assessor, Auditor, Viewer
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',  -- Active, Inactive, Pending, Suspended
    phone VARCHAR(20),
    job_title VARCHAR(100),
    email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),

    INDEX idx_users_organization_id (organization_id),
    INDEX idx_users_email (email),
    INDEX idx_users_status (status)
);
```

### Organizations Table

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    organization_type VARCHAR(50) NOT NULL,  -- Enterprise, SMB, Consultant, C3PAO
    status VARCHAR(50) NOT NULL DEFAULT 'Trial',  -- Active, Trial, Suspended, Inactive
    address VARCHAR(500),
    phone VARCHAR(20),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(255),

    INDEX idx_organizations_status (status),
    INDEX idx_organizations_type (organization_type)
);
```

## Best Practices

### 1. Always Use HTTPS in Production

Never send JWT tokens over unencrypted HTTP in production.

### 2. Store Tokens Securely

- **Web Apps**: Use httpOnly cookies (not localStorage)
- **Mobile Apps**: Use secure keychain/keystore
- **Desktop Apps**: Use encrypted storage

### 3. Rotate Secret Keys

Periodically rotate JWT secret keys:

1. Generate new secret key
2. Sign new tokens with new key
3. Verify tokens with both old and new keys (grace period)
4. After grace period, remove old key

### 4. Monitor Failed Login Attempts

Implement rate limiting and account lockout:

```python
# TODO: Implement with Redis
max_attempts = 5
lockout_duration = 15  # minutes
```

### 5. Audit All Admin Actions

Log all user/organization modifications:

```python
logger.info(
    f"Admin action: {action} by {admin_email} "
    f"on user {target_email} at {timestamp}"
)
```

## Troubleshooting

### Common Issues

**Issue**: `401 Unauthorized` on valid token

**Solution**: Check token expiration, verify secret key matches

**Issue**: `403 Forbidden` on valid user

**Solution**: Check user status is Active, verify role has required permission

**Issue**: Cross-organization access

**Solution**: Verify organization_id filtering in queries, check AuthContext

**Issue**: Password hash verification fails

**Solution**: Ensure using same bcrypt version, check encoding (UTF-8)

## Future Enhancements

- [ ] Email verification workflow
- [ ] Password reset via email
- [ ] Two-factor authentication (TOTP)
- [ ] API key management for programmatic access
- [ ] Rate limiting with Redis
- [ ] Audit log table for compliance
- [ ] Session management (logout all devices)
- [ ] OAuth2/SAML SSO integration
- [ ] IP whitelist/blacklist
- [ ] Anomaly detection (unusual login locations)
