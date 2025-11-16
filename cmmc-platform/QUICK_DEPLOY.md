# Quick Deploy Reference

**30-minute quick reference for experienced admins**

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for detailed instructions.

---

## 1. Server Setup (5 min)

```bash
# Create Hetzner CPX41: Ubuntu 24.04, add SSH key, configure firewall
# Point DNS: cmmc.yourdomain.com → server IP

ssh root@SERVER_IP
apt update && apt upgrade -y
hostnamectl set-hostname cmmc-production
```

## 2. Install Stack (10 min)

```bash
# Python 3.12
apt install -y python3.12 python3.12-venv python3.12-dev python3-pip build-essential git

# PostgreSQL 16 + pgvector
sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget -qO- https://www.postgresql.org/media/keys/ACCC4CF8.asc | apt-key add -
apt update && apt install -y postgresql-16 postgresql-server-dev-16
cd /tmp && git clone https://github.com/pgvector/pgvector.git && cd pgvector && make && make install

# Redis + Nginx
apt install -y redis-server nginx certbot python3-certbot-nginx

# UFW
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw enable
```

## 3. Configure Database (3 min)

```bash
sudo -u postgres psql <<EOF
CREATE USER cmmc_admin WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE cmmc_platform OWNER cmmc_admin;
\c cmmc_platform
CREATE EXTENSION "uuid-ossp";
CREATE EXTENSION "pgcrypto";
CREATE EXTENSION "vector";
\q
EOF
```

## 4. Deploy App (5 min)

```bash
# Create user
adduser deploy && usermod -aG sudo deploy

# Clone
su - deploy
git clone https://github.com/Taycurry15/CISO.git
cd CISO/cmmc-platform

# Python env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # Edit: DATABASE_URL, AI_API_KEY, DOMAIN

# Storage
mkdir -p storage/{evidence,exports} logs
```

## 5. Initialize Database (2 min)

```bash
psql -U cmmc_admin -d cmmc_platform -h localhost -f database/schema.sql

# Create org & user
psql -U cmmc_admin -d cmmc_platform -h localhost <<EOF
INSERT INTO organizations (name, cmmc_level) VALUES ('Your Company', 2);
INSERT INTO users (organization_id, email, name, role)
VALUES ((SELECT id FROM organizations LIMIT 1), 'admin@company.com', 'Admin', 'admin');
EOF
```

## 6. SSL + Nginx (3 min)

```bash
# SSL
systemctl stop nginx
certbot certonly --standalone -d cmmc.yourdomain.com --email you@email.com --agree-tos

# Nginx config (see DEPLOYMENT_GUIDE.md for full config)
nano /etc/nginx/sites-available/cmmc-platform
ln -s /etc/nginx/sites-available/cmmc-platform /etc/nginx/sites-enabled/
nginx -t && systemctl start nginx
```

## 7. Systemd Service (2 min)

```bash
# Create /etc/systemd/system/cmmc-api.service (see guide for full config)
sudo nano /etc/systemd/system/cmmc-api.service

systemctl daemon-reload
systemctl enable cmmc-api
systemctl start cmmc-api
systemctl status cmmc-api
```

## 8. Verify

```bash
# Health check
curl https://cmmc.yourdomain.com/health

# AI services
curl https://cmmc.yourdomain.com/health/ai

# View logs
journalctl -u cmmc-api -f
```

## 9. Optional: Ingest Docs

```bash
# Download PDFs manually to docs/reference/{nist,cmmc}/
python scripts/ingest_reference_docs.py
python scripts/test_rag_search.py --interactive
```

---

## Quick Commands

```bash
# Restart services
sudo systemctl restart cmmc-api nginx postgresql redis

# View logs
sudo journalctl -u cmmc-api -n 100 -f
tail -f /home/deploy/apps/CISO/cmmc-platform/logs/api.log

# Database
psql -U cmmc_admin -d cmmc_platform -h localhost

# Update app
cd /home/deploy/apps/CISO/cmmc-platform
git pull && source venv/bin/activate && pip install -r requirements.txt
sudo systemctl restart cmmc-api

# Backup database
pg_dump -U cmmc_admin -d cmmc_platform -h localhost | gzip > backup_$(date +%Y%m%d).sql.gz
```

---

## Environment Variables (Critical)

```bash
DATABASE_URL=postgresql://cmmc_admin:PASSWORD@localhost:5432/cmmc_platform
AI_PROVIDER=openai
AI_MODEL=gpt-4-turbo-preview
AI_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
DOMAIN=cmmc.yourdomain.com
JWT_SECRET=$(openssl rand -hex 32)
ENVIRONMENT=production
```

---

## Cost Estimate

- **Hetzner CPX41**: €40/month
- **Domain**: $12/year
- **SSL**: Free (Let's Encrypt)
- **AI API**: ~$10-20/month (depends on usage)

**Total: ~€42-50/month**

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 502 Bad Gateway | `systemctl restart cmmc-api` |
| Database connection | Check DATABASE_URL in .env |
| SSL error | `certbot renew --force-renewal` |
| High memory | `systemctl restart postgresql redis` |
| AI timeout | Reduce RAG_TOP_K and AI_MAX_TOKENS in .env |

---

**Full guide**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
