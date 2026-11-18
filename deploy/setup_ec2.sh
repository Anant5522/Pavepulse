#!/usr/bin/env bash
# ==============================================================================
# PavePulse Automated Deployment Script for Ubuntu 22.04 / 24.04 on AWS EC2
# Run as: bash deploy/setup_ec2.sh
# ==============================================================================

set -e

APP_DIR="/home/ubuntu/pavepulse"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/pavepulse"

echo "=================================================="
echo "🚀 Starting PavePulse Cloud Deployment on AWS EC2"
echo "=================================================="

# 1. Update system packages
echo "[1/8] Updating Ubuntu system packages..."
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y

# 2. Install required packages
echo "[2/8] Installing Python, MySQL Server, Nginx, and build dependencies..."
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    default-libmysqlclient-dev \
    build-essential \
    mysql-server \
    nginx \
    git \
    curl \
    ufw

# 3. Configure MySQL
echo "[3/8] Configuring MySQL database & user..."
sudo systemctl enable --now mysql

# Run MySQL setup script
sudo mysql < "$APP_DIR/deploy/mysql_setup.sql"

# 4. Create Python Virtual Environment & Install Dependencies
echo "[4/8] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

"$VENV_DIR/bin/pip" install --upgrade pip setuptools wheel
"$VENV_DIR/bin/pip" install -r "$APP_DIR/requirements.txt"

# 5. Configure Production Environment Variables (.env)
echo "[5/8] Generating production environment configuration..."
if [ ! -f "$APP_DIR/.env" ]; then
    RANDOM_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat <<EOF > "$APP_DIR/.env"
SECRET_KEY=$RANDOM_SECRET
FLASK_ENV=production
DEBUG=False
PORT=5000
DATABASE_URL=mysql+pymysql://pavepulse_user:StrongPavePulse2026!@localhost/pavepulse_db
S3_BUCKET=
AWS_DEFAULT_REGION=ap-south-1
MAX_CONTENT_LENGTH=10485760
EOF
    echo "Created default production .env with secure random secret key."
fi

# 6. Setup Logging and File Permissions
echo "[6/8] Configuring log directories and permissions..."
sudo mkdir -p "$LOG_DIR"
sudo chown -R ubuntu:www-data "$LOG_DIR"
sudo chmod -R 775 "$LOG_DIR"

mkdir -p "$APP_DIR/app/static/uploads"
sudo chown -R ubuntu:www-data "$APP_DIR/app/static/uploads"
sudo chmod -R 775 "$APP_DIR/app/static/uploads"

# 7. Configure and Enable Systemd Service
echo "[7/8] Configuring systemd service..."
sudo cp "$APP_DIR/deploy/pavepulse.service" /etc/systemd/system/pavepulse.service
sudo systemctl daemon-reload
sudo systemctl enable pavepulse.service
sudo systemctl restart pavepulse.service

# 8. Configure Nginx Reverse Proxy & Firewall
echo "[8/8] Configuring Nginx web server & UFW firewall..."
sudo rm -f /etc/nginx/sites-enabled/default
sudo cp "$APP_DIR/deploy/pavepulse_nginx.conf" /etc/nginx/sites-available/pavepulse
sudo ln -sf /etc/nginx/sites-available/pavepulse /etc/nginx/sites-enabled/pavepulse

sudo nginx -t
sudo systemctl restart nginx

# Firewall settings (Allow SSH and Web)
sudo ufw allow OpenSSH || true
sudo ufw allow 'Nginx Full' || true
echo "y" | sudo ufw enable || true

# Get Public IP
PUBLIC_IP=$(curl -s http://checkip.amazonaws.com || echo "your-ec2-public-ip")

echo "=================================================="
echo "✅ PavePulse deployed successfully!"
echo "🌐 Access your app at: http://$PUBLIC_IP"
echo "🔑 Demo Logins:"
echo "   - Admin:   admin@pavepulse.org   / Admin@123"
echo "   - Officer: officer@pavepulse.org / Officer@123"
echo "   - Citizen: citizen@pavepulse.org / Citizen@123"
echo "=================================================="
