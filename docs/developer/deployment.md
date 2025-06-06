# Deployment Guide

Comprehensive guide for deploying the Browser Automation Framework to production environments with high availability, scalability, and security.

## 🎯 Deployment Overview

### Supported Platforms

- **Docker/Kubernetes** - Recommended for production
- **AWS ECS/EKS** - Cloud-native deployment
- **Google Cloud Run/GKE** - Serverless and container options
- **Azure Container Instances/AKS** - Microsoft cloud platform
- **Traditional VMs** - On-premises or cloud VMs

### Architecture Patterns

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Application Load Balancer]
    end
    
    subgraph "Application Tier"
        API1[API Server 1]
        API2[API Server 2]
        API3[API Server 3]
    end
    
    subgraph "Worker Tier"
        W1[Worker Node 1]
        W2[Worker Node 2]
        W3[Worker Node 3]
    end
    
    subgraph "Data Tier"
        DB[(PostgreSQL)]
        REDIS[(Redis Cluster)]
        S3[(Object Storage)]
    end
    
    subgraph "Browser Tier"
        BP1[Browser Pool 1]
        BP2[Browser Pool 2]
        BP3[Browser Pool 3]
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    
    API1 --> W1
    API2 --> W2
    API3 --> W3
    
    W1 --> DB
    W2 --> REDIS
    W3 --> S3
    
    W1 --> BP1
    W2 --> BP2
    W3 --> BP3
```

## 🐳 Docker Deployment

### Production Docker Compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    image: automation-framework:latest
    ports:
      - "8000:8000"
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/automation
      - REDIS_URL=redis://redis:6379
      - LLM_API_KEY=${LLM_API_KEY}
    depends_on:
      - db
      - redis
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  worker:
    image: automation-framework:latest
    command: python -m src.worker
    environment:
      - ENV=production
      - DATABASE_URL=postgresql://user:pass@db:5432/automation
      - REDIS_URL=redis://redis:6379
      - BROWSER_POOL_SIZE=5
    depends_on:
      - db
      - redis
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '4'
          memory: 4G

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=automation
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api

volumes:
  postgres_data:
  redis_data:
```

### Building Production Image

```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    gnupg \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN pip install playwright && playwright install chromium

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Start application
CMD ["python", "-m", "src.main"]
```

```bash
# Build and deploy
docker build -f Dockerfile.prod -t automation-framework:latest .
docker-compose -f docker-compose.prod.yml up -d
```

## ☸️ Kubernetes Deployment

### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: automation-framework

---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: automation-framework
data:
  ENV: "production"
  LOG_LEVEL: "INFO"
  BROWSER_POOL_SIZE: "5"
  MAX_CONCURRENT_WORKFLOWS: "10"
```

### Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
  namespace: automation-framework
type: Opaque
data:
  DATABASE_URL: <base64-encoded-database-url>
  LLM_API_KEY: <base64-encoded-llm-api-key>
  REDIS_URL: <base64-encoded-redis-url>
```

### API Deployment

```yaml
# k8s/api-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-server
  namespace: automation-framework
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api-server
  template:
    metadata:
      labels:
        app: api-server
    spec:
      containers:
      - name: api
        image: automation-framework:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: DATABASE_URL
        - name: LLM_API_KEY
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: LLM_API_KEY
        envFrom:
        - configMapRef:
            name: app-config
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: api-service
  namespace: automation-framework
spec:
  selector:
    app: api-server
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Worker Deployment

```yaml
# k8s/worker-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: worker
  namespace: automation-framework
spec:
  replicas: 2
  selector:
    matchLabels:
      app: worker
  template:
    metadata:
      labels:
        app: worker
    spec:
      containers:
      - name: worker
        image: automation-framework:latest
        command: ["python", "-m", "src.worker"]
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: DATABASE_URL
        envFrom:
        - configMapRef:
            name: app-config
        resources:
          requests:
            cpu: 1
            memory: 2Gi
          limits:
            cpu: 4
            memory: 4Gi
        securityContext:
          runAsNonRoot: true
          runAsUser: 1000
```

### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api-ingress
  namespace: automation-framework
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
spec:
  tls:
  - hosts:
    - api.automation-framework.com
    secretName: api-tls
  rules:
  - host: api.automation-framework.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api-service
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n automation-framework
kubectl get services -n automation-framework
kubectl get ingress -n automation-framework

# View logs
kubectl logs -f deployment/api-server -n automation-framework
kubectl logs -f deployment/worker -n automation-framework
```

## ☁️ Cloud Platform Deployments

### AWS ECS Deployment

```json
{
  "family": "automation-framework",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::account:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "api-server",
      "image": "your-account.dkr.ecr.region.amazonaws.com/automation-framework:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENV",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:automation/database-url"
        },
        {
          "name": "LLM_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:automation/llm-api-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/automation-framework",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### Google Cloud Run Deployment

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: automation-framework
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
        run.googleapis.com/execution-environment: gen2
    spec:
      containerConcurrency: 10
      timeoutSeconds: 300
      containers:
      - image: gcr.io/project-id/automation-framework:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENV
          value: production
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: database-url
              key: url
        resources:
          limits:
            cpu: 2
            memory: 2Gi
          requests:
            cpu: 1
            memory: 1Gi
```

```bash
# Deploy to Cloud Run
gcloud run deploy automation-framework \
  --image gcr.io/project-id/automation-framework:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --max-instances 10 \
  --memory 2Gi \
  --cpu 2
```

## 🔧 Environment Configuration

### Production Environment Variables

```bash
# .env.production
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Database
DATABASE_URL=postgresql://user:password@db-host:5432/automation_prod
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30

# Redis
REDIS_URL=redis://redis-host:6379/0
REDIS_POOL_SIZE=10

# LLM Configuration
LLM_API_KEY=your-production-api-key
LLM_PROVIDER=openai
LLM_MODEL=gpt-4
LLM_TIMEOUT=30
LLM_MAX_RETRIES=3

# Browser Configuration
BROWSER_POOL_SIZE=10
BROWSER_TIMEOUT=60
BROWSER_HEADLESS=true

# Security
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret
CORS_ORIGINS=https://your-domain.com

# Monitoring
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
LOG_AGGREGATION_ENABLED=true

# Performance
MAX_CONCURRENT_WORKFLOWS=20
WORKER_CONCURRENCY=5
TASK_TIMEOUT=300
```

### Configuration Management

```python
# src/config/production.py
from pydantic import BaseSettings

class ProductionConfig(BaseSettings):
    """Production configuration."""
    
    # Application
    env: str = "production"
    debug: bool = False
    log_level: str = "INFO"
    
    # Database
    database_url: str
    database_pool_size: int = 20
    database_max_overflow: int = 30
    
    # Redis
    redis_url: str
    redis_pool_size: int = 10
    
    # Security
    secret_key: str
    jwt_secret: str
    cors_origins: list = ["https://your-domain.com"]
    
    # Performance
    max_concurrent_workflows: int = 20
    worker_concurrency: int = 5
    
    class Config:
        env_file = ".env.production"
```

## 📊 Monitoring & Observability

### Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'automation-framework'
    static_configs:
      - targets: ['api-server:8000']
    metrics_path: /metrics
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Browser Automation Framework",
    "panels": [
      {
        "title": "Workflow Execution Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(workflow_executions_total[5m])",
            "legendFormat": "Executions/sec"
          }
        ]
      },
      {
        "title": "Success Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(workflow_executions_success_total[5m]) / rate(workflow_executions_total[5m]) * 100",
            "legendFormat": "Success %"
          }
        ]
      }
    ]
  }
}
```

### Health Checks

```python
# src/api/health.py
from fastapi import APIRouter, HTTPException
from src.infrastructure.health import HealthChecker

router = APIRouter()
health_checker = HealthChecker()

@router.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "timestamp": datetime.utcnow()}

@router.get("/ready")
async def readiness_check():
    """Readiness check with dependencies."""
    checks = await health_checker.check_all()
    
    if not all(check["healthy"] for check in checks.values()):
        raise HTTPException(status_code=503, detail="Service not ready")
    
    return {"status": "ready", "checks": checks}
```

## 🔒 Security Configuration

### SSL/TLS Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.automation-framework.com;
    
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    
    location / {
        proxy_pass http://api-server:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Security Headers

```python
# src/api/middleware/security.py
from fastapi import Request
from fastapi.responses import Response

async def security_headers_middleware(request: Request, call_next):
    """Add security headers to responses."""
    response = await call_next(request)
    
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response
```

## 🚀 Deployment Automation

### CI/CD Pipeline

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Build Docker image
      run: |
        docker build -f Dockerfile.prod -t automation-framework:${{ github.sha }} .
        
    - name: Push to registry
      run: |
        echo ${{ secrets.DOCKER_PASSWORD }} | docker login -u ${{ secrets.DOCKER_USERNAME }} --password-stdin
        docker push automation-framework:${{ github.sha }}
        
    - name: Deploy to Kubernetes
      run: |
        kubectl set image deployment/api-server api=automation-framework:${{ github.sha }}
        kubectl rollout status deployment/api-server
```

### Blue-Green Deployment

```bash
#!/bin/bash
# scripts/blue-green-deploy.sh

NEW_VERSION=$1
CURRENT_COLOR=$(kubectl get service api-service -o jsonpath='{.spec.selector.color}')
NEW_COLOR=$([ "$CURRENT_COLOR" = "blue" ] && echo "green" || echo "blue")

echo "Deploying version $NEW_VERSION to $NEW_COLOR environment"

# Update deployment with new version
kubectl set image deployment/api-server-$NEW_COLOR api=automation-framework:$NEW_VERSION

# Wait for rollout to complete
kubectl rollout status deployment/api-server-$NEW_COLOR

# Run health checks
if curl -f http://api-$NEW_COLOR.automation-framework.com/health; then
    echo "Health check passed, switching traffic"
    kubectl patch service api-service -p '{"spec":{"selector":{"color":"'$NEW_COLOR'"}}}'
    echo "Traffic switched to $NEW_COLOR"
else
    echo "Health check failed, rolling back"
    kubectl rollout undo deployment/api-server-$NEW_COLOR
    exit 1
fi
```

## 📋 Production Checklist

### Pre-Deployment

- [ ] **Security**
  - [ ] SSL certificates configured
  - [ ] Secrets properly managed
  - [ ] Security headers enabled
  - [ ] Network policies configured

- [ ] **Performance**
  - [ ] Resource limits set
  - [ ] Auto-scaling configured
  - [ ] Caching enabled
  - [ ] Database optimized

- [ ] **Monitoring**
  - [ ] Health checks implemented
  - [ ] Metrics collection enabled
  - [ ] Alerting configured
  - [ ] Log aggregation setup

- [ ] **Backup & Recovery**
  - [ ] Database backups scheduled
  - [ ] Disaster recovery plan
  - [ ] Data retention policies
  - [ ] Recovery procedures tested

### Post-Deployment

- [ ] **Verification**
  - [ ] All services healthy
  - [ ] Endpoints responding
  - [ ] Workflows executing
  - [ ] Metrics flowing

- [ ] **Performance**
  - [ ] Response times acceptable
  - [ ] Resource usage normal
  - [ ] No memory leaks
  - [ ] Error rates low

## 🔗 Next Steps

- **[Monitoring Guide](../operations/monitoring.md)** - Set up comprehensive monitoring
- **[Security Guide](../operations/security.md)** - Implement security best practices
- **[Scaling Guide](../operations/scaling.md)** - Scale for high availability
- **[Performance Tuning](performance.md)** - Optimize for production workloads
