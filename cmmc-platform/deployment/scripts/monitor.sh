#!/bin/bash

##############################################################################
# CMMC Compliance Platform - Health Monitoring Script
# Checks service health and sends alerts if needed
##############################################################################

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

check_service() {
    local service_name=$1
    local health_url=$2

    if curl -f -s "$health_url" > /dev/null 2>&1; then
        log_info "$service_name is healthy ✓"
        return 0
    else
        log_error "$service_name is unhealthy ✗"
        return 1
    fi
}

check_docker_service() {
    local service_name=$1

    if docker ps | grep -q "$service_name.*Up"; then
        log_info "Docker service $service_name is running ✓"
        return 0
    else
        log_error "Docker service $service_name is not running ✗"
        return 1
    fi
}

check_disk_space() {
    local threshold=90
    local usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')

    if [ "$usage" -lt "$threshold" ]; then
        log_info "Disk usage: ${usage}% ✓"
        return 0
    else
        log_error "Disk usage critical: ${usage}% (threshold: ${threshold}%) ✗"
        return 1
    fi
}

check_memory() {
    local threshold=90
    local usage=$(free | grep Mem | awk '{printf("%.0f", ($3/$2) * 100)}')

    if [ "$usage" -lt "$threshold" ]; then
        log_info "Memory usage: ${usage}% ✓"
        return 0
    else
        log_warn "Memory usage high: ${usage}% (threshold: ${threshold}%)"
        return 1
    fi
}

check_ssl_expiry() {
    if [ -f "${PROJECT_ROOT}/.env.production" ]; then
        source "${PROJECT_ROOT}/.env.production"

        if [ -z "$DOMAIN" ]; then
            log_warn "DOMAIN not set, skipping SSL check"
            return 0
        fi

        local cert_file="/etc/letsencrypt/live/${DOMAIN}/cert.pem"

        if [ -f "$cert_file" ]; then
            local expiry_date=$(openssl x509 -enddate -noout -in "$cert_file" | cut -d= -f2)
            local expiry_epoch=$(date -d "$expiry_date" +%s)
            local now_epoch=$(date +%s)
            local days_left=$(( ($expiry_epoch - $now_epoch) / 86400 ))

            if [ "$days_left" -gt 30 ]; then
                log_info "SSL certificate expires in ${days_left} days ✓"
                return 0
            elif [ "$days_left" -gt 0 ]; then
                log_warn "SSL certificate expires in ${days_left} days!"
                return 1
            else
                log_error "SSL certificate has expired!"
                return 1
            fi
        else
            log_warn "SSL certificate not found"
            return 1
        fi
    fi
}

get_container_stats() {
    log_info "Container Resource Usage:"
    docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}" | grep cmmc
}

show_recent_logs() {
    local service=$1
    local lines=${2:-20}

    log_info "Recent logs for $service:"
    docker-compose -f docker-compose.prod.yml logs --tail=$lines "$service"
}

main() {
    log_info "CMMC Platform Health Check - $(date)"
    echo "================================================================"

    cd "$PROJECT_ROOT"

    # Track failures
    failures=0

    # Check Docker services
    log_info "Checking Docker services..."
    check_docker_service "cmmc-postgres" || ((failures++))
    check_docker_service "cmmc-redis" || ((failures++))
    check_docker_service "cmmc-api" || ((failures++))
    check_docker_service "cmmc-frontend" || ((failures++))
    check_docker_service "cmmc-nginx" || ((failures++))

    echo ""

    # Check HTTP endpoints
    log_info "Checking HTTP endpoints..."
    check_service "API" "http://localhost/api/health" || ((failures++))
    check_service "Frontend" "http://localhost/health" || ((failures++))

    echo ""

    # Check system resources
    log_info "Checking system resources..."
    check_disk_space || ((failures++))
    check_memory || ((failures++))

    echo ""

    # Check SSL
    log_info "Checking SSL certificate..."
    check_ssl_expiry || ((failures++))

    echo ""

    # Show container stats
    get_container_stats

    echo ""
    echo "================================================================"

    if [ $failures -eq 0 ]; then
        log_info "All health checks passed! ✅"
        exit 0
    else
        log_error "$failures health check(s) failed! ❌"

        # If running from cron, you could send alert email here
        # Example: echo "Health checks failed" | mail -s "CMMC Platform Alert" admin@example.com

        exit 1
    fi
}

# Handle command line arguments
case "${1:-check}" in
    check)
        main
        ;;
    logs)
        show_recent_logs "${2:-api}" "${3:-50}"
        ;;
    stats)
        get_container_stats
        ;;
    *)
        echo "Usage: $0 {check|logs <service> [lines]|stats}"
        echo ""
        echo "Examples:"
        echo "  $0 check              # Run health checks"
        echo "  $0 logs api 100       # Show last 100 lines of API logs"
        echo "  $0 stats              # Show container resource usage"
        exit 1
        ;;
esac
