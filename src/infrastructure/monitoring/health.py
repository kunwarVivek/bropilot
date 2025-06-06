"""
Health monitoring system.

This module provides comprehensive health monitoring for all system components
with detailed status reporting and alerting capabilities.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional, Callable, Awaitable
from datetime import datetime, timedelta
from enum import Enum
import psutil
import aiohttp

from core.interfaces import IHealthMonitor
from core.exceptions import HealthCheckError
from src.infrastructure.storage.database import get_database_manager


class HealthStatus(str, Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ComponentHealth:
    """Health information for a component."""
    
    def __init__(
        self,
        name: str,
        status: HealthStatus,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[float] = None
    ):
        self.name = name
        self.status = status
        self.message = message
        self.details = details or {}
        self.response_time_ms = response_time_ms
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "name": self.name,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
            "healthy": self.status == HealthStatus.HEALTHY
        }
        
        if self.message:
            result["message"] = self.message
        
        if self.details:
            result["details"] = self.details
        
        if self.response_time_ms is not None:
            result["response_time_ms"] = self.response_time_ms
        
        return result


class HealthMonitor(IHealthMonitor):
    """Comprehensive health monitoring system."""
    
    def __init__(self):
        """Initialize health monitor."""
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, ComponentHealth] = {}
        self.check_timeouts: Dict[str, float] = {}
        self.check_intervals: Dict[str, float] = {}
        self.last_check_times: Dict[str, datetime] = {}
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check of all components."""
        start_time = time.time()
        
        # Run all health checks
        component_results = {}
        overall_healthy = True
        
        # Built-in system checks
        system_checks = {
            "system": self._check_system_health,
            "database": self._check_database_health,
            "memory": self._check_memory_health,
            "disk": self._check_disk_health
        }
        
        # Combine with registered checks
        all_checks = {**system_checks, **self.health_checks}
        
        # Run checks concurrently
        tasks = []
        for component_name, check_function in all_checks.items():
            task = asyncio.create_task(
                self._run_health_check_with_timeout(component_name, check_function)
            )
            tasks.append((component_name, task))
        
        # Wait for all checks to complete
        for component_name, task in tasks:
            try:
                component_health = await task
                component_results[component_name] = component_health.to_dict()
                
                # Update overall health status
                if component_health.status != HealthStatus.HEALTHY:
                    overall_healthy = False
                
                # Cache result
                self.last_check_results[component_name] = component_health
                self.last_check_times[component_name] = datetime.utcnow()
                
            except Exception as e:
                component_results[component_name] = {
                    "name": component_name,
                    "status": HealthStatus.UNHEALTHY.value,
                    "healthy": False,
                    "message": f"Health check failed: {str(e)}",
                    "timestamp": datetime.utcnow().isoformat()
                }
                overall_healthy = False
        
        total_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        return {
            "status": HealthStatus.HEALTHY.value if overall_healthy else HealthStatus.UNHEALTHY.value,
            "healthy": overall_healthy,
            "timestamp": datetime.utcnow().isoformat(),
            "response_time_ms": total_time,
            "components": component_results,
            "summary": {
                "total_components": len(component_results),
                "healthy_components": sum(1 for c in component_results.values() if c["healthy"]),
                "unhealthy_components": sum(1 for c in component_results.values() if not c["healthy"])
            }
        }
    
    async def check_component_health(self, component_name: str) -> bool:
        """Check health of a specific component."""
        if component_name not in self.health_checks:
            return False
        
        try:
            component_health = await self._run_health_check_with_timeout(
                component_name, 
                self.health_checks[component_name]
            )
            return component_health.status == HealthStatus.HEALTHY
        except Exception:
            return False
    
    def register_health_check(
        self, 
        component_name: str, 
        check_function: Callable,
        timeout: float = 10.0,
        interval: float = 30.0
    ) -> None:
        """Register a health check function for a component."""
        self.health_checks[component_name] = check_function
        self.check_timeouts[component_name] = timeout
        self.check_intervals[component_name] = interval
    
    async def _run_health_check_with_timeout(
        self, 
        component_name: str, 
        check_function: Callable
    ) -> ComponentHealth:
        """Run a health check with timeout and error handling."""
        timeout = self.check_timeouts.get(component_name, 10.0)
        start_time = time.time()
        
        try:
            # Run the health check with timeout
            if asyncio.iscoroutinefunction(check_function):
                result = await asyncio.wait_for(check_function(), timeout=timeout)
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(check_function), 
                    timeout=timeout
                )
            
            response_time = (time.time() - start_time) * 1000
            
            # Handle different return types
            if isinstance(result, bool):
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
                return ComponentHealth(
                    name=component_name,
                    status=status,
                    response_time_ms=response_time
                )
            elif isinstance(result, dict):
                status = HealthStatus.HEALTHY if result.get("healthy", True) else HealthStatus.UNHEALTHY
                return ComponentHealth(
                    name=component_name,
                    status=status,
                    message=result.get("message"),
                    details=result.get("details"),
                    response_time_ms=response_time
                )
            else:
                return ComponentHealth(
                    name=component_name,
                    status=HealthStatus.HEALTHY,
                    details={"result": str(result)},
                    response_time_ms=response_time
                )
        
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timed out after {timeout}s"
            )
        except Exception as e:
            return ComponentHealth(
                name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check failed: {str(e)}"
            )
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """Check overall system health."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Load average (Unix systems)
            try:
                load_avg = psutil.getloadavg()
                load_1min, load_5min, load_15min = load_avg
            except AttributeError:
                # Windows doesn't have load average
                load_1min = load_5min = load_15min = None
            
            # System uptime
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time
            
            details = {
                "cpu_percent": cpu_percent,
                "uptime_seconds": uptime_seconds,
                "uptime_hours": uptime_seconds / 3600
            }
            
            if load_1min is not None:
                details.update({
                    "load_1min": load_1min,
                    "load_5min": load_5min,
                    "load_15min": load_15min
                })
            
            # Determine health status
            healthy = cpu_percent < 90  # Consider unhealthy if CPU > 90%
            
            return {
                "healthy": healthy,
                "message": f"CPU: {cpu_percent}%, Uptime: {uptime_seconds/3600:.1f}h",
                "details": details
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "message": f"System check failed: {str(e)}"
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database connectivity and performance."""
        try:
            db_manager = get_database_manager()
            
            # Test connection
            start_time = time.time()
            is_healthy = await db_manager.health_check()
            response_time = (time.time() - start_time) * 1000
            
            if is_healthy:
                # Get connection pool info
                connection_info = await db_manager.get_connection_info()
                
                return {
                    "healthy": True,
                    "message": f"Database connected (response: {response_time:.1f}ms)",
                    "details": {
                        "response_time_ms": response_time,
                        **connection_info
                    }
                }
            else:
                return {
                    "healthy": False,
                    "message": "Database connection failed"
                }
        
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Database check failed: {str(e)}"
            }
    
    async def _check_memory_health(self) -> Dict[str, Any]:
        """Check memory usage."""
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            details = {
                "total_gb": memory.total / (1024**3),
                "available_gb": memory.available / (1024**3),
                "used_percent": memory.percent,
                "swap_used_percent": swap.percent
            }
            
            # Consider unhealthy if memory usage > 90% or swap > 50%
            healthy = memory.percent < 90 and swap.percent < 50
            
            return {
                "healthy": healthy,
                "message": f"Memory: {memory.percent}%, Swap: {swap.percent}%",
                "details": details
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Memory check failed: {str(e)}"
            }
    
    async def _check_disk_health(self) -> Dict[str, Any]:
        """Check disk usage."""
        try:
            disk = psutil.disk_usage('/')
            
            details = {
                "total_gb": disk.total / (1024**3),
                "free_gb": disk.free / (1024**3),
                "used_percent": (disk.used / disk.total) * 100
            }
            
            # Consider unhealthy if disk usage > 90%
            healthy = details["used_percent"] < 90
            
            return {
                "healthy": healthy,
                "message": f"Disk usage: {details['used_percent']:.1f}%",
                "details": details
            }
        
        except Exception as e:
            return {
                "healthy": False,
                "message": f"Disk check failed: {str(e)}"
            }
    
    def get_component_status(self, component_name: str) -> Optional[ComponentHealth]:
        """Get cached status for a component."""
        return self.last_check_results.get(component_name)
    
    def get_all_component_statuses(self) -> Dict[str, ComponentHealth]:
        """Get all cached component statuses."""
        return self.last_check_results.copy()
    
    async def wait_for_healthy(
        self, 
        component_name: str, 
        timeout: float = 60.0,
        check_interval: float = 5.0
    ) -> bool:
        """Wait for a component to become healthy."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                is_healthy = await self.check_component_health(component_name)
                if is_healthy:
                    return True
            except Exception:
                pass
            
            await asyncio.sleep(check_interval)
        
        return False


# Global health monitor instance
health_monitor = HealthMonitor()
