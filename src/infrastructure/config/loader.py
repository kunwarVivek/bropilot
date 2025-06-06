"""
Configuration loader with environment-specific settings.

This module provides functionality to load and merge configuration from
multiple sources including environment variables, YAML files, and defaults.
"""

import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path

from core.interfaces import IConfigurationManager
from core.exceptions import ConfigurationError
from .settings import Settings, Environment


class ConfigurationLoader(IConfigurationManager):
    """Configuration loader that supports multiple sources and environments."""
    
    def __init__(self, config_dir: Optional[str] = None):
        """Initialize configuration loader.
        
        Args:
            config_dir: Directory containing configuration files
        """
        self.config_dir = Path(config_dir or "config")
        self.environments_dir = self.config_dir / "environments"
        self._config_cache = {}
        self._settings = None
    
    def load_settings(self) -> Settings:
        """Load and return complete settings object."""
        if self._settings is None:
            self._settings = Settings()
            
            # Load environment-specific configuration
            env_config = self._load_environment_config()
            if env_config:
                self._apply_config_overrides(self._settings, env_config)
            
            # Validate settings
            self._settings.validate()
        
        return self._settings
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key using dot notation."""
        settings = self.load_settings()
        
        # Navigate through the settings object using dot notation
        keys = key.split('.')
        value = settings
        
        try:
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                elif isinstance(value, dict):
                    value = value[k]
                else:
                    return default
            
            # Handle SecretStr values
            if hasattr(value, 'get_secret_value'):
                return value.get_secret_value()
            
            return value
        except (AttributeError, KeyError, TypeError):
            return default
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value (runtime only)."""
        # This is for runtime configuration changes only
        # Persistent changes should be made to configuration files
        if key not in self._config_cache:
            self._config_cache[key] = value
    
    def get_environment_config(self, environment: str) -> Dict[str, Any]:
        """Get configuration for a specific environment."""
        env_file = self.environments_dir / f"{environment}.yaml"
        
        if not env_file.exists():
            raise ConfigurationError(f"Environment configuration file not found: {env_file}")
        
        try:
            with open(env_file, 'r') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Failed to parse environment configuration: {e}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load environment configuration: {e}")
    
    def reload_config(self) -> None:
        """Reload configuration from source."""
        self._settings = None
        self._config_cache.clear()
    
    def _load_environment_config(self) -> Optional[Dict[str, Any]]:
        """Load configuration for the current environment."""
        # Determine current environment
        env_name = os.getenv("APP_ENVIRONMENT", Environment.DEVELOPMENT.value)
        
        try:
            return self.get_environment_config(env_name)
        except ConfigurationError:
            # If environment-specific config doesn't exist, that's okay
            # We'll use defaults from the Settings classes
            return None
    
    def _apply_config_overrides(self, settings: Settings, config: Dict[str, Any]) -> None:
        """Apply configuration overrides to settings object."""
        
        # Apply app settings
        if "app" in config:
            self._apply_overrides(settings.app, config["app"])
        
        # Apply database settings
        if "database" in config:
            self._apply_overrides(settings.database, config["database"])
        
        # Apply LLM settings
        if "llm" in config:
            llm_config = config["llm"]
            self._apply_overrides(settings.llm, llm_config)
            
            # Handle nested LLM provider configs
            if "gemini" in llm_config:
                self._apply_nested_overrides(settings.llm, llm_config["gemini"], "gemini_")
            if "openai" in llm_config:
                self._apply_nested_overrides(settings.llm, llm_config["openai"], "openai_")
            if "anthropic" in llm_config:
                self._apply_nested_overrides(settings.llm, llm_config["anthropic"], "anthropic_")
        
        # Apply browser settings
        if "browser" in config:
            self._apply_overrides(settings.browser, config["browser"])
        
        # Apply task settings
        if "tasks" in config:
            self._apply_overrides(settings.tasks, config["tasks"])
        
        # Apply logging settings
        if "logging" in config:
            self._apply_overrides(settings.logging, config["logging"])
        
        # Apply metrics settings
        if "metrics" in config:
            self._apply_overrides(settings.metrics, config["metrics"])
        
        # Apply cache settings
        if "cache" in config:
            cache_config = config["cache"]
            self._apply_overrides(settings.cache, cache_config)
            
            # Handle nested Redis config
            if "redis" in cache_config:
                self._apply_nested_overrides(settings.cache, cache_config["redis"], "redis_")
    
    def _apply_overrides(self, settings_obj: Any, overrides: Dict[str, Any]) -> None:
        """Apply configuration overrides to a settings object."""
        for key, value in overrides.items():
            if hasattr(settings_obj, key):
                # Get the field info to handle type conversion
                field_info = settings_obj.__fields__.get(key)
                if field_info:
                    # Convert value to the expected type
                    try:
                        if field_info.type_ == bool and isinstance(value, str):
                            value = value.lower() in ('true', '1', 'yes', 'on')
                        elif field_info.type_ == int and isinstance(value, str):
                            value = int(value)
                        elif field_info.type_ == float and isinstance(value, (str, int)):
                            value = float(value)
                    except (ValueError, TypeError):
                        # If conversion fails, use the original value
                        pass
                
                setattr(settings_obj, key, value)
    
    def _apply_nested_overrides(
        self, 
        settings_obj: Any, 
        overrides: Dict[str, Any], 
        prefix: str
    ) -> None:
        """Apply nested configuration overrides with a prefix."""
        for key, value in overrides.items():
            prefixed_key = f"{prefix}{key}"
            if hasattr(settings_obj, prefixed_key):
                setattr(settings_obj, prefixed_key, value)
    
    def get_database_url(self) -> str:
        """Get the complete database URL."""
        return self.get_config("database.database_url")
    
    def get_llm_config(self) -> Dict[str, Any]:
        """Get LLM configuration for the current provider."""
        settings = self.load_settings()
        provider = settings.llm.llm_provider.value
        
        base_config = {
            "provider": provider,
            "timeout": settings.llm.llm_timeout,
            "max_retries": settings.llm.llm_max_retries,
            "retry_delay": settings.llm.llm_retry_delay
        }
        
        if provider == "gemini":
            base_config.update({
                "api_key": settings.llm.gemini_api_key.get_secret_value(),
                "model": settings.llm.gemini_model,
                "requests_per_second": settings.llm.gemini_requests_per_second,
                "max_bucket_size": settings.llm.gemini_max_bucket_size
            })
        elif provider == "openai":
            base_config.update({
                "api_key": settings.llm.openai_api_key.get_secret_value(),
                "model": settings.llm.openai_model,
                "requests_per_minute": settings.llm.openai_requests_per_minute
            })
        elif provider == "anthropic":
            base_config.update({
                "api_key": settings.llm.anthropic_api_key.get_secret_value(),
                "model": settings.llm.anthropic_model
            })
        
        return base_config
    
    def get_browser_config(self) -> Dict[str, Any]:
        """Get browser configuration."""
        settings = self.load_settings()
        
        return {
            "type": settings.browser.browser_type.value,
            "headless": settings.browser.browser_headless,
            "timeout": settings.browser.browser_timeout,
            "page_load_timeout": settings.browser.browser_page_load_timeout,
            "implicit_wait": settings.browser.browser_implicit_wait,
            "window_size": (settings.browser.browser_window_width, settings.browser.browser_window_height),
            "user_agent": settings.browser.browser_user_agent,
            "download_dir": settings.browser.browser_download_dir,
            "chrome_options": settings.browser.chrome_options
        }
    
    def get_task_credentials(self) -> Dict[str, str]:
        """Get task execution credentials."""
        settings = self.load_settings()
        
        return {
            "email": settings.tasks.login_email,
            "password": settings.tasks.login_password.get_secret_value(),
            "base_url": settings.tasks.target_base_url
        }


# Global configuration loader instance
config_loader = ConfigurationLoader()
