"""
Enhanced browser manager with comprehensive resource management.

This module provides advanced browser lifecycle management with memory monitoring,
automatic cleanup, resource leak detection, and performance optimization.
"""

import asyncio
import uuid
import psutil
import gc
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone, timedelta

from browser_use import Browser, BrowserConfig

from core.interfaces import IBrowserManager
from core.exceptions import BrowserError, ConfigurationError, ResourceError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.infrastructure.resources.browser_pool import BrowserPool, BrowserFactory
from src.infrastructure.resources.pool_manager import PoolConfig
from .enhanced_error_recovery import EnhancedErrorRecovery


class EnhancedBrowserManager(IBrowserManager):
    """
    Enhanced browser manager with comprehensive resource management.

    This manager provides advanced browser lifecycle management with memory monitoring,
    automatic cleanup, resource leak detection, and performance optimization.
    """

    def __init__(
        self,
        browser_pool: Optional[BrowserPool] = None,
        default_browser_config: Optional[Dict[str, Any]] = None,
        enable_pooling: bool = True,
        pool_config: Optional[PoolConfig] = None,
        memory_threshold: float = 0.8,  # 80% memory usage threshold
        cleanup_interval: int = 300,    # 5 minutes cleanup interval
        max_session_duration: int = 3600  # 1 hour max session duration
    ):
        """
        Initialize the enhanced browser manager.

        Args:
            browser_pool: Existing browser pool instance (optional)
            default_browser_config: Default browser configuration
            enable_pooling: Whether to use browser pooling
            pool_config: Configuration for browser pool
            memory_threshold: Memory usage threshold for cleanup
            cleanup_interval: Interval for automatic cleanup (seconds)
            max_session_duration: Maximum session duration (seconds)
        """
        self.browser_pool = browser_pool
        self.enable_pooling = enable_pooling
        self.default_browser_config = default_browser_config or self._get_default_config()
        self.memory_threshold = memory_threshold
        self.cleanup_interval = cleanup_interval
        self.max_session_duration = max_session_duration

        # Session tracking with enhanced metadata
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.direct_browsers: Dict[str, Browser] = {}
        self.session_metrics: Dict[str, Dict[str, Any]] = {}

        # Resource monitoring
        self.resource_monitor_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.last_cleanup: datetime = datetime.now(timezone.utc)

        # Performance tracking
        self.performance_stats = {
            "total_sessions": 0,
            "active_sessions": 0,
            "memory_cleanups": 0,
            "forced_cleanups": 0,
            "average_session_duration": 0.0
        }

        # Error recovery
        self.error_recovery = EnhancedErrorRecovery()

        # Initialize logger
        self.logger = StructuredLogger("enhanced_browser_manager")

        # Initialize browser pool if not provided and pooling is enabled
        if self.enable_pooling and not self.browser_pool:
            pool_config = pool_config or PoolConfig(
                min_size=2,
                max_size=10,
                idle_timeout=300,  # 5 minutes
                health_check_interval=60
            )
            self.browser_pool = BrowserPool(self.default_browser_config, pool_config)

        self.logger.info(
            "Enhanced browser manager initialized",
            enable_pooling=enable_pooling,
            memory_threshold=memory_threshold,
            cleanup_interval=cleanup_interval,
            max_session_duration=max_session_duration
        )
    
    async def initialize(self) -> None:
        """Initialize the enhanced browser manager and its resources."""
        if self.browser_pool:
            await self.browser_pool.initialize()
            self.logger.info("Browser pool initialized")

        # Start resource monitoring
        self.resource_monitor_task = asyncio.create_task(self._resource_monitor_loop())
        self.cleanup_task = asyncio.create_task(self._cleanup_loop())

        self.logger.info("Enhanced browser manager initialized with resource monitoring")
    
    @with_correlation_id
    async def create_browser(self, config: Dict[str, Any]) -> Any:
        """
        Create and configure a new browser instance.
        
        Args:
            config: Browser configuration options
            
        Returns:
            Browser instance (either from pool or direct creation)
            
        Raises:
            BrowserError: If browser creation fails
            ConfigurationError: If configuration is invalid
        """
        session_id = config.get("session_id", str(uuid.uuid4()))
        correlation_id = config.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Creating browser instance",
            session_id=session_id,
            correlation_id=correlation_id,
            use_pooling=self.enable_pooling
        )
        
        try:
            if self.enable_pooling and self.browser_pool:
                # Use browser pool
                browser_session_id = await self._create_pooled_browser(config, session_id)
                
                # Track session
                self.active_sessions[session_id] = {
                    "type": "pooled",
                    "browser_session_id": browser_session_id,
                    "config": config,
                    "created_at": datetime.now(timezone.utc),
                    "correlation_id": correlation_id
                }
                
                # Return the session ID for pooled browsers
                return session_id
            else:
                # Create browser directly
                browser = await self._create_direct_browser(config)
                
                # Track direct browser
                self.direct_browsers[session_id] = browser
                self.active_sessions[session_id] = {
                    "type": "direct",
                    "browser": browser,
                    "config": config,
                    "created_at": datetime.now(timezone.utc),
                    "correlation_id": correlation_id
                }
                
                return browser
                
        except Exception as e:
            self.logger.error(
                "Failed to create browser",
                session_id=session_id,
                error=str(e),
                correlation_id=correlation_id
            )
            raise BrowserError(f"Failed to create browser: {e}") from e
    
    @with_correlation_id
    async def close_browser(self, browser: Any) -> None:
        """
        Close a browser instance safely.
        
        Args:
            browser: Browser instance or session ID to close
        """
        correlation_id = str(uuid.uuid4())
        
        try:
            # Handle both direct browser objects and session IDs
            if isinstance(browser, str):
                # It's a session ID
                session_id = browser
                await self._close_session(session_id, correlation_id)
            else:
                # It's a direct browser object
                await self._close_direct_browser(browser, correlation_id)
                
        except Exception as e:
            self.logger.error(
                "Failed to close browser",
                browser_type=type(browser).__name__,
                error=str(e),
                correlation_id=correlation_id
            )
            # Don't raise exception for cleanup operations
    
    async def get_browser_status(self, browser: Any) -> Dict[str, Any]:
        """
        Get the current status of a browser instance.
        
        Args:
            browser: Browser instance or session ID
            
        Returns:
            Dictionary containing browser status information
        """
        try:
            if isinstance(browser, str):
                # It's a session ID
                session_id = browser
                if session_id not in self.active_sessions:
                    return {"status": "not_found", "session_id": session_id}
                
                session_info = self.active_sessions[session_id]
                status = {
                    "status": "active",
                    "session_id": session_id,
                    "type": session_info["type"],
                    "created_at": session_info["created_at"].isoformat(),
                    "config": session_info["config"]
                }
                
                # Add pool-specific information if available
                if session_info["type"] == "pooled" and self.browser_pool:
                    pool_stats = self.browser_pool.get_statistics()
                    status["pool_statistics"] = pool_stats
                
                return status
            else:
                # It's a direct browser object
                return {
                    "status": "active",
                    "type": "direct",
                    "browser_type": type(browser).__name__
                }
                
        except Exception as e:
            self.logger.error(
                "Failed to get browser status",
                error=str(e)
            )
            return {"status": "error", "error": str(e)}
    
    async def get_browser_instance(self, session_id: str) -> Optional[Any]:
        """
        Get the actual browser instance for a session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Browser instance or None if not found
        """
        if session_id not in self.active_sessions:
            return None
        
        session_info = self.active_sessions[session_id]
        
        if session_info["type"] == "direct":
            return session_info["browser"]
        elif session_info["type"] == "pooled" and self.browser_pool:
            # For pooled browsers, we need to get the browser instance from the pool
            browser_session_id = session_info["browser_session_id"]
            return await self.browser_pool.get_browser_instance(browser_session_id)
        
        return None
    
    async def create_page(self, session_id: str, page_config: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new page in a browser session.
        
        Args:
            session_id: Browser session ID
            page_config: Page configuration options
            
        Returns:
            Page ID
            
        Raises:
            BrowserError: If page creation fails
        """
        if session_id not in self.active_sessions:
            raise BrowserError(f"Session {session_id} not found")
        
        session_info = self.active_sessions[session_id]
        
        try:
            if session_info["type"] == "pooled" and self.browser_pool:
                browser_session_id = session_info["browser_session_id"]
                page_id = await self.browser_pool.create_page(browser_session_id)
                
                self.logger.debug(
                    "Page created in pooled browser",
                    session_id=session_id,
                    page_id=page_id
                )
                
                return page_id
            else:
                # For direct browsers, we need to implement page creation
                # This would require extending the direct browser handling
                raise BrowserError("Page creation not implemented for direct browsers")
                
        except Exception as e:
            self.logger.error(
                "Failed to create page",
                session_id=session_id,
                error=str(e)
            )
            raise BrowserError(f"Failed to create page: {e}") from e
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a comprehensive health check of the browser manager.
        
        Returns:
            Health status information
        """
        health_status = {
            "status": "healthy",
            "active_sessions": len(self.active_sessions),
            "direct_browsers": len(self.direct_browsers),
            "pooling_enabled": self.enable_pooling,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Add browser pool health if available
        if self.browser_pool:
            try:
                pool_stats = self.browser_pool.get_statistics()
                health_status["pool_health"] = {
                    "status": "healthy",
                    "statistics": pool_stats
                }
            except Exception as e:
                health_status["pool_health"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
                health_status["status"] = "degraded"
        
        return health_status
    
    async def shutdown(self) -> None:
        """Shutdown the browser manager and clean up all resources."""
        self.logger.info("Shutting down browser manager")
        
        # Close all active sessions
        for session_id in list(self.active_sessions.keys()):
            await self.close_browser(session_id)
        
        # Close all direct browsers
        for browser in list(self.direct_browsers.values()):
            try:
                await browser.close()
            except Exception as e:
                self.logger.warning(f"Error closing direct browser: {e}")
        
        # Shutdown browser pool
        if self.browser_pool:
            await self.browser_pool.shutdown()
        
        self.logger.info("Browser manager shutdown complete")
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active browser sessions."""
        return {
            session_id: {
                "type": info["type"],
                "created_at": info["created_at"].isoformat(),
                "config": info.get("config", {}),
                "correlation_id": info.get("correlation_id")
            }
            for session_id, info in self.active_sessions.items()
        }

    # Private helper methods

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default browser configuration."""
        return {
            "browser_type": "chromium",
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
                "--disable-web-security",
                "--disable-features=VizDisplayCompositor"
            ],
            "viewport": {"width": 1920, "height": 1080},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

    async def _create_pooled_browser(self, config: Dict[str, Any], session_id: str) -> str:
        """Create a browser using the browser pool."""
        context_options = {
            "viewport": config.get("viewport", self.default_browser_config["viewport"]),
            "user_agent": config.get("user_agent", self.default_browser_config["user_agent"])
        }

        # Add any additional context options from config
        if "context_options" in config:
            context_options.update(config["context_options"])

        browser_session_id = await self.browser_pool.create_session(
            session_id=session_id,
            context_options=context_options,
            timeout=config.get("timeout", 30.0)
        )

        self.logger.debug(
            "Pooled browser session created",
            session_id=session_id,
            browser_session_id=browser_session_id
        )

        return browser_session_id

    async def _resource_monitor_loop(self) -> None:
        """Continuous resource monitoring loop."""
        while True:
            try:
                await self._monitor_resources()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_recovery.handle_error(
                    e, "browser_manager", "resource_monitoring"
                )
                await asyncio.sleep(60)  # Wait longer on error

    async def _cleanup_loop(self) -> None:
        """Automatic cleanup loop."""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._perform_cleanup()
            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.error_recovery.handle_error(
                    e, "browser_manager", "cleanup"
                )

    async def _monitor_resources(self) -> None:
        """Monitor system resources and browser health."""
        try:
            # Get system memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent / 100.0

            # Check if memory threshold exceeded
            if memory_percent > self.memory_threshold:
                self.logger.warning(
                    "Memory threshold exceeded",
                    memory_percent=memory_percent,
                    threshold=self.memory_threshold
                )

                # Trigger emergency cleanup
                await self._emergency_cleanup()

            # Monitor browser processes
            browser_processes = self._get_browser_processes()

            # Check for zombie processes
            zombie_processes = [p for p in browser_processes if p.status() == psutil.STATUS_ZOMBIE]
            if zombie_processes:
                self.logger.warning(
                    "Zombie browser processes detected",
                    count=len(zombie_processes)
                )
                await self._cleanup_zombie_processes(zombie_processes)

            # Update performance stats
            self.performance_stats["active_sessions"] = len(self.active_sessions)

        except Exception as e:
            self.logger.error(f"Resource monitoring failed: {e}")

    def _get_browser_processes(self) -> List[Any]:
        """Get all browser-related processes."""
        browser_processes = []

        try:
            for proc in psutil.process_iter(['pid', 'name', 'status']):
                name = proc.info['name'].lower()
                if any(browser in name for browser in ['chrome', 'firefox', 'safari', 'edge']):
                    browser_processes.append(proc)
        except Exception as e:
            self.logger.warning(f"Failed to enumerate browser processes: {e}")

        return browser_processes

    async def _emergency_cleanup(self) -> None:
        """Perform emergency cleanup when resources are low."""
        self.logger.info("Performing emergency cleanup")

        # Close oldest sessions first
        sessions_by_age = sorted(
            self.active_sessions.items(),
            key=lambda x: x[1]["created_at"]
        )

        cleanup_count = max(1, len(sessions_by_age) // 4)  # Clean up 25% of sessions

        for session_id, _ in sessions_by_age[:cleanup_count]:
            try:
                await self.close_browser(session_id)
                self.performance_stats["forced_cleanups"] += 1
            except Exception as e:
                self.logger.error(f"Failed to close session {session_id}: {e}")

        # Force garbage collection
        gc.collect()

        self.performance_stats["memory_cleanups"] += 1

    async def _perform_cleanup(self) -> None:
        """Perform regular cleanup of expired sessions."""
        now = datetime.now(timezone.utc)
        expired_sessions = []

        # Find expired sessions
        for session_id, session_info in self.active_sessions.items():
            session_age = (now - session_info["created_at"]).total_seconds()

            if session_age > self.max_session_duration:
                expired_sessions.append(session_id)

        # Clean up expired sessions
        for session_id in expired_sessions:
            try:
                await self.close_browser(session_id)
                self.logger.info(
                    "Cleaned up expired session",
                    session_id=session_id
                )
            except Exception as e:
                self.logger.error(f"Failed to cleanup session {session_id}: {e}")

        self.last_cleanup = now

    async def _cleanup_zombie_processes(self, zombie_processes: List[Any]) -> None:
        """Clean up zombie browser processes."""
        for proc in zombie_processes:
            try:
                proc.terminate()
                await asyncio.sleep(1)
                if proc.is_running():
                    proc.kill()

                self.logger.info(f"Cleaned up zombie process {proc.pid}")
            except Exception as e:
                self.logger.error(f"Failed to cleanup zombie process {proc.pid}: {e}")

    def get_resource_stats(self) -> Dict[str, Any]:
        """Get current resource statistics."""
        try:
            memory = psutil.virtual_memory()
            browser_processes = self._get_browser_processes()

            return {
                "system": {
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "memory_used_gb": memory.used / (1024**3)
                },
                "browser_processes": {
                    "count": len(browser_processes),
                    "total_memory_mb": sum(
                        proc.memory_info().rss / (1024**2)
                        for proc in browser_processes
                        if proc.is_running()
                    )
                },
                "sessions": {
                    "active_count": len(self.active_sessions),
                    "direct_browsers": len(self.direct_browsers)
                },
                "performance": self.performance_stats,
                "last_cleanup": self.last_cleanup.isoformat()
            }
        except Exception as e:
            return {"error": str(e)}

    async def cleanup(self) -> None:
        """Enhanced cleanup with resource monitoring shutdown."""
        # Cancel monitoring tasks
        if self.resource_monitor_task:
            self.resource_monitor_task.cancel()
            try:
                await self.resource_monitor_task
            except asyncio.CancelledError:
                pass

        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        # Close all active sessions
        for session_id in list(self.active_sessions.keys()):
            try:
                await self.close_browser(session_id)
            except Exception as e:
                self.logger.error(f"Failed to close session {session_id} during cleanup: {e}")

        # Close direct browsers
        for session_id, browser in list(self.direct_browsers.items()):
            try:
                await browser.close()
            except Exception as e:
                self.logger.error(f"Failed to close direct browser {session_id}: {e}")

        # Cleanup browser pool
        if self.browser_pool:
            await self.browser_pool.cleanup()

        self.logger.info("Enhanced browser manager cleanup completed")


# Backward compatibility alias
BrowserManager = EnhancedBrowserManager
