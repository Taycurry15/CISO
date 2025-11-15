# CMMC Platform - Quick Start Guide

Get the CMMC Compliance Platform running locally in **under 10 minutes**.

## Prerequisites

- **Docker** and **Docker Compose** installed
- **8GB RAM** minimum
- **20GB disk space**
- **OpenAI API key** (optional, for AI features)

## Step 1: Clone Repository

```bash
git clone <your-repo-url>
cd cmmc-platform
```

## Step 2: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your settings (minimum required changes):
nano .env
```

**Required changes in .env**:
```bash
# Strong passwords (change these!)
POSTGRES_PASSWORD=your_secure_password_here
MINIO_ROOT_PASSWORD=your_minio_password_here
JWT_SECRET=your_random_secret_key_here
CISO_ASSISTANT_SECRET_KEY=your_django_secret_here

# Optional: Add OpenAI API key for AI features
OPENAI_API_KEY=sk-your-openai-key-here
```

**Generate secure secrets**:
```bash
# Generate JWT secret
openssl rand -hex 32

# Generate Django secret
python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
```

## Step 3: Create Required Directories

```bash
# Create data and log directories
mkdir -p data/{postgres,redis,minio,evidence,ciso-assistant}
mkdir -p logs/{api,nginx,celery}
mkdir -p config/ssl
```

## Step 4: Start Services

```bash
# Start all services (without nginx for local dev)
docker-compose up -d postgres redis minio ciso-assistant api

# Check service status
docker-compose ps

# Watch logs
docker-compose logs -f
```

**Expected output**:
```
✓ postgres (healthy)
✓ redis (healthy)
✓ minio (healthy)
✓ ciso-assistant (running)
✓ api (running)
```

## Step 5: Initialize Database

```bash
# Wait for postgres to be ready (30 seconds)
sleep 30

# Import database schema (if not auto-imported)
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -f /docker-entrypoint-initdb.d/01-schema.sql

# Verify tables created
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -c "\dt"
```

## Step 6: Import CMMC Framework

```bash
# Run the framework import script
python3 scripts/import_cmmc_framework.py

# This will generate: cmmc_l2_import.sql

# Import into database
docker-compose exec -T postgres psql -U cmmc_admin -d cmmc_platform < cmmc_l2_import.sql

# Verify import (should show 110 controls)
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -c "SELECT COUNT(*) FROM controls;"
```

## Step 7: Create MinIO Bucket

```bash
# Create evidence bucket
docker-compose exec minio sh -c "
  mc alias set local http://localhost:9000 \$MINIO_ROOT_USER \$MINIO_ROOT_PASSWORD &&
  mc mb local/cmmc-evidence &&
  mc anonymous set download local/cmmc-evidence
"

# Verify bucket created
docker-compose exec minio mc ls local/
```

## Step 8: Create Admin User

```bash
# Create CISO Assistant superuser
docker-compose exec ciso-assistant python manage.py createsuperuser

# Follow prompts:
# Username: admin
# Email: admin@example.com
# Password: (your secure password)
```

## Step 9: Access the Platform

Open your browser and navigate to:

- **CISO Assistant UI**: http://localhost:8080
  - Login with the superuser credentials you just created

- **API Documentation**: http://localhost:8000/docs
  - Interactive Swagger UI for testing API endpoints

- **MinIO Console**: http://localhost:9001
  - Login: minio_admin / (your MINIO_ROOT_PASSWORD from .env)

## Step 10: Verify Installation

### Test 1: API Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy"}
```

### Test 2: Check CMMC Controls
```bash
# List first 5 controls
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -c "
  SELECT control_id, title
  FROM controls
  LIMIT 5;
"
```

### Test 3: Upload Test Evidence
```bash
# Create test file
echo "Test evidence document" > test-evidence.txt

# Upload via API (replace with actual assessment_id after creating one)
curl -X POST http://localhost:8000/api/v1/evidence/upload \
  -H "Content-Type: multipart/form-data" \
  -F "file=@test-evidence.txt" \
  -F "title=Test Evidence" \
  -F "evidence_type=document"
```

## Common Issues & Troubleshooting

### Issue: Services won't start

```bash
# Check logs
docker-compose logs postgres
docker-compose logs api

# Verify ports are available
lsof -i :5432  # PostgreSQL
lsof -i :8000  # API
lsof -i :8080  # CISO Assistant

# Clean restart
docker-compose down
docker-compose up -d
```

### Issue: Database connection errors

```bash
# Verify postgres is running
docker-compose ps postgres

# Check database exists
docker-compose exec postgres psql -U cmmc_admin -l

# Test connection
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -c "SELECT 1;"
```

### Issue: Out of disk space

```bash
# Check disk usage
df -h
du -sh data/*

# Clean up Docker
docker system prune -a --volumes
```

### Issue: API not accessible

```bash
# Check API logs
docker-compose logs api

# Verify dependencies
docker-compose exec api pip list

# Restart API
docker-compose restart api
```

## Next Steps

Now that your platform is running:

1. **Create Your First Assessment**:
   - Log into CISO Assistant at http://localhost:8080
   - Navigate to Assessments → Create New Assessment
   - Select CMMC Level 2 framework

2. **Upload Evidence**:
   - Go to your assessment
   - Upload policy documents, screenshots, scan results
   - Link evidence to specific controls

3. **Test AI Analysis** (if API key configured):
   - Use API docs at http://localhost:8000/docs
   - Try POST /api/v1/analyze/{control_id}
   - Review AI-generated findings

4. **Explore Integrations**:
   - Configure Nessus integration (see `integrations/nessus_connector.py`)
   - Test vulnerability import
   - Map findings to controls

5. **Generate Reports**:
   - Use API to generate SSP: POST /api/v1/ssp/{assessment_id}
   - Generate POA&M: POST /api/v1/poam/{assessment_id}
   - Review exported documents

## Development Workflow

### Running locally (without Docker)

```bash
# Install dependencies
cd api
pip install -r requirements.txt

# Start dependencies only
docker-compose up -d postgres redis minio

# Run API locally
export DATABASE_URL="postgresql://cmmc_admin:password@localhost:5432/cmmc_platform"
export REDIS_URL="redis://localhost:6379/0"
uvicorn main:app --reload --port 8000

# API available at http://localhost:8000
```

### Running tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
cd cmmc-platform
pytest tests/ -v

# With coverage
pytest tests/ --cov=api --cov-report=html
```

### Making changes

```bash
# Edit code
vim api/main.py

# Restart service
docker-compose restart api

# View logs
docker-compose logs -f api
```

## Production Deployment

For production deployment to Hetzner VPS, see:
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - Complete production deployment guide
- **[DEVELOPMENT_DEPLOYMENT_PLAN.md](./DEVELOPMENT_DEPLOYMENT_PLAN.md)** - Full project roadmap

## Getting Help

- **Documentation**: See README.md, GETTING_STARTED.md, PROJECT_STRUCTURE.md
- **API Reference**: http://localhost:8000/docs (when running)
- **CISO Assistant Docs**: https://intuitem.github.io/ciso-assistant-docs/
- **Issues**: Open issue in repository

## Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (WARNING: deletes all data)
docker-compose down -v
```

## Backup & Restore

### Backup
```bash
# Backup database
docker-compose exec -T postgres pg_dump -U cmmc_admin cmmc_platform > backup.sql

# Backup evidence files
tar -czf evidence-backup.tar.gz data/evidence/
```

### Restore
```bash
# Restore database
cat backup.sql | docker-compose exec -T postgres psql -U cmmc_admin cmmc_platform

# Restore evidence files
tar -xzf evidence-backup.tar.gz
```

---

**You're all set! 🚀**

Your CMMC Compliance Platform is now running locally. Start by creating your first assessment and exploring the features.

For the complete development roadmap, see [DEVELOPMENT_DEPLOYMENT_PLAN.md](./DEVELOPMENT_DEPLOYMENT_PLAN.md).
