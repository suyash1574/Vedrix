#!/bin/bash
# Production setup script for Vedrix
# Run this once on a fresh server

set -e

echo "=== Vedrix Production Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

# Update system
echo "Updating system packages..."
apt update && apt upgrade -y

# Install Docker
echo "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
fi

# Install Docker Compose
echo "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    apt install -y docker-compose-plugin
fi

# Create vedrix user
echo "Creating vedrix user..."
if ! id -u vedrix &> /dev/null; then
    useradd -m -s /bin/bash vedrix
    usermod -aG docker vedrix
fi

# Create directories
echo "Creating directories..."
mkdir -p /opt/vedrix
mkdir -p /opt/vedrix/backups
mkdir -p /etc/nginx/ssl

# Copy application files
echo "Copying application files..."
cp -r . /opt/vedrix/
cd /opt/vedrix

# Create environment file
echo "Creating environment file..."
if [ ! -f backend/.env ]; then
    cp backend/.env.production backend/.env
    echo "Please edit backend/.env with your configuration!"
fi

# Validate required production configuration before starting any service.
if grep -q "CHANGE_ME_IN_PRODUCTION\|change-me-in-the-deployment-secret-manager\|your-production-secret" backend/.env; then
    echo "Set a real SECRET_KEY and CSRF_SECRET in backend/.env before starting production." >&2
    exit 1
fi
if ! grep -q '^DATABASE_URL=postgresql' backend/.env; then
    echo "DATABASE_URL must point to PostgreSQL in backend/.env." >&2
    exit 1
fi

# Set permissions
echo "Setting permissions..."
chmod 600 backend/.env
chown -R vedrix:vedrix /opt/vedrix

# Start services. The Compose migration job must complete before backend replicas start.
echo "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Setup cron for backups
echo "Setting up automated backups..."
(crontab -l 2>/dev/null || true; echo "0 2 * * * /opt/vedrix/scripts/backup.sh production") | crontab -

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Edit /opt/vedrix/backend/.env with your configuration"
echo "2. Restart services: cd /opt/vedrix && docker-compose -f docker-compose.prod.yml restart"
echo "3. Check health: curl http://localhost:8000/health"
echo ""
echo "Useful commands:"
echo "  make docker-logs    - View logs"
echo "  make db-backup      - Backup database"
echo "  make logs           - View app logs"