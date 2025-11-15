#!/bin/bash

##############################################################################
# CMMC Compliance Platform - Hetzner Server Setup Script
# This script sets up a fresh Hetzner server for the first time
##############################################################################

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

main() {
    log_info "Setting up Hetzner server for CMMC Platform..."

    # Update system
    log_info "Updating system packages..."
    apt-get update
    apt-get upgrade -y

    # Install essential packages
    log_info "Installing essential packages..."
    apt-get install -y \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        git \
        htop \
        vim \
        ufw \
        fail2ban

    # Install Docker
    log_info "Installing Docker..."
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com -o get-docker.sh
        sh get-docker.sh
        rm get-docker.sh

        # Enable Docker service
        systemctl enable docker
        systemctl start docker

        log_info "Docker installed successfully!"
    else
        log_info "Docker is already installed"
    fi

    # Install Docker Compose
    log_info "Installing Docker Compose..."
    if ! docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d\" -f4)
        curl -L "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose

        log_info "Docker Compose installed successfully!"
    else
        log_info "Docker Compose is already installed"
    fi

    # Setup firewall
    log_info "Configuring firewall..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow ssh
    ufw allow 80/tcp
    ufw allow 443/tcp
    echo "y" | ufw enable

    log_info "Firewall configured!"

    # Configure fail2ban
    log_info "Configuring fail2ban..."
    systemctl enable fail2ban
    systemctl start fail2ban

    # Create application user
    log_info "Creating application user..."
    if ! id -u cmmc &>/dev/null; then
        useradd -m -s /bin/bash cmmc
        usermod -aG docker cmmc
        log_info "User 'cmmc' created"
    else
        log_info "User 'cmmc' already exists"
    fi

    # Setup swap (recommended for smaller servers)
    log_info "Setting up swap space..."
    if [ ! -f /swapfile ]; then
        fallocate -l 4G /swapfile
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        log_info "4GB swap created"
    else
        log_info "Swap already exists"
    fi

    # Optimize system settings
    log_info "Optimizing system settings..."
    cat >> /etc/sysctl.conf <<EOF

# CMMC Platform optimizations
vm.swappiness=10
vm.vfs_cache_pressure=50
net.core.somaxconn=65535
net.ipv4.tcp_max_syn_backlog=8192
net.ipv4.ip_local_port_range=1024 65535
EOF
    sysctl -p

    # Setup log rotation
    log_info "Setting up log rotation..."
    cat > /etc/logrotate.d/cmmc-platform <<EOF
/opt/cmmc-platform/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 cmmc cmmc
    sharedscripts
}
EOF

    # Create directory structure
    log_info "Creating application directories..."
    mkdir -p /opt/cmmc-platform
    chown -R cmmc:cmmc /opt/cmmc-platform

    # Setup automated backups (cron)
    log_info "Setting up automated backups..."
    (crontab -u cmmc -l 2>/dev/null; echo "0 2 * * * cd /opt/cmmc-platform && ./deployment/scripts/backup.sh >> /opt/cmmc-platform/logs/backup.log 2>&1") | crontab -u cmmc -

    # Install monitoring tools
    log_info "Installing monitoring tools..."
    apt-get install -y netdata

    # Configure netdata
    systemctl enable netdata
    systemctl start netdata

    log_info "Server setup completed successfully! ✅"
    echo ""
    log_info "Next steps:"
    log_info "1. Switch to cmmc user: su - cmmc"
    log_info "2. Clone repository: git clone <your-repo> /opt/cmmc-platform"
    log_info "3. Create .env.production from .env.production.example"
    log_info "4. Run deployment: cd /opt/cmmc-platform && ./deployment/scripts/deploy.sh"
    echo ""
    log_info "Monitoring available at: http://your-server-ip:19999"
}

main "$@"
