# CMMC Platform - Quick Start Guide for Hetzner

## 1. Server Requirements

- Hetzner VPS: CX41 or better (4 vCPU, 16GB RAM, 160GB SSD)
- Ubuntu 22.04 LTS
- Domain name pointed to server IP

## 2. Initial Setup (5 minutes)

```bash
# SSH into server as root
ssh root@<YOUR_SERVER_IP>

# Run automated setup
curl -fsSL https://raw.githubusercontent.com/your-repo/cmmc-platform/main/deployment/scripts/setup-server.sh -o setup.sh
chmod +x setup.sh
./setup.sh
```

## 3. Application Deployment (10 minutes)

```bash
# Switch to cmmc user
su - cmmc

# Clone repository
cd /opt
sudo chown cmmc:cmmc /opt
git clone https://github.com/your-repo/cmmc-platform.git
cd cmmc-platform

# Configure environment
cp .env.production.example .env.production
nano .env.production
```

### Required Configuration

Edit `.env.production` and set:

```bash
# Domain
DOMAIN=your-domain.com

# Generate strong passwords (use: openssl rand -base64 32)
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
MINIO_ROOT_PASSWORD=<strong-password>
JWT_SECRET_KEY=<random-secret>

# AI API Keys
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

## 4. Deploy

```bash
./deployment/scripts/deploy.sh
```

The script will:
- ✅ Build Docker images
- ✅ Start all services
- ✅ Run database migrations
- ✅ Obtain SSL certificate
- ✅ Perform health checks

## 5. Access Your Application

- **Frontend**: https://your-domain.com
- **API Docs**: https://your-domain.com/api/docs
- **Monitoring**: http://<SERVER_IP>:19999

## Daily Operations

### View Status
```bash
cd /opt/cmmc-platform
docker-compose -f docker-compose.prod.yml ps
```

### View Logs
```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

### Create Backup
```bash
./deployment/scripts/backup.sh
```

### Update Application
```bash
./deployment/scripts/update.sh
```

### Health Check
```bash
./deployment/scripts/monitor.sh check
```

## Troubleshooting

### Services not starting?
```bash
docker-compose -f docker-compose.prod.yml logs
```

### SSL issues?
```bash
docker-compose -f docker-compose.prod.yml logs certbot
docker-compose -f docker-compose.prod.yml logs nginx
```

### Database issues?
```bash
docker-compose -f docker-compose.prod.yml exec postgres pg_isready
docker-compose -f docker-compose.prod.yml logs postgres
```

## Emergency Contacts

- Documentation: `/opt/cmmc-platform/deployment/HETZNER_DEPLOYMENT_GUIDE.md`
- Support: support@cmmc-platform.com
- GitHub Issues: https://github.com/your-repo/cmmc-platform/issues

## Monthly Costs (Hetzner)

| Item | Cost |
|------|------|
| CX41 Server | €17.90 |
| Backups (20%) | €3.58 |
| Storage Box (1TB) | €4.40 |
| **Total** | **€25.88/month** |

## Security Reminders

- ✅ Use strong, unique passwords
- ✅ Enable 2FA on Hetzner account
- ✅ Regularly update system: `sudo apt-get update && sudo apt-get upgrade`
- ✅ Monitor logs: `./deployment/scripts/monitor.sh check`
- ✅ Test backups monthly: `./deployment/scripts/restore.sh <backup-file>`
- ✅ Keep API keys secure and rotate periodically

---

**Need help?** Read the full guide: `deployment/HETZNER_DEPLOYMENT_GUIDE.md`
