#!/bin/bash

###############################################################################
# Social Reply Bot - Hetzner VPS Deployment Script
#
# This script automates the deployment of the Social Reply Bot to a Hetzner VPS
#
# Usage:
#   1. Make executable: chmod +x deploy-hetzner.sh
#   2. Run: ./deploy-hetzner.sh
#
# Prerequisites:
#   - SSH access to your Hetzner VPS
#   - Docker and Docker Compose installed on VPS
#   - .env file configured with secrets
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
VPS_HOST="${VPS_HOST:-your-vps-ip}"
VPS_USER="${VPS_USER:-root}"
VPS_PORT="${VPS_PORT:-22}"
DEPLOY_DIR="/opt/social-reply-bot"
BACKUP_DIR="/opt/backups/social-reply-bot"

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

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if .env exists
    if [ ! -f .env ]; then
        log_error ".env file not found. Copy .env.example to .env and configure it."
        exit 1
    fi

    # Check if SSH key exists
    if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
        log_warn "No SSH key found. You'll need to enter password for each SSH connection."
    fi

    log_info "Prerequisites check passed."
}

setup_vps() {
    log_info "Setting up VPS environment..."

    ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << 'ENDSSH'
        # Update system
        apt-get update
        apt-get upgrade -y

        # Install Docker if not present
        if ! command -v docker &> /dev/null; then
            echo "Installing Docker..."
            curl -fsSL https://get.docker.com -o get-docker.sh
            sh get-docker.sh
            rm get-docker.sh
        fi

        # Install Docker Compose if not present
        if ! command -v docker-compose &> /dev/null; then
            echo "Installing Docker Compose..."
            curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
            chmod +x /usr/local/bin/docker-compose
        fi

        # Create deployment directory
        mkdir -p /opt/social-reply-bot
        mkdir -p /opt/backups/social-reply-bot

        # Install UFW firewall
        apt-get install -y ufw

        # Configure firewall
        ufw --force enable
        ufw default deny incoming
        ufw default allow outgoing
        ufw allow 22/tcp    # SSH
        ufw allow 80/tcp    # HTTP
        ufw allow 443/tcp   # HTTPS

        echo "VPS setup complete."
ENDSSH

    log_info "VPS environment setup complete."
}

backup_existing() {
    log_info "Creating backup of existing deployment..."

    ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << ENDSSH
        if [ -d $DEPLOY_DIR ]; then
            BACKUP_NAME="backup-\$(date +%Y%m%d-%H%M%S)"
            mkdir -p $BACKUP_DIR/\$BACKUP_NAME

            # Backup docker-compose.yml and .env
            cp $DEPLOY_DIR/docker-compose.yml $BACKUP_DIR/\$BACKUP_NAME/ 2>/dev/null || true
            cp $DEPLOY_DIR/.env $BACKUP_DIR/\$BACKUP_NAME/ 2>/dev/null || true

            # Backup data directory
            cp -r $DEPLOY_DIR/data $BACKUP_DIR/\$BACKUP_NAME/ 2>/dev/null || true

            echo "Backup created: $BACKUP_DIR/\$BACKUP_NAME"
        fi
ENDSSH

    log_info "Backup complete."
}

deploy_code() {
    log_info "Deploying code to VPS..."

    # Create tarball of project (excluding data and .git)
    tar czf social-reply-bot.tar.gz \
        --exclude='data' \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.env' \
        .

    # Copy tarball to VPS
    scp -P $VPS_PORT social-reply-bot.tar.gz $VPS_USER@$VPS_HOST:/tmp/

    # Extract on VPS
    ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << ENDSSH
        cd $DEPLOY_DIR
        tar xzf /tmp/social-reply-bot.tar.gz
        rm /tmp/social-reply-bot.tar.gz

        # Create necessary directories
        mkdir -p data/logs data/db config
        chown -R 1000:1000 data config
ENDSSH

    # Copy .env file separately (contains secrets)
    scp -P $VPS_PORT .env $VPS_USER@$VPS_HOST:$DEPLOY_DIR/.env

    # Clean up local tarball
    rm social-reply-bot.tar.gz

    log_info "Code deployment complete."
}

start_services() {
    log_info "Starting Docker services..."

    ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << ENDSSH
        cd $DEPLOY_DIR

        # Pull latest images
        docker-compose pull

        # Build custom images
        docker-compose build

        # Start services
        docker-compose up -d

        # Wait for services to be healthy
        echo "Waiting for services to start..."
        sleep 10

        # Show status
        docker-compose ps
ENDSSH

    log_info "Services started."
}

show_status() {
    log_info "Checking service status..."

    ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << ENDSSH
        cd $DEPLOY_DIR
        docker-compose ps
        echo ""
        echo "Recent logs:"
        docker-compose logs --tail=20
ENDSSH
}

setup_ssl() {
    log_info "Setting up SSL with Let's Encrypt..."

    read -p "Enter your domain name (e.g., bot.beliefforge.com): " DOMAIN
    read -p "Enter your email for Let's Encrypt notifications: " EMAIL

    if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
        log_warn "Domain or email not provided. Skipping SSL setup."
        return
    fi

    ssh -p $VPS_PORT $VPS_USER@$VPS_HOST << ENDSSH
        # Install certbot
        apt-get install -y certbot python3-certbot-nginx

        # Stop nginx temporarily
        cd $DEPLOY_DIR
        docker-compose stop nginx

        # Obtain certificate
        certbot certonly --standalone -d $DOMAIN --email $EMAIL --agree-tos --non-interactive

        # Copy certificates to nginx directory
        mkdir -p $DEPLOY_DIR/nginx/ssl
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem $DEPLOY_DIR/nginx/ssl/
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem $DEPLOY_DIR/nginx/ssl/

        # Restart nginx
        docker-compose start nginx

        # Set up auto-renewal
        (crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'docker-compose -f $DEPLOY_DIR/docker-compose.yml restart nginx'") | crontab -
ENDSSH

    log_info "SSL setup complete."
}

show_logs() {
    log_info "Showing live logs (Ctrl+C to exit)..."
    ssh -p $VPS_PORT $VPS_USER@$VPS_HOST "cd $DEPLOY_DIR && docker-compose logs -f"
}

# Main menu
show_menu() {
    echo ""
    echo "========================================"
    echo "  Social Reply Bot - Hetzner Deployment"
    echo "========================================"
    echo "1. Full deployment (setup + deploy + start)"
    echo "2. Setup VPS environment only"
    echo "3. Deploy code only"
    echo "4. Start/restart services"
    echo "5. Stop services"
    echo "6. Show status"
    echo "7. Show logs"
    echo "8. Setup SSL certificate"
    echo "9. Create backup"
    echo "10. SSH into VPS"
    echo "0. Exit"
    echo "========================================"
}

# Main script
main() {
    check_prerequisites

    while true; do
        show_menu
        read -p "Select option: " choice

        case $choice in
            1)
                setup_vps
                backup_existing
                deploy_code
                start_services
                show_status
                log_info "Full deployment complete!"
                ;;
            2)
                setup_vps
                ;;
            3)
                backup_existing
                deploy_code
                ;;
            4)
                start_services
                show_status
                ;;
            5)
                log_info "Stopping services..."
                ssh -p $VPS_PORT $VPS_USER@$VPS_HOST "cd $DEPLOY_DIR && docker-compose down"
                ;;
            6)
                show_status
                ;;
            7)
                show_logs
                ;;
            8)
                setup_ssl
                ;;
            9)
                backup_existing
                ;;
            10)
                log_info "Opening SSH connection..."
                ssh -p $VPS_PORT $VPS_USER@$VPS_HOST
                ;;
            0)
                log_info "Exiting."
                exit 0
                ;;
            *)
                log_error "Invalid option."
                ;;
        esac
    done
}

# Run main function
main
