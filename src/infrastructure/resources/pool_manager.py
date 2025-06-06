"""
Resource pooling for browsers and connections.

This module provides comprehensive resource pooling with lifecycle management,
health monitoring, and automatic scaling for various resource types.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import uuid
import weakref

from core.exceptions import ResourceError, ConfigurationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


T = TypeVar('T')


class ResourceState(str, Enum):
    """Resource state enumeration."""
    AVAILABLE = "available"
    IN_USE = "in_use"
    MAINTENANCE = "maintenance"
    FAILED = "failed"
    CREATING = "creating"
    DESTROYING = "destroying"


class PoolStrategy(str, Enum):
    """Pool management strategy enumeration."""
    FIXED = "fixed"          # Fixed pool size
    DYNAMIC = "dynamic"      # Dynamic scaling based on demand
    ELASTIC = "elastic"      # Elastic scaling with min/max bounds


@dataclass
class PoolConfig:
    """Configuration for resource pool."""
    min_size: int = 1
    max_size: int = 10
    initial_size: int = 2
    strategy: PoolStrategy = PoolStrategy.DYNAMIC
    max_idle_time: float = 300.0  # 5 minutes
    health_check_interval: float = 60.0  # 1 minute
    creation_timeout: float = 30.0
    destruction_timeout: float = 10.0
    max_retries: int = 3
    scale_up_threshold: float = 0.8  # Scale up when 80% utilized
    scale_down_threshold: float = 0.3  # Scale down when 30% utilized
    scale_factor: float = 1.5  # Scale by 50%


@dataclass
class ResourceInfo:
    """Information about a pooled resource."""
    resource_id: str
    resource: Any
    state: ResourceState = ResourceState.AVAILABLE
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used: datetime = field(default_factory=datetime.utcnow)
    last_health_check: Optional[datetime] = None
    usage_count: int = 0
    error_count: int = 0
    current_user: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ResourceFactory(ABC, Generic[T]):
    """Abstract factory for creating and managing resources."""
    
    @abstractmethod
    async def create_resource(self) -> T:
        """Create a new resource instance."""
        pass
    
    @abstractmethod
    async def destroy_resource(self, resource: T) -> None:
        """Destroy a resource instance."""
        pass
    
    @abstractmethod
    async def health_check(self, resource: T) -> bool:
        """Check if a resource is healthy."""
        pass
    
    @abstractmethod
    async def reset_resource(self, resource: T) -> bool:
        """Reset a resource to clean state."""
        pass


class ResourcePool(Generic[T]):
    """Generic resource pool with lifecycle management."""
    
    def __init__(
        self,
        name: str,
        factory: ResourceFactory[T],
        config: PoolConfig
    ):
        """Initialize resource pool."""
        self.name = name
        self.factory = factory
        self.config = config
        self.logger = StructuredLogger(f"resource_pool.{name}")
        
        # Pool state
        self.resources: Dict[str, ResourceInfo] = {}
        self.available_resources: Set[str] = set()
        self.in_use_resources: Set[str] = set()
        
        # Synchronization
        self.pool_lock = asyncio.Lock()
        self.resource_semaphore = asyncio.Semaphore(config.max_size)
        
        # Background tasks
        self.health_check_task: Optional[asyncio.Task] = None
        self.scaling_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Statistics
        self.total_created = 0
        self.total_destroyed = 0
        self.total_acquisitions = 0
        self.total_releases = 0
        self.total_health_checks = 0
        self.total_failures = 0
        
        # Pool lifecycle
        self.is_initialized = False
        self.is_shutdown = False
    
    async def initialize(self) -> None:
        """Initialize the resource pool."""
        if self.is_initialized:
            return
        
        self.logger.info(
            "Initializing resource pool",
            pool_name=self.name,
            config=self.config.__dict__
        )
        
        try:
            # Create initial resources
            for _ in range(self.config.initial_size):
                await self._create_resource()
            
            # Start background tasks
            self.health_check_task = asyncio.create_task(self._health_check_loop())
            self.scaling_task = asyncio.create_task(self._scaling_loop())
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            
            self.is_initialized = True
            
            self.logger.info(
                "Resource pool initialized",
                pool_name=self.name,
                initial_size=len(self.resources)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to initialize resource pool",
                pool_name=self.name,
                error=str(e)
            )
            raise ResourceError(f"Pool initialization failed: {e}") from e
    
    async def acquire(self, user_id: Optional[str] = None, timeout: Optional[float] = None) -> T:
        """Acquire a resource from the pool."""
        if not self.is_initialized:
            await self.initialize()
        
        if self.is_shutdown:
            raise ResourceError(f"Pool {self.name} is shutdown")
        
        start_time = time.time()
        
        try:
            # Wait for available slot
            if timeout:
                await asyncio.wait_for(
                    self.resource_semaphore.acquire(),
                    timeout=timeout
                )
            else:
                await self.resource_semaphore.acquire()
            
            async with self.pool_lock:
                # Find available resource
                resource_info = await self._get_available_resource()
                
                if not resource_info:
                    # Try to create new resource if pool not at max
                    if len(self.resources) < self.config.max_size:
                        resource_info = await self._create_resource()
                    else:
                        self.resource_semaphore.release()
                        raise ResourceError(f"No resources available in pool {self.name}")
                
                # Mark resource as in use
                resource_info.state = ResourceState.IN_USE
                resource_info.current_user = user_id
                resource_info.last_used = datetime.utcnow()
                resource_info.usage_count += 1
                
                self.available_resources.discard(resource_info.resource_id)
                self.in_use_resources.add(resource_info.resource_id)
                
                self.total_acquisitions += 1
                
                acquisition_time = time.time() - start_time
                
                self.logger.debug(
                    "Resource acquired",
                    pool_name=self.name,
                    resource_id=resource_info.resource_id,
                    user_id=user_id,
                    acquisition_time=acquisition_time,
                    pool_utilization=len(self.in_use_resources) / len(self.resources)
                )
                
                return resource_info.resource
        
        except Exception as e:
            self.resource_semaphore.release()
            self.logger.error(
                "Failed to acquire resource",
                pool_name=self.name,
                user_id=user_id,
                error=str(e)
            )
            raise
    
    async def release(self, resource: T, user_id: Optional[str] = None) -> None:
        """Release a resource back to the pool."""
        
        async with self.pool_lock:
            # Find resource info
            resource_info = None
            for info in self.resources.values():
                if info.resource is resource:
                    resource_info = info
                    break
            
            if not resource_info:
                self.logger.warning(
                    "Attempted to release unknown resource",
                    pool_name=self.name,
                    user_id=user_id
                )
                return
            
            # Reset resource if possible
            try:
                reset_success = await self.factory.reset_resource(resource)
                if not reset_success:
                    self.logger.warning(
                        "Resource reset failed, marking for destruction",
                        pool_name=self.name,
                        resource_id=resource_info.resource_id
                    )
                    await self._destroy_resource(resource_info.resource_id)
                    self.resource_semaphore.release()
                    return
            
            except Exception as e:
                self.logger.error(
                    "Resource reset error, destroying resource",
                    pool_name=self.name,
                    resource_id=resource_info.resource_id,
                    error=str(e)
                )
                await self._destroy_resource(resource_info.resource_id)
                self.resource_semaphore.release()
                return
            
            # Mark resource as available
            resource_info.state = ResourceState.AVAILABLE
            resource_info.current_user = None
            resource_info.last_used = datetime.utcnow()
            
            self.in_use_resources.discard(resource_info.resource_id)
            self.available_resources.add(resource_info.resource_id)
            
            self.total_releases += 1
            
            self.logger.debug(
                "Resource released",
                pool_name=self.name,
                resource_id=resource_info.resource_id,
                user_id=user_id,
                usage_count=resource_info.usage_count
            )
            
            self.resource_semaphore.release()
    
    async def _get_available_resource(self) -> Optional[ResourceInfo]:
        """Get an available resource from the pool."""
        
        # Find healthy available resource
        for resource_id in list(self.available_resources):
            resource_info = self.resources[resource_id]
            
            if resource_info.state == ResourceState.AVAILABLE:
                # Check if resource is still healthy
                try:
                    is_healthy = await self.factory.health_check(resource_info.resource)
                    if is_healthy:
                        return resource_info
                    else:
                        # Remove unhealthy resource
                        await self._destroy_resource(resource_id)
                except Exception as e:
                    self.logger.error(
                        "Health check failed for resource",
                        pool_name=self.name,
                        resource_id=resource_id,
                        error=str(e)
                    )
                    await self._destroy_resource(resource_id)
        
        return None
    
    async def _create_resource(self) -> ResourceInfo:
        """Create a new resource."""
        
        resource_id = str(uuid.uuid4())
        
        self.logger.debug(
            "Creating new resource",
            pool_name=self.name,
            resource_id=resource_id
        )
        
        try:
            # Create resource with timeout
            resource = await asyncio.wait_for(
                self.factory.create_resource(),
                timeout=self.config.creation_timeout
            )
            
            resource_info = ResourceInfo(
                resource_id=resource_id,
                resource=resource,
                state=ResourceState.AVAILABLE
            )
            
            self.resources[resource_id] = resource_info
            self.available_resources.add(resource_id)
            self.total_created += 1
            
            self.logger.info(
                "Resource created successfully",
                pool_name=self.name,
                resource_id=resource_id,
                pool_size=len(self.resources)
            )
            
            return resource_info
            
        except Exception as e:
            self.logger.error(
                "Failed to create resource",
                pool_name=self.name,
                resource_id=resource_id,
                error=str(e)
            )
            self.total_failures += 1
            raise ResourceError(f"Resource creation failed: {e}") from e
    
    async def _destroy_resource(self, resource_id: str) -> None:
        """Destroy a resource."""
        
        if resource_id not in self.resources:
            return
        
        resource_info = self.resources[resource_id]
        
        self.logger.debug(
            "Destroying resource",
            pool_name=self.name,
            resource_id=resource_id
        )
        
        try:
            resource_info.state = ResourceState.DESTROYING
            
            # Destroy resource with timeout
            await asyncio.wait_for(
                self.factory.destroy_resource(resource_info.resource),
                timeout=self.config.destruction_timeout
            )
            
            # Remove from tracking
            del self.resources[resource_id]
            self.available_resources.discard(resource_id)
            self.in_use_resources.discard(resource_id)
            self.total_destroyed += 1
            
            self.logger.info(
                "Resource destroyed successfully",
                pool_name=self.name,
                resource_id=resource_id,
                pool_size=len(self.resources)
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to destroy resource",
                pool_name=self.name,
                resource_id=resource_id,
                error=str(e)
            )
            # Mark as failed but keep tracking
            resource_info.state = ResourceState.FAILED
    
    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        
        while not self.is_shutdown:
            try:
                await asyncio.sleep(self.config.health_check_interval)
                
                if self.is_shutdown:
                    break
                
                await self._perform_health_checks()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Health check loop error",
                    pool_name=self.name,
                    error=str(e)
                )
    
    async def _perform_health_checks(self) -> None:
        """Perform health checks on all resources."""
        
        async with self.pool_lock:
            unhealthy_resources = []
            
            for resource_id, resource_info in self.resources.items():
                if resource_info.state in [ResourceState.AVAILABLE, ResourceState.IN_USE]:
                    try:
                        is_healthy = await self.factory.health_check(resource_info.resource)
                        resource_info.last_health_check = datetime.utcnow()
                        self.total_health_checks += 1
                        
                        if not is_healthy:
                            unhealthy_resources.append(resource_id)
                            resource_info.error_count += 1
                    
                    except Exception as e:
                        self.logger.error(
                            "Health check error",
                            pool_name=self.name,
                            resource_id=resource_id,
                            error=str(e)
                        )
                        unhealthy_resources.append(resource_id)
                        resource_info.error_count += 1
            
            # Remove unhealthy resources
            for resource_id in unhealthy_resources:
                await self._destroy_resource(resource_id)
    
    async def _scaling_loop(self) -> None:
        """Background scaling loop."""
        
        while not self.is_shutdown:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if self.is_shutdown:
                    break
                
                if self.config.strategy in [PoolStrategy.DYNAMIC, PoolStrategy.ELASTIC]:
                    await self._auto_scale()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Scaling loop error",
                    pool_name=self.name,
                    error=str(e)
                )
    
    async def _auto_scale(self) -> None:
        """Automatically scale the pool based on utilization."""
        
        async with self.pool_lock:
            total_resources = len(self.resources)
            in_use_resources = len(self.in_use_resources)
            
            if total_resources == 0:
                return
            
            utilization = in_use_resources / total_resources
            
            # Scale up if utilization is high
            if (utilization >= self.config.scale_up_threshold and 
                total_resources < self.config.max_size):
                
                scale_count = max(1, int(total_resources * (self.config.scale_factor - 1)))
                scale_count = min(scale_count, self.config.max_size - total_resources)
                
                self.logger.info(
                    "Scaling up pool",
                    pool_name=self.name,
                    current_size=total_resources,
                    scale_count=scale_count,
                    utilization=utilization
                )
                
                for _ in range(scale_count):
                    try:
                        await self._create_resource()
                    except Exception as e:
                        self.logger.error(
                            "Failed to scale up",
                            pool_name=self.name,
                            error=str(e)
                        )
                        break
            
            # Scale down if utilization is low
            elif (utilization <= self.config.scale_down_threshold and 
                  total_resources > self.config.min_size):
                
                scale_count = max(1, int(total_resources * (1 - self.config.scale_down_threshold)))
                scale_count = min(scale_count, total_resources - self.config.min_size)
                
                # Only scale down available resources
                available_count = len(self.available_resources)
                scale_count = min(scale_count, available_count)
                
                if scale_count > 0:
                    self.logger.info(
                        "Scaling down pool",
                        pool_name=self.name,
                        current_size=total_resources,
                        scale_count=scale_count,
                        utilization=utilization
                    )
                    
                    resources_to_remove = list(self.available_resources)[:scale_count]
                    for resource_id in resources_to_remove:
                        await self._destroy_resource(resource_id)
    
    async def _cleanup_loop(self) -> None:
        """Background cleanup loop for idle resources."""
        
        while not self.is_shutdown:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                if self.is_shutdown:
                    break
                
                await self._cleanup_idle_resources()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Cleanup loop error",
                    pool_name=self.name,
                    error=str(e)
                )
    
    async def _cleanup_idle_resources(self) -> None:
        """Clean up idle resources that exceed max idle time."""
        
        if self.config.max_idle_time <= 0:
            return
        
        async with self.pool_lock:
            current_time = datetime.utcnow()
            idle_resources = []
            
            for resource_id, resource_info in self.resources.items():
                if (resource_info.state == ResourceState.AVAILABLE and
                    resource_id in self.available_resources):
                    
                    idle_time = (current_time - resource_info.last_used).total_seconds()
                    
                    if (idle_time > self.config.max_idle_time and
                        len(self.resources) > self.config.min_size):
                        idle_resources.append(resource_id)
            
            # Remove idle resources
            for resource_id in idle_resources:
                self.logger.info(
                    "Removing idle resource",
                    pool_name=self.name,
                    resource_id=resource_id,
                    idle_time=idle_time
                )
                await self._destroy_resource(resource_id)
    
    async def shutdown(self) -> None:
        """Shutdown the resource pool."""
        
        if self.is_shutdown:
            return
        
        self.logger.info(
            "Shutting down resource pool",
            pool_name=self.name
        )
        
        self.is_shutdown = True
        
        # Cancel background tasks
        if self.health_check_task:
            self.health_check_task.cancel()
        if self.scaling_task:
            self.scaling_task.cancel()
        if self.cleanup_task:
            self.cleanup_task.cancel()
        
        # Wait for background tasks to finish
        tasks = [t for t in [self.health_check_task, self.scaling_task, self.cleanup_task] if t]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        # Destroy all resources
        async with self.pool_lock:
            resource_ids = list(self.resources.keys())
            for resource_id in resource_ids:
                await self._destroy_resource(resource_id)
        
        self.logger.info(
            "Resource pool shutdown complete",
            pool_name=self.name
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get pool statistics."""
        
        total_resources = len(self.resources)
        available_resources = len(self.available_resources)
        in_use_resources = len(self.in_use_resources)
        
        return {
            "pool_name": self.name,
            "total_resources": total_resources,
            "available_resources": available_resources,
            "in_use_resources": in_use_resources,
            "utilization": in_use_resources / total_resources if total_resources > 0 else 0,
            "total_created": self.total_created,
            "total_destroyed": self.total_destroyed,
            "total_acquisitions": self.total_acquisitions,
            "total_releases": self.total_releases,
            "total_health_checks": self.total_health_checks,
            "total_failures": self.total_failures,
            "config": self.config.__dict__,
            "is_initialized": self.is_initialized,
            "is_shutdown": self.is_shutdown
        }
