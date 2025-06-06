"""
Unit tests for execution adapters.

This module tests the functionality of all execution adapters including
browser-use, Gemini, OpenAI, and the adapter factory.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from core.interfaces import TaskDefinition, ExecutionResult, TaskStatus
from core.exceptions import BrowserError, LLMError, ConfigurationError
from src.execution.adapters.browser_use import BrowserUseAdapter
from src.execution.adapters.gemini import GeminiAdapter
from src.execution.adapters.openai import OpenAIAdapter
from src.execution.adapters.adapter_factory import AdapterFactory, AdapterType


@pytest.fixture
def task_definition():
    """Create a sample task definition."""
    return TaskDefinition(
        name="test_task",
        description="A test task",
        prompt_template="Navigate to https://example.com and click login",
        timeout=60,
        retry_count=3,
        metadata={"test": True}
    )


@pytest.fixture
def execution_context():
    """Create a sample execution context."""
    return {
        "session_id": "test_session_123",
        "correlation_id": "test_correlation_456",
        "target_url": "https://example.com",
        "use_vision": True
    }


@pytest.fixture
def mock_browser():
    """Create a mock browser instance."""
    browser = Mock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = Mock()
    return provider


class TestBrowserUseAdapter:
    """Test cases for BrowserUseAdapter."""
    
    def test_init(self):
        """Test BrowserUseAdapter initialization."""
        adapter = BrowserUseAdapter(
            save_logs=False,
            logs_base_path="test_logs"
        )
        
        assert adapter.save_logs is False
        assert adapter.logs_base_path == "test_logs"
        assert len(adapter.active_sessions) == 0
        assert adapter.default_config is not None
    
    @pytest.mark.asyncio
    async def test_create_browser(self):
        """Test browser creation via adapter."""
        with patch('src.execution.adapters.browser_use.Browser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser_class.return_value = mock_browser
            
            adapter = BrowserUseAdapter()
            config = {"headless": True, "browser_type": "chrome"}
            
            browser = await adapter.create_browser(config)
            
            assert browser == mock_browser
            mock_browser_class.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_browser_failure(self):
        """Test browser creation failure."""
        with patch('src.execution.adapters.browser_use.Browser') as mock_browser_class:
            mock_browser_class.side_effect = Exception("Browser creation failed")
            
            adapter = BrowserUseAdapter()
            config = {"headless": True}
            
            with pytest.raises(BrowserError, match="Failed to create browser"):
                await adapter.create_browser(config)
    
    @pytest.mark.asyncio
    async def test_close_browser(self, mock_browser):
        """Test browser closing via adapter."""
        adapter = BrowserUseAdapter()
        
        await adapter.close_browser(mock_browser)
        
        mock_browser.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_task_success(
        self, 
        task_definition, 
        execution_context, 
        mock_browser, 
        mock_llm_provider
    ):
        """Test successful task execution."""
        with patch('src.execution.adapters.browser_use.Agent') as mock_agent_class:
            # Setup mock agent
            mock_agent = Mock()
            mock_history = Mock()
            mock_history.final_result = Mock(return_value="Task completed successfully")
            mock_agent.run = AsyncMock(return_value=mock_history)
            mock_agent_class.return_value = mock_agent
            
            adapter = BrowserUseAdapter(save_logs=False)
            
            result = await adapter.execute_task(
                task_definition,
                mock_browser,
                mock_llm_provider,
                execution_context
            )
            
            assert isinstance(result, ExecutionResult)
            assert result.status == TaskStatus.COMPLETED
            assert result.result == "Task completed successfully"
            assert result.metadata["adapter"] == "browser_use"
            assert result.metadata["session_id"] == "test_session_123"
    
    @pytest.mark.asyncio
    async def test_execute_task_failure(
        self, 
        task_definition, 
        execution_context, 
        mock_browser, 
        mock_llm_provider
    ):
        """Test task execution failure."""
        with patch('src.execution.adapters.browser_use.Agent') as mock_agent_class:
            mock_agent_class.side_effect = Exception("Agent creation failed")
            
            adapter = BrowserUseAdapter(save_logs=False)
            
            result = await adapter.execute_task(
                task_definition,
                mock_browser,
                mock_llm_provider,
                execution_context
            )
            
            assert result.status == TaskStatus.FAILED
            assert "Agent creation failed" in result.error_message
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with patch.object(BrowserUseAdapter, 'create_browser') as mock_create, \
             patch.object(BrowserUseAdapter, 'close_browser') as mock_close:
            
            mock_browser = Mock()
            mock_create.return_value = mock_browser
            mock_close.return_value = None
            
            adapter = BrowserUseAdapter()
            
            health = await adapter.health_check()
            
            assert health["status"] == "healthy"
            assert health["adapter"] == "browser_use"
            assert health["can_create_browser"] is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        with patch.object(BrowserUseAdapter, 'create_browser') as mock_create:
            mock_create.side_effect = Exception("Browser creation failed")
            
            adapter = BrowserUseAdapter()
            
            health = await adapter.health_check()
            
            assert health["status"] == "unhealthy"
            assert health["can_create_browser"] is False
            assert "Browser creation failed" in health["error"]


class TestGeminiAdapter:
    """Test cases for GeminiAdapter."""
    
    def test_init(self):
        """Test GeminiAdapter initialization."""
        adapter = GeminiAdapter(
            api_key="test_key",
            model="test_model",
            config={"temperature": 0.2}
        )
        
        assert adapter.api_key == "test_key"
        assert adapter.model == "test_model"
        assert adapter.config["temperature"] == 0.2
        assert adapter.request_count == 0
        assert adapter.error_count == 0
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful Gemini initialization."""
        with patch('src.execution.adapters.gemini.ChatGoogleGenerativeAI') as mock_chat, \
             patch('src.execution.adapters.gemini.InMemoryRateLimiter') as mock_limiter, \
             patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            
            mock_provider = Mock()
            mock_chat.return_value = mock_provider
            mock_rate_limiter = Mock()
            mock_limiter.return_value = mock_rate_limiter
            
            adapter = GeminiAdapter()
            await adapter.initialize()
            
            assert adapter.provider == mock_provider
            assert adapter.rate_limiter == mock_rate_limiter
            mock_chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_no_api_key(self):
        """Test Gemini initialization without API key."""
        with patch.dict('os.environ', {}, clear=True):
            adapter = GeminiAdapter()
            
            with pytest.raises(ConfigurationError, match="Gemini API key not found"):
                await adapter.initialize()
    
    @pytest.mark.asyncio
    async def test_invoke_success(self):
        """Test successful Gemini invocation."""
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "Test response from Gemini"
        mock_provider.ainvoke = AsyncMock(return_value=mock_response)
        
        adapter = GeminiAdapter()
        adapter.provider = mock_provider
        
        response = await adapter.invoke("Test prompt")
        
        assert response == "Test response from Gemini"
        assert adapter.request_count == 1
        assert adapter.error_count == 0
        mock_provider.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invoke_failure(self):
        """Test Gemini invocation failure."""
        mock_provider = Mock()
        mock_provider.ainvoke = AsyncMock(side_effect=Exception("API error"))
        
        adapter = GeminiAdapter()
        adapter.provider = mock_provider
        
        with pytest.raises(LLMError, match="Gemini invocation failed"):
            await adapter.invoke("Test prompt")
        
        assert adapter.error_count == 1
    
    @pytest.mark.asyncio
    async def test_generate_response(self):
        """Test structured response generation."""
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "Structured response"
        mock_provider.ainvoke = AsyncMock(return_value=mock_response)
        
        adapter = GeminiAdapter()
        adapter.provider = mock_provider
        
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        
        response = await adapter.generate_response(messages)
        
        assert response["content"] == "Structured response"
        assert response["role"] == "assistant"
        assert response["metadata"]["provider"] == "gemini"
        assert "usage" in response
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "OK"
        mock_provider.ainvoke = AsyncMock(return_value=mock_response)
        
        adapter = GeminiAdapter()
        adapter.provider = mock_provider
        
        health = await adapter.health_check()
        
        assert health["status"] == "healthy"
        assert health["adapter"] == "gemini"
        assert health["test_response"] == "OK"
    
    @pytest.mark.asyncio
    async def test_health_check_not_initialized(self):
        """Test health check when provider not initialized."""
        adapter = GeminiAdapter()
        
        health = await adapter.health_check()
        
        assert health["status"] == "unhealthy"
        assert "Provider not initialized" in health["error"]


class TestOpenAIAdapter:
    """Test cases for OpenAIAdapter."""
    
    def test_init(self):
        """Test OpenAIAdapter initialization."""
        adapter = OpenAIAdapter(
            api_key="test_key",
            model="gpt-4",
            config={"temperature": 0.1}
        )
        
        assert adapter.api_key == "test_key"
        assert adapter.model == "gpt-4"
        assert adapter.config["temperature"] == 0.1
        assert adapter.request_count == 0
        assert adapter.total_cost == 0.0
    
    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful OpenAI initialization."""
        with patch('src.execution.adapters.openai.ChatOpenAI') as mock_chat, \
             patch.dict('os.environ', {'OPENAI_API_KEY': 'test_key'}):
            
            mock_provider = Mock()
            mock_chat.return_value = mock_provider
            
            adapter = OpenAIAdapter()
            await adapter.initialize()
            
            assert adapter.provider == mock_provider
            mock_chat.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invoke_success(self):
        """Test successful OpenAI invocation."""
        mock_provider = Mock()
        mock_response = Mock()
        mock_response.content = "Test response from OpenAI"
        mock_provider.ainvoke = AsyncMock(return_value=mock_response)
        
        adapter = OpenAIAdapter()
        adapter.provider = mock_provider
        
        response = await adapter.invoke("Test prompt")
        
        assert response == "Test response from OpenAI"
        assert adapter.request_count == 1
        assert adapter.total_cost > 0  # Should have estimated cost
    
    def test_estimate_cost(self):
        """Test cost estimation."""
        adapter = OpenAIAdapter(model="gpt-4")
        
        cost = adapter._estimate_cost(1000, 500)  # 1000 prompt, 500 completion tokens
        
        assert cost > 0
        assert isinstance(cost, float)
    
    @pytest.mark.asyncio
    async def test_analyze_image_unsupported_model(self):
        """Test image analysis with unsupported model."""
        adapter = OpenAIAdapter(model="gpt-3.5-turbo")
        adapter.provider = Mock()
        
        with pytest.raises(LLMError, match="does not support vision capabilities"):
            await adapter.analyze_image(b"fake_image_data")


class TestAdapterFactory:
    """Test cases for AdapterFactory."""
    
    def test_init(self):
        """Test AdapterFactory initialization."""
        config = {"global_setting": "value"}
        factory = AdapterFactory(config)
        
        assert factory.config == config
        assert len(factory.adapters) == 0
        assert len(factory.adapter_configs) == 0
        assert AdapterType.BROWSER_USE in factory.adapter_classes
    
    @pytest.mark.asyncio
    async def test_create_browser_use_adapter(self):
        """Test creating a browser-use adapter."""
        factory = AdapterFactory()
        
        adapter = await factory.create_adapter(
            AdapterType.BROWSER_USE,
            "test_browser_adapter",
            {"save_logs": False}
        )
        
        assert isinstance(adapter, BrowserUseAdapter)
        assert "test_browser_adapter" in factory.adapters
        assert factory.adapter_configs["test_browser_adapter"]["type"] == "browser_use"
    
    @pytest.mark.asyncio
    async def test_create_gemini_adapter(self):
        """Test creating a Gemini adapter."""
        with patch.object(GeminiAdapter, 'initialize') as mock_init:
            mock_init.return_value = None
            
            factory = AdapterFactory()
            
            adapter = await factory.create_adapter(
                AdapterType.GEMINI,
                "test_gemini_adapter",
                {"api_key": "test_key"}
            )
            
            assert isinstance(adapter, GeminiAdapter)
            assert "test_gemini_adapter" in factory.adapters
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_adapter_invalid_type(self):
        """Test creating adapter with invalid type."""
        factory = AdapterFactory()
        
        with pytest.raises(ConfigurationError, match="Unsupported adapter type"):
            await factory.create_adapter("invalid_type")
    
    @pytest.mark.asyncio
    async def test_get_adapter(self):
        """Test getting an existing adapter."""
        factory = AdapterFactory()
        
        # Create an adapter first
        adapter = await factory.create_adapter(AdapterType.BROWSER_USE, "test_adapter")
        
        # Get the adapter
        retrieved_adapter = await factory.get_adapter("test_adapter")
        
        assert retrieved_adapter is adapter
    
    @pytest.mark.asyncio
    async def test_get_adapter_not_found(self):
        """Test getting a non-existent adapter."""
        factory = AdapterFactory()
        
        adapter = await factory.get_adapter("nonexistent")
        
        assert adapter is None
    
    @pytest.mark.asyncio
    async def test_remove_adapter(self):
        """Test removing an adapter."""
        factory = AdapterFactory()
        
        # Create an adapter first
        await factory.create_adapter(AdapterType.BROWSER_USE, "test_adapter")
        
        # Remove the adapter
        result = await factory.remove_adapter("test_adapter")
        
        assert result is True
        assert "test_adapter" not in factory.adapters
        assert "test_adapter" not in factory.adapter_configs
    
    @pytest.mark.asyncio
    async def test_remove_adapter_not_found(self):
        """Test removing a non-existent adapter."""
        factory = AdapterFactory()
        
        result = await factory.remove_adapter("nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """Test health check for all adapters."""
        factory = AdapterFactory()
        
        # Create adapters
        await factory.create_adapter(AdapterType.BROWSER_USE, "adapter1")
        
        # Mock health check
        with patch.object(BrowserUseAdapter, 'health_check') as mock_health:
            mock_health.return_value = {"status": "healthy"}
            
            health_results = await factory.health_check_all()
            
            assert "adapter1" in health_results
            assert health_results["adapter1"]["status"] == "healthy"
    
    def test_get_statistics(self):
        """Test getting factory statistics."""
        factory = AdapterFactory()
        
        stats = factory.get_statistics()
        
        assert stats["total_adapters"] == 0
        assert "adapter_types" in stats
        assert "supported_types" in stats
        assert "timestamp" in stats
    
    @pytest.mark.asyncio
    async def test_shutdown(self):
        """Test factory shutdown."""
        factory = AdapterFactory()
        
        # Create some adapters
        await factory.create_adapter(AdapterType.BROWSER_USE, "adapter1")
        
        # Shutdown
        await factory.shutdown()
        
        assert len(factory.adapters) == 0
        assert len(factory.adapter_configs) == 0
