# CMMC Compliance Platform - Complete Hetzner Deployment Guide

## Quick Start

```bash
# 1. Setup server (run as root)
curl -fsSL https://raw.githubusercontent.com/your-repo/cmmc-platform/main/deployment/scripts/setup-server.sh | bash

# 2. Clone and configure (as cmmc user)
su - cmmc
git clone https://github.com/your-repo/cmmc-platform.git /opt/cmmc-platform
cd /opt/cmmc-platform
cp .env.production.example .env.production
vim .env.production  # Configure your settings

# 3. Deploy
./deployment/scripts/deploy.sh
```

## Deployment Files Reference

### Docker Compose Files
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production environment with optimizations

### Scripts (`deployment/scripts/`)
- `setup-server.sh` - Initial Hetzner server setup (Docker, firewall, etc.)
- `deploy.sh` - Deploy application to production
- `update.sh` - Update running application with zero-downtime
- `backup.sh` - Create complete backup (DB + files)
- `restore.sh` - Restore from backup
- `monitor.sh` - Health checks and monitoring

### Configuration (`deployment/nginx/`)
- `nginx.conf` - Main Nginx configuration
- `conf.d/cmmc.conf` - Site-specific configuration with SSL
- `frontend.conf` - Frontend container nginx config

### Environment Files
- `.env.production.example` - Template for production environment
- `.env.production` - Your actual production configuration (create from example)

## Estimated Costs (Hetzner)

| Server Type | CPU | RAM | Storage | Price/month | Use Case |
|-------------|-----|-----|---------|-------------|----------|
| CX31 | 2 vCPU | 8 GB | 80 GB | €9.50 | Development/Testing |
| CX41 | 4 vCPU | 16 GB | 160 GB | €17.90 | Small Production (< 100 users) |
| CX51 | 8 vCPU | 32 GB | 240 GB | €37.90 | Production (< 500 users) |
| CCX32 | 8 vCPU | 32 GB | 240 GB | €43.50 | High Performance |

**Additional costs:**
- Backups: €1.90/month (20% of server cost)
- Storage Box (1 TB): €4.40/month
- Load Balancer (optional): €5.83/month

## Architecture

```
Internet → Cloudflare (optional) → Hetzner Firewall → Nginx (SSL) → Backend Services
```

**Services:**
1. **Nginx** - Reverse proxy with SSL termination
2. **Frontend** - React application (Vite build)
3. **API** - FastAPI backend (Gunicorn + Uvicorn workers)
4. **PostgreSQL** - Database with pgvector extension
5. **Redis** - Caching and Celery message broker
6. **MinIO** - S3-compatible object storage
7. **Celery Worker** - Background task processing
8. **Celery Beat** - Scheduled tasks
9. **Certbot** - Automatic SSL certificate renewal

## Deployment Checklist

### Before Deployment
- [ ] Hetzner server created and accessible
- [ ] Domain DNS configured (A record pointing to server IP)
- [ ] SSH key added to server
- [ ] OpenAI API key obtained (if using AI features)
- [ ] Anthropic API key obtained (if using Claude)
- [ ] SMTP credentials for email (optional)

### During Deployment
- [ ] Server setup completed (`setup-server.sh`)
- [ ] Repository cloned
- [ ] `.env.production` configured with all required values
- [ ] Strong passwords generated for database, Redis, MinIO
- [ ] JWT secret key generated
- [ ] Domain name updated in nginx config
- [ ] Deployment script executed successfully
- [ ] SSL certificate obtained
- [ ] All services health checks passed

### After Deployment
- [ ] Application accessible via HTTPS
- [ ] Create first admin user
- [ ] Test file upload functionality
- [ ] Verify email sending (if configured)
- [ ] Setup automated backups
- [ ] Configure monitoring alerts
- [ ] Test backup and restore process
- [ ] Document credentials in secure location

## Post-Deployment Configuration

### 1. Create Admin User

SSH into server and run:

```bash
cd /opt/cmmc-platform
docker-compose -f docker-compose.prod.yml exec api python -c "
from user_api import create_admin_user
create_admin_user(
    email='admin@your-domain.com',
    password='ChangeMe123!',
    full_name='Admin User'
)
"
```

### 2. Configure Automated Backups

Backups are automatically scheduled via cron. Verify:

```bash
crontab -l | grep backup
```

### 3. Setup Monitoring

Add health check cron:

```bash
crontab -e
# Add:
*/15 * * * * cd /opt/cmmc-platform && ./deployment/scripts/monitor.sh check >> logs/health-check.log 2>&1
```

### 4. Configure Log Rotation

Already configured during server setup. Verify:

```bash
cat /etc/logrotate.d/cmmc-platform
```

## Maintenance Operations

### View Logs

```bash
# Real-time logs for all services
docker-compose -f docker-compose.prod.yml logs -f

# API logs only
docker-compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api

# Search for errors
docker-compose -f docker-compose.prod.yml logs api | grep -i error
```

### Restart Services

```bash
# Restart all services
docker-compose -f docker-compose.prod.yml restart

# Restart specific service
docker-compose -f docker-compose.prod.yml restart api

# Full restart (stops and starts)
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d
```

### Update Application

```bash
cd /opt/cmmc-platform
./deployment/scripts/update.sh
```

### Database Operations

```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U cmmc_user -d cmmc_platform

# Backup database manually
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U cmmc_user cmmc_platform > backup.sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U cmmc_user cmmc_platform < backup.sql

# Run vacuum
docker-compose -f docker-compose.prod.yml exec postgres psql -U cmmc_user -d cmmc_platform -c "VACUUM ANALYZE;"
```

### Check Resource Usage

```bash
# Container stats
docker stats

# Disk usage
df -h
docker system df

# Memory usage
free -h

# Monitor script
./deployment/scripts/monitor.sh stats
```

## Security Hardening

### 1. SSH Hardening

```bash
# Edit SSH config
sudo vim /etc/ssh/sshd_config

# Recommended settings:
PermitRootLogin prohibit-password
PasswordAuthentication no
PubkeyAuthentication yes
X11Forwarding no
MaxAuthTries 3
ClientAliveInterval 300
ClientAliveCountMax 2

# Restart SSH
sudo systemctl restart sshd
```

### 2. Automatic Security Updates

```bash
# Install unattended-upgrades
sudo apt-get install unattended-upgrades

# Enable automatic security updates
sudo dpkg-reconfigure --priority=low unattended-upgrades
```

### 3. Fail2Ban Configuration

```bash
# Check Fail2Ban status
sudo fail2ban-client status

# Check SSH jail
sudo fail2ban-client status sshd

# Unban IP if needed
sudo fail2ban-client unban <IP_ADDRESS>
```

### 4. Regular Updates

```bash
# Update system packages (monthly recommended)
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get autoremove -y

# Update Docker images
cd /opt/cmmc-platform
docker-compose -f docker-compose.prod.yml pull
./deployment/scripts/update.sh
```

## Backup Strategy

### Automated Daily Backups

Configured via cron (2 AM daily):
- Database dump (PostgreSQL)
- Evidence files
- MinIO data
- Configuration files

Retention: 7 days

### Offsite Backup Setup (Hetzner Storage Box)

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure for Hetzner Storage Box
rclone config
# Name: hetzner-box
# Type: sftp
# Host: <username>.your-storagebox.de
# User: <username>
# Password: <password>

# Test connection
rclone ls hetzner-box:

# Add to backup script
# Edit deployment/scripts/backup.sh and add:
# rclone copy ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz hetzner-box:cmmc-backups/
```

### Backup to S3 (Alternative)

```bash
# Configure rclone for S3
rclone config
# Name: s3-backup
# Type: s3
# Provider: AWS
# Access Key ID: <your-key>
# Secret Access Key: <your-secret>

# Sync backups to S3
rclone sync backups/ s3-backup:your-bucket/cmmc-backups/
```

## Monitoring and Alerts

### Netdata Dashboard

Access at: `http://<SERVER_IP>:19999`

Features:
- Real-time system metrics
- Container resource usage
- Network traffic
- Disk I/O
- Custom alerts

### Email Alerts for Health Checks

Edit `deployment/scripts/monitor.sh` and uncomment email notification:

```bash
# At the end of main() function
if [ $failures -ne 0 ]; then
    echo "Health checks failed on $(hostname)" | mail -s "CMMC Platform Alert" admin@your-domain.com
fi
```

Install mail utility:

```bash
sudo apt-get install mailutils
```

### Uptime Monitoring (External)

Recommended services:
- **UptimeRobot** (free tier available)
- **Pingdom**
- **StatusCake**

Monitor endpoints:
- `https://your-domain.com/health`
- `https://your-domain.com/api/health`

## Troubleshooting

### Common Issues

**1. "Connection refused" errors**

```bash
# Check if services are running
docker-compose -f docker-compose.prod.yml ps

# Check firewall
sudo ufw status

# Check nginx logs
docker-compose -f docker-compose.prod.yml logs nginx
```

**2. Database connection errors**

```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# Check credentials in .env.production
cat .env.production | grep POSTGRES

# Restart database
docker-compose -f docker-compose.prod.yml restart postgres
```

**3. Out of disk space**

```bash
# Check disk usage
df -h

# Clean Docker system
docker system prune -a --volumes

# Remove old logs
find logs/ -name "*.log" -mtime +7 -delete

# Remove old backups
find backups/ -name "*.tar.gz" -mtime +14 -delete
```

**4. High memory usage**

```bash
# Check container memory usage
docker stats

# Reduce Celery workers
# Edit docker-compose.prod.yml:
# Change --concurrency=4 to --concurrency=2

# Restart services
docker-compose -f docker-compose.prod.yml restart celery-worker
```

**5. SSL certificate issues**

```bash
# Check certificate status
docker-compose -f docker-compose.prod.yml run --rm certbot certificates

# Renew manually
docker-compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal
docker-compose -f docker-compose.prod.yml restart nginx

# Debug certificate issues
docker-compose -f docker-compose.prod.yml logs certbot
```

## Performance Optimization

### Database Tuning

Edit PostgreSQL configuration for production workload:

```bash
# Increase shared_buffers (25% of RAM)
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U cmmc_user -d cmmc_platform \
  -c "ALTER SYSTEM SET shared_buffers = '4GB';"

# Increase effective_cache_size (50% of RAM)
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U cmmc_user -d cmmc_platform \
  -c "ALTER SYSTEM SET effective_cache_size = '8GB';"

# Restart PostgreSQL
docker-compose -f docker-compose.prod.yml restart postgres
```

### Redis Optimization

Monitor cache effectiveness:

```bash
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO stats
```

### Application Scaling

For high traffic, scale services:

```bash
# Scale Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4

# Scale API workers (edit Dockerfile.prod gunicorn --workers)
```

## Cost Optimization

### 1. Use Hetzner's Free Backups

Enable automated snapshots in Hetzner Cloud Console (20% of server cost).

### 2. CDN for Static Assets

Use Cloudflare (free tier) for static asset caching.

### 3. Compression

Already enabled in Nginx config:
- Gzip compression for text files
- Brotli compression (optional)

### 4. Database Optimization

Regular maintenance:
```bash
# Weekly vacuum
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U cmmc_user -d cmmc_platform -c "VACUUM ANALYZE;"

# Reindex (monthly)
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U cmmc_user -d cmmc_platform -c "REINDEX DATABASE cmmc_platform;"
```

## Migration from Development to Production

```bash
# 1. Export development database
docker-compose exec postgres pg_dump -U cmmc_user cmmc_platform > dev_backup.sql

# 2. Copy to production server
scp dev_backup.sql cmmc@production-server:/tmp/

# 3. Import to production
cat /tmp/dev_backup.sql | docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U cmmc_user cmmc_platform

# 4. Copy evidence files
rsync -avz ./data/evidence/ cmmc@production-server:/opt/cmmc-platform/data/evidence/
```

## Support

For deployment issues:
1. Check logs: `./deployment/scripts/monitor.sh logs api`
2. Run health checks: `./deployment/scripts/monitor.sh check`
3. Review this guide
4. Check GitHub issues: https://github.com/your-repo/cmmc-platform/issues
5. Contact support: support@cmmc-platform.com

## License

© 2024 CMMC Compliance Platform. All rights reserved.
