"""
Unit tests for TaskLLMProvider implementation.

This module tests the core functionality of the TaskLLMProvider class
to ensure it properly implements the ILLMProvider interface.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from core.exceptions import LLMError, ConfigurationError
from src.execution.llm_provider import TaskLLMProvider, LLMProviderType, create_llm_provider


@pytest.fixture
def mock_langchain_provider():
    """Create a mock LangChain provider."""
    provider = Mock()
    provider.ainvoke = AsyncMock()
    
    # Mock response with content attribute
    mock_response = Mock()
    mock_response.content = "Test response from LLM"
    provider.ainvoke.return_value = mock_response
    
    return provider


@pytest.fixture
def provider_config():
    """Create a sample provider configuration."""
    return {
        "temperature": 0.1,
        "max_tokens": 2000,
        "timeout": 30,
        "model": "test-model",
        "api_key": "test-api-key"
    }


class TestTaskLLMProvider:
    """Test cases for TaskLLMProvider class."""
    
    def test_init(self):
        """Test TaskLLMProvider initialization."""
        provider = TaskLLMProvider(
            provider_type=LLMProviderType.OPENAI,
            config={"temperature": 0.2},
            fallback_provider=LLMProviderType.GEMINI
        )
        
        assert provider.provider_type == LLMProviderType.OPENAI
        assert provider.fallback_provider == LLMProviderType.GEMINI
        assert provider.config["temperature"] == 0.2
        assert provider.request_count == 0
        assert provider.error_count == 0
        assert provider.fallback_count == 0
    
    def test_init_defaults(self):
        """Test TaskLLMProvider initialization with defaults."""
        provider = TaskLLMProvider()
        
        assert provider.provider_type == LLMProviderType.GEMINI
        assert provider.fallback_provider is None
        assert provider.config == {}
    
    @pytest.mark.asyncio
    async def test_initialize_success(self, provider_config):
        """Test successful provider initialization."""
        with patch.object(TaskLLMProvider, '_create_provider_instance') as mock_create:
            mock_provider = Mock()
            mock_create.return_value = mock_provider
            
            provider = TaskLLMProvider(
                provider_type=LLMProviderType.OPENAI,
                config=provider_config
            )
            
            await provider.initialize()
            
            assert provider.primary_provider == mock_provider
            mock_create.assert_called_once_with(LLMProviderType.OPENAI, provider_config)
    
    @pytest.mark.asyncio
    async def test_initialize_with_fallback(self, provider_config):
        """Test provider initialization with fallback."""
        with patch.object(TaskLLMProvider, '_create_provider_instance') as mock_create:
            mock_primary = Mock()
            mock_fallback = Mock()
            mock_create.side_effect = [mock_primary, mock_fallback]
            
            provider = TaskLLMProvider(
                provider_type=LLMProviderType.OPENAI,
                config=provider_config,
                fallback_provider=LLMProviderType.GEMINI
            )
            
            await provider.initialize()
            
            assert provider.primary_provider == mock_primary
            assert provider.fallback_provider_instance == mock_fallback
            assert mock_create.call_count == 2
    
    @pytest.mark.asyncio
    async def test_initialize_failure(self, provider_config):
        """Test provider initialization failure."""
        with patch.object(TaskLLMProvider, '_create_provider_instance') as mock_create:
            mock_create.side_effect = Exception("Provider creation failed")
            
            provider = TaskLLMProvider(
                provider_type=LLMProviderType.OPENAI,
                config=provider_config
            )
            
            with pytest.raises(LLMError, match="Failed to initialize LLM provider"):
                await provider.initialize()
    
    @pytest.mark.asyncio
    async def test_invoke_success(self, mock_langchain_provider):
        """Test successful LLM invocation."""
        provider = TaskLLMProvider()
        provider.primary_provider = mock_langchain_provider
        
        response = await provider.invoke("Test prompt")
        
        assert response == "Test response from LLM"
        assert provider.request_count == 1
        assert provider.error_count == 0
        mock_langchain_provider.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invoke_with_fallback(self, mock_langchain_provider):
        """Test LLM invocation with fallback on primary failure."""
        # Setup primary provider to fail
        primary_provider = Mock()
        primary_provider.ainvoke = AsyncMock(side_effect=Exception("Primary failed"))
        
        # Setup fallback provider to succeed
        fallback_provider = mock_langchain_provider
        
        provider = TaskLLMProvider()
        provider.primary_provider = primary_provider
        provider.fallback_provider_instance = fallback_provider
        
        response = await provider.invoke("Test prompt")
        
        assert response == "Test response from LLM"
        assert provider.request_count == 1
        assert provider.error_count == 1
        assert provider.fallback_count == 1
        
        primary_provider.ainvoke.assert_called_once()
        fallback_provider.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_invoke_both_providers_fail(self):
        """Test LLM invocation when both primary and fallback fail."""
        # Setup both providers to fail
        primary_provider = Mock()
        primary_provider.ainvoke = AsyncMock(side_effect=Exception("Primary failed"))
        
        fallback_provider = Mock()
        fallback_provider.ainvoke = AsyncMock(side_effect=Exception("Fallback failed"))
        
        provider = TaskLLMProvider()
        provider.primary_provider = primary_provider
        provider.fallback_provider_instance = fallback_provider
        
        with pytest.raises(LLMError, match="All providers failed"):
            await provider.invoke("Test prompt")
        
        assert provider.error_count == 1
    
    @pytest.mark.asyncio
    async def test_invoke_no_fallback(self):
        """Test LLM invocation failure with no fallback."""
        # Setup primary provider to fail
        primary_provider = Mock()
        primary_provider.ainvoke = AsyncMock(side_effect=Exception("Primary failed"))
        
        provider = TaskLLMProvider()
        provider.primary_provider = primary_provider
        provider.fallback_provider_instance = None
        
        with pytest.raises(LLMError, match="LLM provider failed"):
            await provider.invoke("Test prompt")
        
        assert provider.error_count == 1
        assert provider.fallback_count == 0
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, mock_langchain_provider):
        """Test successful health check."""
        provider = TaskLLMProvider()
        provider.primary_provider = mock_langchain_provider
        
        is_healthy = await provider.health_check()
        
        assert is_healthy is True
        mock_langchain_provider.ainvoke.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        # Setup provider to fail
        primary_provider = Mock()
        primary_provider.ainvoke = AsyncMock(side_effect=Exception("Health check failed"))
        
        provider = TaskLLMProvider()
        provider.primary_provider = primary_provider
        provider.fallback_provider_instance = None
        
        is_healthy = await provider.health_check()
        
        assert is_healthy is False
    
    def test_get_token_count(self):
        """Test token count estimation."""
        provider = TaskLLMProvider()
        
        # Test with various text lengths
        assert provider.get_token_count("") == 1  # Minimum 1 token
        assert provider.get_token_count("hello") == 1  # 5 chars / 4 = 1.25 -> 1
        assert provider.get_token_count("hello world") == 2  # 11 chars / 4 = 2.75 -> 2
        assert provider.get_token_count("a" * 20) == 5  # 20 chars / 4 = 5
    
    @pytest.mark.asyncio
    async def test_generate_response(self, mock_langchain_provider):
        """Test structured response generation."""
        provider = TaskLLMProvider()
        provider.primary_provider = mock_langchain_provider
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"}
        ]
        
        response = await provider.generate_response(
            messages=messages,
            temperature=0.2,
            max_tokens=1000
        )
        
        assert response["content"] == "Test response from LLM"
        assert response["role"] == "assistant"
        assert "usage" in response
        assert "metadata" in response
        assert response["metadata"]["temperature"] == 0.2
        assert response["metadata"]["max_tokens"] == 1000
    
    def test_get_conversation_manager(self):
        """Test conversation manager creation."""
        provider = TaskLLMProvider()
        
        # Create first conversation manager
        cm1 = provider.get_conversation_manager(
            context_id="test_context_1",
            system_prompt="Test system prompt"
        )
        
        # Get the same conversation manager
        cm2 = provider.get_conversation_manager(context_id="test_context_1")
        
        # Create different conversation manager
        cm3 = provider.get_conversation_manager(context_id="test_context_2")
        
        assert cm1 is cm2  # Same instance for same context
        assert cm1 is not cm3  # Different instance for different context
        assert len(provider.conversation_managers) == 2
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        provider = TaskLLMProvider(
            provider_type=LLMProviderType.OPENAI,
            fallback_provider=LLMProviderType.GEMINI
        )
        
        # Simulate some activity
        provider.request_count = 10
        provider.error_count = 2
        provider.fallback_count = 1
        
        stats = provider.get_statistics()
        
        assert stats["provider_type"] == "openai"
        assert stats["fallback_provider"] == "gemini"
        assert stats["request_count"] == 10
        assert stats["error_count"] == 2
        assert stats["fallback_count"] == 1
        assert stats["success_rate"] == 0.8  # (10-2)/10
        assert stats["active_conversations"] == 0
        assert "timestamp" in stats
    
    def test_messages_to_prompt(self):
        """Test message to prompt conversion."""
        provider = TaskLLMProvider()
        
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"}
        ]
        
        prompt = provider._messages_to_prompt(messages)
        
        expected = "System: You are helpful\n\nHuman: Hello\n\nAssistant: Hi there!\n\nHuman: How are you?\n\nAssistant:"
        assert prompt == expected
    
    def test_add_function_context(self):
        """Test adding function context to prompt."""
        provider = TaskLLMProvider()
        
        base_prompt = "Original prompt"
        functions = ["function1", "function2"]
        tools = ["tool1", "tool2"]
        
        enhanced_prompt = provider._add_function_context(
            base_prompt, functions, tools
        )
        
        assert "Original prompt" in enhanced_prompt
        assert "Available functions: function1, function2" in enhanced_prompt
        assert "Available tools: tool1, tool2" in enhanced_prompt
        assert "FUNCTION_CALL" in enhanced_prompt
        assert "TOOL_USE" in enhanced_prompt


class TestCreateLLMProvider:
    """Test cases for the factory function."""
    
    @pytest.mark.asyncio
    async def test_create_llm_provider_success(self):
        """Test successful provider creation via factory."""
        with patch.object(TaskLLMProvider, 'initialize') as mock_init:
            mock_init.return_value = None
            
            provider = await create_llm_provider(
                provider_type="openai",
                config={"temperature": 0.1},
                fallback_provider="gemini"
            )
            
            assert isinstance(provider, TaskLLMProvider)
            assert provider.provider_type == LLMProviderType.OPENAI
            assert provider.fallback_provider == LLMProviderType.GEMINI
            mock_init.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_llm_provider_invalid_type(self):
        """Test provider creation with invalid provider type."""
        with pytest.raises(ConfigurationError, match="Unsupported provider type"):
            await create_llm_provider(provider_type="invalid_provider")
    
    @pytest.mark.asyncio
    async def test_create_llm_provider_invalid_fallback(self):
        """Test provider creation with invalid fallback type."""
        with pytest.raises(ConfigurationError, match="Unsupported fallback provider type"):
            await create_llm_provider(
                provider_type="openai",
                fallback_provider="invalid_fallback"
            )
