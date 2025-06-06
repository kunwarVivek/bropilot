"""
Provider-agnostic LLM abstraction layer.

This module provides a unified interface for all LLM providers, eliminating
vendor lock-in and providing a consistent API across different providers.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Type
from datetime import datetime, timezone
from enum import Enum

from core.interfaces import ILLMProvider
from core.exceptions import LLMError, ConfigurationError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class ProviderCapability(str, Enum):
    """Capabilities that LLM providers can support."""
    TEXT_GENERATION = "text_generation"
    CONVERSATION = "conversation"
    FUNCTION_CALLING = "function_calling"
    VISION = "vision"
    STREAMING = "streaming"
    EMBEDDINGS = "embeddings"


class LLMRequest:
    """Standardized LLM request format."""
    
    def __init__(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 2000,
        messages: Optional[List[Dict[str, Any]]] = None,
        functions: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.prompt = prompt
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.messages = messages or []
        self.functions = functions or []
        self.metadata = metadata or {}
        self.request_id = str(uuid.uuid4())
        self.timestamp = datetime.now(timezone.utc)


class LLMResponse:
    """Standardized LLM response format."""
    
    def __init__(
        self,
        content: str,
        request_id: str,
        provider: str,
        model: str,
        usage: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.content = content
        self.request_id = request_id
        self.provider = provider
        self.model = model
        self.usage = usage or {}
        self.metadata = metadata or {}
        self.timestamp = datetime.now(timezone.utc)


class AbstractLLMProvider(ABC):
    """Abstract base class for all LLM providers."""
    
    def __init__(self, provider_name: str, model: str, config: Dict[str, Any]):
        self.provider_name = provider_name
        self.model = model
        self.config = config
        self.logger = StructuredLogger(f"llm_provider_{provider_name}")
        self.capabilities: List[ProviderCapability] = []
        self.is_initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the provider."""
        pass
    
    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response for the given request."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is healthy."""
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Get token count for text."""
        pass
    
    def supports_capability(self, capability: ProviderCapability) -> bool:
        """Check if provider supports a capability."""
        return capability in self.capabilities
    
    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        pass


class LLMProviderRegistry:
    """Registry for managing LLM providers."""
    
    def __init__(self):
        self.providers: Dict[str, Type[AbstractLLMProvider]] = {}
        self.instances: Dict[str, AbstractLLMProvider] = {}
        self.logger = StructuredLogger("llm_provider_registry")
    
    def register_provider(
        self, 
        provider_name: str, 
        provider_class: Type[AbstractLLMProvider]
    ) -> None:
        """Register a new provider class."""
        self.providers[provider_name] = provider_class
        self.logger.info(f"Registered LLM provider: {provider_name}")
    
    async def create_provider(
        self,
        provider_name: str,
        model: str,
        config: Dict[str, Any],
        instance_id: Optional[str] = None
    ) -> AbstractLLMProvider:
        """Create and initialize a provider instance."""
        if provider_name not in self.providers:
            raise ConfigurationError(f"Unknown provider: {provider_name}")
        
        provider_class = self.providers[provider_name]
        instance = provider_class(provider_name, model, config)
        
        await instance.initialize()
        
        if instance_id:
            self.instances[instance_id] = instance
        
        return instance
    
    def get_provider(self, instance_id: str) -> Optional[AbstractLLMProvider]:
        """Get a provider instance by ID."""
        return self.instances.get(instance_id)
    
    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self.providers.keys())
    
    def get_provider_capabilities(self, provider_name: str) -> List[ProviderCapability]:
        """Get capabilities of a provider."""
        if provider_name not in self.providers:
            return []
        
        # Create a temporary instance to check capabilities
        temp_instance = self.providers[provider_name](provider_name, "temp", {})
        return temp_instance.capabilities


class UnifiedLLMProvider(ILLMProvider):
    """
    Unified LLM provider that abstracts away vendor-specific implementations.
    
    This provider uses the registry to manage different LLM providers and
    provides a consistent interface regardless of the underlying provider.
    """
    
    def __init__(
        self,
        primary_provider: str,
        primary_model: str,
        primary_config: Dict[str, Any],
        fallback_provider: Optional[str] = None,
        fallback_model: Optional[str] = None,
        fallback_config: Optional[Dict[str, Any]] = None
    ):
        self.primary_provider_name = primary_provider
        self.primary_model = primary_model
        self.primary_config = primary_config
        
        self.fallback_provider_name = fallback_provider
        self.fallback_model = fallback_model
        self.fallback_config = fallback_config or {}
        
        self.registry = LLMProviderRegistry()
        self.primary_provider: Optional[AbstractLLMProvider] = None
        self.fallback_provider: Optional[AbstractLLMProvider] = None
        
        self.logger = StructuredLogger("unified_llm_provider")
        self.request_count = 0
        self.error_count = 0
    
    async def initialize(self) -> None:
        """Initialize the unified provider."""
        # Auto-register known providers
        await self._register_known_providers()
        
        # Create primary provider
        self.primary_provider = await self.registry.create_provider(
            self.primary_provider_name,
            self.primary_model,
            self.primary_config,
            "primary"
        )
        
        # Create fallback provider if specified
        if self.fallback_provider_name:
            self.fallback_provider = await self.registry.create_provider(
                self.fallback_provider_name,
                self.fallback_model,
                self.fallback_config,
                "fallback"
            )
        
        self.logger.info(
            "Unified LLM provider initialized",
            primary_provider=self.primary_provider_name,
            primary_model=self.primary_model,
            fallback_provider=self.fallback_provider_name,
            fallback_model=self.fallback_model
        )
    
    async def _register_known_providers(self) -> None:
        """Register all known provider implementations."""
        # Import and register providers dynamically
        try:
            from .providers.openai_provider import OpenAIProvider
            self.registry.register_provider("openai", OpenAIProvider)
        except ImportError:
            self.logger.warning("OpenAI provider not available")
        
        try:
            from .providers.anthropic_provider import AnthropicProvider
            self.registry.register_provider("anthropic", AnthropicProvider)
        except ImportError:
            self.logger.warning("Anthropic provider not available")
        
        try:
            from .providers.gemini_provider import GeminiProvider
            self.registry.register_provider("gemini", GeminiProvider)
        except ImportError:
            self.logger.warning("Gemini provider not available")
        
        try:
            from .providers.local_provider import LocalProvider
            self.registry.register_provider("local", LocalProvider)
        except ImportError:
            self.logger.warning("Local provider not available")
    
    @with_correlation_id
    async def invoke(self, prompt: str, **kwargs) -> str:
        """Invoke the LLM with a prompt."""
        correlation_id = kwargs.get("correlation_id", str(uuid.uuid4()))
        
        # Create standardized request
        request = LLMRequest(
            prompt=prompt,
            temperature=kwargs.get("temperature", 0.1),
            max_tokens=kwargs.get("max_tokens", 2000),
            messages=kwargs.get("messages", []),
            functions=kwargs.get("functions", []),
            metadata={"correlation_id": correlation_id}
        )
        
        self.request_count += 1
        
        try:
            # Try primary provider
            if self.primary_provider:
                response = await self.primary_provider.generate(request)
                return response.content
            else:
                raise LLMError("Primary provider not initialized")
                
        except Exception as e:
            self.error_count += 1
            self.logger.warning(
                "Primary provider failed, trying fallback",
                error=str(e),
                correlation_id=correlation_id
            )
            
            # Try fallback provider
            if self.fallback_provider:
                try:
                    response = await self.fallback_provider.generate(request)
                    return response.content
                except Exception as fallback_error:
                    self.logger.error(
                        "Fallback provider also failed",
                        error=str(fallback_error),
                        correlation_id=correlation_id
                    )
                    raise LLMError(f"Both providers failed: {e}, {fallback_error}")
            else:
                raise LLMError(f"Primary provider failed and no fallback: {e}")
    
    async def health_check(self) -> bool:
        """Check health of providers."""
        primary_healthy = False
        fallback_healthy = False
        
        if self.primary_provider:
            primary_healthy = await self.primary_provider.health_check()
        
        if self.fallback_provider:
            fallback_healthy = await self.fallback_provider.health_check()
        
        return primary_healthy or fallback_healthy
    
    def get_token_count(self, text: str) -> int:
        """Get token count using primary provider."""
        if self.primary_provider:
            return self.primary_provider.get_token_count(text)
        return len(text) // 4  # Rough estimate
    
    def get_capabilities(self) -> Dict[str, List[ProviderCapability]]:
        """Get capabilities of all providers."""
        capabilities = {}
        
        if self.primary_provider:
            capabilities["primary"] = self.primary_provider.capabilities
        
        if self.fallback_provider:
            capabilities["fallback"] = self.fallback_provider.capabilities
        
        return capabilities
    
    async def cleanup(self) -> None:
        """Cleanup all providers."""
        if self.primary_provider:
            await self.primary_provider.cleanup()
        
        if self.fallback_provider:
            await self.fallback_provider.cleanup()


# Factory function for easy creation
async def create_unified_llm_provider(
    primary_provider: str,
    primary_model: str,
    primary_config: Dict[str, Any],
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
    fallback_config: Optional[Dict[str, Any]] = None
) -> UnifiedLLMProvider:
    """Create and initialize a unified LLM provider."""
    provider = UnifiedLLMProvider(
        primary_provider=primary_provider,
        primary_model=primary_model,
        primary_config=primary_config,
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
        fallback_config=fallback_config
    )
    
    await provider.initialize()
    return provider
