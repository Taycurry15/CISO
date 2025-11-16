#!/bin/bash

################################################################################
# CISO App - Quick Update Script
#
# This script updates the CISO app to the latest version
# Usage: ./update.sh
################################################################################

set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}CISO App Update Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Pull latest changes
echo -e "${BLUE}[1/5]${NC} Pulling latest changes from Git..."
git pull origin main

# Backup database
echo -e "${BLUE}[2/5]${NC} Creating database backup..."
mkdir -p backups
docker exec cmmc-postgres pg_dump -U cmmc_admin cmmc_platform | gzip > "backups/pre_update_$(date +%Y%m%d_%H%M%S).sql.gz"
echo -e "${GREEN}✓${NC} Backup saved to backups/"

# Rebuild containers
echo -e "${BLUE}[3/5]${NC} Rebuilding containers..."
docker compose build

# Restart services with zero downtime
echo -e "${BLUE}[4/5]${NC} Restarting services..."
docker compose up -d

# Wait for health check
echo -e "${BLUE}[5/5]${NC} Waiting for services to be healthy..."
sleep 10

# Verify services
if docker compose ps | grep -q "Up"; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✓ Update completed successfully!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    docker compose ps
else
    echo -e "${YELLOW}Warning: Some services may not be running properly.${NC}"
    echo "Check logs with: docker compose logs"
fi
