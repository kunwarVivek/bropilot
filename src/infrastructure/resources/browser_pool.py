"""
Browser resource pool implementation.

This module provides browser-specific resource pooling with proper lifecycle
management, session isolation, and performance optimization.
"""

import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from core.exceptions import ResourceError, ConfigurationError
from src.infrastructure.logging.logger import StructuredLogger
from .pool_manager import ResourceFactory, ResourcePool, PoolConfig


class BrowserInstance:
    """Wrapper for browser instance with context management."""
    
    def __init__(self, browser: Browser, browser_type: str):
        self.browser = browser
        self.browser_type = browser_type
        self.contexts: Dict[str, BrowserContext] = {}
        self.pages: Dict[str, Page] = {}
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.session_count = 0
    
    async def create_context(self, context_id: Optional[str] = None, **kwargs) -> str:
        """Create a new browser context."""
        if not context_id:
            context_id = str(uuid.uuid4())
        
        context = await self.browser.new_context(**kwargs)
        self.contexts[context_id] = context
        self.session_count += 1
        self.last_activity = datetime.utcnow()
        
        return context_id
    
    async def get_context(self, context_id: str) -> Optional[BrowserContext]:
        """Get a browser context by ID."""
        return self.contexts.get(context_id)
    
    async def create_page(self, context_id: str, page_id: Optional[str] = None) -> str:
        """Create a new page in a context."""
        if context_id not in self.contexts:
            raise ResourceError(f"Context {context_id} not found")
        
        if not page_id:
            page_id = str(uuid.uuid4())
        
        context = self.contexts[context_id]
        page = await context.new_page()
        self.pages[page_id] = page
        self.last_activity = datetime.utcnow()
        
        return page_id
    
    async def get_page(self, page_id: str) -> Optional[Page]:
        """Get a page by ID."""
        return self.pages.get(page_id)
    
    async def close_page(self, page_id: str) -> None:
        """Close a specific page."""
        if page_id in self.pages:
            page = self.pages[page_id]
            await page.close()
            del self.pages[page_id]
            self.last_activity = datetime.utcnow()
    
    async def close_context(self, context_id: str) -> None:
        """Close a specific context and all its pages."""
        if context_id in self.contexts:
            # Close all pages in this context
            pages_to_close = [
                page_id for page_id, page in self.pages.items()
                if page.context == self.contexts[context_id]
            ]
            
            for page_id in pages_to_close:
                await self.close_page(page_id)
            
            # Close the context
            context = self.contexts[context_id]
            await context.close()
            del self.contexts[context_id]
            self.last_activity = datetime.utcnow()
    
    async def reset(self) -> bool:
        """Reset browser instance by closing all contexts and pages."""
        try:
            # Close all pages
            for page_id in list(self.pages.keys()):
                await self.close_page(page_id)
            
            # Close all contexts
            for context_id in list(self.contexts.keys()):
                await self.close_context(context_id)
            
            self.last_activity = datetime.utcnow()
            return True
            
        except Exception:
            return False
    
    async def close(self) -> None:
        """Close the browser instance."""
        await self.reset()
        await self.browser.close()


class BrowserFactory(ResourceFactory[BrowserInstance]):
    """Factory for creating and managing browser instances."""
    
    def __init__(self, browser_config: Dict[str, Any]):
        """Initialize browser factory."""
        self.browser_config = browser_config
        self.logger = StructuredLogger("browser_factory")
        self.playwright = None
        self.browser_type_name = browser_config.get("browser_type", "chromium")
        
        # Browser launch options
        self.launch_options = {
            "headless": browser_config.get("headless", True),
            "args": browser_config.get("args", []),
            "timeout": browser_config.get("launch_timeout", 30000),
        }
        
        # Add executable path if specified
        if "executable_path" in browser_config:
            self.launch_options["executable_path"] = browser_config["executable_path"]
    
    async def create_resource(self) -> BrowserInstance:
        """Create a new browser instance."""
        
        try:
            # Initialize playwright if not already done
            if not self.playwright:
                self.playwright = await async_playwright().start()
            
            # Get browser type
            if self.browser_type_name == "chromium":
                browser_type = self.playwright.chromium
            elif self.browser_type_name == "firefox":
                browser_type = self.playwright.firefox
            elif self.browser_type_name == "webkit":
                browser_type = self.playwright.webkit
            else:
                raise ConfigurationError(f"Unsupported browser type: {self.browser_type_name}")
            
            # Launch browser
            browser = await browser_type.launch(**self.launch_options)
            
            browser_instance = BrowserInstance(browser, self.browser_type_name)
            
            self.logger.info(
                "Browser instance created",
                browser_type=self.browser_type_name,
                headless=self.launch_options["headless"]
            )
            
            return browser_instance
            
        except Exception as e:
            self.logger.error(
                "Failed to create browser instance",
                browser_type=self.browser_type_name,
                error=str(e)
            )
            raise ResourceError(f"Browser creation failed: {e}") from e
    
    async def destroy_resource(self, resource: BrowserInstance) -> None:
        """Destroy a browser instance."""
        
        try:
            await resource.close()
            
            self.logger.info(
                "Browser instance destroyed",
                browser_type=resource.browser_type,
                session_count=resource.session_count
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to destroy browser instance",
                browser_type=resource.browser_type,
                error=str(e)
            )
            raise ResourceError(f"Browser destruction failed: {e}") from e
    
    async def health_check(self, resource: BrowserInstance) -> bool:
        """Check if browser instance is healthy."""
        
        try:
            # Check if browser is connected
            if not resource.browser.is_connected():
                return False
            
            # Try to create and close a simple context
            context = await resource.browser.new_context()
            await context.close()
            
            return True
            
        except Exception as e:
            self.logger.warning(
                "Browser health check failed",
                browser_type=resource.browser_type,
                error=str(e)
            )
            return False
    
    async def reset_resource(self, resource: BrowserInstance) -> bool:
        """Reset browser instance to clean state."""
        
        try:
            return await resource.reset()
            
        except Exception as e:
            self.logger.error(
                "Failed to reset browser instance",
                browser_type=resource.browser_type,
                error=str(e)
            )
            return False
    
    async def cleanup(self) -> None:
        """Cleanup factory resources."""
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None


class BrowserPool:
    """High-level browser pool with session management."""
    
    def __init__(self, browser_config: Dict[str, Any], pool_config: PoolConfig):
        """Initialize browser pool."""
        self.browser_config = browser_config
        self.pool_config = pool_config
        self.logger = StructuredLogger("browser_pool")
        
        # Create factory and pool
        self.factory = BrowserFactory(browser_config)
        self.pool = ResourcePool("browser_pool", self.factory, pool_config)
        
        # Session tracking
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    async def initialize(self) -> None:
        """Initialize the browser pool."""
        await self.pool.initialize()
        
        self.logger.info(
            "Browser pool initialized",
            browser_type=self.browser_config.get("browser_type", "chromium"),
            pool_config=self.pool_config.__dict__
        )
    
    async def create_session(
        self,
        session_id: Optional[str] = None,
        context_options: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> str:
        """Create a new browser session."""
        
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Acquire browser instance
        browser_instance = await self.pool.acquire(session_id, timeout)
        
        # Create context
        context_options = context_options or {}
        context_id = await browser_instance.create_context(**context_options)
        
        # Track session
        self.active_sessions[session_id] = {
            "browser_instance": browser_instance,
            "context_id": context_id,
            "created_at": datetime.utcnow(),
            "pages": {}
        }
        
        self.logger.info(
            "Browser session created",
            session_id=session_id,
            context_id=context_id
        )
        
        return session_id
    
    async def get_page(
        self,
        session_id: str,
        page_id: Optional[str] = None,
        create_if_not_exists: bool = True
    ) -> Optional[Page]:
        """Get or create a page in a session."""
        
        if session_id not in self.active_sessions:
            raise ResourceError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        browser_instance = session["browser_instance"]
        context_id = session["context_id"]
        
        if not page_id:
            page_id = "default"
        
        # Check if page already exists
        if page_id in session["pages"]:
            page_info = session["pages"][page_id]
            return await browser_instance.get_page(page_info["page_id"])
        
        # Create new page if requested
        if create_if_not_exists:
            actual_page_id = await browser_instance.create_page(context_id)
            session["pages"][page_id] = {
                "page_id": actual_page_id,
                "created_at": datetime.utcnow()
            }
            
            return await browser_instance.get_page(actual_page_id)
        
        return None
    
    async def close_session(self, session_id: str) -> None:
        """Close a browser session."""
        
        if session_id not in self.active_sessions:
            return
        
        session = self.active_sessions[session_id]
        browser_instance = session["browser_instance"]
        context_id = session["context_id"]
        
        try:
            # Close the context (this will close all pages)
            await browser_instance.close_context(context_id)
            
            # Release browser instance back to pool
            await self.pool.release(browser_instance, session_id)
            
            # Remove session tracking
            del self.active_sessions[session_id]
            
            self.logger.info(
                "Browser session closed",
                session_id=session_id
            )
            
        except Exception as e:
            self.logger.error(
                "Failed to close browser session",
                session_id=session_id,
                error=str(e)
            )
    
    async def shutdown(self) -> None:
        """Shutdown the browser pool."""
        
        # Close all active sessions
        for session_id in list(self.active_sessions.keys()):
            await self.close_session(session_id)
        
        # Shutdown pool
        await self.pool.shutdown()
        
        # Cleanup factory
        await self.factory.cleanup()
        
        self.logger.info("Browser pool shutdown complete")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get browser pool statistics."""
        
        pool_stats = self.pool.get_statistics()
        
        return {
            **pool_stats,
            "active_sessions": len(self.active_sessions),
            "browser_type": self.browser_config.get("browser_type", "chromium"),
            "headless": self.browser_config.get("headless", True)
        }
