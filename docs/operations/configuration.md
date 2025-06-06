# Configuration Reference

Complete reference for configuring the Browser Automation Framework for production environments.

## 🎯 Configuration Overview

### Configuration Sources

The framework loads configuration from multiple sources in order of precedence:

1. **Environment Variables** (highest priority)
2. **Configuration Files** (.env, config.yaml)
3. **Command Line Arguments**
4. **Default Values** (lowest priority)

### Configuration Structure

```mermaid
graph TB
    subgraph "Configuration Layers"
        ENV[Environment Variables]
        FILES[Configuration Files]
        CLI[Command Line Args]
        DEFAULTS[Default Values]
    end
    
    subgraph "Configuration Categories"
        APP[Application Config]
        DB[Database Config]
        REDIS[Redis Config]
        LLM[LLM Config]
        BROWSER[Browser Config]
        SECURITY[Security Config]
        MONITORING[Monitoring Config]
    end
    
    ENV --> APP
    FILES --> DB
    CLI --> REDIS
    DEFAULTS --> LLM
    
    APP --> BROWSER
    DB --> SECURITY
    REDIS --> MONITORING
```

## 🔧 Core Configuration

### Application Settings

```yaml
# config/application.yaml
application:
  name: "Browser Automation Framework"
  version: "1.0.0"
  environment: "production"  # development, staging, production
  debug: false
  
  # Server configuration
  server:
    host: "0.0.0.0"
    port: 8000
    workers: 4
    worker_class: "uvicorn.workers.UvicornWorker"
    timeout: 300
    keepalive: 2
    max_requests: 1000
    max_requests_jitter: 100
  
  # Logging configuration
  logging:
    level: "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    format: "json"  # json, text
    file: "/var/log/automation/app.log"
    max_size: "100MB"
    backup_count: 10
    
  # Performance settings
  performance:
    max_concurrent_workflows: 50
    worker_concurrency: 10
    task_timeout: 300
    request_timeout: 60
    
  # Feature flags
  features:
    enable_llm_assistance: true
    enable_multimodal: true
    enable_analytics: true
    enable_caching: true
```

### Environment Variables

```bash
# Core Application
APP_NAME="Browser Automation Framework"
APP_VERSION="1.0.0"
ENV=production
DEBUG=false
LOG_LEVEL=INFO

# Server Configuration
HOST=0.0.0.0
PORT=8000
WORKERS=4
TIMEOUT=300

# Security
SECRET_KEY=your-super-secret-key-here
JWT_SECRET=your-jwt-secret-here
JWT_EXPIRATION=3600
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
ALLOWED_HOSTS=your-domain.com,api.your-domain.com

# Performance
MAX_CONCURRENT_WORKFLOWS=50
WORKER_CONCURRENCY=10
TASK_TIMEOUT=300
REQUEST_TIMEOUT=60
```

## 🗄️ Database Configuration

### PostgreSQL Settings

```yaml
# config/database.yaml
database:
  # Connection settings
  url: "postgresql://user:password@localhost:5432/automation_prod"
  driver: "asyncpg"
  
  # Pool configuration
  pool:
    size: 20
    max_overflow: 30
    timeout: 30
    recycle: 3600
    pre_ping: true
    
  # Query settings
  query:
    timeout: 30
    echo: false  # Set to true for SQL debugging
    echo_pool: false
    
  # Migration settings
  migration:
    directory: "migrations"
    auto_upgrade: false
    
  # Backup settings
  backup:
    enabled: true
    schedule: "0 2 * * *"  # Daily at 2 AM
    retention_days: 30
    compression: true
```

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://automation_user:secure_password@db-host:5432/automation_prod
DATABASE_DRIVER=asyncpg
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=30
DATABASE_TIMEOUT=30
DATABASE_RECYCLE=3600
DATABASE_ECHO=false

# SSL Configuration (for cloud databases)
DATABASE_SSL_MODE=require
DATABASE_SSL_CERT=/path/to/client-cert.pem
DATABASE_SSL_KEY=/path/to/client-key.pem
DATABASE_SSL_ROOT_CERT=/path/to/ca-cert.pem
```

## 🔴 Redis Configuration

### Redis Settings

```yaml
# config/redis.yaml
redis:
  # Connection settings
  url: "redis://localhost:6379/0"
  password: "your-redis-password"
  
  # Pool configuration
  pool:
    size: 10
    max_connections: 50
    timeout: 5
    retry_on_timeout: true
    
  # Cluster configuration (if using Redis Cluster)
  cluster:
    enabled: false
    nodes:
      - "redis-node-1:6379"
      - "redis-node-2:6379"
      - "redis-node-3:6379"
    
  # Cache settings
  cache:
    default_ttl: 3600
    max_memory: "2gb"
    eviction_policy: "allkeys-lru"
    
  # Pub/Sub settings
  pubsub:
    enabled: true
    channels:
      - "workflow_events"
      - "system_alerts"
```

### Environment Variables

```bash
# Redis Configuration
REDIS_URL=redis://redis-host:6379/0
REDIS_PASSWORD=your-redis-password
REDIS_POOL_SIZE=10
REDIS_MAX_CONNECTIONS=50
REDIS_TIMEOUT=5
REDIS_DEFAULT_TTL=3600

# Redis Cluster (if applicable)
REDIS_CLUSTER_ENABLED=false
REDIS_CLUSTER_NODES=redis-node-1:6379,redis-node-2:6379,redis-node-3:6379
```

## 🤖 LLM Configuration

### LLM Provider Settings

```yaml
# config/llm.yaml
llm:
  # Default provider
  default_provider: "openai"
  
  # Provider configurations
  providers:
    openai:
      api_key: "${OPENAI_API_KEY}"
      organization: "${OPENAI_ORG_ID}"
      base_url: "https://api.openai.com/v1"
      model: "gpt-4"
      temperature: 0.1
      max_tokens: 2000
      timeout: 30
      max_retries: 3
      
    anthropic:
      api_key: "${ANTHROPIC_API_KEY}"
      base_url: "https://api.anthropic.com"
      model: "claude-3-sonnet-20240229"
      temperature: 0.1
      max_tokens: 2000
      timeout: 30
      
    azure:
      api_key: "${AZURE_OPENAI_API_KEY}"
      endpoint: "${AZURE_OPENAI_ENDPOINT}"
      deployment_name: "gpt-4"
      api_version: "2024-02-15-preview"
      
    local:
      endpoint: "http://localhost:11434"
      model: "llama2:13b"
      temperature: 0.1
      context_length: 4096
  
  # Rate limiting
  rate_limit:
    requests_per_minute: 100
    tokens_per_minute: 50000
    burst_limit: 10
    
  # Caching
  cache:
    enabled: true
    ttl: 3600
    max_size: 1000
```

### Environment Variables

```bash
# LLM Configuration
LLM_DEFAULT_PROVIDER=openai
LLM_TIMEOUT=30
LLM_MAX_RETRIES=3
LLM_RATE_LIMIT_RPM=100
LLM_CACHE_ENABLED=true

# OpenAI
OPENAI_API_KEY=your-openai-api-key
OPENAI_ORG_ID=your-organization-id
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=2000

# Anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Azure OpenAI
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Local LLM
LOCAL_LLM_ENDPOINT=http://localhost:11434
LOCAL_LLM_MODEL=llama2:13b
```

## 🌐 Browser Configuration

### Browser Pool Settings

```yaml
# config/browser.yaml
browser:
  # Pool configuration
  pool:
    min_size: 5
    max_size: 20
    idle_timeout: 300
    startup_timeout: 60
    health_check_interval: 60
    
  # Browser settings
  settings:
    headless: true
    timeout: 60
    viewport:
      width: 1920
      height: 1080
    user_agent: "Mozilla/5.0 (compatible; AutomationBot/1.0)"
    
  # Performance settings
  performance:
    disable_images: false
    disable_javascript: false
    disable_css: false
    disable_fonts: false
    memory_limit: "512MB"
    page_limit: 5
    
  # Proxy settings
  proxy:
    enabled: false
    server: "http://proxy-server:8080"
    username: "proxy_user"
    password: "proxy_password"
    
  # Recording settings
  recording:
    enabled: false
    video: false
    screenshots: true
    trace: false
    har: false
```

### Environment Variables

```bash
# Browser Configuration
BROWSER_POOL_MIN_SIZE=5
BROWSER_POOL_MAX_SIZE=20
BROWSER_IDLE_TIMEOUT=300
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=60
BROWSER_MEMORY_LIMIT=512MB
BROWSER_PAGE_LIMIT=5

# Browser Features
BROWSER_DISABLE_IMAGES=false
BROWSER_DISABLE_JAVASCRIPT=false
BROWSER_DISABLE_CSS=false

# Proxy Configuration
BROWSER_PROXY_ENABLED=false
BROWSER_PROXY_SERVER=http://proxy-server:8080
BROWSER_PROXY_USERNAME=proxy_user
BROWSER_PROXY_PASSWORD=proxy_password

# Recording
BROWSER_RECORDING_ENABLED=false
BROWSER_SCREENSHOTS_ENABLED=true
```

## 🔒 Security Configuration

### Security Settings

```yaml
# config/security.yaml
security:
  # Authentication
  authentication:
    enabled: true
    method: "jwt"  # jwt, oauth2, api_key
    jwt:
      secret: "${JWT_SECRET}"
      algorithm: "HS256"
      expiration: 3600
      refresh_enabled: true
      refresh_expiration: 86400
      
  # Authorization
  authorization:
    enabled: true
    default_role: "user"
    admin_users:
      - "admin@company.com"
      
  # CORS settings
  cors:
    enabled: true
    origins:
      - "https://your-domain.com"
      - "https://api.your-domain.com"
    methods: ["GET", "POST", "PUT", "DELETE"]
    headers: ["*"]
    credentials: true
    
  # Rate limiting
  rate_limiting:
    enabled: true
    default_limit: "100/minute"
    burst_limit: 10
    storage: "redis"
    
  # SSL/TLS
  ssl:
    enabled: true
    cert_file: "/etc/ssl/certs/automation.crt"
    key_file: "/etc/ssl/private/automation.key"
    ca_file: "/etc/ssl/certs/ca.crt"
    
  # Security headers
  headers:
    x_content_type_options: "nosniff"
    x_frame_options: "DENY"
    x_xss_protection: "1; mode=block"
    strict_transport_security: "max-age=31536000; includeSubDomains"
    content_security_policy: "default-src 'self'"
```

### Environment Variables

```bash
# Security Configuration
SECURITY_ENABLED=true
JWT_SECRET=your-jwt-secret-here
JWT_EXPIRATION=3600
JWT_REFRESH_ENABLED=true

# CORS
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
CORS_METHODS=GET,POST,PUT,DELETE
CORS_CREDENTIALS=true

# Rate Limiting
RATE_LIMITING_ENABLED=true
RATE_LIMITING_DEFAULT=100/minute
RATE_LIMITING_BURST=10

# SSL/TLS
SSL_ENABLED=true
SSL_CERT_FILE=/etc/ssl/certs/automation.crt
SSL_KEY_FILE=/etc/ssl/private/automation.key
```

## 📊 Monitoring Configuration

### Monitoring Settings

```yaml
# config/monitoring.yaml
monitoring:
  # Metrics
  metrics:
    enabled: true
    endpoint: "/metrics"
    port: 9090
    interval: 10
    
  # Health checks
  health:
    enabled: true
    endpoint: "/health"
    checks:
      - "database"
      - "redis"
      - "llm_provider"
      - "browser_pool"
      
  # Logging
  logging:
    level: "INFO"
    format: "json"
    structured: true
    correlation_id: true
    
  # Alerting
  alerting:
    enabled: true
    channels:
      email:
        enabled: true
        smtp_server: "smtp.company.com"
        smtp_port: 587
        username: "alerts@company.com"
        password: "${SMTP_PASSWORD}"
        recipients:
          - "admin@company.com"
          - "ops@company.com"
      slack:
        enabled: true
        webhook_url: "${SLACK_WEBHOOK_URL}"
        channel: "#automation-alerts"
      webhook:
        enabled: true
        url: "https://your-system.com/webhooks/alerts"
        
  # Tracing
  tracing:
    enabled: true
    service_name: "automation-framework"
    jaeger_endpoint: "http://jaeger:14268/api/traces"
    sample_rate: 0.1
```

### Environment Variables

```bash
# Monitoring Configuration
MONITORING_ENABLED=true
METRICS_ENABLED=true
METRICS_PORT=9090
HEALTH_CHECKS_ENABLED=true

# Alerting
ALERTING_ENABLED=true
SMTP_SERVER=smtp.company.com
SMTP_PORT=587
SMTP_USERNAME=alerts@company.com
SMTP_PASSWORD=your-smtp-password
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# Tracing
TRACING_ENABLED=true
JAEGER_ENDPOINT=http://jaeger:14268/api/traces
TRACING_SAMPLE_RATE=0.1
```

## 🔧 Advanced Configuration

### Custom Configuration Loader

```python
# src/config/loader.py
import os
import yaml
from typing import Dict, Any
from pydantic import BaseSettings

class ConfigLoader:
    """Advanced configuration loader with multiple sources."""
    
    def __init__(self):
        self.config = {}
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from multiple sources."""
        
        # Load default configuration
        self._load_defaults()
        
        # Load from YAML files
        self._load_yaml_files()
        
        # Load from environment variables
        self._load_environment()
        
        # Load from command line arguments
        self._load_cli_args()
        
        return self.config
    
    def _load_yaml_files(self):
        """Load configuration from YAML files."""
        config_files = [
            "config/application.yaml",
            "config/database.yaml",
            "config/redis.yaml",
            "config/llm.yaml",
            "config/browser.yaml",
            "config/security.yaml",
            "config/monitoring.yaml"
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    file_config = yaml.safe_load(f)
                    self._merge_config(file_config)
    
    def _load_environment(self):
        """Load configuration from environment variables."""
        env_mapping = {
            "APP_NAME": "application.name",
            "ENV": "application.environment",
            "DEBUG": "application.debug",
            "DATABASE_URL": "database.url",
            "REDIS_URL": "redis.url",
            "LLM_API_KEY": "llm.providers.openai.api_key"
        }
        
        for env_var, config_path in env_mapping.items():
            value = os.getenv(env_var)
            if value is not None:
                self._set_nested_value(config_path, value)
    
    def _merge_config(self, new_config: Dict[str, Any]):
        """Merge new configuration with existing."""
        def merge_dict(base: dict, update: dict):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(self.config, new_config)
    
    def _set_nested_value(self, path: str, value: Any):
        """Set nested configuration value using dot notation."""
        keys = path.split('.')
        current = self.config
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
```

### Configuration Validation

```python
# src/config/validator.py
from pydantic import BaseModel, validator
from typing import Optional, List

class DatabaseConfig(BaseModel):
    """Database configuration validation."""
    url: str
    pool_size: int = 20
    max_overflow: int = 30
    timeout: int = 30
    
    @validator('pool_size')
    def validate_pool_size(cls, v):
        if v < 1 or v > 100:
            raise ValueError('Pool size must be between 1 and 100')
        return v

class LLMConfig(BaseModel):
    """LLM configuration validation."""
    default_provider: str
    timeout: int = 30
    max_retries: int = 3
    
    @validator('default_provider')
    def validate_provider(cls, v):
        allowed_providers = ['openai', 'anthropic', 'azure', 'local']
        if v not in allowed_providers:
            raise ValueError(f'Provider must be one of {allowed_providers}')
        return v

class ApplicationConfig(BaseModel):
    """Main application configuration."""
    name: str = "Browser Automation Framework"
    environment: str = "production"
    debug: bool = False
    database: DatabaseConfig
    llm: LLMConfig
    
    @validator('environment')
    def validate_environment(cls, v):
        allowed_envs = ['development', 'staging', 'production']
        if v not in allowed_envs:
            raise ValueError(f'Environment must be one of {allowed_envs}')
        return v
```

## 🔗 Next Steps

- **[Security Guide](security.md)** - Implement security best practices
- **[Monitoring Guide](monitoring.md)** - Set up comprehensive monitoring
- **[Backup & Recovery](backup-recovery.md)** - Configure backup strategies
- **[Scaling Guide](scaling.md)** - Scale for high availability
