"""
Adapter factory for creating and managing execution adapters.

This module provides a factory pattern for creating adapters and managing
their lifecycle, configuration, and health monitoring.
"""

from typing import Dict, Optional, Any, Union, Type
from datetime import datetime, timezone
from enum import Enum

from core.exceptions import ConfigurationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id

from .browser_use import BrowserUseAdapter


class AdapterType(str, Enum):
    """Supported adapter types."""
    BROWSER_USE = "browser_use"
    # LLM adapters are now handled by the unified LLM abstraction


class AdapterFactory:
    """
    Factory for creating and managing execution adapters.
    
    This factory provides a centralized way to create, configure, and manage
    different types of adapters used in the execution layer.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter factory.
        
        Args:
            config: Global configuration for adapters
        """
        self.config = config or {}
        self.adapters: Dict[str, Any] = {}
        self.adapter_configs: Dict[str, Dict[str, Any]] = {}
        
        # Initialize logger
        self.logger = StructuredLogger("adapter_factory")
        
        # Adapter type mappings (LLM adapters removed - now handled by unified abstraction)
        self.adapter_classes = {
            AdapterType.BROWSER_USE: BrowserUseAdapter,
            # Additional non-LLM adapters can be added here
        }
        
        self.logger.info(
            "Adapter factory initialized",
            supported_adapters=list(self.adapter_classes.keys()),
            config_keys=list(self.config.keys())
        )
    
    @with_correlation_id()
    async def create_adapter(
        self,
        adapter_type: Union[AdapterType, str],
        adapter_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Create an adapter instance.
        
        Args:
            adapter_type: Type of adapter to create
            adapter_id: Unique identifier for the adapter instance
            config: Adapter-specific configuration
            
        Returns:
            Initialized adapter instance
            
        Raises:
            ConfigurationError: If adapter type is not supported or configuration is invalid
        """
        correlation_id = str(id(self))  # Use object id as correlation
        
        # Convert string to enum if needed
        if isinstance(adapter_type, str):
            try:
                adapter_type = AdapterType(adapter_type.lower())
            except ValueError:
                raise ConfigurationError(f"Unsupported adapter type: {adapter_type}")
        
        # Generate adapter ID if not provided
        if not adapter_id:
            adapter_id = f"{adapter_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(
            "Creating adapter",
            adapter_type=adapter_type.value,
            adapter_id=adapter_id,
            correlation_id=correlation_id
        )
        
        try:
            # Get adapter class
            adapter_class = self.adapter_classes.get(adapter_type)
            if not adapter_class:
                raise ConfigurationError(f"No implementation found for adapter type: {adapter_type}")
            
            # Merge configurations
            merged_config = self._merge_config(adapter_type, config)
            
            # Create adapter instance
            adapter = await self._create_adapter_instance(
                adapter_class,
                adapter_type,
                merged_config,
                correlation_id
            )
            
            # Store adapter and its config
            self.adapters[adapter_id] = adapter
            self.adapter_configs[adapter_id] = {
                "type": adapter_type.value,
                "config": merged_config,
                "created_at": datetime.now(timezone.utc),
                "correlation_id": correlation_id
            }
            
            self.logger.info(
                "Adapter created successfully",
                adapter_type=adapter_type.value,
                adapter_id=adapter_id,
                correlation_id=correlation_id
            )
            
            return adapter
            
        except Exception as e:
            self.logger.error(
                "Failed to create adapter",
                adapter_type=adapter_type.value,
                adapter_id=adapter_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise ConfigurationError(f"Failed to create {adapter_type.value} adapter: {e}") from e
    
    async def get_adapter(self, adapter_id: str) -> Optional[Any]:
        """
        Get an existing adapter by ID.
        
        Args:
            adapter_id: Adapter identifier
            
        Returns:
            Adapter instance or None if not found
        """
        return self.adapters.get(adapter_id)
    
    async def remove_adapter(self, adapter_id: str) -> bool:
        """
        Remove an adapter and clean up its resources.
        
        Args:
            adapter_id: Adapter identifier
            
        Returns:
            True if adapter was removed, False if not found
        """
        if adapter_id not in self.adapters:
            return False
        
        try:
            adapter = self.adapters[adapter_id]
            
            # Try to cleanup adapter if it has cleanup methods
            if hasattr(adapter, 'cleanup'):
                await adapter.cleanup()
            elif hasattr(adapter, 'close'):
                await adapter.close()
            
            # Remove from tracking
            del self.adapters[adapter_id]
            del self.adapter_configs[adapter_id]
            
            self.logger.info(
                "Adapter removed",
                adapter_id=adapter_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to remove adapter",
                adapter_id=adapter_id,
                error=str(e)
            )
            return False
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health checks on all adapters.
        
        Returns:
            Dictionary mapping adapter IDs to their health status
        """
        health_results = {}
        
        for adapter_id, adapter in self.adapters.items():
            try:
                if hasattr(adapter, 'health_check'):
                    health_results[adapter_id] = await adapter.health_check()
                else:
                    health_results[adapter_id] = {
                        "status": "unknown",
                        "message": "Health check not supported",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    }
            except Exception as e:
                health_results[adapter_id] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
        
        return health_results
    
    def get_adapter_info(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about an adapter.
        
        Args:
            adapter_id: Adapter identifier
            
        Returns:
            Adapter information or None if not found
        """
        if adapter_id not in self.adapter_configs:
            return None
        
        config_info = self.adapter_configs[adapter_id].copy()
        config_info["created_at"] = config_info["created_at"].isoformat()
        
        return config_info
    
    def list_adapters(self) -> Dict[str, Dict[str, Any]]:
        """
        List all registered adapters.
        
        Returns:
            Dictionary mapping adapter IDs to their information
        """
        return {
            adapter_id: self.get_adapter_info(adapter_id)
            for adapter_id in self.adapters.keys()
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get factory statistics."""
        adapter_types = {}
        for config in self.adapter_configs.values():
            adapter_type = config["type"]
            adapter_types[adapter_type] = adapter_types.get(adapter_type, 0) + 1
        
        return {
            "total_adapters": len(self.adapters),
            "adapter_types": adapter_types,
            "supported_types": [t.value for t in self.adapter_classes.keys()],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def shutdown(self) -> None:
        """Shutdown the factory and clean up all adapters."""
        self.logger.info("Shutting down adapter factory")
        
        # Remove all adapters
        adapter_ids = list(self.adapters.keys())
        for adapter_id in adapter_ids:
            await self.remove_adapter(adapter_id)
        
        self.logger.info("Adapter factory shutdown complete")
    
    # Private helper methods
    
    def _merge_config(
        self,
        adapter_type: AdapterType,
        specific_config: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Merge global and adapter-specific configuration."""
        # Start with global config
        merged_config = self.config.copy()
        
        # Add adapter-type specific config from global config
        adapter_global_config = self.config.get(adapter_type.value, {})
        merged_config.update(adapter_global_config)
        
        # Add specific config (highest priority)
        if specific_config:
            merged_config.update(specific_config)
        
        return merged_config
    
    async def _create_adapter_instance(
        self,
        adapter_class: Type,
        adapter_type: AdapterType,
        config: Dict[str, Any],
        correlation_id: str
    ) -> Any:
        """Create an adapter instance based on its type."""
        try:
            if adapter_type == AdapterType.BROWSER_USE:
                adapter = adapter_class(
                    default_config=config.get("browser_config"),
                    save_logs=config.get("save_logs", True),
                    logs_base_path=config.get("logs_base_path", "logs")
                )
                # Browser-use adapter doesn't need async initialization
                return adapter

            else:
                raise ConfigurationError(f"Adapter creation not implemented for: {adapter_type}")
                
        except Exception as e:
            self.logger.error(
                "Failed to create adapter instance",
                adapter_type=adapter_type.value,
                error=str(e),
                correlation_id=correlation_id
            )
            raise


# Global factory instance
_global_factory: Optional[AdapterFactory] = None


def get_adapter_factory(config: Optional[Dict[str, Any]] = None) -> AdapterFactory:
    """
    Get the global adapter factory instance.
    
    Args:
        config: Configuration for the factory (only used on first call)
        
    Returns:
        AdapterFactory instance
    """
    global _global_factory
    
    if _global_factory is None:
        _global_factory = AdapterFactory(config)
    
    return _global_factory


async def create_adapter(
    adapter_type: Union[AdapterType, str],
    adapter_id: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    factory_config: Optional[Dict[str, Any]] = None
) -> Any:
    """
    Convenience function to create an adapter using the global factory.
    
    Args:
        adapter_type: Type of adapter to create
        adapter_id: Unique identifier for the adapter
        config: Adapter-specific configuration
        factory_config: Factory configuration (only used if factory doesn't exist)
        
    Returns:
        Initialized adapter instance
    """
    factory = get_adapter_factory(factory_config)
    return await factory.create_adapter(adapter_type, adapter_id, config)
