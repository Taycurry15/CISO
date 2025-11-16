# CISO App - Quick Start Guide

**Deploy your CMMC Compliance Platform in 10 minutes**

## Prerequisites Checklist

- [ ] Hetzner VPS (Ubuntu 22.04/24.04, min 8GB RAM)
- [ ] Domain name pointing to VPS IP
- [ ] OpenAI or Anthropic API key
- [ ] Email for SSL certificates

## One-Command Deployment

```bash
# SSH into your server
ssh root@YOUR_VPS_IP

# Clone and deploy
git clone https://github.com/Taycurry15/CISO.git && \
cd CISO && \
chmod +x deploy.sh && \
sudo ./deploy.sh
```

The script will ask for:
1. **Domain name**: cmmc.yourdomain.com
2. **Email**: your@email.com (for SSL)
3. **Database password**: (create secure password)
4. **AI API key**: sk-... (OpenAI or Anthropic)

**Wait 10-15 minutes** while the script:
- ✅ Installs Docker & dependencies
- ✅ Configures firewall
- ✅ Sets up PostgreSQL, Redis, MinIO
- ✅ Obtains SSL certificate
- ✅ Deploys all services
- ✅ Configures automated backups

## Verify Deployment

```bash
# Check all services are running
docker compose ps

# Test health endpoint
curl https://your-domain.com/health

# View API docs
# Open browser: https://your-domain.com/api/docs
```

Expected output:
```
{
  "status": "healthy",
  "services": {
    "database": "connected",
    "redis": "connected",
    "ai": "configured"
  }
}
```

## Create Your First User

```bash
docker exec -it cmmc-postgres psql -U cmmc_admin -d cmmc_platform
```

```sql
-- Create organization
INSERT INTO organizations (name, cmmc_level, industry)
VALUES ('Your Company', 2, 'Defense');

-- Create admin user
INSERT INTO users (organization_id, email, name, role)
VALUES (
  (SELECT id FROM organizations LIMIT 1),
  'admin@company.com',
  'Admin User',
  'admin'
);

-- Exit
\q
```

## Essential Commands

```bash
# View logs
docker compose logs -f

# Restart services
docker compose restart

# Update app
./update.sh

# Backup database
docker exec cmmc-postgres pg_dump -U cmmc_admin cmmc_platform | gzip > backup.sql.gz

# Stop all services
docker compose down

# Start all services
docker compose up -d
```

## Access Points

| Service | URL | Credentials |
|---------|-----|-------------|
| Landing Page | https://your-domain.com | Public |
| API Docs | https://your-domain.com/api/docs | Public |
| Health Check | https://your-domain.com/health | Public |
| MinIO Console | http://YOUR_IP:9001 | See .env file |
| Database | localhost:5432 | See .env file |

## Common Tasks

### Upload Reference Documents

```bash
# Create directories
mkdir -p docs/reference/{nist,cmmc}

# Upload PDFs to docs/reference/nist/ and docs/reference/cmmc/

# Ingest documents
docker exec cmmc-api python scripts/ingest_reference_docs.py
```

### Configure Integrations

Edit `cmmc-platform/.env`:

```bash
# Nessus
NESSUS_ACCESS_KEY=your_key
NESSUS_SECRET_KEY=your_secret

# Splunk
SPLUNK_HOST=splunk.company.com
SPLUNK_TOKEN=your_token

# Azure
AZURE_TENANT_ID=your_tenant
AZURE_CLIENT_ID=your_client
AZURE_CLIENT_SECRET=your_secret
```

Restart: `docker compose restart`

### Monitor Performance

```bash
# Resource usage
docker stats

# Disk space
df -h

# Database size
docker exec cmmc-postgres psql -U cmmc_admin -d cmmc_platform -c \
  "SELECT pg_size_pretty(pg_database_size('cmmc_platform'));"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 502 Bad Gateway | `docker compose restart nginx api` |
| Database connection failed | Check DATABASE_URL in `.env` |
| SSL certificate error | `docker compose run --rm certbot renew --force-renewal` |
| High memory usage | `docker compose restart postgres redis` |
| API timeout | Increase `AI_TIMEOUT` in `cmmc-platform/.env` |

## Next Steps

1. ✅ Customize branding in `landing-page/`
2. ✅ Upload compliance documents
3. ✅ Configure integrations (Nessus, Splunk)
4. ✅ Set up monitoring alerts
5. ✅ Create additional users
6. ✅ Test backup restoration
7. ✅ Review security settings

## Support

- 📖 Full guide: `DEPLOYMENT_README.md`
- 🔧 Detailed deployment: `cmmc-platform/DEPLOYMENT_GUIDE.md`
- 🏗️ Architecture: `cmmc-platform/PROJECT_STRUCTURE.md`
- 🤖 AI setup: `cmmc-platform/AI_RAG_INTEGRATION.md`

## Update Application

```bash
cd /path/to/CISO
./update.sh
```

Or manually:
```bash
git pull
docker compose build
docker compose up -d
```

## Backup & Restore

### Automated Backups
- **Schedule**: Daily at 2:00 AM UTC
- **Location**: `/home/deploy/backups`
- **Retention**: 30 days

### Manual Backup
```bash
/home/deploy/backup-ciso.sh
```

### Restore
```bash
gunzip -c backup.sql.gz | \
  docker exec -i cmmc-postgres psql -U cmmc_admin -d cmmc_platform
```

## Cost Estimate

| Item | Cost |
|------|------|
| Hetzner CPX41 VPS | €40/month |
| Domain name | $12/year |
| SSL certificate | Free (Let's Encrypt) |
| AI API usage | $10-50/month |
| **Total** | **~€42-65/month** |

---

**Ready to deploy?** Run `./deploy.sh` and you'll be live in 10 minutes!
