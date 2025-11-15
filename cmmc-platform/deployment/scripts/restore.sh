#!/bin/bash

##############################################################################
# CMMC Compliance Platform - Restore Script
# Restores from a backup created by backup.sh
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
BACKUP_DIR="${PROJECT_ROOT}/backups"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

list_backups() {
    log_info "Available backups:"
    ls -lh "${BACKUP_DIR}"/cmmc_backup_*.tar.gz 2>/dev/null || {
        log_error "No backups found in ${BACKUP_DIR}"
        exit 1
    }
}

restore_backup() {
    local backup_file="$1"

    if [ ! -f "$backup_file" ]; then
        log_error "Backup file not found: $backup_file"
        exit 1
    fi

    log_warn "This will restore from backup and overwrite current data!"
    read -p "Are you sure you want to continue? (yes/no): " confirm

    if [ "$confirm" != "yes" ]; then
        log_info "Restore cancelled."
        exit 0
    fi

    cd "$PROJECT_ROOT"

    # Load environment variables
    if [ -f "${PROJECT_ROOT}/.env.production" ]; then
        source "${PROJECT_ROOT}/.env.production"
    fi

    # Extract backup
    log_info "Extracting backup..."
    TEMP_DIR=$(mktemp -d)
    tar xzf "$backup_file" -C "$TEMP_DIR"
    BACKUP_NAME=$(basename "$backup_file" .tar.gz)

    # Stop services
    log_info "Stopping services..."
    docker-compose -f docker-compose.prod.yml down

    # Restore database
    log_info "Restoring database..."
    docker-compose -f docker-compose.prod.yml up -d postgres
    sleep 10

    docker-compose -f docker-compose.prod.yml exec -T postgres psql \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        < "${TEMP_DIR}/${BACKUP_NAME}/database.sql"

    # Restore evidence files
    log_info "Restoring evidence files..."
    docker run --rm \
        -v cmmc-platform_evidence-data:/data \
        -v "${TEMP_DIR}/${BACKUP_NAME}":/backup \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/evidence.tar.gz -C /data"

    # Restore MinIO data
    log_info "Restoring MinIO data..."
    docker run --rm \
        -v cmmc-platform_minio-data:/data \
        -v "${TEMP_DIR}/${BACKUP_NAME}":/backup \
        alpine sh -c "rm -rf /data/* && tar xzf /backup/minio.tar.gz -C /data"

    # Clean up temp directory
    rm -rf "$TEMP_DIR"

    # Start all services
    log_info "Starting services..."
    docker-compose -f docker-compose.prod.yml up -d

    # Wait for services
    sleep 20

    # Check health
    if curl -f http://localhost/api/health &> /dev/null; then
        log_info "Restore completed successfully! ✅"
    else
        log_error "Health check failed after restore! ❌"
        exit 1
    fi

    docker-compose -f docker-compose.prod.yml ps
}

usage() {
    echo "Usage: $0 <backup_file>"
    echo ""
    echo "Example: $0 ${BACKUP_DIR}/cmmc_backup_20240101_120000.tar.gz"
    echo ""
    list_backups
}

main() {
    if [ $# -eq 0 ]; then
        usage
        exit 1
    fi

    restore_backup "$1"
}

main "$@"
