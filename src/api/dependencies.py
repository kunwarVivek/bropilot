"""
FastAPI dependency injection providers.

This module provides dependency injection functions for FastAPI endpoints,
managing component lifecycle and providing clean separation of concerns.
"""

import asyncio
from typing import Optional, Dict, Any
from functools import lru_cache
from fastapi import Depends, HTTPException

from src.infrastructure.logging.logger import StructuredLogger
from src.execution.feature_flags import get_feature_flag_manager, FeatureFlagManager
from src.execution.legacy_bridge import get_legacy_bridge, LegacyTaskBridge
from src.orchestration.workflow_engine import WorkflowEngine
from src.orchestration.task_scheduler import TaskScheduler, create_task_scheduler
from src.execution.task_executor import TaskExecutor
from src.execution.browser_manager import BrowserManager
from src.execution.llm_provider import TaskLLMProvider, create_llm_provider, LLMProviderType


# Global component instances
_workflow_engine: Optional[WorkflowEngine] = None
_task_scheduler: Optional[TaskScheduler] = None
_task_executor: Optional[TaskExecutor] = None
_browser_manager: Optional[BrowserManager] = None
_llm_provider: Optional[TaskLLMProvider] = None
_logger: Optional[StructuredLogger] = None
_feature_flags: Optional[FeatureFlagManager] = None
_legacy_bridge: Optional[LegacyTaskBridge] = None

# Initialization flags
_components_initialized = False
_initialization_lock = asyncio.Lock()


async def initialize_components(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Initialize all system components.
    
    This function initializes all the core components needed for the API
    to function properly. It should be called during application startup.
    
    Args:
        config: Optional configuration dictionary
    """
    global _components_initialized, _workflow_engine, _task_scheduler
    global _task_executor, _browser_manager, _llm_provider, _logger
    global _feature_flags, _legacy_bridge
    
    async with _initialization_lock:
        if _components_initialized:
            return
        
        config = config or {}
        
        try:
            # Initialize logger first
            _logger = StructuredLogger("api_dependencies")
            _logger.info("Initializing API components")
            
            # Initialize feature flags
            _feature_flags = get_feature_flag_manager()
            _logger.info("Feature flags manager initialized")
            
            # Initialize legacy bridge (which handles component creation based on feature flags)
            bridge_config = {
                "use_new_execution": _feature_flags.is_enabled("use_new_execution_layer"),
                "fallback_to_legacy": _feature_flags.is_enabled("fallback_to_legacy"),
                "llm_provider": config.get("llm_provider", "gemini"),
                "llm_config": config.get("llm_config", {}),
                "browser_config": config.get("browser_config", {}),
                "enable_browser_pooling": _feature_flags.is_enabled("use_browser_pooling"),
                "default_timeout": config.get("default_timeout", 300),
                "save_logs": config.get("save_logs", True),
                "logs_base_path": config.get("logs_base_path", "logs")
            }
            
            _legacy_bridge = get_legacy_bridge(bridge_config)
            
            # Initialize bridge if new execution is enabled
            if _feature_flags.is_enabled("use_new_execution_layer"):
                await _legacy_bridge.initialize()
                _logger.info("Legacy bridge initialized with new execution layer")
            else:
                _logger.info("Legacy bridge initialized in legacy mode")
            
            # Get components from bridge or create directly
            if hasattr(_legacy_bridge, 'task_executor') and _legacy_bridge.task_executor:
                _task_executor = _legacy_bridge.task_executor
                _browser_manager = _legacy_bridge.browser_manager
                _llm_provider = _legacy_bridge.llm_provider
                _logger.info("Components obtained from legacy bridge")
            else:
                # Create components directly for API-only usage
                await _create_components_directly(config)
                _logger.info("Components created directly")
            
            # Initialize workflow engine if enabled
            if _feature_flags.is_enabled("use_enhanced_workflow") and _task_executor:
                _workflow_engine = WorkflowEngine(
                    task_executor=_task_executor,
                    default_execution_mode="dependency_based"
                )
                await _workflow_engine.initialize()
                _logger.info("Workflow engine initialized")
            
            # Initialize task scheduler if enabled
            if _feature_flags.is_enabled("use_task_scheduling"):
                _task_scheduler = create_task_scheduler(
                    strategy="intelligent",
                    max_concurrent_tasks=config.get("max_concurrent_tasks", 5),
                    available_memory=config.get("available_memory", 8.0),
                    available_cpu=config.get("available_cpu", 4.0),
                    available_browsers=config.get("available_browsers", 3)
                )
                await _task_scheduler.start()
                _logger.info("Task scheduler initialized and started")
            
            _components_initialized = True
            _logger.info("All API components initialized successfully")
            
        except Exception as e:
            _logger.error("Failed to initialize API components", error=str(e))
            raise


async def _create_components_directly(config: Dict[str, Any]) -> None:
    """Create components directly when not using the bridge."""
    global _task_executor, _browser_manager, _llm_provider
    
    try:
        # Create browser manager
        _browser_manager = BrowserManager(
            enable_pooling=config.get("enable_browser_pooling", False),
            default_browser_config=config.get("browser_config", {})
        )
        await _browser_manager.initialize()
        
        # Create LLM provider
        _llm_provider = await create_llm_provider(
            provider_type=LLMProviderType.GEMINI,
            config=config.get("llm_config", {}),
            fallback_provider=config.get("fallback_llm_provider")
        )
        
        # Create task executor
        _task_executor = TaskExecutor(
            browser_manager=_browser_manager,
            llm_provider=_llm_provider,
            default_timeout=config.get("default_timeout", 300),
            save_logs=config.get("save_logs", True),
            logs_base_path=config.get("logs_base_path", "logs")
        )
        
    except Exception as e:
        _logger.error("Failed to create components directly", error=str(e))
        raise


async def shutdown_components() -> None:
    """
    Shutdown all system components.
    
    This function should be called during application shutdown to properly
    clean up resources and stop background tasks.
    """
    global _components_initialized, _workflow_engine, _task_scheduler
    global _task_executor, _browser_manager, _llm_provider, _legacy_bridge
    
    async with _initialization_lock:
        if not _components_initialized:
            return
        
        try:
            if _logger:
                _logger.info("Shutting down API components")
            
            # Stop task scheduler
            if _task_scheduler:
                await _task_scheduler.stop()
            
            # Shutdown workflow engine
            if _workflow_engine:
                await _workflow_engine.shutdown()
            
            # Shutdown browser manager
            if _browser_manager:
                await _browser_manager.shutdown()
            
            # Shutdown legacy bridge
            if _legacy_bridge:
                await _legacy_bridge.shutdown()
            
            # Reset global variables
            _workflow_engine = None
            _task_scheduler = None
            _task_executor = None
            _browser_manager = None
            _llm_provider = None
            _legacy_bridge = None
            
            _components_initialized = False
            
            if _logger:
                _logger.info("API components shutdown complete")
            
        except Exception as e:
            if _logger:
                _logger.error("Error during component shutdown", error=str(e))


# Dependency injection functions

async def get_workflow_engine() -> Optional[WorkflowEngine]:
    """Get the workflow engine instance."""
    if not _components_initialized:
        raise HTTPException(
            status_code=503,
            detail="System components not initialized"
        )
    return _workflow_engine


async def get_task_scheduler() -> Optional[TaskScheduler]:
    """Get the task scheduler instance."""
    if not _components_initialized:
        raise HTTPException(
            status_code=503,
            detail="System components not initialized"
        )
    return _task_scheduler


async def get_task_executor() -> Optional[TaskExecutor]:
    """Get the task executor instance."""
    if not _components_initialized:
        raise HTTPException(
            status_code=503,
            detail="System components not initialized"
        )
    return _task_executor


async def get_browser_manager() -> Optional[BrowserManager]:
    """Get the browser manager instance."""
    if not _components_initialized:
        raise HTTPException(
            status_code=503,
            detail="System components not initialized"
        )
    return _browser_manager


async def get_llm_provider() -> Optional[TaskLLMProvider]:
    """Get the LLM provider instance."""
    if not _components_initialized:
        raise HTTPException(
            status_code=503,
            detail="System components not initialized"
        )
    return _llm_provider


async def get_logger() -> StructuredLogger:
    """Get the logger instance."""
    if not _logger:
        # Create a default logger if not initialized
        return StructuredLogger("api_fallback")
    return _logger


async def get_feature_flags() -> Optional[FeatureFlagManager]:
    """Get the feature flags manager instance."""
    return _feature_flags


async def get_legacy_bridge() -> Optional[LegacyTaskBridge]:
    """Get the legacy bridge instance."""
    return _legacy_bridge


# Health check dependency
async def check_system_health() -> Dict[str, Any]:
    """
    Check the health of all system components.
    
    Returns:
        Dictionary with health status of all components
    """
    health_status = {
        "components_initialized": _components_initialized,
        "workflow_engine": _workflow_engine is not None,
        "task_scheduler": _task_scheduler is not None,
        "task_executor": _task_executor is not None,
        "browser_manager": _browser_manager is not None,
        "llm_provider": _llm_provider is not None,
        "feature_flags": _feature_flags is not None,
        "legacy_bridge": _legacy_bridge is not None
    }
    
    return health_status


# Configuration dependency
@lru_cache()
def get_api_config() -> Dict[str, Any]:
    """
    Get API configuration.
    
    This function returns the API configuration, cached for performance.
    In a production environment, this would load from environment variables
    or configuration files.
    """
    return {
        "api_version": "1.0.0",
        "max_request_size": 10 * 1024 * 1024,  # 10MB
        "request_timeout": 300,  # 5 minutes
        "enable_cors": True,
        "cors_origins": ["*"],
        "enable_docs": True,
        "log_level": "INFO"
    }


# Authentication dependency (placeholder)
async def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Get current authenticated user.
    
    This is a placeholder for authentication. In a production environment,
    this would validate JWT tokens or API keys.
    """
    # For now, return a default user
    return {
        "user_id": "api_user",
        "username": "api",
        "permissions": ["read", "write", "admin"]
    }


# Rate limiting dependency (placeholder)
async def check_rate_limit() -> bool:
    """
    Check rate limiting for the current request.
    
    This is a placeholder for rate limiting. In a production environment,
    this would implement proper rate limiting logic.
    """
    # For now, always allow requests
    return True
