#!/bin/bash

################################################################################
# CISO App - Automated Deployment Script for Hetzner VPS
#
# This script automates the deployment of the CMMC Compliance Platform
# on a Hetzner VPS running Ubuntu 22.04 or 24.04
#
# Usage: sudo ./deploy.sh
################################################################################

set -e  # Exit on error
set -u  # Exit on undefined variable

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root (use sudo)"
   exit 1
fi

################################################################################
# Configuration
################################################################################

log_info "Starting CISO App deployment..."

# Prompt for configuration
read -p "Enter your domain name (e.g., cmmc.example.com): " DOMAIN
read -p "Enter your email for Let's Encrypt SSL: " EMAIL
read -p "Enter database password: " -s DB_PASSWORD
echo
read -p "Enter your OpenAI API key (or leave empty for Anthropic): " AI_API_KEY

if [[ -z "$AI_API_KEY" ]]; then
    read -p "Enter your Anthropic API key: " AI_API_KEY
    AI_PROVIDER="anthropic"
    AI_MODEL="claude-3-5-sonnet-20241022"
else
    AI_PROVIDER="openai"
    AI_MODEL="gpt-4-turbo-preview"
fi

# Generate secure secrets
JWT_SECRET=$(openssl rand -hex 32)
MINIO_PASSWORD=$(openssl rand -hex 16)
MINIO_KMS_SECRET_KEY=$(openssl rand -base64 32)
REDIS_PASSWORD=$(openssl rand -hex 16)

if [[ "$AI_PROVIDER" == "openai" ]]; then
    EMBEDDING_PROVIDER="openai"
    EMBEDDING_MODEL="text-embedding-3-small"
else
    EMBEDDING_PROVIDER="$AI_PROVIDER"
    EMBEDDING_MODEL="voyage-2"
fi

################################################################################
# Step 1: System Update & Basic Setup
################################################################################

log_info "Step 1: Updating system packages..."
apt update && apt upgrade -y

log_info "Setting hostname..."
hostnamectl set-hostname ciso-production

log_info "Configuring timezone to UTC..."
timedatectl set-timezone UTC

log_success "System update completed"

################################################################################
# Step 2: Install Docker & Docker Compose
################################################################################

log_info "Step 2: Installing Docker..."

# Remove old versions
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Install dependencies
apt install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    software-properties-common

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

log_success "Docker installed successfully"

################################################################################
# Step 3: Configure Firewall
################################################################################

log_info "Step 3: Configuring UFW firewall..."

# Install UFW if not present
apt install -y ufw

# Configure firewall
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS
ufw --force enable

log_success "Firewall configured"

################################################################################
# Step 4: Create Deploy User
################################################################################

log_info "Step 4: Creating deployment user..."

# Create deploy user if doesn't exist
if ! id -u deploy &>/dev/null; then
    useradd -m -s /bin/bash deploy
    usermod -aG docker deploy
    log_success "Deploy user created"
else
    log_warning "Deploy user already exists"
fi

################################################################################
# Step 5: Clone Repository
################################################################################

log_info "Step 5: Cloning CISO repository..."

# Create apps directory
mkdir -p /home/deploy/apps
cd /home/deploy/apps

# Clone or pull repository
if [ -d "CISO" ]; then
    log_warning "CISO directory exists, pulling latest changes..."
    cd CISO
    sudo -u deploy git pull
else
    log_info "Cloning repository..."
    sudo -u deploy git clone https://github.com/Taycurry15/CISO.git
    cd CISO
fi

DEPLOY_DIR="/home/deploy/apps/CISO"

log_success "Repository ready"

################################################################################
# Step 6: Configure Environment
################################################################################

log_info "Step 6: Configuring environment variables..."

# Create .env file for docker-compose
cat > "$DEPLOY_DIR/.env" <<EOF
# Database Configuration
POSTGRES_USER=cmmc_admin
POSTGRES_PASSWORD=$DB_PASSWORD
POSTGRES_DB=cmmc_platform
REDIS_PASSWORD=$REDIS_PASSWORD

# MinIO Configuration
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=$MINIO_PASSWORD
MINIO_KMS_SECRET_KEY=$MINIO_KMS_SECRET_KEY

# Domain Configuration
DOMAIN=$DOMAIN
LETSENCRYPT_EMAIL=$EMAIL
EOF

# Create .env file for CMMC platform
cat > "$DEPLOY_DIR/cmmc-platform/.env" <<EOF
# Database
DATABASE_URL=postgresql://cmmc_admin:$DB_PASSWORD@postgres:5432/cmmc_platform

# AI Provider
AI_PROVIDER=$AI_PROVIDER
AI_MODEL=$AI_MODEL
AI_API_KEY=$AI_API_KEY
AI_TEMPERATURE=0.1
AI_MAX_TOKENS=4000

# Embeddings
EMBEDDING_PROVIDER=$EMBEDDING_PROVIDER
EMBEDDING_MODEL=$EMBEDDING_MODEL

# Object Storage
MINIO_ENDPOINT=minio:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=$MINIO_PASSWORD
MINIO_BUCKET_NAME=cmmc-evidence
MINIO_USE_SSL=false
OBJECT_STORAGE_PATH=/var/cmmc/evidence

# Redis & Celery
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/0
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/0

# Application
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
CORS_ORIGINS=https://$DOMAIN

# Security
JWT_SECRET=$JWT_SECRET
JWT_EXPIRATION=86400
BCRYPT_ROUNDS=12

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Feature Flags
ENABLE_AI_ANALYSIS=true
ENABLE_RAG=true
ENABLE_PROVIDER_INHERITANCE=true
ENABLE_DIAGRAM_EXTRACTION=false

# Cache
CACHE_AI_RESPONSES=true
AI_CACHE_TTL=3600

# RAG Settings
RAG_TOP_K=10
RAG_SIMILARITY_THRESHOLD=0.7
RAG_CHUNK_SIZE=1000
RAG_CHUNK_OVERLAP=200

# Audit & Compliance
ENABLE_AUDIT_LOG=true
AUDIT_LOG_RETENTION=2555
ENABLE_CHAIN_OF_CUSTODY=true

# Backup
BACKUP_ENABLED=true
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=30

# Domain
DOMAIN=$DOMAIN
LETSENCRYPT_EMAIL=$EMAIL
EOF

# Set proper permissions
chown -R deploy:deploy "$DEPLOY_DIR"

log_success "Environment configured"

################################################################################
# Step 7: Configure Nginx
################################################################################

log_info "Step 7: Configuring Nginx..."

# Replace domain placeholder in nginx config
sed -i "s/\${DOMAIN}/$DOMAIN/g" "$DEPLOY_DIR/nginx/conf.d/cmmc-platform.conf"

log_success "Nginx configured"

################################################################################
# Step 8: Initial SSL Certificate (HTTP-01 Challenge)
################################################################################

log_info "Step 8: Obtaining initial SSL certificate..."

# Create certbot directories
mkdir -p "$DEPLOY_DIR/certbot/conf"
mkdir -p "$DEPLOY_DIR/certbot/www"

# Start nginx temporarily for certbot
cd "$DEPLOY_DIR"
docker compose up -d nginx

# Wait for nginx to start
sleep 5

# Obtain certificate
docker compose run --rm certbot certonly --webroot \
    --webroot-path /var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

if [ $? -eq 0 ]; then
    log_success "SSL certificate obtained"
else
    log_error "Failed to obtain SSL certificate. Make sure your domain points to this server's IP."
    exit 1
fi

# Stop nginx temporarily
docker compose down

################################################################################
# Step 9: Build and Start Services
################################################################################

log_info "Step 9: Building and starting all services..."

cd "$DEPLOY_DIR"

# Build images
docker compose build

# Start all services
docker compose up -d

# Wait for services to be healthy
log_info "Waiting for services to be healthy..."
sleep 30

# Check service health
docker compose ps

log_success "All services started"

################################################################################
# Step 10: Initialize Database
################################################################################

log_info "Step 10: Initializing database..."

# Wait for PostgreSQL to be ready
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U cmmc_admin -d cmmc_platform > /dev/null 2>&1; then
        log_success "PostgreSQL is ready"
        break
    fi
    log_info "Waiting for PostgreSQL... ($i/30)"
    sleep 2
done

# Initialize MinIO bucket
log_info "Initializing MinIO bucket..."
docker compose exec -T minio sh -c "
    mc alias set local http://localhost:9000 minioadmin $MINIO_PASSWORD
    mc mb local/cmmc-evidence || true
    mc anonymous set download local/cmmc-evidence
"

log_success "Database initialized"

################################################################################
# Step 11: Setup Backup Cron Job
################################################################################

log_info "Step 11: Setting up automated backups..."

# Create backup script
cat > /home/deploy/backup-ciso.sh <<'BACKUP_SCRIPT'
#!/bin/bash
BACKUP_DIR="/home/deploy/backups"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
docker exec cmmc-postgres pg_dump -U cmmc_admin cmmc_platform | gzip > "$BACKUP_DIR/db_backup_$DATE.sql.gz"

# Backup MinIO data
docker exec cmmc-minio tar czf - /data | cat > "$BACKUP_DIR/minio_backup_$DATE.tar.gz"

# Keep only last 30 days of backups
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo "Backup completed: $DATE"
BACKUP_SCRIPT

chmod +x /home/deploy/backup-ciso.sh
chown deploy:deploy /home/deploy/backup-ciso.sh

# Add to crontab for deploy user
(crontab -u deploy -l 2>/dev/null; echo "0 2 * * * /home/deploy/backup-ciso.sh >> /home/deploy/backup.log 2>&1") | crontab -u deploy -

log_success "Backup cron job configured"

################################################################################
# Step 12: Setup Systemd Service for Auto-restart
################################################################################

log_info "Step 12: Setting up systemd service..."

cat > /etc/systemd/system/ciso-app.service <<EOF
[Unit]
Description=CISO App Docker Compose Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$DEPLOY_DIR
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
User=deploy
Group=deploy

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ciso-app.service
systemctl start ciso-app.service

log_success "Systemd service configured"

################################################################################
# Step 13: Display Information
################################################################################

echo ""
echo "================================================================================"
log_success "CISO App Deployment Complete!"
echo "================================================================================"
echo ""
echo -e "${GREEN}Application URL:${NC} https://$DOMAIN"
echo -e "${GREEN}API Documentation:${NC} https://$DOMAIN/api/docs"
echo -e "${GREEN}Health Check:${NC} https://$DOMAIN/health"
echo ""
echo "================================================================================"
echo -e "${BLUE}Service Management:${NC}"
echo "  - Start:   sudo systemctl start ciso-app"
echo "  - Stop:    sudo systemctl stop ciso-app"
echo "  - Restart: sudo systemctl restart ciso-app"
echo "  - Status:  sudo systemctl status ciso-app"
echo ""
echo -e "${BLUE}Docker Management:${NC}"
echo "  - View logs:    docker compose -f $DEPLOY_DIR/docker-compose.yml logs -f"
echo "  - View status:  docker compose -f $DEPLOY_DIR/docker-compose.yml ps"
echo "  - Restart:      docker compose -f $DEPLOY_DIR/docker-compose.yml restart"
echo ""
echo -e "${BLUE}Database Access:${NC}"
echo "  - Connect: docker exec -it cmmc-postgres psql -U cmmc_admin -d cmmc_platform"
echo ""
echo -e "${BLUE}Backups:${NC}"
echo "  - Location: /home/deploy/backups"
echo "  - Schedule: Daily at 2:00 AM UTC"
echo "  - Manual:   /home/deploy/backup-ciso.sh"
echo ""
echo "================================================================================"
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Create your first organization and user in the database"
echo "  2. Upload reference documents (NIST 800-171, CMMC guidelines)"
echo "  3. Configure integrations (Nessus, Splunk, etc.) in .env"
echo "  4. Test the application: curl https://$DOMAIN/health"
echo "================================================================================"
echo ""

# Save deployment info
cat > /home/deploy/deployment-info.txt <<EOF
CISO App Deployment Information
================================

Deployment Date: $(date)
Domain: $DOMAIN
Application Directory: $DEPLOY_DIR

Database Credentials:
  User: cmmc_admin
  Password: $DB_PASSWORD
  Database: cmmc_platform

MinIO Credentials:
  User: minioadmin
  Password: $MINIO_PASSWORD

JWT Secret: $JWT_SECRET

AI Provider: $AI_PROVIDER
AI Model: $AI_MODEL

Services:
  - PostgreSQL: Running on port 5432
  - Redis: Running on port 6379
  - MinIO: Running on ports 9000, 9001
  - API: Running on port 8000
  - Nginx: Running on ports 80, 443

SSL Certificate: /etc/letsencrypt/live/$DOMAIN/
EOF

chown deploy:deploy /home/deploy/deployment-info.txt
chmod 600 /home/deploy/deployment-info.txt

log_success "Deployment information saved to /home/deploy/deployment-info.txt"

exit 0
