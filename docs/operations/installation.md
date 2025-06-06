# Production Installation Guide

Complete guide for installing and configuring the Browser Automation Framework in production environments.

## 🎯 Installation Overview

### System Requirements

| Component | Minimum | Recommended | Enterprise |
|-----------|---------|-------------|------------|
| **CPU** | 4 cores | 8 cores | 16+ cores |
| **Memory** | 8GB RAM | 16GB RAM | 32+ GB RAM |
| **Storage** | 50GB SSD | 100GB SSD | 500+ GB SSD |
| **Network** | 100 Mbps | 1 Gbps | 10+ Gbps |
| **OS** | Ubuntu 20.04+ | Ubuntu 22.04 LTS | RHEL 8+ |

### Supported Deployment Options

- **Docker Compose** - Single-node deployment with containers
- **Kubernetes** - Multi-node orchestrated deployment
- **Virtual Machines** - Traditional server deployment
- **Cloud Platforms** - AWS, GCP, Azure managed services

### Pre-Installation Checklist

- [ ] System meets minimum requirements
- [ ] Network connectivity verified
- [ ] DNS records configured
- [ ] SSL certificates obtained
- [ ] Database server prepared
- [ ] Redis server prepared
- [ ] LLM API keys obtained
- [ ] Monitoring infrastructure ready

## 🐳 Docker Installation

### Prerequisites

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker --version
docker-compose --version
```

### Production Docker Setup

```bash
# Create application directory
sudo mkdir -p /opt/automation-framework
cd /opt/automation-framework

# Download production configuration
curl -O https://raw.githubusercontent.com/your-org/browser-automation-framework/main/docker-compose.prod.yml
curl -O https://raw.githubusercontent.com/your-org/browser-automation-framework/main/.env.production.example

# Configure environment
cp .env.production.example .env.production
sudo nano .env.production
```

### Environment Configuration

```bash
# .env.production
# Application Settings
ENV=production
DEBUG=false
LOG_LEVEL=INFO
SECRET_KEY=your-super-secret-key-here
JWT_SECRET=your-jwt-secret-here

# Database Configuration
DATABASE_URL=postgresql://automation_user:secure_password@db:5432/automation_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your-redis-password

# LLM Configuration
LLM_API_KEY=your-llm-api-key
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_TIMEOUT=30

# Browser Configuration
BROWSER_POOL_SIZE=10
BROWSER_TIMEOUT=60
BROWSER_HEADLESS=true

# Security Configuration
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
METRICS_PORT=9090

# Performance Configuration
MAX_CONCURRENT_WORKFLOWS=50
WORKER_CONCURRENCY=10
TASK_TIMEOUT=300
```

### Start Production Services

```bash
# Start all services
docker-compose -f docker-compose.prod.yml up -d

# Verify services are running
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f api
docker-compose -f docker-compose.prod.yml logs -f worker

# Run database migrations
docker-compose -f docker-compose.prod.yml exec api python -m alembic upgrade head

# Create initial admin user
docker-compose -f docker-compose.prod.yml exec api python -m src.cli create-admin-user
```

## ☸️ Kubernetes Installation

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installation
kubectl version --client
helm version
```

### Namespace Setup

```bash
# Create namespace
kubectl create namespace automation-framework

# Set as default namespace
kubectl config set-context --current --namespace=automation-framework
```

### Secrets Configuration

```bash
# Create secrets from environment file
kubectl create secret generic app-secrets \
  --from-env-file=.env.production \
  --namespace=automation-framework

# Create TLS secret for ingress
kubectl create secret tls api-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key \
  --namespace=automation-framework
```

### Database Setup

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: automation-framework
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15
        env:
        - name: POSTGRES_DB
          value: automation_prod
        - name: POSTGRES_USER
          value: automation_user
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: DB_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 4Gi
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 100Gi

---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: automation-framework
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  type: ClusterIP
```

### Redis Setup

```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: automation-framework
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--appendonly", "yes", "--requirepass", "$(REDIS_PASSWORD)"]
        env:
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: REDIS_PASSWORD
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        resources:
          requests:
            cpu: 250m
            memory: 512Mi
          limits:
            cpu: 1
            memory: 2Gi
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: automation-framework
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi

---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: automation-framework
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  type: ClusterIP
```

### Application Deployment

```bash
# Deploy database and Redis
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# Wait for database to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# Deploy application
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/worker-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Run database migrations
kubectl exec -it deployment/api-server -- python -m alembic upgrade head

# Verify deployment
kubectl get pods
kubectl get services
kubectl get ingress
```

## 🖥️ VM Installation

### System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    postgresql-client \
    redis-tools \
    nginx \
    supervisor \
    git \
    curl \
    wget \
    unzip

# Install Node.js (for Playwright)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Create application user
sudo useradd -m -s /bin/bash automation
sudo usermod -aG sudo automation
```

### Application Setup

```bash
# Switch to application user
sudo su - automation

# Create application directory
mkdir -p /home/automation/app
cd /home/automation/app

# Clone repository
git clone https://github.com/your-org/browser-automation-framework.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium

# Copy configuration
cp .env.example .env.production
nano .env.production
```

### Database Setup

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE automation_prod;
CREATE USER automation_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE automation_prod TO automation_user;
ALTER USER automation_user CREATEDB;
\q
EOF

# Run migrations
cd /home/automation/app
source venv/bin/activate
python -m alembic upgrade head
```

### Redis Setup

```bash
# Install Redis
sudo apt install -y redis-server

# Configure Redis
sudo nano /etc/redis/redis.conf
# Add/modify:
# requirepass your-redis-password
# maxmemory 2gb
# maxmemory-policy allkeys-lru

# Restart Redis
sudo systemctl restart redis-server
sudo systemctl enable redis-server
```

### Supervisor Configuration

```bash
# Create supervisor configuration
sudo nano /etc/supervisor/conf.d/automation-framework.conf
```

```ini
[program:automation-api]
command=/home/automation/app/venv/bin/python -m src.main
directory=/home/automation/app
user=automation
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/automation/api.log
environment=ENV="production"

[program:automation-worker]
command=/home/automation/app/venv/bin/python -m src.worker
directory=/home/automation/app
user=automation
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/automation/worker.log
environment=ENV="production"
numprocs=2
process_name=%(program_name)s_%(process_num)02d
```

```bash
# Create log directory
sudo mkdir -p /var/log/automation
sudo chown automation:automation /var/log/automation

# Update supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all

# Check status
sudo supervisorctl status
```

### Nginx Configuration

```bash
# Create Nginx configuration
sudo nano /etc/nginx/sites-available/automation-framework
```

```nginx
upstream automation_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/ssl/certs/automation-framework.crt;
    ssl_certificate_key /etc/ssl/private/automation-framework.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    location / {
        proxy_pass http://automation_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://automation_api/health;
        access_log off;
    }

    location /metrics {
        proxy_pass http://automation_api/metrics;
        allow 127.0.0.1;
        allow 10.0.0.0/8;
        deny all;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/automation-framework /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
sudo systemctl enable nginx
```

## 🔒 Security Setup

### SSL Certificate

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d api.your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run
```

### Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw enable
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Allow specific IPs for admin access
sudo ufw allow from YOUR_ADMIN_IP to any port 22

# Check status
sudo ufw status verbose
```

## 📊 Monitoring Setup

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "automation_rules.yml"

scrape_configs:
  - job_name: 'automation-framework'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### Install Monitoring Stack

```bash
# Install Prometheus
wget https://github.com/prometheus/prometheus/releases/latest/download/prometheus-*.linux-amd64.tar.gz
tar xvfz prometheus-*.linux-amd64.tar.gz
sudo mv prometheus-*/prometheus /usr/local/bin/
sudo mv prometheus-*/promtool /usr/local/bin/

# Install Node Exporter
wget https://github.com/prometheus/node_exporter/releases/latest/download/node_exporter-*.linux-amd64.tar.gz
tar xvfz node_exporter-*.linux-amd64.tar.gz
sudo mv node_exporter-*/node_exporter /usr/local/bin/

# Create systemd services
sudo nano /etc/systemd/system/prometheus.service
sudo nano /etc/systemd/system/node-exporter.service

# Start services
sudo systemctl daemon-reload
sudo systemctl enable prometheus node-exporter
sudo systemctl start prometheus node-exporter
```

## ✅ Installation Verification

### Health Checks

```bash
# Check application health
curl -f http://localhost:8000/health

# Check database connection
curl -f http://localhost:8000/health/db

# Check Redis connection
curl -f http://localhost:8000/health/redis

# Check LLM provider
curl -f http://localhost:8000/health/llm

# Run test workflow
curl -X POST http://localhost:8000/api/v1/workflows/test \
  -H "Content-Type: application/json" \
  -d '{"test": true}'
```

### Performance Verification

```bash
# Load test with Apache Bench
ab -n 100 -c 10 http://localhost:8000/health

# Monitor resource usage
htop
iotop
nethogs

# Check logs
tail -f /var/log/automation/api.log
tail -f /var/log/automation/worker.log
```

## 🔧 Post-Installation

### Backup Setup

```bash
# Create backup script
sudo nano /usr/local/bin/backup-automation.sh
sudo chmod +x /usr/local/bin/backup-automation.sh

# Schedule backups
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-automation.sh
```

### Log Rotation

```bash
# Configure logrotate
sudo nano /etc/logrotate.d/automation-framework
```

```
/var/log/automation/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 automation automation
    postrotate
        supervisorctl restart automation-api automation-worker
    endscript
}
```

## 🔗 Next Steps

- **[Configuration Guide](configuration.md)** - Detailed configuration options
- **[Security Guide](security.md)** - Implement security best practices
- **[Monitoring Guide](monitoring.md)** - Set up comprehensive monitoring
- **[Backup & Recovery](backup-recovery.md)** - Configure backup and disaster recovery
