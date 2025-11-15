# CMMC Platform - Deployment Directory

This directory contains all files needed for production deployment to Hetzner.

## Directory Structure

```
deployment/
├── nginx/                      # Nginx configuration files
│   ├── nginx.conf             # Main Nginx config
│   ├── conf.d/
│   │   └── cmmc.conf          # Site-specific config with SSL
│   └── frontend.conf          # Frontend container nginx config
│
├── scripts/                   # Deployment and maintenance scripts
│   ├── setup-server.sh        # Initial server setup (run once)
│   ├── deploy.sh              # Deploy application
│   ├── update.sh              # Update running application
│   ├── backup.sh              # Create backups
│   ├── restore.sh             # Restore from backup
│   └── monitor.sh             # Health checks and monitoring
│
├── certbot/                   # SSL certificates (created automatically)
│   ├── conf/                  # Let's Encrypt certificates
│   └── www/                   # ACME challenge files
│
├── HETZNER_DEPLOYMENT_GUIDE.md  # Complete deployment guide
├── QUICK_START.md               # Quick start guide
└── README.md                    # This file
```

## Quick Links

- **Quick Start**: [QUICK_START.md](QUICK_START.md) - Get started in 15 minutes
- **Full Guide**: [HETZNER_DEPLOYMENT_GUIDE.md](HETZNER_DEPLOYMENT_GUIDE.md) - Complete documentation
- **Scripts Reference**: [scripts/](scripts/) - All deployment scripts

## Scripts Overview

### Setup & Deployment

```bash
# One-time server setup (as root)
./scripts/setup-server.sh

# Deploy application (as cmmc user)
./scripts/deploy.sh

# Update application
./scripts/update.sh
```

### Backup & Restore

```bash
# Create backup
./scripts/backup.sh

# List backups
./scripts/restore.sh

# Restore from backup
./scripts/restore.sh backups/cmmc_backup_20240101_120000.tar.gz
```

### Monitoring

```bash
# Run health checks
./scripts/monitor.sh check

# View logs
./scripts/monitor.sh logs api 100

# View resource stats
./scripts/monitor.sh stats
```

## Quick Reference

### View Running Services

```bash
cd /opt/cmmc-platform
docker-compose -f docker-compose.prod.yml ps
```

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f api

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 api
```

### Restart Services

```bash
# All services
docker-compose -f docker-compose.prod.yml restart

# Specific service
docker-compose -f docker-compose.prod.yml restart api
```

### Database Access

```bash
# Connect to PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U cmmc_user -d cmmc_platform

# Backup database
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U cmmc_user cmmc_platform > backup.sql

# Restore database
cat backup.sql | docker-compose -f docker-compose.prod.yml exec -T postgres \
  psql -U cmmc_user -d cmmc_platform
```

## Environment Configuration

Required environment variables in `.env.production`:

```bash
# Core
DOMAIN=your-domain.com
ENVIRONMENT=production

# Database
POSTGRES_USER=cmmc_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=cmmc_platform

# Redis
REDIS_PASSWORD=<strong-password>

# MinIO
MINIO_ROOT_USER=cmmc_minio
MINIO_ROOT_PASSWORD=<strong-password>

# Security
JWT_SECRET_KEY=<random-secret>

# AI
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

See [.env.production.example](../.env.production.example) for all options.

## SSL Certificates

SSL certificates are automatically obtained via Let's Encrypt during deployment.

**Location**: `deployment/certbot/conf/live/<DOMAIN>/`

**Renewal**: Automatic via certbot container (runs daily)

**Manual renewal**:
```bash
docker-compose -f docker-compose.prod.yml run --rm certbot renew
docker-compose -f docker-compose.prod.yml restart nginx
```

## Monitoring

### Netdata Dashboard

Access system monitoring at: `http://<SERVER_IP>:19999`

### Health Checks

Automated health checks run every 15 minutes via cron:

```bash
crontab -l | grep monitor
```

Manual health check:

```bash
./scripts/monitor.sh check
```

## Backup Strategy

### Automated Backups

- **Frequency**: Daily at 2 AM
- **Retention**: 7 days
- **Location**: `backups/`
- **Contents**: Database, files, configuration

### Offsite Backup

Recommended: Setup Hetzner Storage Box or S3 backup

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure storage
rclone config

# Sync backups
rclone sync backups/ remote:cmmc-backups/
```

## Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   docker-compose -f docker-compose.prod.yml logs
   ```

2. **Database connection errors**
   ```bash
   docker-compose -f docker-compose.prod.yml exec postgres pg_isready
   ```

3. **SSL certificate issues**
   ```bash
   docker-compose -f docker-compose.prod.yml logs certbot
   docker-compose -f docker-compose.prod.yml logs nginx
   ```

4. **Out of disk space**
   ```bash
   docker system prune -a --volumes
   find logs/ -name "*.log" -mtime +7 -delete
   ```

See [HETZNER_DEPLOYMENT_GUIDE.md](HETZNER_DEPLOYMENT_GUIDE.md) for detailed troubleshooting.

## Security

### Firewall Rules

```bash
sudo ufw status
```

Open ports:
- 22 (SSH)
- 80 (HTTP - redirects to HTTPS)
- 443 (HTTPS)

### fail2ban

```bash
sudo fail2ban-client status sshd
```

### Regular Updates

```bash
sudo apt-get update && sudo apt-get upgrade -y
```

## Support

- **Documentation**: [HETZNER_DEPLOYMENT_GUIDE.md](HETZNER_DEPLOYMENT_GUIDE.md)
- **Issues**: https://github.com/your-repo/cmmc-platform/issues
- **Email**: support@cmmc-platform.com

## License

© 2024 CMMC Compliance Platform. All rights reserved.
