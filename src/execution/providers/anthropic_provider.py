"""
Anthropic Claude provider implementation for the unified LLM abstraction.

This module provides a provider-agnostic implementation for Anthropic's Claude models,
eliminating vendor lock-in through the unified interface.
"""

import os
import uuid
from typing import Dict, Any, Optional

from ..llm_abstraction import (
    AbstractLLMProvider, 
    LLMRequest, 
    LLMResponse, 
    ProviderCapability
)
from core.exceptions import LLMError, ConfigurationError
from src.infrastructure.logging.logger import with_correlation_id


class AnthropicProvider(AbstractLLMProvider):
    """Provider implementation for Anthropic Claude models."""
    
    def __init__(self, provider_name: str, model: str, config: Dict[str, Any]):
        super().__init__(provider_name, model, config)
        
        # Set capabilities
        self.capabilities = [
            ProviderCapability.TEXT_GENERATION,
            ProviderCapability.CONVERSATION,
            ProviderCapability.STREAMING
        ]
        
        # Add vision capability for vision models
        if "vision" in model.lower() or "claude-3" in model.lower():
            self.capabilities.append(ProviderCapability.VISION)
        
        self.client = None
        self.api_key = None
    
    async def initialize(self) -> None:
        """Initialize the Anthropic provider."""
        try:
            # Import Anthropic dependencies
            from anthropic import AsyncAnthropic
            
            # Get API key
            self.api_key = self.config.get("api_key") or os.environ.get("ANTHROPIC_API_KEY")
            if not self.api_key:
                raise ConfigurationError("Anthropic API key not found")
            
            # Create client
            self.client = AsyncAnthropic(
                api_key=self.api_key,
                timeout=self.config.get("timeout", 30),
                max_retries=self.config.get("max_retries", 3)
            )
            
            self.is_initialized = True
            
            self.logger.info(
                "Anthropic provider initialized",
                model=self.model,
                capabilities=len(self.capabilities)
            )
            
        except ImportError as e:
            raise ConfigurationError(f"Anthropic dependencies not installed: {e}") from e
        except Exception as e:
            raise LLMError(f"Failed to initialize Anthropic provider: {e}") from e
    
    @with_correlation_id
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using Anthropic Claude."""
        if not self.is_initialized or not self.client:
            raise LLMError("Anthropic provider not initialized")
        
        correlation_id = request.metadata.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Generating Anthropic response",
            model=self.model,
            prompt_length=len(request.prompt),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            correlation_id=correlation_id
        )
        
        try:
            # Prepare messages
            messages = []
            if request.messages:
                messages = request.messages
            else:
                messages = [{"role": "user", "content": request.prompt}]
            
            # Make API call
            response = await self.client.messages.create(
                model=self.model,
                messages=messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            # Extract content
            content = ""
            if response.content:
                content = response.content[0].text if response.content else ""
            
            # Extract usage information
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            
            # Create standardized response
            llm_response = LLMResponse(
                content=content,
                request_id=request.request_id,
                provider=self.provider_name,
                model=self.model,
                usage=usage,
                metadata={
                    "correlation_id": correlation_id,
                    "response_id": response.id,
                    "stop_reason": response.stop_reason
                }
            )
            
            self.logger.info(
                "Anthropic response generated successfully",
                response_length=len(content),
                usage=usage,
                correlation_id=correlation_id
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(
                "Anthropic generation failed",
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=correlation_id
            )
            raise LLMError(f"Anthropic generation failed: {e}") from e
    
    async def health_check(self) -> bool:
        """Check if Anthropic provider is healthy."""
        if not self.is_initialized or not self.client:
            return False
        
        try:
            # Make a simple test request
            response = await self.client.messages.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return response is not None
            
        except Exception as e:
            self.logger.warning(f"Anthropic health check failed: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """Get token count for text (estimated for Anthropic)."""
        # Anthropic doesn't provide a public tokenizer
        # Use a rough estimation based on character count
        return len(text) // 4
    
    async def cleanup(self) -> None:
        """Cleanup Anthropic provider resources."""
        if self.client:
            await self.client.close()
        self.is_initialized = False
        
        self.logger.info("Anthropic provider cleaned up")
