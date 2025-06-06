"""
Graceful degradation strategies.

This module provides mechanisms for graceful degradation when services
are unavailable or performing poorly, ensuring system resilience.
"""

import asyncio
import time
from typing import Any, Callable, Optional, Dict, List, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import functools

from core.exceptions import ExternalServiceError, ConfigurationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class DegradationLevel(str, Enum):
    """Degradation level enumeration."""
    NONE = "none"              # Full functionality
    MINIMAL = "minimal"        # Slight reduction in features
    MODERATE = "moderate"      # Significant feature reduction
    SEVERE = "severe"          # Basic functionality only
    EMERGENCY = "emergency"    # Critical functions only


class FallbackStrategy(str, Enum):
    """Fallback strategy enumeration."""
    CACHE = "cache"            # Use cached data
    DEFAULT = "default"        # Return default values
    SIMPLIFIED = "simplified"  # Use simplified logic
    ALTERNATIVE = "alternative"  # Use alternative service
    QUEUE = "queue"            # Queue for later processing
    FAIL_FAST = "fail_fast"    # Fail immediately


@dataclass
class DegradationConfig:
    """Configuration for degradation behavior."""
    enabled: bool = True
    degradation_level: DegradationLevel = DegradationLevel.NONE
    fallback_strategy: FallbackStrategy = FallbackStrategy.DEFAULT
    fallback_data: Optional[Any] = None
    cache_ttl: float = 300.0  # Cache TTL in seconds
    queue_max_size: int = 1000
    health_check_interval: float = 30.0  # Health check interval
    recovery_threshold: float = 0.8  # Health threshold for recovery
    degradation_threshold: float = 0.3  # Health threshold for degradation


@dataclass
class ServiceHealth:
    """Service health information."""
    service_name: str
    is_healthy: bool
    health_score: float  # 0.0 to 1.0
    last_check: datetime
    response_time: float
    error_rate: float
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class DegradationManager:
    """Manager for graceful degradation strategies."""
    
    def __init__(self):
        """Initialize degradation manager."""
        self.logger = StructuredLogger("degradation_manager")
        
        # Service health tracking
        self.service_health: Dict[str, ServiceHealth] = {}
        
        # Degradation configurations
        self.degradation_configs: Dict[str, DegradationConfig] = {}
        
        # Fallback caches
        self.fallback_caches: Dict[str, Dict[str, Tuple[Any, datetime]]] = {}
        
        # Queued operations
        self.operation_queues: Dict[str, List[Dict[str, Any]]] = {}
        
        # Health monitoring tasks
        self.health_monitoring_tasks: Dict[str, asyncio.Task] = {}
    
    def register_service(
        self,
        service_name: str,
        config: DegradationConfig,
        health_check_func: Optional[Callable] = None
    ) -> None:
        """Register a service for degradation management."""
        
        self.degradation_configs[service_name] = config
        self.fallback_caches[service_name] = {}
        self.operation_queues[service_name] = []
        
        # Initialize service health
        self.service_health[service_name] = ServiceHealth(
            service_name=service_name,
            is_healthy=True,
            health_score=1.0,
            last_check=datetime.utcnow(),
            response_time=0.0,
            error_rate=0.0
        )
        
        # Start health monitoring if health check function provided
        if health_check_func and config.health_check_interval > 0:
            task = asyncio.create_task(
                self._monitor_service_health(service_name, health_check_func, config)
            )
            self.health_monitoring_tasks[service_name] = task
        
        self.logger.info(
            "Service registered for degradation management",
            service_name=service_name,
            config=config.__dict__
        )
    
    async def execute_with_degradation(
        self,
        service_name: str,
        operation: Callable,
        operation_key: Optional[str] = None,
        *args,
        **kwargs
    ) -> Any:
        """Execute an operation with degradation handling."""
        
        if service_name not in self.degradation_configs:
            raise ConfigurationError(f"Service {service_name} not registered")
        
        config = self.degradation_configs[service_name]
        health = self.service_health[service_name]
        
        if not operation_key:
            operation_key = getattr(operation, '__name__', 'unknown')
        
        self.logger.debug(
            "Executing operation with degradation",
            service_name=service_name,
            operation_key=operation_key,
            health_score=health.health_score,
            degradation_level=config.degradation_level.value
        )
        
        # Check if degradation is needed
        if not config.enabled or health.health_score >= config.recovery_threshold:
            # Normal execution
            try:
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(operation):
                    result = await operation(*args, **kwargs)
                else:
                    result = operation(*args, **kwargs)
                
                execution_time = time.time() - start_time
                
                # Update health metrics on success
                await self._update_health_on_success(service_name, execution_time)
                
                # Cache successful result
                await self._cache_result(service_name, operation_key, result)
                
                return result
                
            except Exception as e:
                # Update health metrics on failure
                await self._update_health_on_failure(service_name, e)
                
                # Apply degradation strategy
                return await self._apply_degradation_strategy(
                    service_name, operation_key, config, e, *args, **kwargs
                )
        
        else:
            # Service is unhealthy, apply degradation immediately
            self.logger.warning(
                "Service unhealthy, applying degradation",
                service_name=service_name,
                health_score=health.health_score,
                degradation_level=config.degradation_level.value
            )
            
            return await self._apply_degradation_strategy(
                service_name, operation_key, config, None, *args, **kwargs
            )
    
    async def _apply_degradation_strategy(
        self,
        service_name: str,
        operation_key: str,
        config: DegradationConfig,
        exception: Optional[Exception],
        *args,
        **kwargs
    ) -> Any:
        """Apply the configured degradation strategy."""
        
        strategy = config.fallback_strategy
        
        self.logger.info(
            "Applying degradation strategy",
            service_name=service_name,
            operation_key=operation_key,
            strategy=strategy.value,
            exception=str(exception) if exception else None
        )
        
        if strategy == FallbackStrategy.CACHE:
            return await self._get_cached_result(service_name, operation_key, config)
        
        elif strategy == FallbackStrategy.DEFAULT:
            return config.fallback_data
        
        elif strategy == FallbackStrategy.SIMPLIFIED:
            return await self._execute_simplified_logic(service_name, operation_key, *args, **kwargs)
        
        elif strategy == FallbackStrategy.ALTERNATIVE:
            return await self._execute_alternative_service(service_name, operation_key, *args, **kwargs)
        
        elif strategy == FallbackStrategy.QUEUE:
            return await self._queue_operation(service_name, operation_key, args, kwargs)
        
        elif strategy == FallbackStrategy.FAIL_FAST:
            if exception:
                raise exception
            else:
                raise ExternalServiceError(f"Service {service_name} is degraded")
        
        else:
            return config.fallback_data
    
    async def _get_cached_result(
        self,
        service_name: str,
        operation_key: str,
        config: DegradationConfig
    ) -> Any:
        """Get cached result for an operation."""
        
        cache = self.fallback_caches.get(service_name, {})
        
        if operation_key in cache:
            result, timestamp = cache[operation_key]
            
            # Check if cache is still valid
            if datetime.utcnow() - timestamp <= timedelta(seconds=config.cache_ttl):
                self.logger.info(
                    "Returning cached result",
                    service_name=service_name,
                    operation_key=operation_key,
                    cache_age=(datetime.utcnow() - timestamp).total_seconds()
                )
                return result
            else:
                # Remove expired cache entry
                del cache[operation_key]
        
        # No valid cache available
        self.logger.warning(
            "No valid cached result available",
            service_name=service_name,
            operation_key=operation_key
        )
        
        return config.fallback_data
    
    async def _cache_result(
        self,
        service_name: str,
        operation_key: str,
        result: Any
    ) -> None:
        """Cache a successful result."""
        
        if service_name not in self.fallback_caches:
            self.fallback_caches[service_name] = {}
        
        self.fallback_caches[service_name][operation_key] = (result, datetime.utcnow())
        
        self.logger.debug(
            "Result cached",
            service_name=service_name,
            operation_key=operation_key
        )
    
    async def _execute_simplified_logic(
        self,
        service_name: str,
        operation_key: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute simplified logic as fallback."""
        
        # This would be implemented based on specific service requirements
        # For now, return a simplified default response
        
        self.logger.info(
            "Executing simplified logic",
            service_name=service_name,
            operation_key=operation_key
        )
        
        return {"status": "degraded", "message": "Simplified response due to service degradation"}
    
    async def _execute_alternative_service(
        self,
        service_name: str,
        operation_key: str,
        *args,
        **kwargs
    ) -> Any:
        """Execute using alternative service."""
        
        # This would be implemented to call alternative services
        # For now, return a placeholder response
        
        self.logger.info(
            "Using alternative service",
            service_name=service_name,
            operation_key=operation_key
        )
        
        return {"status": "alternative", "message": "Response from alternative service"}
    
    async def _queue_operation(
        self,
        service_name: str,
        operation_key: str,
        args: tuple,
        kwargs: dict
    ) -> Any:
        """Queue operation for later processing."""
        
        config = self.degradation_configs[service_name]
        queue = self.operation_queues[service_name]
        
        if len(queue) >= config.queue_max_size:
            self.logger.warning(
                "Operation queue full, dropping oldest operation",
                service_name=service_name,
                queue_size=len(queue)
            )
            queue.pop(0)  # Remove oldest operation
        
        operation_data = {
            "operation_key": operation_key,
            "args": args,
            "kwargs": kwargs,
            "timestamp": datetime.utcnow(),
            "retry_count": 0
        }
        
        queue.append(operation_data)
        
        self.logger.info(
            "Operation queued for later processing",
            service_name=service_name,
            operation_key=operation_key,
            queue_size=len(queue)
        )
        
        return {"status": "queued", "message": "Operation queued for processing when service recovers"}
    
    async def _update_health_on_success(
        self,
        service_name: str,
        execution_time: float
    ) -> None:
        """Update service health metrics on successful operation."""
        
        health = self.service_health[service_name]
        health.consecutive_successes += 1
        health.consecutive_failures = 0
        health.response_time = execution_time
        health.last_check = datetime.utcnow()
        
        # Improve health score
        health.health_score = min(1.0, health.health_score + 0.1)
        health.is_healthy = health.health_score >= self.degradation_configs[service_name].recovery_threshold
        
        # Update degradation level based on health
        await self._update_degradation_level(service_name)
    
    async def _update_health_on_failure(
        self,
        service_name: str,
        exception: Exception
    ) -> None:
        """Update service health metrics on failed operation."""
        
        health = self.service_health[service_name]
        health.consecutive_failures += 1
        health.consecutive_successes = 0
        health.last_check = datetime.utcnow()
        
        # Decrease health score
        health.health_score = max(0.0, health.health_score - 0.2)
        health.is_healthy = health.health_score >= self.degradation_configs[service_name].recovery_threshold
        
        # Update degradation level based on health
        await self._update_degradation_level(service_name)
    
    async def _update_degradation_level(self, service_name: str) -> None:
        """Update degradation level based on service health."""
        
        health = self.service_health[service_name]
        config = self.degradation_configs[service_name]
        old_level = config.degradation_level
        
        if health.health_score >= 0.9:
            config.degradation_level = DegradationLevel.NONE
        elif health.health_score >= 0.7:
            config.degradation_level = DegradationLevel.MINIMAL
        elif health.health_score >= 0.5:
            config.degradation_level = DegradationLevel.MODERATE
        elif health.health_score >= 0.3:
            config.degradation_level = DegradationLevel.SEVERE
        else:
            config.degradation_level = DegradationLevel.EMERGENCY
        
        if old_level != config.degradation_level:
            self.logger.warning(
                "Degradation level changed",
                service_name=service_name,
                old_level=old_level.value,
                new_level=config.degradation_level.value,
                health_score=health.health_score
            )
    
    async def _monitor_service_health(
        self,
        service_name: str,
        health_check_func: Callable,
        config: DegradationConfig
    ) -> None:
        """Monitor service health continuously."""
        
        while True:
            try:
                await asyncio.sleep(config.health_check_interval)
                
                start_time = time.time()
                
                if asyncio.iscoroutinefunction(health_check_func):
                    is_healthy = await health_check_func()
                else:
                    is_healthy = health_check_func()
                
                execution_time = time.time() - start_time
                
                if is_healthy:
                    await self._update_health_on_success(service_name, execution_time)
                else:
                    await self._update_health_on_failure(service_name, Exception("Health check failed"))
                
            except asyncio.CancelledError:
                self.logger.info(
                    "Health monitoring cancelled",
                    service_name=service_name
                )
                break
            except Exception as e:
                self.logger.error(
                    "Health monitoring error",
                    service_name=service_name,
                    error=str(e)
                )
                await self._update_health_on_failure(service_name, e)
    
    def get_service_health(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get service health information."""
        
        if service_name not in self.service_health:
            return None
        
        health = self.service_health[service_name]
        config = self.degradation_configs[service_name]
        
        return {
            "service_name": service_name,
            "is_healthy": health.is_healthy,
            "health_score": health.health_score,
            "degradation_level": config.degradation_level.value,
            "fallback_strategy": config.fallback_strategy.value,
            "last_check": health.last_check.isoformat(),
            "response_time": health.response_time,
            "error_rate": health.error_rate,
            "consecutive_failures": health.consecutive_failures,
            "consecutive_successes": health.consecutive_successes,
            "queue_size": len(self.operation_queues.get(service_name, [])),
            "cache_entries": len(self.fallback_caches.get(service_name, {}))
        }
    
    def get_all_service_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health information for all registered services."""
        
        return {
            service_name: self.get_service_health(service_name)
            for service_name in self.service_health.keys()
        }
    
    async def process_queued_operations(self, service_name: str) -> int:
        """Process queued operations when service recovers."""
        
        if service_name not in self.operation_queues:
            return 0
        
        queue = self.operation_queues[service_name]
        processed_count = 0
        
        while queue and self.service_health[service_name].is_healthy:
            operation_data = queue.pop(0)
            
            try:
                # This would need to be implemented based on specific requirements
                # For now, just log the processing
                self.logger.info(
                    "Processing queued operation",
                    service_name=service_name,
                    operation_key=operation_data["operation_key"],
                    queue_age=(datetime.utcnow() - operation_data["timestamp"]).total_seconds()
                )
                
                processed_count += 1
                
            except Exception as e:
                self.logger.error(
                    "Failed to process queued operation",
                    service_name=service_name,
                    operation_key=operation_data["operation_key"],
                    error=str(e)
                )
        
        return processed_count


def degradation(
    service_name: str,
    fallback_strategy: FallbackStrategy = FallbackStrategy.DEFAULT,
    fallback_data: Optional[Any] = None,
    cache_ttl: float = 300.0,
    degradation_threshold: float = 0.3,
    recovery_threshold: float = 0.8
):
    """Decorator for adding degradation functionality to functions."""
    
    def decorator(func: Callable) -> Callable:
        config = DegradationConfig(
            fallback_strategy=fallback_strategy,
            fallback_data=fallback_data,
            cache_ttl=cache_ttl,
            degradation_threshold=degradation_threshold,
            recovery_threshold=recovery_threshold
        )
        
        # Register service if not already registered
        if service_name not in degradation_manager.degradation_configs:
            degradation_manager.register_service(service_name, config)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await degradation_manager.execute_with_degradation(
                service_name, func, None, *args, **kwargs
            )
        
        return wrapper
    
    return decorator


# Global degradation manager instance
degradation_manager = DegradationManager()
