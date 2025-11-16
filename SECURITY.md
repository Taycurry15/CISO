# Security Documentation - CMMC Compliance Platform

## Overview

This document describes the security architecture, controls, and best practices implemented in the CMMC Compliance Platform to meet industry standards including:

- **OWASP API Security Top 10**
- **NIST 800-53** security controls
- **NIST 800-171** CUI protection requirements
- **CMMC Level 2** compliance standards
- **CIS Docker Benchmarks**
- **PCI DSS** (where applicable)

## Table of Contents

1. [Security Architecture](#security-architecture)
2. [Authentication & Authorization](#authentication--authorization)
3. [Data Protection](#data-protection)
4. [Network Security](#network-security)
5. [Application Security](#application-security)
6. [Infrastructure Security](#infrastructure-security)
7. [Monitoring & Logging](#monitoring--logging)
8. [Incident Response](#incident-response)
9. [Security Configuration](#security-configuration)
10. [Compliance Mapping](#compliance-mapping)

---

## Security Architecture

### Defense in Depth

The platform implements multiple layers of security:

```
┌─────────────────────────────────────────────────────────────┐
│ Layer 1: Network (Nginx, TLS 1.3, Firewall)                │
├─────────────────────────────────────────────────────────────┤
│ Layer 2: Application (Rate Limiting, CORS, CSP)            │
├─────────────────────────────────────────────────────────────┤
│ Layer 3: Authentication (JWT, Session Management)          │
├─────────────────────────────────────────────────────────────┤
│ Layer 4: Authorization (RBAC, RLS)                         │
├─────────────────────────────────────────────────────────────┤
│ Layer 5: Data (Encryption at Rest & Transit)               │
├─────────────────────────────────────────────────────────────┤
│ Layer 6: Audit (Comprehensive Logging)                     │
└─────────────────────────────────────────────────────────────┘
```

### Security Principles

1. **Least Privilege**: All services run with minimum required permissions
2. **Fail Secure**: Errors default to denying access
3. **Complete Mediation**: Every access is checked
4. **Defense in Depth**: Multiple security layers
5. **Separation of Duties**: Role-based access control
6. **Secure by Default**: Secure configurations out-of-the-box

---

## Authentication & Authorization

### JWT Authentication (AC-3, IA-2, IA-5)

**Implementation**: `cmmc-platform/api/auth.py`

#### Security Features:

1. **Token-Based Authentication**
   - Algorithm: HS256 (HMAC with SHA-256)
   - Access token expiration: 60 minutes (configurable)
   - Refresh token expiration: 30 days (configurable)
   - Secret key: Loaded from environment (required)

2. **Password Security**
   - Hashing: bcrypt with configurable rounds (default: 12)
   - Minimum complexity requirements enforced
   - Password history tracking
   - Account lockout after failed attempts

3. **Session Management**
   - Session tracking in database
   - Revocation capability (logout)
   - Session expiration
   - Concurrent session limits

#### Configuration:

```bash
# Required
JWT_SECRET=<generate with: openssl rand -hex 32>

# Optional
JWT_EXPIRATION_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
BCRYPT_ROUNDS=12
```

#### Password Requirements:

- Minimum 12 characters
- Must contain uppercase letter
- Must contain lowercase letter
- Must contain digit
- Must contain special character

**Validation Function**: `database/migrations/001_security_enhancements.sql:validate_password_strength()`

### Role-Based Access Control (AC-2, AC-3)

#### User Roles:

| Role | Permissions | Use Case |
|------|------------|----------|
| `admin` | Full system access | System administrators |
| `assessor` | Create/modify assessments and findings | CMMC assessors |
| `viewer` | Read-only access | Auditors, stakeholders |
| `integration` | API access for automated systems | CI/CD pipelines |

#### Row-Level Security (RLS):

PostgreSQL RLS policies ensure multi-tenant isolation:

```sql
-- Users can only access data from their organization
CREATE POLICY user_organization_isolation ON users
    FOR ALL
    USING (organization_id::TEXT = current_setting('app.current_organization_id', TRUE));
```

### Brute Force Protection (SI-10)

**Implementation**: `database/migrations/001_security_enhancements.sql:failed_login_attempts`

- Failed login attempt tracking
- Account lockout after 5 failed attempts in 15 minutes
- Automatic unlock after lockout period
- Security event logging

---

## Data Protection

### Encryption at Rest (SC-28)

#### Database Encryption:

- **PostgreSQL**: Full disk encryption (deployment-dependent)
- **Sensitive fields**: Application-level encryption for:
  - Integration credentials (JSONB encrypted)
  - API keys (bcrypt hashed)
  - Evidence files (SHA-256 hash verification)

#### Object Storage Encryption:

**MinIO Server-Side Encryption (SSE-S3)**:

```bash
MINIO_KMS_SECRET_KEY=<generate with: openssl rand -base64 32>
MINIO_SERVER_SIDE_ENCRYPTION_S3=on
```

All evidence files stored in MinIO are encrypted at rest using AES-256.

### Encryption in Transit (SC-8, SC-13)

#### TLS Configuration:

**Nginx**: `nginx/nginx.conf`

```nginx
# TLS 1.2 and 1.3 only
ssl_protocols TLSv1.2 TLSv1.3;

# Strong cipher suites
ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256...';

# HSTS with 2-year max-age
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
```

#### Database Connections:

PostgreSQL connections use `sslmode=prefer`:

```
DATABASE_URL=postgresql://user:pass@postgres:5432/db?sslmode=prefer
```

#### Redis Authentication:

```bash
REDIS_PASSWORD=<generate with: openssl rand -base64 32>
```

### Data Classification (MP-4)

Evidence files support data classification:

| Level | Description | Retention |
|-------|-------------|-----------|
| `public` | Public information | N/A |
| `internal` | Internal use only | Standard |
| `confidential` | Confidential information | 3 years (CMMC) |
| `restricted` | Highly sensitive (CUI) | 3 years (CMMC) |

**Database field**: `evidence.data_classification`

### Data Integrity (SI-7)

1. **File Integrity**:
   - SHA-256 hashing of all uploaded files
   - Hash verification on retrieval
   - Immutable storage (no overwrites)

2. **Chain of Custody**:
   - Every evidence access logged
   - IP address and user agent tracking
   - Timestamp recording

3. **Audit Trail**:
   - All database changes logged via triggers
   - Before/after values recorded
   - User attribution for all changes

---

## Network Security

### Firewall Configuration (SC-7)

**Docker Network Isolation**:

- All services on isolated `cmmc-network` bridge
- Services bound to `127.0.0.1` (not externally accessible)
- Only Nginx exposed on ports 80/443
- Internal service communication only

**Port Bindings** (Production):

```yaml
# External
nginx: 80, 443 (public)

# Internal only (127.0.0.1)
api: 8000
postgres: 5432
redis: 6379
minio: 9000, 9001
```

### Rate Limiting (SI-10)

**Implementation**: `cmmc-platform/api/security_middleware.py:RateLimitMiddleware`

#### Per-Endpoint Limits:

| Endpoint | Rate Limit | Purpose |
|----------|-----------|---------|
| `/api/v1/auth/login` | 5/min | Prevent brute force |
| `/api/v1/auth/register` | 3/min | Prevent spam accounts |
| `/api/v1/auth/refresh` | 10/min | Moderate refresh rate |
| `/api/v1/evidence/upload` | 30/min | Prevent upload abuse |
| `/api/v1/ingest/document` | 20/min | Prevent ingest abuse |
| Default | 100/min | General protection |

#### Features:

- Sliding window algorithm
- Per-IP tracking
- Automatic IP blocking for repeat offenders
- HTTP 429 responses with `Retry-After` header

### CORS Configuration (SC-7)

**Implementation**: `cmmc-platform/api/security_middleware.py:get_cors_config()`

```bash
# Allowed origins (comma-separated)
CORS_ALLOWED_ORIGINS=https://app.example.com,https://dashboard.example.com
```

**Security**:

- Specific origin whitelisting (no wildcards)
- Credentials allowed only for whitelisted origins
- Limited HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Restricted headers
- Max age: 10 minutes

---

## Application Security

### OWASP API Security Top 10

| Risk | Control | Implementation |
|------|---------|----------------|
| API1: Broken Object Level Authorization | RBAC + RLS | `auth.py`, PostgreSQL RLS |
| API2: Broken Authentication | JWT + Session Management | `auth.py` |
| API3: Broken Object Property Level Authorization | Pydantic validation | All API routes |
| API4: Unrestricted Resource Consumption | Rate limiting | `security_middleware.py` |
| API5: Broken Function Level Authorization | Role-based dependencies | `@Depends(get_current_admin_user)` |
| API6: Unrestricted Access to Sensitive Business Flows | Rate limiting + RBAC | Combined controls |
| API7: Server Side Request Forgery (SSRF) | Input validation | `InputSanitizer` |
| API8: Security Misconfiguration | Security headers + CSP | `SecurityHeadersMiddleware` |
| API9: Improper Inventory Management | API documentation | OpenAPI/Swagger |
| API10: Unsafe Consumption of APIs | Input validation | All external API calls |

### Input Validation & Sanitization (SI-10)

**Implementation**: `cmmc-platform/api/security_middleware.py:InputValidationMiddleware`

#### Protections:

1. **XSS Prevention**:
   - HTML escaping of all user inputs
   - Pattern detection for `<script>`, `javascript:`, event handlers
   - Content Security Policy (CSP) headers

2. **SQL Injection Prevention**:
   - Parameterized queries (asyncpg, asyncio)
   - Pattern detection for SQL keywords
   - No raw SQL execution from user input

3. **Path Traversal Prevention**:
   - Filename sanitization
   - Pattern detection for `../`, `..\\`, URL encoding
   - Basename extraction only

4. **File Upload Validation**:
   - MIME type whitelisting
   - Magic byte verification
   - File size limits (100MB)
   - Filename sanitization

**Allowed MIME Types**:

```python
ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",  # DOCX
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # XLSX
    "text/plain",
    "text/csv",
    "application/json",
    "image/png",
    "image/jpeg",
}
```

### Security Headers (SC-8)

**Implementation**: `cmmc-platform/api/security_middleware.py:SecurityHeadersMiddleware`

#### Headers Set:

```http
Content-Security-Policy: default-src 'self'; script-src 'self'; ...
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
```

---

## Infrastructure Security

### Container Security (CIS Docker Benchmarks)

#### Docker Hardening:

1. **Non-Root User**:
   ```dockerfile
   USER postgres  # PostgreSQL
   USER redis     # Redis
   USER appuser   # API/Celery
   ```

2. **Read-Only Root Filesystem**:
   ```yaml
   read_only: true
   tmpfs:
     - /tmp
   ```

3. **Resource Limits**:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '4'
         memory: 4G
   ```

4. **Network Isolation**:
   ```yaml
   networks:
     - cmmc-network  # Isolated bridge network
   ```

5. **Health Checks**:
   ```yaml
   healthcheck:
     test: ["CMD-SHELL", "pg_isready"]
     interval: 10s
     timeout: 5s
     retries: 5
   ```

### Secrets Management (IA-5)

**Environment Variables** (`.env` file):

```bash
# CRITICAL: Never commit .env to version control

# Database
POSTGRES_USER=cmmc_admin
POSTGRES_PASSWORD=<generate with: openssl rand -base64 32>
POSTGRES_DB=cmmc_platform

# JWT
JWT_SECRET=<generate with: openssl rand -hex 32>

# Redis
REDIS_PASSWORD=<generate with: openssl rand -base64 32>

# MinIO
MINIO_ROOT_USER=<username>
MINIO_ROOT_PASSWORD=<generate with: openssl rand -base64 32>
MINIO_KMS_SECRET_KEY=<generate with: openssl rand -base64 32>

# AI Provider
AI_API_KEY=<your-api-key>
```

**Production Recommendations**:

1. Use **HashiCorp Vault**, **AWS Secrets Manager**, or **Azure Key Vault**
2. Rotate secrets regularly (90 days)
3. Use separate secrets per environment
4. Enable secret auditing

---

## Monitoring & Logging

### Audit Logging (AU-2, AU-3, AU-12)

**Implementation**: `cmmc-platform/api/security_middleware.py:AuditLoggingMiddleware`

#### Logged Information:

```json
{
  "timestamp": "2025-11-16T12:34:56Z",
  "method": "POST",
  "path": "/api/v1/evidence/upload",
  "client_ip": "192.168.1.100",
  "forwarded_for": "203.0.113.45",
  "user_agent": "Mozilla/5.0...",
  "status_code": 201,
  "response_time": "0.234s"
}
```

#### Database Audit Triggers:

All table changes automatically logged via PostgreSQL triggers:

```sql
CREATE TRIGGER audit_trigger
AFTER INSERT OR UPDATE OR DELETE ON <table>
FOR EACH ROW EXECUTE FUNCTION audit_trigger_func();
```

**Audit log includes**:

- Before/after values
- User ID
- Timestamp
- Operation type
- IP address (if available)

### Security Event Monitoring (SI-4)

**Table**: `security_events`

**Event Types**:

- `unauthorized_access` - Failed authorization attempts
- `suspicious_activity` - Unusual patterns detected
- `rate_limit_exceeded` - Rate limit violations
- `brute_force_attempt` - Multiple failed logins
- `session_hijacking_attempt` - Suspicious session activity
- `data_exfiltration_attempt` - Large data downloads

**Severity Levels**: `low`, `medium`, `high`, `critical`

### Log Sanitization (AU-9)

**Implementation**: `cmmc-platform/api/security_middleware.py:AuditLoggingMiddleware.redact_sensitive_data()`

Automatically redacts sensitive fields:

- `password`
- `token`
- `secret`
- `api_key`
- `authorization`

Output: `***REDACTED***`

---

## Incident Response

### Security Event Response (IR-4, IR-5)

1. **Detection**:
   - Monitor `security_events` table
   - Alert on critical severity events
   - Rate limit violations
   - Brute force attempts

2. **Response**:
   - Review audit logs
   - Check `failed_login_attempts`
   - Identify affected users/IPs
   - Revoke sessions if needed

3. **Recovery**:
   ```sql
   -- Revoke all user sessions
   SELECT logout_all_sessions('user_id');

   -- Block IP address (application-level)
   -- Add to rate limiter blocked IPs

   -- Reset user password
   UPDATE users
   SET require_password_change = TRUE
   WHERE id = 'user_id';
   ```

4. **Lessons Learned**:
   - Document incident in `security_events`
   - Update detection rules
   - Patch vulnerabilities

### Backup & Recovery (CP-9)

**Backup Strategy**:

1. **Database**: Daily automated backups
2. **Evidence Files**: Replicated to secondary storage
3. **Configuration**: Version controlled (Git)
4. **Encryption Keys**: Secure offline storage

**Recovery Point Objective (RPO)**: 24 hours
**Recovery Time Objective (RTO)**: 4 hours

---

## Security Configuration

### Quick Start Security Setup

#### 1. Generate Secrets:

```bash
# JWT Secret (64 characters hex)
openssl rand -hex 32

# Database password
openssl rand -base64 32

# Redis password
openssl rand -base64 32

# MinIO credentials
openssl rand -base64 32  # root password
openssl rand -base64 32  # KMS key
```

#### 2. Configure .env:

Copy `.env.example` to `.env` and fill in all required values.

#### 3. Apply Database Migrations:

```bash
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -f /docker-entrypoint-initdb.d/migrations/001_security_enhancements.sql
```

#### 4. Run Security Scan:

```bash
cd cmmc-platform
python security_scan.py
```

#### 5. Review Security Report:

```bash
cat cmmc-platform/security_report.json
```

### Production Deployment Checklist

- [ ] All secrets generated and configured
- [ ] SSL/TLS certificates installed (Let's Encrypt)
- [ ] Firewall configured (UFW/iptables)
- [ ] Services bound to localhost only
- [ ] CORS origins set to production domains
- [ ] Rate limiting configured appropriately
- [ ] Database backups automated
- [ ] Log aggregation configured (ELK, Splunk)
- [ ] Monitoring alerts configured
- [ ] Incident response plan documented
- [ ] Security scan passes without critical issues
- [ ] Penetration testing completed

---

## Compliance Mapping

### NIST 800-171 Controls

| Control Family | Controls Implemented | Evidence |
|----------------|---------------------|----------|
| **AC** - Access Control | AC-2, AC-3, AC-7, AC-17 | RBAC, RLS, Session management |
| **AU** - Audit | AU-2, AU-3, AU-6, AU-9, AU-12 | Audit logging, log protection |
| **IA** - Identification & Authentication | IA-2, IA-5, IA-8 | JWT, password policy, MFA-ready |
| **SC** - System & Communications | SC-7, SC-8, SC-13, SC-28 | Network isolation, TLS, encryption |
| **SI** - System & Information Integrity | SI-4, SI-7, SI-10 | Monitoring, integrity checks, input validation |

### CMMC Level 2 Requirements

All 110 NIST 800-171 controls mapped and addressed:

- **Authentication**: Multi-factor ready (IA-2)
- **Encryption**: At rest and in transit (SC-8, SC-28)
- **Audit**: Comprehensive logging (AU-*)
- **Access Control**: RBAC and RLS (AC-*)
- **Incident Response**: Event logging and response procedures (IR-*)

### OWASP Compliance

Full implementation of OWASP API Security Top 10 (2023).

---

## Security Contact

For security issues, please contact:

- **Email**: security@example.com
- **PGP Key**: [Link to public key]
- **Bug Bounty**: [Link to program]

**Responsible Disclosure**:

We follow a 90-day disclosure policy. Please report vulnerabilities privately before public disclosure.

---

## Document Version

- **Version**: 1.0.0
- **Last Updated**: 2025-11-16
- **Next Review**: 2026-02-16 (Quarterly)

---

## References

1. NIST 800-171 Rev 2 - Protecting Controlled Unclassified Information
2. NIST 800-53 Rev 5 - Security and Privacy Controls
3. OWASP API Security Top 10 (2023)
4. CIS Docker Benchmarks v1.6.0
5. CMMC Model Version 2.0
6. OWASP Top 10 Web Application Security Risks
7. ISO 27001:2013 - Information Security Management
