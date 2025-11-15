#!/bin/bash

##############################################################################
# CMMC Compliance Platform - Hetzner Deployment Script
# This script deploys the application to a Hetzner server
##############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="${PROJECT_ROOT}/.env.production"

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_requirements() {
    log_info "Checking requirements..."

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi

    # Check if .env.production exists
    if [ ! -f "$ENV_FILE" ]; then
        log_error ".env.production file not found. Please create it from .env.production.example"
        exit 1
    fi

    log_info "All requirements met!"
}

setup_directories() {
    log_info "Setting up directories..."

    mkdir -p "${PROJECT_ROOT}/logs/nginx"
    mkdir -p "${PROJECT_ROOT}/logs/api"
    mkdir -p "${PROJECT_ROOT}/logs/celery"
    mkdir -p "${PROJECT_ROOT}/backups"
    mkdir -p "${PROJECT_ROOT}/deployment/certbot/conf"
    mkdir -p "${PROJECT_ROOT}/deployment/certbot/www"

    log_info "Directories created!"
}

setup_ssl() {
    log_info "Setting up SSL certificates..."

    # Load domain from env file
    source "$ENV_FILE"

    if [ -z "$DOMAIN" ]; then
        log_error "DOMAIN not set in .env.production"
        exit 1
    fi

    # Check if certificates already exist
    if [ -d "${PROJECT_ROOT}/deployment/certbot/conf/live/${DOMAIN}" ]; then
        log_info "SSL certificates already exist for ${DOMAIN}"
        return
    fi

    log_info "Obtaining SSL certificate for ${DOMAIN}..."

    # Start nginx with HTTP only first
    docker-compose -f docker-compose.prod.yml up -d nginx

    # Wait for nginx to start
    sleep 5

    # Get certificate
    docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "${SMTP_FROM_EMAIL:-admin@${DOMAIN}}" \
        --agree-tos \
        --no-eff-email \
        -d "${DOMAIN}"

    # Update nginx config with actual domain
    sed -i "s/DOMAIN/${DOMAIN}/g" "${PROJECT_ROOT}/deployment/nginx/conf.d/cmmc.conf"

    # Restart nginx with SSL
    docker-compose -f docker-compose.prod.yml restart nginx

    log_info "SSL certificates obtained successfully!"
}

pull_images() {
    log_info "Pulling latest Docker images..."

    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml pull

    log_info "Images pulled successfully!"
}

build_images() {
    log_info "Building application images..."

    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml build --no-cache

    log_info "Images built successfully!"
}

run_migrations() {
    log_info "Running database migrations..."

    cd "$PROJECT_ROOT"

    # Wait for database to be ready
    docker-compose -f docker-compose.prod.yml up -d postgres
    sleep 10

    # Migrations are automatically run via init scripts in docker-compose
    log_info "Database migrations completed!"
}

start_services() {
    log_info "Starting services..."

    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.prod.yml up -d

    log_info "Services started successfully!"
}

check_health() {
    log_info "Checking service health..."

    # Wait for services to start
    sleep 15

    # Check API health
    if curl -f http://localhost/api/health &> /dev/null; then
        log_info "API is healthy!"
    else
        log_warn "API health check failed. Check logs with: docker-compose -f docker-compose.prod.yml logs api"
    fi

    # Check frontend health
    if curl -f http://localhost/health &> /dev/null; then
        log_info "Frontend is healthy!"
    else
        log_warn "Frontend health check failed. Check logs with: docker-compose -f docker-compose.prod.yml logs frontend"
    fi
}

show_status() {
    log_info "Deployment Status:"
    echo ""
    docker-compose -f docker-compose.prod.yml ps
    echo ""
    log_info "Application is running at: https://$(grep DOMAIN $ENV_FILE | cut -d '=' -f2)"
    log_info "View logs: docker-compose -f docker-compose.prod.yml logs -f"
}

main() {
    log_info "Starting CMMC Platform deployment to Hetzner..."
    echo ""

    check_requirements
    setup_directories
    pull_images
    build_images
    run_migrations
    start_services
    setup_ssl
    check_health
    show_status

    echo ""
    log_info "Deployment completed successfully! 🎉"
}

# Run main function
main "$@"
