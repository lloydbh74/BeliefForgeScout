# Deployment Guide - Hetzner VPS

Complete guide for deploying the Social Reply Bot to a Hetzner VPS using Docker.

## Prerequisites

### Local Machine
- Docker installed (for testing)
- SSH client
- Git
- Access to .env secrets

### Hetzner VPS
- **Minimum Specs**: 2 vCPU, 4GB RAM, 40GB SSD (CX21 or better)
- **Recommended**: 2 vCPU, 8GB RAM, 80GB SSD (CX31)
- **OS**: Ubuntu 22.04 LTS (recommended)
- **Network**: Public IPv4 address
- **SSH Access**: Root or sudo user

### Estimated Costs
- **VPS**: €5-10/month (Hetzner CX21-CX31)
- **OpenRouter API**: $10-30/month
- **Total**: €20-40/month (~$22-44)

## Quick Start (Automated)

### 1. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your credentials
nano .env
```

Required variables:
```bash
POSTGRES_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_redis_password_here
OPENROUTER_API_KEY=sk-or-v1-your-key-here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
JWT_SECRET=your-super-secret-jwt-key-min-32-chars
```

### 2. Configure VPS Connection

```bash
# Set VPS connection details
export VPS_HOST=your-vps-ip-address
export VPS_USER=root
export VPS_PORT=22
```

### 3. Run Deployment Script

```bash
# Make script executable
chmod +x deploy-hetzner.sh

# Run deployment
./deploy-hetzner.sh
```

Select option **1** for full deployment.

### 4. Verify Deployment

```bash
# SSH into VPS
ssh root@your-vps-ip

# Check services
cd /opt/social-reply-bot
docker-compose ps

# Check logs
docker-compose logs -f
```

## Manual Deployment

### Step 1: Set Up Hetzner VPS

1. **Create VPS** on Hetzner Cloud Console
   - Select datacenter (e.g., Nuremberg)
   - Choose Ubuntu 22.04 LTS
   - Select CX21 or higher
   - Add SSH key

2. **Initial VPS Setup**

```bash
# SSH into VPS
ssh root@your-vps-ip

# Update system
apt-get update && apt-get upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

3. **Configure Firewall**

```bash
# Install UFW
apt-get install -y ufw

# Configure rules
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # HTTP
ufw allow 443/tcp   # HTTPS

# Enable firewall
ufw --force enable

# Check status
ufw status
```

### Step 2: Deploy Application

1. **Create Deployment Directory**

```bash
# On VPS
mkdir -p /opt/social-reply-bot
cd /opt/social-reply-bot
```

2. **Transfer Files**

```bash
# On local machine
# Create tarball (excluding data and .git)
tar czf social-reply-bot.tar.gz \
    --exclude='data' \
    --exclude='.git' \
    --exclude='__pycache__' \
    .

# Copy to VPS
scp social-reply-bot.tar.gz root@your-vps-ip:/opt/social-reply-bot/

# Copy .env separately
scp .env root@your-vps-ip:/opt/social-reply-bot/
```

3. **Extract and Prepare**

```bash
# On VPS
cd /opt/social-reply-bot
tar xzf social-reply-bot.tar.gz
rm social-reply-bot.tar.gz

# Create directories
mkdir -p data/logs data/db config
chown -R 1000:1000 data config
```

### Step 3: Start Services

```bash
# On VPS
cd /opt/social-reply-bot

# Pull base images
docker-compose pull

# Build custom images
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

### Step 4: Set Up Twitter Authentication

The bot needs authenticated Twitter session cookies:

**Option A: Use Browser Extension (Recommended)**

1. Install "EditThisCookie" or "Cookie Editor" in your browser
2. Login to Twitter/X
3. Export cookies as JSON
4. Copy to VPS:

```bash
# On local machine
scp cookies.json root@your-vps-ip:/opt/social-reply-bot/data/

# On VPS
cd /opt/social-reply-bot
docker-compose restart bot
```

**Option B: Manual Browser Authentication**

```bash
# On VPS - Run bot interactively once
docker-compose run --rm bot python src/auth/manual_login.py

# Follow prompts to login
# Cookies will be saved automatically
```

### Step 5: Configure Domain & SSL (Optional)

1. **Point Domain to VPS**
   - Add A record: `bot.beliefforge.com` → `your-vps-ip`

2. **Install SSL Certificate**

```bash
# On VPS
apt-get install -y certbot python3-certbot-nginx

# Stop nginx temporarily
cd /opt/social-reply-bot
docker-compose stop nginx

# Obtain certificate
certbot certonly --standalone \
    -d bot.beliefforge.com \
    --email lloyd@beliefforge.com \
    --agree-tos

# Copy certificates
mkdir -p nginx/ssl
cp /etc/letsencrypt/live/bot.beliefforge.com/fullchain.pem nginx/ssl/
cp /etc/letsencrypt/live/bot.beliefforge.com/privkey.pem nginx/ssl/

# Start nginx
docker-compose start nginx

# Set up auto-renewal
(crontab -l 2>/dev/null; echo "0 3 * * * certbot renew --quiet --post-hook 'docker-compose -f /opt/social-reply-bot/docker-compose.yml restart nginx'") | crontab -
```

3. **Update Nginx Config**

Edit `nginx/nginx.conf` to use SSL certificates.

## Service Management

### Start/Stop Services

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart bot

# View status
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f bot

# Last 100 lines
docker-compose logs --tail=100

# Since timestamp
docker-compose logs --since=2024-01-07T10:00:00
```

### Update Application

```bash
# On local machine - create new deployment
tar czf social-reply-bot.tar.gz --exclude='data' .
scp social-reply-bot.tar.gz root@your-vps-ip:/tmp/

# On VPS
cd /opt/social-reply-bot

# Backup current
cp -r . /opt/backups/social-reply-bot-$(date +%Y%m%d-%H%M%S)

# Extract update
tar xzf /tmp/social-reply-bot.tar.gz
rm /tmp/social-reply-bot.tar.gz

# Rebuild and restart
docker-compose build
docker-compose up -d
```

### Database Backup

```bash
# Manual backup
docker exec social_reply_db pg_dump -U social_reply social_reply > backup-$(date +%Y%m%d).sql

# Restore from backup
docker exec -i social_reply_db psql -U social_reply social_reply < backup-20240107.sql

# Automated daily backup (add to crontab)
0 2 * * * docker exec social_reply_db pg_dump -U social_reply social_reply > /opt/backups/db-backup-$(date +\%Y\%m\%d).sql
```

## Monitoring

### Health Checks

```bash
# Check service health
docker-compose ps

# Check container logs for errors
docker-compose logs --tail=50 | grep -i error

# Check disk space
df -h

# Check memory usage
free -h

# Check Docker resource usage
docker stats
```

### Access Dashboard

Once deployed with SSL:
- Dashboard: `https://bot.beliefforge.com`
- Login: `admin@beliefforge.com` / `changeme123` (change this!)

### Telegram Commands

Send to your Telegram bot:
- `/status` - Bot status
- `/queue` - Pending replies
- `/stop` - Emergency stop
- `/start` - Start bot

## Troubleshooting

### Bot Not Starting

```bash
# Check logs
docker-compose logs bot

# Check environment variables
docker-compose exec bot env | grep OPENROUTER

# Restart with fresh state
docker-compose down
docker-compose up -d
```

### Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose logs postgres

# Test connection
docker exec -it social_reply_db psql -U social_reply -d social_reply -c "SELECT 1;"

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

### Twitter Authentication Expired

```bash
# Re-authenticate
docker-compose run --rm bot python src/auth/manual_login.py

# Or copy fresh cookies
scp cookies.json root@your-vps-ip:/opt/social-reply-bot/data/
docker-compose restart bot
```

### Out of Memory

```bash
# Check memory usage
docker stats

# Reduce resource usage in docker-compose.yml:
services:
  bot:
    deploy:
      resources:
        limits:
          memory: 2G

# Upgrade VPS tier if needed
```

### Disk Space Full

```bash
# Check usage
df -h

# Clean old Docker images
docker system prune -a

# Clean old logs
find /opt/social-reply-bot/data/logs -name "*.log" -mtime +30 -delete

# Clean old backups
find /opt/backups -mtime +90 -delete
```

## Performance Optimization

### Optimize Docker Images

```bash
# Use multi-stage builds (already in Dockerfile)
# Prune unused images regularly
docker system prune -af --volumes

# Set log rotation
docker-compose -f docker-compose.yml config services.bot.logging
```

### PostgreSQL Tuning

```bash
# Edit postgresql.conf for better performance
docker exec -it social_reply_db bash
apt-get update && apt-get install -y nano
nano /var/lib/postgresql/data/postgresql.conf

# Recommended settings for 4GB RAM:
shared_buffers = 1GB
effective_cache_size = 3GB
maintenance_work_mem = 256MB
work_mem = 16MB
```

## Security Best Practices

1. **Change default passwords** in `.env`
2. **Disable root SSH** after setting up sudo user
3. **Enable SSH key authentication** only
4. **Keep system updated**: `apt-get update && apt-get upgrade`
5. **Monitor logs** for suspicious activity
6. **Use fail2ban** to prevent brute force attacks
7. **Regular backups** (automated via cron)
8. **Limit Docker container resources**

## Costs Breakdown (Monthly)

| Service | Cost (EUR) | Cost (USD) |
|---------|-----------|-----------|
| Hetzner CX21 VPS | €5.83 | ~$6 |
| OpenRouter API | €10-30 | $10-30 |
| Domain (optional) | €1 | ~$1 |
| **Total** | **€16-36** | **$17-37** |

## Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Review troubleshooting section above
3. Open issue on GitHub
4. Contact: lloyd@beliefforge.com

---

**Last Updated**: 2025-01-07
**Author**: Lloyd
**Project**: Social Reply Bot for Belief Forge
