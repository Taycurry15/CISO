#!/bin/bash

##############################################################################
# CMMC Compliance Platform - Backup Script
# Creates backups of database, uploaded files, and configuration
##############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="cmmc_backup_${TIMESTAMP}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Load environment variables
if [ -f "${PROJECT_ROOT}/.env.production" ]; then
    source "${PROJECT_ROOT}/.env.production"
fi

main() {
    log_info "Starting backup process..."

    # Create backup directory
    mkdir -p "${BACKUP_DIR}/${BACKUP_NAME}"

    cd "$PROJECT_ROOT"

    # Backup database
    log_info "Backing up PostgreSQL database..."
    docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump \
        -U "${POSTGRES_USER}" \
        -d "${POSTGRES_DB}" \
        --clean \
        --if-exists \
        > "${BACKUP_DIR}/${BACKUP_NAME}/database.sql"

    # Backup volumes (evidence files, etc.)
    log_info "Backing up evidence files..."
    docker run --rm \
        -v cmmc-platform_evidence-data:/data \
        -v "${BACKUP_DIR}/${BACKUP_NAME}":/backup \
        alpine tar czf /backup/evidence.tar.gz -C /data .

    # Backup MinIO data
    log_info "Backing up MinIO data..."
    docker run --rm \
        -v cmmc-platform_minio-data:/data \
        -v "${BACKUP_DIR}/${BACKUP_NAME}":/backup \
        alpine tar czf /backup/minio.tar.gz -C /data .

    # Backup configuration files
    log_info "Backing up configuration files..."
    cp "${PROJECT_ROOT}/.env.production" "${BACKUP_DIR}/${BACKUP_NAME}/"
    cp -r "${PROJECT_ROOT}/deployment/nginx" "${BACKUP_DIR}/${BACKUP_NAME}/"

    # Create a compressed archive of everything
    log_info "Creating compressed archive..."
    cd "${BACKUP_DIR}"
    tar czf "${BACKUP_NAME}.tar.gz" "${BACKUP_NAME}"
    rm -rf "${BACKUP_NAME}"

    # Get backup size
    BACKUP_SIZE=$(du -h "${BACKUP_NAME}.tar.gz" | cut -f1)

    log_info "Backup completed successfully!"
    log_info "Backup file: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz (${BACKUP_SIZE})"

    # Clean up old backups (keep last 7 days)
    log_info "Cleaning up old backups..."
    find "${BACKUP_DIR}" -name "cmmc_backup_*.tar.gz" -mtime +7 -delete

    # List current backups
    log_info "Available backups:"
    ls -lh "${BACKUP_DIR}"/cmmc_backup_*.tar.gz 2>/dev/null || log_warn "No backups found"
}

main "$@"
