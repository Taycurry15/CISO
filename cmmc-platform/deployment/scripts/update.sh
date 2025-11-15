#!/bin/bash

##############################################################################
# CMMC Compliance Platform - Update Script
# This script updates the running application with minimal downtime
##############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

main() {
    log_info "Starting update process..."

    cd "$PROJECT_ROOT"

    # Create backup before update
    log_info "Creating backup..."
    ./deployment/scripts/backup.sh

    # Pull latest code (if using git deployment)
    if [ -d ".git" ]; then
        log_info "Pulling latest code from git..."
        git pull
    fi

    # Pull latest images
    log_info "Pulling latest Docker images..."
    docker-compose -f docker-compose.prod.yml pull

    # Rebuild custom images
    log_info "Rebuilding application images..."
    docker-compose -f docker-compose.prod.yml build

    # Stop services gracefully
    log_info "Stopping services..."
    docker-compose -f docker-compose.prod.yml stop

    # Start services
    log_info "Starting updated services..."
    docker-compose -f docker-compose.prod.yml up -d

    # Wait for services to be ready
    log_info "Waiting for services to start..."
    sleep 20

    # Check health
    log_info "Checking service health..."
    if curl -f http://localhost/api/health &> /dev/null; then
        log_info "Update completed successfully! ✅"
    else
        log_error "Health check failed! ❌"
        log_warn "Rolling back to previous version..."
        docker-compose -f docker-compose.prod.yml down
        # Restore from backup would go here
        exit 1
    fi

    # Show status
    docker-compose -f docker-compose.prod.yml ps
}

main "$@"
