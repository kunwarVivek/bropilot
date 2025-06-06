"""
Application settings and configuration management.

This module provides centralized configuration management with environment-specific
settings, validation, and secure credential handling.
"""

import os
from typing import Optional, Dict, Any, List
from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings
from enum import Enum


class Environment(str, Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Supported log formats."""
    JSON = "json"
    TEXT = "text"


class BrowserType(str, Enum):
    """Supported browser types."""
    CHROME = "chrome"
    FIREFOX = "firefox"
    EDGE = "edge"


class LLMProvider(str, Enum):
    """Supported LLM providers."""
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class ApplicationSettings(BaseSettings):
    """Application-level configuration settings."""
    
    # Application metadata
    app_name: str = Field(default="browser-automation-framework", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(
        default="A robust browser automation framework with LLM integration",
        env="APP_DESCRIPTION"
    )
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="APP_ENVIRONMENT")
    debug: bool = Field(default=False, env="APP_DEBUG")
    
    # API configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_prefix: str = Field(default="/api/v1", env="API_PREFIX")
    api_cors_origins: List[str] = Field(default=["*"], env="API_CORS_ORIGINS")
    
    # Security
    secret_key: SecretStr = Field(default="", env="SECRET_KEY")
    api_key_header: str = Field(default="X-API-Key", env="API_KEY_HEADER")
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    @field_validator("secret_key", mode="before")
    @classmethod
    def validate_secret_key(cls, v):
        if not v:
            # Generate a default secret key for development
            import secrets
            return secrets.token_urlsafe(32)
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class DatabaseSettings(BaseSettings):
    """Database configuration settings."""
    
    database_url: Optional[str] = Field(env="DATABASE_URL")
    database_host: str = Field(default="localhost", env="DATABASE_HOST")
    database_port: int = Field(default=5432, env="DATABASE_PORT")
    database_name: str = Field(default="browser_automation", env="DATABASE_NAME")
    database_user: str = Field(default="postgres", env="DATABASE_USER")
    database_password: SecretStr = Field(default="", env="DATABASE_PASSWORD")
    database_pool_size: int = Field(default=10, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    
    @model_validator(mode="before")
    @classmethod
    def build_database_url(cls, values):
        if isinstance(values, dict) and not values.get("database_url"):
            # Build URL from components
            password = values.get("database_password", "")
            if password:
                password = f":{password.get_secret_value()}" if hasattr(password, 'get_secret_value') else f":{password}"

            values["database_url"] = (
                f"postgresql://{values.get('database_user', 'postgres')}"
                f"{password}@{values.get('database_host', 'localhost')}"
                f":{values.get('database_port', 5432)}/{values.get('database_name', 'browser_automation')}"
            )
        return values
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class LLMSettings(BaseSettings):
    """LLM provider configuration settings."""
    
    # Primary LLM provider
    llm_provider: LLMProvider = Field(default=LLMProvider.GEMINI, env="LLM_PROVIDER")
    
    # Gemini configuration
    gemini_api_key: SecretStr = Field(default="", env="GEMINI_API_KEY")
    gemini_model: str = Field(default="models/gemini-2.5-flash-preview-04-17", env="GEMINI_MODEL")
    gemini_requests_per_second: float = Field(default=1.0, env="GEMINI_REQUESTS_PER_SECOND")
    gemini_max_bucket_size: int = Field(default=10, env="GEMINI_MAX_BUCKET_SIZE")
    
    # OpenAI configuration
    openai_api_key: SecretStr = Field(default="", env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")
    openai_requests_per_minute: int = Field(default=60, env="OPENAI_REQUESTS_PER_MINUTE")
    
    # Anthropic configuration
    anthropic_api_key: SecretStr = Field(default="", env="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-3-sonnet-20240229", env="ANTHROPIC_MODEL")
    
    # General LLM settings
    llm_timeout: int = Field(default=60, env="LLM_TIMEOUT")
    llm_max_retries: int = Field(default=3, env="LLM_MAX_RETRIES")
    llm_retry_delay: float = Field(default=1.0, env="LLM_RETRY_DELAY")
    
    @field_validator("gemini_api_key", "openai_api_key", "anthropic_api_key")
    @classmethod
    def validate_api_keys(cls, v):
        # In production, require API keys for the selected provider
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class BrowserSettings(BaseSettings):
    """Browser configuration settings."""
    
    browser_type: BrowserType = Field(default=BrowserType.CHROME, env="BROWSER_TYPE")
    browser_headless: bool = Field(default=False, env="BROWSER_HEADLESS")
    browser_timeout: int = Field(default=30, env="BROWSER_TIMEOUT")
    browser_page_load_timeout: int = Field(default=30, env="BROWSER_PAGE_LOAD_TIMEOUT")
    browser_implicit_wait: int = Field(default=10, env="BROWSER_IMPLICIT_WAIT")
    browser_window_width: int = Field(default=1920, env="BROWSER_WINDOW_WIDTH")
    browser_window_height: int = Field(default=1080, env="BROWSER_WINDOW_HEIGHT")
    browser_user_agent: Optional[str] = Field(default=None, env="BROWSER_USER_AGENT")
    browser_download_dir: str = Field(default="./downloads", env="BROWSER_DOWNLOAD_DIR")
    browser_pool_size: int = Field(default=5, env="BROWSER_POOL_SIZE")
    
    # Browser-specific options
    chrome_options: List[str] = Field(
        default=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-extensions"
        ],
        env="CHROME_OPTIONS"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class TaskSettings(BaseSettings):
    """Task execution configuration settings."""
    
    # Default task settings
    default_task_timeout: int = Field(default=300, env="DEFAULT_TASK_TIMEOUT")  # 5 minutes
    default_retry_count: int = Field(default=3, env="DEFAULT_RETRY_COUNT")
    default_retry_delay: float = Field(default=1.0, env="DEFAULT_RETRY_DELAY")
    max_parallel_tasks: int = Field(default=5, env="MAX_PARALLEL_TASKS")
    
    # Workflow settings
    workflow_timeout: int = Field(default=1800, env="WORKFLOW_TIMEOUT")  # 30 minutes
    workflow_checkpoint_interval: int = Field(default=60, env="WORKFLOW_CHECKPOINT_INTERVAL")  # 1 minute
    
    # Task-specific URLs and settings
    target_base_url: str = Field(default="https://dev.gotrust.tech", env="TARGET_BASE_URL")
    login_email: str = Field(default="", env="LOGIN_EMAIL")
    login_password: SecretStr = Field(default="", env="LOGIN_PASSWORD")
    
    # Cookie consent settings
    cookie_consent_timeout: int = Field(default=5, env="COOKIE_CONSENT_TIMEOUT")
    cookie_consent_buttons: List[str] = Field(
        default=["Allow all", "Accept all", "Accept"],
        env="COOKIE_CONSENT_BUTTONS"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class LoggingSettings(BaseSettings):
    """Logging configuration settings."""
    
    log_level: LogLevel = Field(default=LogLevel.INFO, env="LOG_LEVEL")
    log_format: LogFormat = Field(default=LogFormat.JSON, env="LOG_FORMAT")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    log_max_size: str = Field(default="10MB", env="LOG_MAX_SIZE")
    log_backup_count: int = Field(default=5, env="LOG_BACKUP_COUNT")
    log_correlation_id_header: str = Field(default="X-Correlation-ID", env="LOG_CORRELATION_ID_HEADER")
    
    # Structured logging settings
    log_include_timestamp: bool = Field(default=True, env="LOG_INCLUDE_TIMESTAMP")
    log_include_level: bool = Field(default=True, env="LOG_INCLUDE_LEVEL")
    log_include_logger_name: bool = Field(default=True, env="LOG_INCLUDE_LOGGER_NAME")
    log_include_correlation_id: bool = Field(default=True, env="LOG_INCLUDE_CORRELATION_ID")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class MetricsSettings(BaseSettings):
    """Metrics collection configuration settings."""
    
    metrics_enabled: bool = Field(default=True, env="METRICS_ENABLED")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    metrics_path: str = Field(default="/metrics", env="METRICS_PATH")
    metrics_namespace: str = Field(default="browser_automation", env="METRICS_NAMESPACE")
    
    # Prometheus settings
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    prometheus_multiproc: bool = Field(default=False, env="PROMETHEUS_MULTIPROC")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class CacheSettings(BaseSettings):
    """Cache configuration settings."""
    
    cache_enabled: bool = Field(default=True, env="CACHE_ENABLED")
    cache_type: str = Field(default="memory", env="CACHE_TYPE")  # memory, redis
    cache_ttl: int = Field(default=3600, env="CACHE_TTL")  # 1 hour
    
    # Redis settings (if using Redis cache)
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: SecretStr = Field(default="", env="REDIS_PASSWORD")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class Settings:
    """Centralized settings container."""
    
    def __init__(self):
        self.app = ApplicationSettings()
        self.database = DatabaseSettings()
        self.llm = LLMSettings()
        self.browser = BrowserSettings()
        self.tasks = TaskSettings()
        self.logging = LoggingSettings()
        self.metrics = MetricsSettings()
        self.cache = CacheSettings()
    
    def validate(self) -> None:
        """Validate all settings and raise errors for invalid configurations."""
        errors = []
        
        # Validate LLM provider has required API key
        if self.llm.llm_provider == LLMProvider.GEMINI and not self.llm.gemini_api_key.get_secret_value():
            errors.append("GEMINI_API_KEY is required when using Gemini as LLM provider")
        elif self.llm.llm_provider == LLMProvider.OPENAI and not self.llm.openai_api_key.get_secret_value():
            errors.append("OPENAI_API_KEY is required when using OpenAI as LLM provider")
        elif self.llm.llm_provider == LLMProvider.ANTHROPIC and not self.llm.anthropic_api_key.get_secret_value():
            errors.append("ANTHROPIC_API_KEY is required when using Anthropic as LLM provider")
        
        # Validate task credentials
        if not self.tasks.login_email:
            errors.append("LOGIN_EMAIL is required for task execution")
        if not self.tasks.login_password.get_secret_value():
            errors.append("LOGIN_PASSWORD is required for task execution")
        
        # Validate timeouts are positive
        if self.tasks.default_task_timeout <= 0:
            errors.append("DEFAULT_TASK_TIMEOUT must be positive")
        if self.browser.browser_timeout <= 0:
            errors.append("BROWSER_TIMEOUT must be positive")
        
        if errors:
            from core.exceptions import ConfigurationError
            raise ConfigurationError(f"Configuration validation failed: {'; '.join(errors)}")
    
    def get_environment_name(self) -> str:
        """Get the current environment name."""
        return self.app.environment.value
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app.environment == Environment.DEVELOPMENT
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app.environment == Environment.PRODUCTION
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (excluding secrets)."""
        return {
            "app": self.app.dict(exclude={"secret_key"}),
            "database": self.database.dict(exclude={"database_password"}),
            "llm": self.llm.dict(exclude={"gemini_api_key", "openai_api_key", "anthropic_api_key"}),
            "browser": self.browser.dict(),
            "tasks": self.tasks.dict(exclude={"login_password"}),
            "logging": self.logging.dict(),
            "metrics": self.metrics.dict(),
            "cache": self.cache.dict(exclude={"redis_password"})
        }


# Global settings instance
settings = Settings()
