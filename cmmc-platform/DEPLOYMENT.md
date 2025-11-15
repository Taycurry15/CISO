# CMMC Compliance Platform - Hetzner Deployment Guide

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Hetzner VPS (Ubuntu 24.04)                │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────┐ │
│  │ CISO Assistant│  │  FastAPI      │  │ PostgreSQL │ │
│  │   (Port 8080) │  │  (Port 8000)  │  │ + pgvector │ │
│  │               │  │               │  │            │ │
│  │  Django-based │  │  AI/RAG/      │  │  Evidence  │ │
│  │  GRC Core     │  │  Integrations │  │  Storage   │ │
│  └───────────────┘  └───────────────┘  └────────────┘ │
│          │                  │                  │       │
│  ┌───────────────┐  ┌───────────────┐  ┌────────────┐ │
│  │    Redis      │  │    MinIO      │  │   Celery   │ │
│  │  (Port 6379)  │  │  (Port 9000)  │  │   Worker   │ │
│  │               │  │               │  │            │ │
│  │  Cache/Queue  │  │  Object Store │  │ Background │ │
│  └───────────────┘  └───────────────┘  └────────────┘ │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Nginx Reverse Proxy                │   │
│  │            (Ports 80/443 + SSL/TLS)             │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Prerequisites

### 1. Hetzner Server Specs (Recommended)
- **VPS Type**: CPX41 or better
  - 8 vCPU cores
  - 16 GB RAM
  - 240 GB NVMe SSD
  - 20 TB traffic
- **OS**: Ubuntu 24.04 LTS
- **Cost**: ~€40/month

### 2. Domain Setup
- Register domain (e.g., `cmmc-platform.yourcompany.com`)
- Point A record to your Hetzner IP
- Set up DNS for SSL certificate

## Installation Steps

### Step 1: Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin -y

# Create deployment user
sudo useradd -m -s /bin/bash cmmc
sudo usermod -aG docker cmmc
sudo su - cmmc

# Clone repository (or upload files)
mkdir -p ~/cmmc-platform
cd ~/cmmc-platform
```

### Step 2: Directory Structure

```bash
# Create necessary directories
mkdir -p {database,api,scripts,config,data/{postgres,minio,evidence},logs}

# Copy the files we created
# - database/schema.sql
# - api/main.py
# - scripts/import_cmmc_framework.py
```

### Step 3: Environment Configuration

Create `.env` file:

```bash
cat > .env << 'EOF'
# Database
POSTGRES_USER=cmmc_admin
POSTGRES_PASSWORD=CHANGE_ME_STRONG_PASSWORD
POSTGRES_DB=cmmc_platform
DATABASE_URL=postgresql://cmmc_admin:CHANGE_ME_STRONG_PASSWORD@postgres:5432/cmmc_platform

# Redis
REDIS_URL=redis://redis:6379/0

# MinIO (Object Storage)
MINIO_ROOT_USER=minio_admin
MINIO_ROOT_PASSWORD=CHANGE_ME_MINIO_PASSWORD
MINIO_ENDPOINT=minio:9000
MINIO_BUCKET=cmmc-evidence

# API Keys
OPENAI_API_KEY=sk-your-openai-key-here
ANTHROPIC_API_KEY=sk-ant-your-anthropic-key-here

# JWT Secret
JWT_SECRET=CHANGE_ME_RANDOM_SECRET_KEY

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO

# CISO Assistant
CISO_ASSISTANT_SECRET_KEY=CHANGE_ME_DJANGO_SECRET
CISO_ASSISTANT_DB_HOST=postgres
CISO_ASSISTANT_DB_PORT=5432
CISO_ASSISTANT_DB_NAME=cmmc_platform
CISO_ASSISTANT_DB_USER=cmmc_admin
CISO_ASSISTANT_DB_PASSWORD=CHANGE_ME_STRONG_PASSWORD
EOF

# Secure the env file
chmod 600 .env
```

### Step 4: Docker Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  # PostgreSQL with pgvector extension
  postgres:
    image: pgvector/pgvector:pg16
    container_name: cmmc-postgres
    restart: unless-stopped
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - cmmc-network

  # Redis for caching and task queue
  redis:
    image: redis:7-alpine
    container_name: cmmc-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - ./data/redis:/data
    ports:
      - "127.0.0.1:6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - cmmc-network

  # MinIO for object storage (evidence files)
  minio:
    image: minio/minio:latest
    container_name: cmmc-minio
    restart: unless-stopped
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - ./data/minio:/data
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    networks:
      - cmmc-network

  # CISO Assistant (Core GRC Platform)
  ciso-assistant:
    image: ghcr.io/intuitem/ciso-assistant-community:latest
    container_name: cmmc-ciso-assistant
    restart: unless-stopped
    environment:
      DJANGO_SECRET_KEY: ${CISO_ASSISTANT_SECRET_KEY}
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_NAME: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    depends_on:
      postgres:
        condition: service_healthy
    ports:
      - "127.0.0.1:8080:8000"
    volumes:
      - ./data/ciso-assistant:/app/media
    networks:
      - cmmc-network

  # FastAPI Service (AI/RAG/Integrations)
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: cmmc-api
    restart: unless-stopped
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      MINIO_ENDPOINT: ${MINIO_ENDPOINT}
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
      LOG_LEVEL: ${LOG_LEVEL}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "127.0.0.1:8000:8000"
    volumes:
      - ./data/evidence:/var/cmmc/evidence
      - ./logs:/var/cmmc/logs
    networks:
      - cmmc-network

  # Celery Worker (Background tasks)
  celery-worker:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: cmmc-celery-worker
    restart: unless-stopped
    command: celery -A tasks worker --loglevel=info
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - redis
      - postgres
    volumes:
      - ./data/evidence:/var/cmmc/evidence
    networks:
      - cmmc-network

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: cmmc-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./config/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - ciso-assistant
      - api
    networks:
      - cmmc-network

networks:
  cmmc-network:
    driver: bridge

volumes:
  postgres-data:
  redis-data:
  minio-data:
```

### Step 5: FastAPI Dockerfile

Create `api/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY main.py .

# Create directories
RUN mkdir -p /var/cmmc/evidence /var/cmmc/logs

# Run as non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /var/cmmc
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Create `api/requirements.txt`:

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.6.0
asyncpg==0.29.0
redis==5.0.1
celery==5.3.6
python-multipart==0.0.6
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
openai==1.12.0
anthropic==0.18.1
minio==7.2.3
pypdf2==3.0.1
python-docx==1.1.0
openpyxl==3.1.2
pillow==10.2.0
numpy==1.26.4
```

### Step 6: Nginx Configuration

Create `config/nginx.conf`:

```nginx
events {
    worker_connections 1024;
}

http {
    upstream ciso_assistant {
        server ciso-assistant:8000;
    }

    upstream api {
        server api:8000;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=app_limit:10m rate=30r/s;

    server {
        listen 80;
        server_name cmmc-platform.yourcompany.com;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name cmmc-platform.yourcompany.com;

        # SSL Configuration (use Let's Encrypt)
        ssl_certificate /etc/nginx/ssl/fullchain.pem;
        ssl_certificate_key /etc/nginx/ssl/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security headers
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;

        # CISO Assistant (main app)
        location / {
            limit_req zone=app_limit burst=20 nodelay;
            proxy_pass http://ciso_assistant;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_buffering off;
        }

        # FastAPI endpoints
        location /api/ {
            limit_req zone=api_limit burst=10 nodelay;
            proxy_pass http://api;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # Increase timeouts for long-running AI operations
            proxy_connect_timeout 300s;
            proxy_send_timeout 300s;
            proxy_read_timeout 300s;
        }

        # Upload size limit (for evidence files)
        client_max_body_size 100M;
    }
}
```

### Step 7: SSL Certificate Setup

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Stop nginx temporarily
docker-compose stop nginx

# Get certificate
sudo certbot certonly --standalone -d cmmc-platform.yourcompany.com

# Copy certificates to config directory
sudo cp /etc/letsencrypt/live/cmmc-platform.yourcompany.com/fullchain.pem config/ssl/
sudo cp /etc/letsencrypt/live/cmmc-platform.yourcompany.com/privkey.pem config/ssl/
sudo chown -R cmmc:cmmc config/ssl

# Set up auto-renewal
echo "0 0 1 * * certbot renew --quiet && docker-compose restart nginx" | sudo crontab -
```

### Step 8: Deploy the Platform

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f

# Verify services are running
docker-compose ps

# Initialize database
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -f /docker-entrypoint-initdb.d/01-schema.sql

# Import CMMC framework
python3 scripts/import_cmmc_framework.py
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -f cmmc_l2_import.sql

# Create MinIO bucket
docker-compose exec minio mc alias set local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
docker-compose exec minio mc mb local/cmmc-evidence
docker-compose exec minio mc anonymous set download local/cmmc-evidence
```

### Step 9: Access the Platform

- **CISO Assistant UI**: https://cmmc-platform.yourcompany.com
- **API Documentation**: https://cmmc-platform.yourcompany.com/api/docs
- **MinIO Console**: http://YOUR_IP:9001 (accessible only via SSH tunnel)

### Step 10: Create First Admin User

```bash
# Access CISO Assistant container
docker-compose exec ciso-assistant python manage.py createsuperuser

# Follow prompts to create admin account
```

## Monitoring & Maintenance

### Health Checks

```bash
# Check all services
docker-compose ps

# View logs
docker-compose logs -f api
docker-compose logs -f ciso-assistant

# Check disk usage
df -h

# Monitor database
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -c "SELECT count(*) FROM evidence;"
```

### Backup Strategy

```bash
# Database backup (daily cron)
cat > /home/cmmc/backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker-compose exec -T postgres pg_dump -U cmmc_admin cmmc_platform | gzip > ~/backups/db_$DATE.sql.gz
# Keep only last 30 days
find ~/backups -name "db_*.sql.gz" -mtime +30 -delete
EOF

chmod +x /home/cmmc/backup.sh
(crontab -l 2>/dev/null; echo "0 2 * * * /home/cmmc/backup.sh") | crontab -

# Evidence backup (sync to external storage)
# Configure rclone for Hetzner Storage Box or S3
```

### Resource Management

```bash
# Monitor resource usage
docker stats

# Prune unused images/volumes
docker system prune -a --volumes -f

# Rotate logs
echo "/home/cmmc/logs/*.log {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
}" | sudo tee /etc/logrotate.d/cmmc
```

## Security Hardening

### Firewall Setup

```bash
# Allow SSH, HTTP, HTTPS only
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Database Security

```bash
# PostgreSQL is only accessible from localhost in docker-compose
# For additional security, set strong password and enable SSL
```

### Application Security

- Change all default passwords in `.env`
- Use strong JWT secrets
- Enable rate limiting (already configured in nginx)
- Regular dependency updates
- Enable audit logging

## Integration Setup

### Nessus Integration

See `/home/cmmc/integrations/nessus_connector.py` for setup

### Splunk Integration

See `/home/cmmc/integrations/splunk_connector.py` for setup

## Troubleshooting

### Common Issues

**Issue**: Services not starting
```bash
# Check logs
docker-compose logs api
docker-compose logs postgres

# Verify network connectivity
docker network inspect cmmc-platform_cmmc-network
```

**Issue**: Database connection errors
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U cmmc_admin -d cmmc_platform -c "SELECT 1;"
```

**Issue**: Out of disk space
```bash
# Check usage
df -h
du -sh /home/cmmc/data/*

# Clean up old evidence (if needed)
# Clean Docker
docker system prune -a --volumes
```

## Performance Tuning

### PostgreSQL Tuning

Edit `config/postgres.conf`:

```
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
work_mem = 64MB
max_connections = 100
```

### Redis Tuning

```
maxmemory 2gb
maxmemory-policy allkeys-lru
```

## Upgrade Procedure

```bash
# Pull latest code
cd ~/cmmc-platform
git pull

# Backup database
./backup.sh

# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Start services
docker-compose up -d

# Run migrations (if any)
docker-compose exec api alembic upgrade head
```

## Cost Estimate

- **Hetzner CPX41**: €40/month
- **Domain**: €15/year
- **Backup Storage**: €10/month (optional)
- **Total**: ~€50/month for complete setup

## Support

- CISO Assistant: https://github.com/intuitem/ciso-assistant-community
- FastAPI: https://fastapi.tiangolo.com
- Report issues: [Your support channel]
