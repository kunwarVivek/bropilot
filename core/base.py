"""
Base implementations for core framework components.

This module provides default implementations and utilities that can be
extended by concrete implementations.
"""

import asyncio
import time
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from .interfaces import (
    ILogger, IMetricsCollector, IHealthMonitor, IConfigurationManager,
    ExecutionResult, TaskStatus, WorkflowStatus
)
from .exceptions import FrameworkException, ConfigurationError


class BaseLogger(ILogger):
    """Base implementation of the logger interface using Python's logging module."""
    
    def __init__(self, name: str = "framework", level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(correlation_id)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def log(
        self, 
        level: str, 
        message: str, 
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        extra = {"correlation_id": correlation_id or "N/A"}
        extra.update(kwargs)
        
        log_level = getattr(logging, level.upper())
        self.logger.log(log_level, message, extra=extra)
    
    def info(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        self.log("INFO", message, correlation_id, **kwargs)
    
    def warning(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        self.log("WARNING", message, correlation_id, **kwargs)
    
    def error(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        self.log("ERROR", message, correlation_id, **kwargs)
    
    def debug(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        self.log("DEBUG", message, correlation_id, **kwargs)


class BaseMetricsCollector(IMetricsCollector):
    """Base implementation of metrics collector (in-memory for now)."""
    
    def __init__(self):
        self.metrics = {}
        self.timers = {}
    
    def increment_counter(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> None:
        key = self._build_metric_key(metric_name, tags)
        self.metrics[key] = self.metrics.get(key, 0) + 1
    
    def record_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        key = self._build_metric_key(metric_name, tags)
        self.metrics[key] = value
    
    def record_histogram(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        key = self._build_metric_key(metric_name, tags)
        if key not in self.metrics:
            self.metrics[key] = []
        self.metrics[key].append(value)
    
    def start_timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> str:
        timer_id = str(uuid.uuid4())
        self.timers[timer_id] = {
            "metric_name": metric_name,
            "tags": tags,
            "start_time": time.time()
        }
        return timer_id
    
    def stop_timer(self, timer_id: str) -> float:
        if timer_id not in self.timers:
            return 0.0
        
        timer_info = self.timers.pop(timer_id)
        duration = time.time() - timer_info["start_time"]
        self.record_histogram(timer_info["metric_name"], duration, timer_info["tags"])
        return duration
    
    def _build_metric_key(self, metric_name: str, tags: Optional[Dict[str, str]]) -> str:
        if not tags:
            return metric_name
        
        tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
        return f"{metric_name}[{tag_str}]"
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        return self.metrics.copy()


class BaseHealthMonitor(IHealthMonitor):
    """Base implementation of health monitoring."""
    
    def __init__(self):
        self.health_checks = {}
        self.last_check_results = {}
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        results = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "components": {}
        }
        
        overall_healthy = True
        
        for component_name, check_function in self.health_checks.items():
            try:
                component_healthy = await self._run_health_check(check_function)
                results["components"][component_name] = {
                    "status": "healthy" if component_healthy else "unhealthy",
                    "healthy": component_healthy
                }
                
                if not component_healthy:
                    overall_healthy = False
                    
            except Exception as e:
                results["components"][component_name] = {
                    "status": "error",
                    "healthy": False,
                    "error": str(e)
                }
                overall_healthy = False
        
        results["status"] = "healthy" if overall_healthy else "unhealthy"
        self.last_check_results = results
        return results
    
    async def check_component_health(self, component_name: str) -> bool:
        """Check the health of a specific component."""
        if component_name not in self.health_checks:
            return False
        
        try:
            return await self._run_health_check(self.health_checks[component_name])
        except Exception:
            return False
    
    def register_health_check(self, component_name: str, check_function: callable) -> None:
        """Register a health check function for a component."""
        self.health_checks[component_name] = check_function
    
    async def _run_health_check(self, check_function: callable) -> bool:
        """Run a health check function safely."""
        if asyncio.iscoroutinefunction(check_function):
            return await check_function()
        else:
            return check_function()


class BaseConfigurationManager(IConfigurationManager):
    """Base implementation of configuration management."""
    
    def __init__(self, config_data: Optional[Dict[str, Any]] = None):
        self.config_data = config_data or {}
        self.environment_configs = {}
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key using dot notation."""
        keys = key.split('.')
        value = self.config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value using dot notation."""
        keys = key.split('.')
        config = self.config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_environment_config(self, environment: str) -> Dict[str, Any]:
        """Get configuration for a specific environment."""
        return self.environment_configs.get(environment, {})
    
    def set_environment_config(self, environment: str, config: Dict[str, Any]) -> None:
        """Set configuration for a specific environment."""
        self.environment_configs[environment] = config
    
    def reload_config(self) -> None:
        """Reload configuration from source (override in subclasses)."""
        pass
    
    def merge_config(self, new_config: Dict[str, Any]) -> None:
        """Merge new configuration with existing configuration."""
        self._deep_merge(self.config_data, new_config)
    
    def _deep_merge(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """Deep merge two dictionaries."""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value


class ExecutionContext:
    """Context object for tracking execution state and metadata."""
    
    def __init__(self, execution_id: Optional[str] = None):
        self.execution_id = execution_id or str(uuid.uuid4())
        self.correlation_id = str(uuid.uuid4())
        self.start_time = datetime.utcnow()
        self.metadata = {}
        self.variables = {}
    
    def set_variable(self, key: str, value: Any) -> None:
        """Set a context variable."""
        self.variables[key] = value
    
    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a context variable."""
        return self.variables.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for this execution."""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata for this execution."""
        return self.metadata.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "execution_id": self.execution_id,
            "correlation_id": self.correlation_id,
            "start_time": self.start_time.isoformat(),
            "metadata": self.metadata,
            "variables": self.variables
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionContext":
        """Create context from dictionary."""
        context = cls(data.get("execution_id"))
        context.correlation_id = data.get("correlation_id", str(uuid.uuid4()))
        context.start_time = datetime.fromisoformat(data.get("start_time", datetime.utcnow().isoformat()))
        context.metadata = data.get("metadata", {})
        context.variables = data.get("variables", {})
        return context
