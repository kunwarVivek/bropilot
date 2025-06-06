"""
Unit tests for BrowserManager implementation.

This module tests the core functionality of the BrowserManager class
to ensure it properly implements the IBrowserManager interface.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from core.exceptions import BrowserError, ConfigurationError
from src.execution.browser_manager import BrowserManager
from src.infrastructure.resources.pool_manager import PoolConfig


@pytest.fixture
def mock_browser_pool():
    """Create a mock browser pool."""
    pool = Mock()
    pool.initialize = AsyncMock()
    pool.create_session = AsyncMock(return_value="browser_session_123")
    pool.close_session = AsyncMock()
    pool.create_page = AsyncMock(return_value="page_123")
    pool.get_browser_instance = AsyncMock(return_value=Mock())
    pool.get_statistics = Mock(return_value={
        "active_resources": 2,
        "available_resources": 3,
        "total_resources": 5
    })
    pool.shutdown = AsyncMock()
    return pool


@pytest.fixture
def mock_browser():
    """Create a mock browser instance."""
    browser = Mock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def browser_config():
    """Create a sample browser configuration."""
    return {
        "session_id": "test_session_123",
        "correlation_id": "test_correlation_456",
        "headless": True,
        "browser_type": "chromium",
        "viewport": {"width": 1920, "height": 1080},
        "timeout": 30.0
    }


class TestBrowserManager:
    """Test cases for BrowserManager class."""
    
    def test_init_with_pooling(self, mock_browser_pool):
        """Test BrowserManager initialization with pooling enabled."""
        manager = BrowserManager(
            browser_pool=mock_browser_pool,
            enable_pooling=True
        )
        
        assert manager.browser_pool == mock_browser_pool
        assert manager.enable_pooling is True
        assert len(manager.active_sessions) == 0
        assert len(manager.direct_browsers) == 0
    
    def test_init_without_pooling(self):
        """Test BrowserManager initialization with pooling disabled."""
        manager = BrowserManager(enable_pooling=False)
        
        assert manager.browser_pool is None
        assert manager.enable_pooling is False
        assert len(manager.active_sessions) == 0
        assert len(manager.direct_browsers) == 0
    
    def test_init_auto_create_pool(self):
        """Test BrowserManager initialization with auto-created pool."""
        with patch('src.execution.browser_manager.BrowserPool') as mock_pool_class:
            mock_pool_instance = Mock()
            mock_pool_class.return_value = mock_pool_instance
            
            manager = BrowserManager(enable_pooling=True)
            
            assert manager.browser_pool == mock_pool_instance
            mock_pool_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize(self, mock_browser_pool):
        """Test browser manager initialization."""
        manager = BrowserManager(browser_pool=mock_browser_pool)
        
        await manager.initialize()
        
        mock_browser_pool.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_pooled_browser(self, mock_browser_pool, browser_config):
        """Test creating a browser using the pool."""
        manager = BrowserManager(
            browser_pool=mock_browser_pool,
            enable_pooling=True
        )
        
        session_id = await manager.create_browser(browser_config)
        
        assert session_id == "test_session_123"
        assert session_id in manager.active_sessions
        
        session_info = manager.active_sessions[session_id]
        assert session_info["type"] == "pooled"
        assert session_info["browser_session_id"] == "browser_session_123"
        assert session_info["config"] == browser_config
        
        mock_browser_pool.create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_direct_browser(self, browser_config):
        """Test creating a browser directly."""
        with patch('src.execution.browser_manager.Browser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser_class.return_value = mock_browser
            
            manager = BrowserManager(enable_pooling=False)
            
            browser = await manager.create_browser(browser_config)
            
            assert browser == mock_browser
            assert "test_session_123" in manager.active_sessions
            assert "test_session_123" in manager.direct_browsers
            
            session_info = manager.active_sessions["test_session_123"]
            assert session_info["type"] == "direct"
            assert session_info["browser"] == mock_browser
    
    @pytest.mark.asyncio
    async def test_close_pooled_browser(self, mock_browser_pool, browser_config):
        """Test closing a pooled browser session."""
        manager = BrowserManager(
            browser_pool=mock_browser_pool,
            enable_pooling=True
        )
        
        # Create a session first
        session_id = await manager.create_browser(browser_config)
        assert session_id in manager.active_sessions
        
        # Close the session
        await manager.close_browser(session_id)
        
        assert session_id not in manager.active_sessions
        mock_browser_pool.close_session.assert_called_once_with("browser_session_123")
    
    @pytest.mark.asyncio
    async def test_close_direct_browser(self, browser_config):
        """Test closing a direct browser."""
        with patch('src.execution.browser_manager.Browser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser.close = AsyncMock()
            mock_browser_class.return_value = mock_browser
            
            manager = BrowserManager(enable_pooling=False)
            
            # Create a browser first
            browser = await manager.create_browser(browser_config)
            session_id = "test_session_123"
            assert session_id in manager.active_sessions
            assert session_id in manager.direct_browsers
            
            # Close the browser
            await manager.close_browser(browser)
            
            mock_browser.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_browser_status_pooled(self, mock_browser_pool, browser_config):
        """Test getting status of a pooled browser."""
        manager = BrowserManager(
            browser_pool=mock_browser_pool,
            enable_pooling=True
        )
        
        # Create a session first
        session_id = await manager.create_browser(browser_config)
        
        # Get status
        status = await manager.get_browser_status(session_id)
        
        assert status["status"] == "active"
        assert status["session_id"] == session_id
        assert status["type"] == "pooled"
        assert "created_at" in status
        assert "config" in status
        assert "pool_statistics" in status
    
    @pytest.mark.asyncio
    async def test_get_browser_status_direct(self, browser_config):
        """Test getting status of a direct browser."""
        with patch('src.execution.browser_manager.Browser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser_class.return_value = mock_browser
            
            manager = BrowserManager(enable_pooling=False)
            
            # Create a browser first
            browser = await manager.create_browser(browser_config)
            
            # Get status
            status = await manager.get_browser_status(browser)
            
            assert status["status"] == "active"
            assert status["type"] == "direct"
    
    @pytest.mark.asyncio
    async def test_get_browser_status_not_found(self):
        """Test getting status of a non-existent browser."""
        manager = BrowserManager()
        
        status = await manager.get_browser_status("nonexistent_session")
        
        assert status["status"] == "not_found"
        assert status["session_id"] == "nonexistent_session"
    
    @pytest.mark.asyncio
    async def test_get_browser_instance_pooled(self, mock_browser_pool, browser_config):
        """Test getting browser instance for pooled browser."""
        mock_browser_instance = Mock()
        mock_browser_pool.get_browser_instance.return_value = mock_browser_instance
        
        manager = BrowserManager(
            browser_pool=mock_browser_pool,
            enable_pooling=True
        )
        
        # Create a session first
        session_id = await manager.create_browser(browser_config)
        
        # Get browser instance
        browser_instance = await manager.get_browser_instance(session_id)
        
        assert browser_instance == mock_browser_instance
        mock_browser_pool.get_browser_instance.assert_called_once_with("browser_session_123")
    
    @pytest.mark.asyncio
    async def test_get_browser_instance_direct(self, browser_config):
        """Test getting browser instance for direct browser."""
        with patch('src.execution.browser_manager.Browser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser_class.return_value = mock_browser
            
            manager = BrowserManager(enable_pooling=False)
            
            # Create a browser first
            await manager.create_browser(browser_config)
            session_id = "test_session_123"
            
            # Get browser instance
            browser_instance = await manager.get_browser_instance(session_id)
            
            assert browser_instance == mock_browser
    
    @pytest.mark.asyncio
    async def test_get_browser_instance_not_found(self):
        """Test getting browser instance for non-existent session."""
        manager = BrowserManager()
        
        browser_instance = await manager.get_browser_instance("nonexistent_session")
        
        assert browser_instance is None
    
    @pytest.mark.asyncio
    async def test_create_page_pooled(self, mock_browser_pool, browser_config):
        """Test creating a page in a pooled browser."""
        manager = BrowserManager(
            browser_pool=mock_browser_pool,
            enable_pooling=True
        )
        
        # Create a session first
        session_id = await manager.create_browser(browser_config)
        
        # Create a page
        page_id = await manager.create_page(session_id)
        
        assert page_id == "page_123"
        mock_browser_pool.create_page.assert_called_once_with("browser_session_123")
    
    @pytest.mark.asyncio
    async def test_create_page_session_not_found(self):
        """Test creating a page for non-existent session."""
        manager = BrowserManager()
        
        with pytest.raises(BrowserError, match="Session .* not found"):
            await manager.create_page("nonexistent_session")
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_browser_pool):
        """Test health check functionality."""
        manager = BrowserManager(browser_pool=mock_browser_pool)
        
        health = await manager.health_check()
        
        assert health["status"] == "healthy"
        assert health["active_sessions"] == 0
        assert health["direct_browsers"] == 0
        assert health["pooling_enabled"] is True
        assert "timestamp" in health
        assert "pool_health" in health
        assert health["pool_health"]["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_health_check_pool_error(self, mock_browser_pool):
        """Test health check with pool error."""
        mock_browser_pool.get_statistics.side_effect = Exception("Pool error")
        
        manager = BrowserManager(browser_pool=mock_browser_pool)
        
        health = await manager.health_check()
        
        assert health["status"] == "degraded"
        assert health["pool_health"]["status"] == "unhealthy"
        assert "Pool error" in health["pool_health"]["error"]
    
    def test_get_active_sessions(self, mock_browser_pool):
        """Test getting active sessions information."""
        manager = BrowserManager(browser_pool=mock_browser_pool)
        
        # Manually add a session for testing
        session_id = "test_session_123"
        manager.active_sessions[session_id] = {
            "type": "pooled",
            "created_at": datetime.now(timezone.utc),
            "config": {"headless": True},
            "correlation_id": "test_correlation_456"
        }
        
        active_sessions = manager.get_active_sessions()
        
        assert session_id in active_sessions
        assert active_sessions[session_id]["type"] == "pooled"
        assert "created_at" in active_sessions[session_id]
        assert active_sessions[session_id]["config"]["headless"] is True
        assert active_sessions[session_id]["correlation_id"] == "test_correlation_456"
    
    @pytest.mark.asyncio
    async def test_shutdown(self, mock_browser_pool, browser_config):
        """Test browser manager shutdown."""
        manager = BrowserManager(browser_pool=mock_browser_pool)
        
        # Create a session first
        await manager.create_browser(browser_config)
        
        # Shutdown
        await manager.shutdown()
        
        assert len(manager.active_sessions) == 0
        mock_browser_pool.shutdown.assert_called_once()
