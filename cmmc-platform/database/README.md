## Database Schema & Migrations

Complete PostgreSQL database schema and migration system for the CMMC Compliance Platform.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Database Tables](#database-tables)
- [Migrations](#migrations)
- [Seed Data](#seed-data)
- [Connection Management](#connection-management)
- [Performance Optimization](#performance-optimization)
- [Backup & Recovery](#backup--recovery)

## Overview

The CMMC Platform uses PostgreSQL 14+ with the following features:

- **16 tables** for multi-tenant SaaS architecture
- **pgvector extension** for AI embeddings (RAG system)
- **UUID primary keys** for distributed systems
- **Automatic triggers** for `updated_at` timestamps
- **Alembic migrations** for schema versioning
- **asyncpg** for high-performance async I/O

### Key Statistics

- **Tables**: 16
- **Indexes**: 65+
- **Views**: 2
- **Triggers**: 8
- **Extensions**: 2 (uuid-ossp, vector)

## Architecture

### Schema Organization

```
┌─────────────────────────────────────────────────────────┐
│                   CMMC Platform Database                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Multi-Tenant Layer                                     │
│  ├── organizations (tenant isolation)                   │
│  └── users (RBAC)                                       │
│                                                          │
│  Master Data                                            │
│  ├── cmmc_controls (110 CMMC L2 controls)              │
│  └── provider_inheritance (M365, Azure, AWS)            │
│                                                          │
│  Assessment Data                                         │
│  ├── assessments (lifecycle management)                 │
│  ├── control_findings (results)                         │
│  ├── evidence (files + embeddings)                      │
│  └── poam_items (remediation tracking)                  │
│                                                          │
│  AI & RAG                                               │
│  ├── documents (policy/procedure library)               │
│  ├── document_chunks (vector search)                    │
│  └── ai_analysis_results (audit trail)                  │
│                                                          │
│  Collaboration                                           │
│  ├── comments (threaded discussions)                    │
│  └── notifications (in-app + email)                     │
│                                                          │
│  Audit & Security                                        │
│  ├── audit_logs (compliance trail)                      │
│  └── system_config (platform settings)                  │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### Entity Relationships

```
organizations (1) ──< (N) users
              (1) ──< (N) assessments
              (1) ──< (N) evidence
              (1) ──< (N) documents

assessments (1) ──< (N) control_findings
            (1) ──< (N) evidence
            (1) ──< (N) poam_items

cmmc_controls (1) ──< (N) control_findings
              (1) ──< (N) provider_inheritance
              (1) ──< (N) poam_items

users (1) ──< (N) assessments (as lead_assessor)
      (1) ──< (N) control_findings (as assigned_to)
      (1) ──< (N) comments (as created_by)
```

## Quick Start

### Prerequisites

- PostgreSQL 14+
- Python 3.11+
- `alembic` package
- `asyncpg` package

### Installation

```bash
# 1. Install PostgreSQL extensions
sudo -u postgres psql <<EOF
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;
EOF

# 2. Navigate to database directory
cd database

# 3. Run initialization script
./init_db.sh

# 4. Verify installation
psql -U cmmc_user -d cmmc_db -c "SELECT COUNT(*) FROM cmmc_controls;"
```

### Environment Variables

Create `.env` file:

```bash
# Database connection
DATABASE_URL=postgresql://cmmc_user:cmmc_password@localhost:5432/cmmc_db

# Or individual components
DB_USER=cmmc_user
DB_PASSWORD=cmmc_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=cmmc_db

# For initialization
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_postgres_password
```

## Database Tables

### 1. Organizations

Multi-tenant organization management.

```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    organization_type VARCHAR(50) NOT NULL, -- Enterprise, SMB, Consultant, C3PAO
    status VARCHAR(50) NOT NULL DEFAULT 'Trial', -- Active, Trial, Suspended, Inactive
    address TEXT,
    phone VARCHAR(20),
    email VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255)
);
```

**Indexes:**
- `idx_organizations_status` on `status`
- `idx_organizations_type` on `organization_type`

### 2. Users

User authentication and RBAC.

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL, -- Admin, Assessor, Auditor, Viewer
    status VARCHAR(50) NOT NULL DEFAULT 'Pending',
    phone VARCHAR(20),
    job_title VARCHAR(100),
    email_verified BOOLEAN DEFAULT FALSE,
    last_login TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_users_organization_id` on `organization_id`
- `idx_users_email` on `email` (unique)
- `idx_users_status` on `status`
- `idx_users_role` on `role`

### 3. CMMC Controls

Master data for 110 CMMC Level 2 controls.

```sql
CREATE TABLE cmmc_controls (
    id VARCHAR(50) PRIMARY KEY, -- e.g., "AC.L2-3.1.1"
    level INTEGER NOT NULL,
    domain VARCHAR(50) NOT NULL, -- AC, AT, AU, CA, CM, IA, IR, MA, MP, PE, PS, RA, SA, SC, SI
    practice_id VARCHAR(50) NOT NULL,
    title TEXT NOT NULL,
    objective TEXT NOT NULL,
    discussion TEXT,
    nist_control_id VARCHAR(50),
    assessment_objectives TEXT[],
    examine_items TEXT[],
    interview_items TEXT[],
    test_items TEXT[]
);
```

**Indexes:**
- `idx_controls_level` on `level`
- `idx_controls_domain` on `domain`
- `idx_controls_nist` on `nist_control_id`

### 4. Assessments

Assessment lifecycle management.

```sql
CREATE TABLE assessments (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    assessment_type VARCHAR(50) NOT NULL, -- CMMC_L1, CMMC_L2, CMMC_L3
    target_level INTEGER NOT NULL DEFAULT 2,
    status VARCHAR(50) NOT NULL DEFAULT 'Draft',
    scope_domains TEXT[],
    scope_cloud_providers TEXT[],
    start_date TIMESTAMP WITH TIME ZONE,
    end_date TIMESTAMP WITH TIME ZONE,
    lead_assessor_id UUID REFERENCES users(id),
    total_controls INTEGER DEFAULT 0,
    controls_met INTEGER DEFAULT 0,
    completion_percentage INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_assessments_organization_id` on `organization_id`
- `idx_assessments_status` on `status`
- `idx_assessments_created_at` on `created_at DESC`

### 5. Control Findings

Assessment results for each control.

```sql
CREATE TABLE control_findings (
    id UUID PRIMARY KEY,
    assessment_id UUID NOT NULL REFERENCES assessments(id),
    control_id VARCHAR(50) NOT NULL REFERENCES cmmc_controls(id),
    status VARCHAR(50) NOT NULL DEFAULT 'Not Started',
    implementation_narrative TEXT,
    evidence_ids UUID[],
    ai_generated_narrative TEXT,
    ai_confidence_score DECIMAL(3,2),
    uses_provider_inheritance BOOLEAN DEFAULT FALSE,
    risk_level VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_control_findings_assessment` on `assessment_id`
- `idx_control_findings_control` on `control_id`
- `idx_control_findings_unique` on `(assessment_id, control_id)` UNIQUE

### 6. Evidence

File storage with vector embeddings.

```sql
CREATE TABLE evidence (
    id UUID PRIMARY KEY,
    assessment_id UUID NOT NULL REFERENCES assessments(id),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    evidence_type VARCHAR(50) NOT NULL,
    control_ids VARCHAR(50)[],
    extracted_text TEXT,
    embedding vector(3072), -- pgvector for semantic search
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Indexes:**
- `idx_evidence_assessment` on `assessment_id`
- `idx_evidence_organization` on `organization_id`
- `idx_evidence_embedding` using ivfflat (vector index)

### Full Table List

| Table                | Purpose                        | Key Features                          |
|----------------------|--------------------------------|---------------------------------------|
| organizations        | Multi-tenant isolation         | Primary tenant boundary               |
| users                | Authentication & RBAC          | bcrypt passwords, JWT tokens          |
| cmmc_controls        | Master control library         | 110 CMMC L2 controls                  |
| provider_inheritance | Cloud control mappings         | M365, Azure, AWS inheritance          |
| assessments          | Assessment lifecycle           | 6-status workflow                     |
| control_findings     | Assessment results             | AI narratives, confidence scores      |
| evidence             | File storage + RAG             | Vector embeddings for semantic search |
| documents            | Policy/procedure library       | Document-level embeddings             |
| document_chunks      | RAG chunking                   | Chunk-level embeddings                |
| ai_analysis_results  | AI audit trail                 | Tracks all AI operations              |
| poam_items           | Remediation tracking           | POA&M with milestones                 |
| comments             | Threaded discussions           | @mentions, threading                  |
| notifications        | In-app + email alerts          | Multi-channel delivery                |
| audit_logs           | Compliance audit trail         | JSONB change tracking                 |
| system_config        | Platform configuration         | JSONB key-value store                 |

## Migrations

### Using Alembic

Alembic manages database schema versioning.

#### Initialize (already done)

```bash
cd database
alembic init alembic
```

#### Create New Migration

```bash
# Auto-generate from schema changes
alembic revision --autogenerate -m "Add new table"

# Manual migration
alembic revision -m "Custom migration"
```

#### Apply Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific version
alembic upgrade <revision_id>

# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision_id>
```

#### Check Status

```bash
# Show current version
alembic current

# Show migration history
alembic history

# Show pending migrations
alembic show head
```

### Migration Best Practices

1. **Always backup before migrations**
   ```bash
   pg_dump -U cmmc_user cmmc_db > backup_$(date +%Y%m%d).sql
   ```

2. **Test migrations in development first**
   ```bash
   # Create test database
   createdb cmmc_db_test
   DATABASE_URL=postgresql://...cmmc_db_test alembic upgrade head
   ```

3. **Write reversible migrations**
   - Always implement `downgrade()`
   - Test both upgrade and downgrade paths

4. **Use transactions**
   - Migrations run in transactions by default
   - Can be disabled with `transaction_per_migration = False`

## Seed Data

### Loading Seed Data

```bash
# Load CMMC controls
psql -U cmmc_user -d cmmc_db -f seeds/01_cmmc_controls.sql

# Load all seed files
for file in seeds/*.sql; do
    psql -U cmmc_user -d cmmc_db -f "$file"
done
```

### Available Seed Files

- `01_cmmc_controls.sql` - 110 CMMC Level 2 controls
- `02_provider_inheritance.sql` - Cloud provider mappings (create as needed)
- `03_sample_data.sql` - Demo organizations and users (create as needed)

### Creating Custom Seed Data

```sql
-- seeds/03_sample_org.sql
INSERT INTO organizations (id, name, organization_type, status, created_by)
VALUES (
    uuid_generate_v4(),
    'Demo Organization',
    'SMB',
    'Active',
    'system'
);

INSERT INTO users (id, organization_id, email, password_hash, full_name, role, status)
SELECT
    uuid_generate_v4(),
    o.id,
    'admin@demo.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oDT.bPqkV.8m', -- "password123"
    'Demo Admin',
    'Admin',
    'Active'
FROM organizations o
WHERE o.name = 'Demo Organization';
```

## Connection Management

### Python/FastAPI Usage

```python
from database import database, get_db_pool
from fastapi import FastAPI, Depends
import asyncpg

# Initialize database on startup
@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

# Use in endpoints
@app.get("/users")
async def get_users(pool: asyncpg.Pool = Depends(get_db_pool)):
    async with pool.acquire() as conn:
        users = await conn.fetch("SELECT * FROM users")
    return users

# Or use database helper methods
@app.get("/controls")
async def get_controls():
    controls = await database.fetch(
        "SELECT * FROM cmmc_controls WHERE level = $1",
        2
    )
    return controls
```

### Connection Pool Settings

Default settings (in `api/database.py`):

```python
pool = await asyncpg.create_pool(
    database_url,
    min_size=5,              # Minimum connections
    max_size=20,             # Maximum connections
    max_queries=50000,       # Queries before connection recycling
    max_inactive_connection_lifetime=300.0,  # 5 minutes
    timeout=30.0,            # Connection acquisition timeout
    command_timeout=60.0,    # Query execution timeout
)
```

### Health Checks

```python
# Check database health
health = await database.health_check()

# Returns:
{
    "status": "healthy",
    "pool_size": 10,
    "pool_free": 7,
    "pool_in_use": 3,
    "max_size": 20,
    "min_size": 5
}
```

## Performance Optimization

### Indexes

All tables have appropriate indexes for:
- Foreign keys
- Frequently queried columns
- Sort/filter columns
- Unique constraints

### Vector Indexes

pgvector uses IVFFlat indexes for fast similarity search:

```sql
CREATE INDEX idx_evidence_embedding
ON evidence
USING ivfflat(embedding vector_cosine_ops)
WITH (lists = 100);
```

**Tuning:**
- `lists = 100` for <1M vectors
- `lists = 1000` for 1M-10M vectors
- Rebuild index after bulk inserts

### Query Optimization

```sql
-- Use EXPLAIN ANALYZE to check query plans
EXPLAIN ANALYZE
SELECT * FROM control_findings
WHERE assessment_id = 'uuid-here';

-- Monitor slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
WHERE mean_exec_time > 1000
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Materialized Views

For expensive aggregations:

```sql
CREATE MATERIALIZED VIEW assessment_stats AS
SELECT
    a.id,
    a.name,
    COUNT(cf.id) as findings_count,
    AVG(cf.ai_confidence_score) as avg_confidence
FROM assessments a
LEFT JOIN control_findings cf ON a.id = cf.assessment_id
GROUP BY a.id, a.name;

-- Refresh periodically
REFRESH MATERIALIZED VIEW assessment_stats;
```

## Backup & Recovery

### Full Backup

```bash
# Backup entire database
pg_dump -U cmmc_user -Fc cmmc_db > backup_$(date +%Y%m%d_%H%M%S).dump

# Backup schema only
pg_dump -U cmmc_user --schema-only cmmc_db > schema_backup.sql

# Backup data only
pg_dump -U cmmc_user --data-only cmmc_db > data_backup.sql
```

### Restore

```bash
# Restore from custom format
pg_restore -U cmmc_user -d cmmc_db backup.dump

# Restore from SQL
psql -U cmmc_user -d cmmc_db < backup.sql
```

### Point-in-Time Recovery

Enable WAL archiving in `postgresql.conf`:

```conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/archive/%f'
```

### Automated Backups

```bash
# Add to crontab
0 2 * * * /usr/bin/pg_dump -U cmmc_user -Fc cmmc_db > /backups/cmmc_$(date +\%Y\%m\%d).dump

# Keep last 30 days
0 3 * * * find /backups -name "cmmc_*.dump" -mtime +30 -delete
```

## Troubleshooting

### Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check connections
psql -U cmmc_user -d cmmc_db -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
AND state_change < NOW() - INTERVAL '1 hour';
```

### Performance Issues

```bash
# Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

# Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

# Vacuum and analyze
VACUUM ANALYZE;
```

### Migration Issues

```bash
# Check current version
alembic current

# Stamp database at specific version (if out of sync)
alembic stamp head

# Downgrade and re-upgrade
alembic downgrade -1
alembic upgrade head
```

## Contributing

When making schema changes:

1. Create migration: `alembic revision -m "Description"`
2. Implement `upgrade()` and `downgrade()`
3. Test both directions
4. Update this README
5. Update seed data if needed

## License

Internal use only - CMMC Compliance Platform
