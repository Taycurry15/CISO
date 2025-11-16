# Complete Hetzner VPS Deployment Guide

**Production deployment guide for CMMC Compliance Platform on Hetzner Cloud**

Estimated time: 2-3 hours
Estimated cost: €40-50/month

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Setup](#server-setup)
3. [Security Hardening](#security-hardening)
4. [Install Dependencies](#install-dependencies)
5. [PostgreSQL Setup](#postgresql-setup)
6. [Redis Setup](#redis-setup)
7. [Application Setup](#application-setup)
8. [SSL/TLS Configuration](#ssltls-configuration)
9. [Nginx Configuration](#nginx-configuration)
10. [Systemd Services](#systemd-services)
11. [Database Initialization](#database-initialization)
12. [Reference Documentation](#reference-documentation)
13. [Testing & Verification](#testing--verification)
14. [Monitoring & Maintenance](#monitoring--maintenance)
15. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### What You Need

- [ ] Hetzner Cloud account
- [ ] Domain name (e.g., `cmmc.yourdomain.com`)
- [ ] OpenAI or Anthropic API key
- [ ] SSH key pair
- [ ] Basic Linux command line knowledge

### Recommended Server Specs

**Hetzner CPX41** (or equivalent):
- **vCPU**: 8 cores
- **RAM**: 16 GB
- **Storage**: 240 GB NVMe SSD
- **Network**: 20 TB traffic
- **Cost**: ~€40/month

**Minimum specs** (for testing):
- CPX21: 3 vCPU, 4 GB RAM (~€10/month)

---

## Server Setup

### Step 1: Create Hetzner Server

1. **Login to Hetzner Cloud Console**
   - Visit: https://console.hetzner.cloud/

2. **Create New Project**
   - Name: `cmmc-platform`

3. **Create Server**
   - **Location**: Choose closest to your users (e.g., Ashburn for US)
   - **Image**: Ubuntu 24.04 LTS
   - **Type**: CPX41 (8 vCPU, 16 GB RAM)
   - **Networking**:
     - ✅ IPv4
     - ✅ IPv6 (optional)
   - **SSH Key**: Upload your public key
   - **Volume**: None (using local NVMe)
   - **Firewall**: Create new (configure below)
   - **Name**: `cmmc-production`

4. **Configure Firewall**
   ```
   Inbound Rules:
   - SSH (22) from Your IP only
   - HTTP (80) from Anywhere
   - HTTPS (443) from Anywhere

   Outbound Rules:
   - All traffic allowed
   ```

5. **Note Server IP**
   - Copy the server's public IPv4 address
   - Example: `116.203.123.45`

### Step 2: Configure DNS

Point your domain to the server:

```
Type: A
Name: cmmc (or @)
Value: 116.203.123.45
TTL: 3600
```

Wait 5-10 minutes for DNS propagation, then verify:

```bash
# On your local machine
dig cmmc.yourdomain.com +short
# Should return: 116.203.123.45
```

### Step 3: Initial Connection

```bash
# SSH into server (replace with your IP and domain)
ssh root@116.203.123.45

# Update system
apt update && apt upgrade -y

# Set timezone
timedatectl set-timezone America/New_York  # or your timezone

# Set hostname
hostnamectl set-hostname cmmc-production
```

---

## Security Hardening

### Step 1: Create Non-Root User

```bash
# Create deployment user
adduser deploy

# Add to sudo group
usermod -aG sudo deploy

# Copy SSH keys
mkdir -p /home/deploy/.ssh
cp /root/.ssh/authorized_keys /home/deploy/.ssh/
chown -R deploy:deploy /home/deploy/.ssh
chmod 700 /home/deploy/.ssh
chmod 600 /home/deploy/.ssh/authorized_keys

# Test login (from local machine)
# ssh deploy@cmmc.yourdomain.com
```

### Step 2: Disable Root SSH

```bash
# Edit SSH config
nano /etc/ssh/sshd_config

# Change these settings:
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no

# Restart SSH
systemctl restart sshd
```

### Step 3: Configure UFW Firewall

```bash
# Enable UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Enable firewall
ufw enable

# Check status
ufw status verbose
```

### Step 4: Install Fail2Ban

```bash
# Install fail2ban
apt install fail2ban -y

# Create config
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
EOF

# Start service
systemctl enable fail2ban
systemctl start fail2ban
```

---

## Install Dependencies

### Step 1: System Packages

```bash
# Update package list
apt update

# Install essentials
apt install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    htop \
    unzip \
    software-properties-common \
    apt-transport-https \
    ca-certificates \
    gnupg \
    lsb-release

# Install Python 3.12
apt install -y \
    python3.12 \
    python3.12-venv \
    python3.12-dev \
    python3-pip

# Set Python 3.12 as default
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1
```

### Step 2: PostgreSQL 16 with pgvector

```bash
# Add PostgreSQL repository
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -

# Update and install PostgreSQL 16
apt update
apt install -y postgresql-16 postgresql-contrib-16 postgresql-server-dev-16

# Install pgvector
cd /tmp
git clone --branch v0.7.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install

# Clean up
cd /tmp
rm -rf pgvector
```

### Step 3: Redis

```bash
# Install Redis
apt install -y redis-server

# Configure Redis
sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf
sed -i 's/# maxmemory <bytes>/maxmemory 2gb/' /etc/redis/redis.conf
sed -i 's/# maxmemory-policy noeviction/maxmemory-policy allkeys-lru/' /etc/redis/redis.conf

# Restart Redis
systemctl restart redis-server
systemctl enable redis-server

# Test
redis-cli ping
# Should return: PONG
```

### Step 4: Nginx

```bash
# Install Nginx
apt install -y nginx

# Stop for now (configure later)
systemctl stop nginx
```

### Step 5: Certbot (SSL)

```bash
# Install Certbot
apt install -y certbot python3-certbot-nginx
```

---

## PostgreSQL Setup

### Step 1: Create Database and User

```bash
# Switch to postgres user
sudo -u postgres psql

# In PostgreSQL shell:
```

```sql
-- Create user
CREATE USER cmmc_admin WITH PASSWORD 'YOUR_SECURE_PASSWORD_HERE';

-- Create database
CREATE DATABASE cmmc_platform OWNER cmmc_admin;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE cmmc_platform TO cmmc_admin;

-- Exit
\q
```

### Step 2: Enable pgvector Extension

```bash
# Connect to database
sudo -u postgres psql -d cmmc_platform

# In PostgreSQL shell:
```

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- Verify
SELECT * FROM pg_extension WHERE extname IN ('uuid-ossp', 'pgcrypto', 'vector');

-- Exit
\q
```

### Step 3: Configure PostgreSQL for Network Access

```bash
# Edit postgresql.conf
nano /etc/postgresql/16/main/postgresql.conf

# Find and modify:
listen_addresses = 'localhost'  # Keep localhost only for security
max_connections = 100
shared_buffers = 4GB  # 25% of RAM
effective_cache_size = 12GB  # 75% of RAM
work_mem = 64MB
maintenance_work_mem = 1GB

# Edit pg_hba.conf
nano /etc/postgresql/16/main/pg_hba.conf

# Add this line (for local connections):
local   cmmc_platform    cmmc_admin                    scram-sha-256

# Restart PostgreSQL
systemctl restart postgresql
```

### Step 4: Test Connection

```bash
# Test as cmmc_admin
psql -U cmmc_admin -d cmmc_platform -h localhost

# Should prompt for password, then show:
# cmmc_platform=>

# Exit
\q
```

---

## Redis Setup

Already installed in previous steps. Verify:

```bash
# Check status
systemctl status redis-server

# Test connection
redis-cli ping
# Should return: PONG

# Check memory
redis-cli info memory | grep used_memory_human
```

---

## Application Setup

### Step 1: Clone Repository

```bash
# Switch to deploy user
su - deploy

# Create app directory
mkdir -p /home/deploy/apps
cd /home/deploy/apps

# Clone repository (use your actual repo URL)
git clone https://github.com/Taycurry15/CISO.git
cd CISO/cmmc-platform

# Checkout your branch
git checkout claude/evaluate-product-sales-01TeLJFjbCyqqdoBRLqnE6Fq
```

### Step 2: Create Python Virtual Environment

```bash
# Create venv
python3 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Step 3: Install Python Dependencies

```bash
# Install requirements
pip install -r requirements.txt

# This will install:
# - FastAPI, Uvicorn
# - PostgreSQL drivers (asyncpg)
# - AI libraries (openai, anthropic, sentence-transformers)
# - Document processing (PyPDF2, python-docx, openpyxl)
# - Vector operations (pgvector, numpy)
# - And all other dependencies
```

### Step 4: Configure Environment

```bash
# Copy example env
cp .env.example .env

# Edit configuration
nano .env
```

**Critical settings to configure in `.env`:**

```bash
# Database
DATABASE_URL=postgresql://cmmc_admin:YOUR_SECURE_PASSWORD_HERE@localhost:5432/cmmc_platform

# Object Storage
OBJECT_STORAGE_PATH=/home/deploy/apps/CISO/cmmc-platform/storage/evidence

# AI Provider (choose one)
AI_PROVIDER=openai  # or "anthropic"
AI_MODEL=gpt-4-turbo-preview
AI_API_KEY=sk-your-openai-api-key-here

# Embedding Provider
EMBEDDING_PROVIDER=openai  # or "sentence_transformers" for free
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_API_KEY=  # Leave blank to use AI_API_KEY

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# Domain
DOMAIN=cmmc.yourdomain.com

# Security
JWT_SECRET=$(openssl rand -hex 32)  # Generate secure secret
BCRYPT_ROUNDS=12

# Enable AI features
ENABLE_AI_ANALYSIS=true
ENABLE_RAG=true
ENABLE_PROVIDER_INHERITANCE=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

Save and exit (`Ctrl+X`, `Y`, `Enter`).

### Step 5: Create Storage Directories

```bash
# Create evidence storage
mkdir -p /home/deploy/apps/CISO/cmmc-platform/storage/evidence
mkdir -p /home/deploy/apps/CISO/cmmc-platform/storage/exports
mkdir -p /home/deploy/apps/CISO/cmmc-platform/logs

# Set permissions
chmod 755 /home/deploy/apps/CISO/cmmc-platform/storage
```

---

## SSL/TLS Configuration

### Step 1: Obtain SSL Certificate

```bash
# Make sure Nginx is stopped
sudo systemctl stop nginx

# Obtain certificate (replace with your domain and email)
sudo certbot certonly --standalone \
  -d cmmc.yourdomain.com \
  --non-interactive \
  --agree-tos \
  --email your-email@example.com

# Certificate will be saved to:
# /etc/letsencrypt/live/cmmc.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/cmmc.yourdomain.com/privkey.pem
```

### Step 2: Set Up Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Should show: Congratulations, all renewals succeeded!
```

Certbot automatically creates a cron job for renewal. Verify:

```bash
sudo systemctl list-timers | grep certbot
```

---

## Nginx Configuration

### Step 1: Create Nginx Config

```bash
# Remove default config
sudo rm /etc/nginx/sites-enabled/default

# Create new config
sudo nano /etc/nginx/sites-available/cmmc-platform
```

**Paste this configuration (replace domain):**

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=general_limit:10m rate=30r/s;

# Upstream backend
upstream cmmc_backend {
    server 127.0.0.1:8000 fail_timeout=0;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    listen [::]:80;
    server_name cmmc.yourdomain.com;

    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    # Redirect all other traffic to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name cmmc.yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/cmmc.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/cmmc.yourdomain.com/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Logging
    access_log /var/log/nginx/cmmc-platform-access.log;
    error_log /var/log/nginx/cmmc-platform-error.log;

    # Max upload size (for evidence files)
    client_max_body_size 100M;

    # API endpoints (with rate limiting)
    location /api/ {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://cmmc_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for AI requests
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }

    # Health check (no rate limit)
    location /health {
        proxy_pass http://cmmc_backend;
        proxy_set_header Host $host;
        access_log off;
    }

    # Static files (if any)
    location /static/ {
        alias /home/deploy/apps/CISO/cmmc-platform/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Root
    location / {
        limit_req zone=general_limit burst=50 nodelay;

        proxy_pass http://cmmc_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 2: Enable and Test Config

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/cmmc-platform /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Should show:
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# Start Nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

---

## Systemd Services

### Step 1: Create FastAPI Service

```bash
sudo nano /etc/systemd/system/cmmc-api.service
```

**Paste this configuration:**

```ini
[Unit]
Description=CMMC Platform FastAPI Application
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=notify
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/apps/CISO/cmmc-platform
Environment="PATH=/home/deploy/apps/CISO/cmmc-platform/venv/bin"
EnvironmentFile=/home/deploy/apps/CISO/cmmc-platform/.env

ExecStart=/home/deploy/apps/CISO/cmmc-platform/venv/bin/uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-level info \
    --access-log \
    --use-colors

# Restart policy
Restart=always
RestartSec=10
StandardOutput=append:/home/deploy/apps/CISO/cmmc-platform/logs/api.log
StandardError=append:/home/deploy/apps/CISO/cmmc-platform/logs/api-error.log

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/deploy/apps/CISO/cmmc-platform/storage
ReadWritePaths=/home/deploy/apps/CISO/cmmc-platform/logs

[Install]
WantedBy=multi-user.target
```

### Step 2: Create Celery Worker Service (for background tasks)

```bash
sudo nano /etc/systemd/system/cmmc-celery.service
```

```ini
[Unit]
Description=CMMC Platform Celery Worker
After=network.target redis.service
Requires=redis.service

[Service]
Type=forking
User=deploy
Group=deploy
WorkingDirectory=/home/deploy/apps/CISO/cmmc-platform
Environment="PATH=/home/deploy/apps/CISO/cmmc-platform/venv/bin"
EnvironmentFile=/home/deploy/apps/CISO/cmmc-platform/.env

ExecStart=/home/deploy/apps/CISO/cmmc-platform/venv/bin/celery -A api.celery worker \
    --loglevel=info \
    --concurrency=2

Restart=always
RestartSec=10
StandardOutput=append:/home/deploy/apps/CISO/cmmc-platform/logs/celery.log
StandardError=append:/home/deploy/apps/CISO/cmmc-platform/logs/celery-error.log

[Install]
WantedBy=multi-user.target
```

### Step 3: Enable and Start Services

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable cmmc-api
# sudo systemctl enable cmmc-celery  # Uncomment when Celery is configured

# Start API
sudo systemctl start cmmc-api

# Check status
sudo systemctl status cmmc-api

# Should show: Active: active (running)
```

### Step 4: View Logs

```bash
# API logs
sudo journalctl -u cmmc-api -f

# Or view log files
tail -f /home/deploy/apps/CISO/cmmc-platform/logs/api.log
```

---

## Database Initialization

### Step 1: Initialize Schema

```bash
# Switch to deploy user and activate venv
su - deploy
cd /home/deploy/apps/CISO/cmmc-platform
source venv/bin/activate

# Initialize database
psql -U cmmc_admin -d cmmc_platform -h localhost -f database/schema.sql

# Enter password when prompted
```

### Step 2: Create Initial Organization

```bash
# Connect to database
psql -U cmmc_admin -d cmmc_platform -h localhost
```

```sql
-- Create initial organization
INSERT INTO organizations (name, duns_number, cage_code, cmmc_level, target_certification_date)
VALUES (
    'Your Company Name',
    '123456789',
    'ABCDE',
    2,
    '2025-12-31'
);

-- Create admin user
INSERT INTO users (organization_id, email, name, role)
VALUES (
    (SELECT id FROM organizations LIMIT 1),
    'admin@yourcompany.com',
    'Admin User',
    'admin'
);

-- Verify
SELECT * FROM organizations;
SELECT * FROM users;

-- Exit
\q
```

### Step 3: Import CMMC Framework (Optional - if you have the import script)

```bash
# If you have scripts/import_cmmc_framework.py, run:
python scripts/import_cmmc_framework.py

# This will import:
# - 14 control domains (AC, AU, AT, CM, etc.)
# - 110 controls
# - 320+ assessment objectives
```

---

## Reference Documentation

### Step 1: Download CMMC/NIST PDFs

**Manual download recommended** (government sites block automation):

```bash
# Create directories
mkdir -p /home/deploy/apps/CISO/cmmc-platform/docs/reference/{nist,cmmc,guides}
cd /home/deploy/apps/CISO/cmmc-platform/docs/reference
```

**Download these PDFs manually** (from your local computer):

1. **NIST SP 800-171 Rev 2**: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171r2.pdf
2. **NIST SP 800-171A**: https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-171a.pdf
3. **CMMC Model v2.13**: https://dodcio.defense.gov/Portals/0/Documents/CMMC/ModelOverviewv2.pdf
4. **CMMC Assessment Guide**: https://dodcio.defense.gov/Portals/0/Documents/CMMC/AssessmentGuideL2v2.pdf

**Upload to server:**

```bash
# From your local machine:
scp NIST.SP.800-171r2.pdf deploy@cmmc.yourdomain.com:/home/deploy/apps/CISO/cmmc-platform/docs/reference/nist/
scp NIST.SP.800-171a.pdf deploy@cmmc.yourdomain.com:/home/deploy/apps/CISO/cmmc-platform/docs/reference/nist/
scp CMMC-Model-v2.13.pdf deploy@cmmc.yourdomain.com:/home/deploy/apps/CISO/cmmc-platform/docs/reference/cmmc/
scp CMMC-AssessmentGuide-L2-v2.13.pdf deploy@cmmc.yourdomain.com:/home/deploy/apps/CISO/cmmc-platform/docs/reference/cmmc/
```

### Step 2: Ingest into RAG

```bash
# On server, as deploy user
cd /home/deploy/apps/CISO/cmmc-platform
source venv/bin/activate

# Check status (should show 0 initially)
python scripts/ingest_reference_docs.py --status

# Ingest all downloaded docs
python scripts/ingest_reference_docs.py

# This will:
# - Extract text from PDFs (~10-15 minutes)
# - Create ~1500 chunks
# - Generate embeddings (costs ~$0.02 with OpenAI)
# - Store in PostgreSQL with pgvector

# Verify ingestion
python scripts/ingest_reference_docs.py --status

# Should show:
# Documents Ingested: 4
# Chunks with Embeddings: ~1500
# Control IDs found: ~110
```

### Step 3: Test RAG Search

```bash
# Interactive search
python scripts/test_rag_search.py --interactive

# Try queries:
# > multi-factor authentication
# > access control policy
# > incident response

# Exit with Ctrl+C
```

---

## Testing & Verification

### Step 1: Health Check

```bash
# From your local machine or server:
curl https://cmmc.yourdomain.com/health

# Should return:
# {"status":"healthy","timestamp":"2024-11-16T..."}

# Check AI services
curl https://cmmc.yourdomain.com/health/ai

# Should show all services healthy
```

### Step 2: Test API Endpoints

```bash
# Get API documentation
curl https://cmmc.yourdomain.com/docs

# Should redirect to FastAPI Swagger UI
# Visit in browser: https://cmmc.yourdomain.com/docs
```

### Step 3: Test Control Analysis

```bash
# Analyze a control (requires assessment setup)
curl -X POST https://cmmc.yourdomain.com/api/v1/analyze/AC.L2-3.1.1 \
  -H "Content-Type: application/json" \
  -d '{
    "assessment_id": "00000000-0000-0000-0000-000000000000",
    "include_provider_inheritance": true,
    "include_diagram_context": true
  }'

# Should return AI analysis with determination, confidence, narrative
```

### Step 4: Check Logs

```bash
# API logs
tail -f /home/deploy/apps/CISO/cmmc-platform/logs/api.log

# Nginx logs
sudo tail -f /var/log/nginx/cmmc-platform-access.log
sudo tail -f /var/log/nginx/cmmc-platform-error.log

# System logs
sudo journalctl -u cmmc-api -f
```

### Step 5: Database Verification

```bash
# Connect to database
psql -U cmmc_admin -d cmmc_platform -h localhost

# Check tables
\dt

# Check document chunks
SELECT COUNT(*) FROM document_chunks WHERE embedding IS NOT NULL;

# Check controls (if imported)
SELECT COUNT(*) FROM controls;

# Exit
\q
```

---

## Monitoring & Maintenance

### Step 1: Set Up Log Rotation

```bash
sudo nano /etc/logrotate.d/cmmc-platform
```

```
/home/deploy/apps/CISO/cmmc-platform/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 deploy deploy
    sharedscripts
    postrotate
        systemctl reload cmmc-api
    endscript
}
```

### Step 2: Database Backups

```bash
# Create backup script
sudo nano /usr/local/bin/backup-cmmc-db.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/home/deploy/backups/database"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="cmmc_platform_${DATE}.sql.gz"

mkdir -p $BACKUP_DIR

# Backup database
PGPASSWORD='YOUR_SECURE_PASSWORD_HERE' pg_dump \
    -U cmmc_admin \
    -h localhost \
    -d cmmc_platform \
    | gzip > "$BACKUP_DIR/$FILENAME"

# Keep only last 30 days
find $BACKUP_DIR -name "cmmc_platform_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $FILENAME"
```

```bash
# Make executable
sudo chmod +x /usr/local/bin/backup-cmmc-db.sh

# Test backup
sudo /usr/local/bin/backup-cmmc-db.sh

# Schedule daily backups (2 AM)
sudo crontab -e

# Add this line:
0 2 * * * /usr/local/bin/backup-cmmc-db.sh >> /var/log/cmmc-backup.log 2>&1
```

### Step 3: System Monitoring

```bash
# Install monitoring tools
sudo apt install -y htop iotop nethogs

# Check system resources
htop

# Check disk usage
df -h

# Check database size
sudo -u postgres psql -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database;"
```

### Step 4: Update Application

```bash
# Switch to deploy user
su - deploy
cd /home/deploy/apps/CISO/cmmc-platform

# Pull latest code
git pull origin claude/evaluate-product-sales-01TeLJFjbCyqqdoBRLqnE6Fq

# Activate venv
source venv/bin/activate

# Update dependencies
pip install --upgrade -r requirements.txt

# Restart service
sudo systemctl restart cmmc-api

# Check status
sudo systemctl status cmmc-api
```

---

## Troubleshooting

### Issue: API Not Starting

**Check logs:**
```bash
sudo journalctl -u cmmc-api -n 100
```

**Common causes:**
- Database connection failed → Check DATABASE_URL in .env
- Missing API key → Check AI_API_KEY in .env
- Port already in use → Check: `sudo lsof -i :8000`

### Issue: SSL Certificate Error

**Renew certificate:**
```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

### Issue: High Memory Usage

**Check processes:**
```bash
htop
# Press F5 to sort by memory

# Restart services
sudo systemctl restart cmmc-api
sudo systemctl restart postgresql
sudo systemctl restart redis-server
```

### Issue: Slow AI Responses

**Possible causes:**
- API rate limits → Check OpenAI/Anthropic dashboard
- Large context → Reduce RAG_TOP_K in .env
- Network latency → Check: `ping api.openai.com`

**Optimize:**
```bash
# Edit .env
RAG_TOP_K=5  # Instead of 10
AI_MAX_TOKENS=2000  # Instead of 4000

# Restart
sudo systemctl restart cmmc-api
```

### Issue: Database Connection Errors

**Check PostgreSQL status:**
```bash
sudo systemctl status postgresql

# Check connections
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE datname = 'cmmc_platform';"

# Restart PostgreSQL
sudo systemctl restart postgresql
```

### Issue: Nginx 502 Bad Gateway

**Causes:**
- API service not running → `sudo systemctl start cmmc-api`
- Firewall blocking → `sudo ufw status`
- Wrong upstream port → Check nginx config

**Fix:**
```bash
# Check API is running
sudo systemctl status cmmc-api

# Check API is listening
sudo netstat -tlnp | grep 8000

# Restart everything
sudo systemctl restart cmmc-api
sudo systemctl restart nginx
```

---

## Performance Tuning

### PostgreSQL

```bash
sudo nano /etc/postgresql/16/main/postgresql.conf

# For 16GB RAM server:
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 64MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8

# Restart
sudo systemctl restart postgresql
```

### Nginx

```bash
sudo nano /etc/nginx/nginx.conf

# Add to http block:
worker_processes auto;
worker_rlimit_nofile 65535;

events {
    worker_connections 4096;
    use epoll;
    multi_accept on;
}

http {
    # Enable gzip
    gzip on;
    gzip_vary on;
    gzip_types text/plain text/css text/xml text/javascript application/json application/javascript application/xml+rss;

    # Connection pooling
    keepalive_timeout 65;
    keepalive_requests 100;
}

# Restart
sudo systemctl restart nginx
```

---

## Security Checklist

- [ ] UFW firewall enabled with minimal ports
- [ ] Fail2Ban protecting SSH
- [ ] Root SSH disabled
- [ ] Strong database password
- [ ] SSL/TLS certificate valid
- [ ] Security headers configured in Nginx
- [ ] Database backups scheduled
- [ ] Log rotation configured
- [ ] System updates automated
- [ ] Monitoring in place

---

## Next Steps

1. **Set up monitoring**: Consider Prometheus + Grafana or UptimeRobot
2. **Configure backups**: Set up off-site backups (S3, Backblaze B2)
3. **Load testing**: Test with expected user load
4. **Documentation**: Create runbook for team
5. **Disaster recovery**: Document restoration procedures

---

## Support

**Logs locations:**
- API: `/home/deploy/apps/CISO/cmmc-platform/logs/api.log`
- Nginx: `/var/log/nginx/cmmc-platform-*.log`
- PostgreSQL: `/var/log/postgresql/postgresql-16-main.log`
- System: `sudo journalctl -u cmmc-api`

**Configuration files:**
- App: `/home/deploy/apps/CISO/cmmc-platform/.env`
- Nginx: `/etc/nginx/sites-available/cmmc-platform`
- PostgreSQL: `/etc/postgresql/16/main/postgresql.conf`
- Systemd: `/etc/systemd/system/cmmc-api.service`

---

**Deployment complete! 🚀**

Access your platform at: `https://cmmc.yourdomain.com`

Estimated total time: **2-3 hours**
Monthly cost: **~€40-50** (server) + **~$10-20** (AI API usage)
