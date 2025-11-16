# CISO App - Deployment Guide

Complete guide for deploying the CMMC Compliance Platform to your Hetzner VPS.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Manual Deployment](#manual-deployment)
- [Post-Deployment](#post-deployment)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Overview

The CISO App is a comprehensive CMMC compliance platform consisting of:

- **FastAPI Backend** - API services for compliance management
- **PostgreSQL 16 + pgvector** - Database with vector search capabilities
- **Redis** - Caching and task queue
- **MinIO** - S3-compatible object storage for evidence files
- **Celery** - Background task processing
- **Nginx** - Reverse proxy with SSL/TLS
- **Landing Page** - Static marketing site

## Prerequisites

### Server Requirements

- **Provider**: Hetzner VPS (recommended: CPX41)
- **OS**: Ubuntu 22.04 or 24.04 LTS
- **CPU**: 8 vCPU (minimum 4)
- **RAM**: 16 GB (minimum 8 GB)
- **Storage**: 160 GB SSD (minimum 80 GB)
- **Network**: 20 TB traffic

**Estimated Cost**: ~€40/month

### Domain Setup

1. Purchase a domain name
2. Point an A record to your VPS IP address
3. Wait for DNS propagation (usually 5-30 minutes)

Example DNS configuration:
```
Type: A
Name: cmmc (or your subdomain)
Value: YOUR_VPS_IP_ADDRESS
TTL: 3600
```

### Required Credentials

Before deployment, have these ready:

- ✅ Domain name (e.g., cmmc.yourdomain.com)
- ✅ Email address (for Let's Encrypt SSL)
- ✅ OpenAI API key OR Anthropic API key
- ✅ Database password (create a strong password)

## Quick Start

### Option 1: Automated Deployment (Recommended)

The automated script handles everything from system setup to SSL configuration.

```bash
# 1. SSH into your Hetzner VPS
ssh root@YOUR_VPS_IP

# 2. Download deployment script
curl -O https://raw.githubusercontent.com/Taycurry15/CISO/main/deploy.sh
# Or clone the repository
git clone https://github.com/Taycurry15/CISO.git
cd CISO

# 3. Make script executable
chmod +x deploy.sh

# 4. Run deployment
sudo ./deploy.sh
```

The script will prompt you for:
- Domain name
- Email for SSL certificates
- Database password
- AI API key (OpenAI or Anthropic)

**Deployment time**: ~10-15 minutes

### Option 2: Docker Compose Deployment

If you already have Docker installed:

```bash
# 1. Clone repository
git clone https://github.com/Taycurry15/CISO.git
cd CISO

# 2. Configure environment
cp .env.example .env
nano .env  # Edit with your values

cp cmmc-platform/.env.example cmmc-platform/.env
nano cmmc-platform/.env  # Edit with your values

# 3. Update domain in nginx config
sed -i "s/\${DOMAIN}/your-domain.com/g" nginx/conf.d/cmmc-platform.conf

# 4. Start services
docker compose up -d

# 5. Check status
docker compose ps
```

## Manual Deployment

For detailed step-by-step manual deployment, see:
- [`cmmc-platform/DEPLOYMENT_GUIDE.md`](./cmmc-platform/DEPLOYMENT_GUIDE.md) - Full deployment guide
- [`cmmc-platform/QUICK_DEPLOY.md`](./cmmc-platform/QUICK_DEPLOY.md) - Quick reference

## Post-Deployment

### 1. Verify Installation

```bash
# Check service health
curl https://your-domain.com/health

# Check API documentation
curl https://your-domain.com/api/docs

# View all services
docker compose ps

# Expected output:
# cmmc-postgres     running
# cmmc-redis        running
# cmmc-minio        running
# cmmc-api          running
# cmmc-celery-worker running
# cmmc-nginx        running
```

### 2. Create First Organization and User

```bash
# Connect to database
docker exec -it cmmc-postgres psql -U cmmc_admin -d cmmc_platform

# Create organization
INSERT INTO organizations (name, cmmc_level, industry)
VALUES ('Your Company Name', 2, 'Defense');

# Create admin user
INSERT INTO users (organization_id, email, name, role)
VALUES (
  (SELECT id FROM organizations WHERE name = 'Your Company Name'),
  'admin@yourcompany.com',
  'Admin User',
  'admin'
);

# Exit
\q
```

### 3. Upload Reference Documents (Optional but Recommended)

For AI-powered RAG (Retrieval Augmented Generation):

```bash
# Download NIST and CMMC documents
mkdir -p docs/reference/nist
mkdir -p docs/reference/cmmc

# Place PDFs in the directories:
# - NIST SP 800-171 Rev 2
# - CMMC 2.0 Model
# - CMMC Assessment Guide

# Run ingestion script
docker exec cmmc-api python scripts/ingest_reference_docs.py

# Test RAG search
docker exec -it cmmc-api python scripts/test_rag_search.py --interactive
```

### 4. Configure Integrations

Edit `cmmc-platform/.env` to add integration credentials:

```bash
# Nessus (vulnerability scanning)
NESSUS_MODE=api
NESSUS_BASE_URL=https://cloud.tenable.com
NESSUS_ACCESS_KEY=your_access_key
NESSUS_SECRET_KEY=your_secret_key

# Splunk (SIEM integration)
SPLUNK_HOST=your-splunk-host.com
SPLUNK_PORT=8089
SPLUNK_TOKEN=your_splunk_token

# Azure
AZURE_TENANT_ID=your_tenant_id
AZURE_CLIENT_ID=your_client_id
AZURE_CLIENT_SECRET=your_client_secret

# AWS GovCloud
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-gov-west-1
```

Restart services after configuration:
```bash
docker compose restart
```

## Maintenance

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f celery-worker
docker compose logs -f postgres

# Last 100 lines
docker compose logs --tail=100 api
```

### Restart Services

```bash
# All services
docker compose restart

# Specific service
docker compose restart api
docker compose restart postgres
```

### Update Application

```bash
cd /home/deploy/apps/CISO  # or your installation directory

# Use update script (recommended)
./update.sh

# Or manually
git pull
docker compose build
docker compose up -d
```

### Backup Database

Automated backups run daily at 2 AM UTC. Manual backup:

```bash
# Manual backup
docker exec cmmc-postgres pg_dump -U cmmc_admin cmmc_platform | \
  gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
gunzip -c backup_20240101.sql.gz | \
  docker exec -i cmmc-postgres psql -U cmmc_admin -d cmmc_platform
```

### SSL Certificate Renewal

Certificates auto-renew via certbot. To manually renew:

```bash
docker compose run --rm certbot renew
docker compose restart nginx
```

### Monitor Resources

```bash
# Docker resource usage
docker stats

# Disk usage
df -h

# Service status
docker compose ps

# Database size
docker exec cmmc-postgres psql -U cmmc_admin -d cmmc_platform -c \
  "SELECT pg_size_pretty(pg_database_size('cmmc_platform'));"
```

## Troubleshooting

### Service Won't Start

```bash
# Check service logs
docker compose logs api

# Check if port is in use
sudo netstat -tulpn | grep :8000

# Restart all services
docker compose down
docker compose up -d
```

### Database Connection Issues

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Verify connection
docker exec cmmc-postgres pg_isready -U cmmc_admin

# Test connection
docker exec -it cmmc-postgres psql -U cmmc_admin -d cmmc_platform -c "SELECT version();"
```

### SSL Certificate Issues

```bash
# Check certificate status
docker compose run --rm certbot certificates

# Force renewal
docker compose run --rm certbot renew --force-renewal

# Check nginx configuration
docker compose exec nginx nginx -t

# Restart nginx
docker compose restart nginx
```

### High Memory Usage

```bash
# Check memory usage
free -h

# Restart services
docker compose restart postgres redis

# Reduce AI workers if needed (edit .env)
API_WORKERS=2  # Default is 4
```

### API Timeouts

```bash
# Increase timeouts in cmmc-platform/.env
AI_TIMEOUT=120  # Default is 60
RAG_TOP_K=5     # Default is 10 (reduce for faster responses)

# Restart API
docker compose restart api
```

### MinIO Access Issues

```bash
# Check MinIO status
docker compose logs minio

# Access MinIO console
# Browser: http://YOUR_SERVER_IP:9001
# Username: minioadmin
# Password: (check .env for MINIO_ROOT_PASSWORD)

# Recreate bucket if needed
docker exec cmmc-minio mc mb local/cmmc-evidence
```

## Useful Commands

### Service Management

```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# Restart a service
docker compose restart api

# View running containers
docker compose ps

# Remove all containers and volumes (CAUTION: deletes data)
docker compose down -v
```

### Database Management

```bash
# Connect to database
docker exec -it cmmc-postgres psql -U cmmc_admin -d cmmc_platform

# Backup database
docker exec cmmc-postgres pg_dump -U cmmc_admin cmmc_platform > backup.sql

# Restore database
cat backup.sql | docker exec -i cmmc-postgres psql -U cmmc_admin -d cmmc_platform

# List all tables
docker exec cmmc-postgres psql -U cmmc_admin -d cmmc_platform -c "\dt"
```

### Performance Optimization

```bash
# View resource usage
docker stats

# Clean up Docker
docker system prune -a

# View disk usage
docker system df

# Remove unused images
docker image prune -a
```

## Security Best Practices

1. **Change Default Passwords**: Update all passwords in `.env` files
2. **Enable Firewall**: Use UFW to limit access to ports 22, 80, 443
3. **Regular Updates**: Keep system and Docker images updated
4. **Backup Regularly**: Verify backups are working
5. **Monitor Logs**: Check logs regularly for suspicious activity
6. **Use Strong JWT Secret**: Generate with `openssl rand -hex 32`
7. **Limit SSH Access**: Use SSH keys, disable password auth
8. **Enable Fail2Ban**: Protect against brute force attacks

## Support

- **Documentation**: See `cmmc-platform/` for detailed docs
- **Issues**: https://github.com/Taycurry15/CISO/issues
- **Deployment Issues**: Check logs with `docker compose logs`

## License

See LICENSE file in repository.

---

**Need Help?** Check the detailed guides in `cmmc-platform/`:
- `DEPLOYMENT_GUIDE.md` - Complete deployment instructions
- `GETTING_STARTED.md` - Getting started guide
- `AI_RAG_INTEGRATION.md` - AI and RAG setup
- `PROJECT_STRUCTURE.md` - Understanding the codebase
