"""
Local LLM provider implementation for the unified LLM abstraction.

This module provides a provider-agnostic implementation for local LLM models
(e.g., Ollama), eliminating vendor lock-in through the unified interface.
"""

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


class LocalProvider(AbstractLLMProvider):
    """Provider implementation for local LLM models."""
    
    def __init__(self, provider_name: str, model: str, config: Dict[str, Any]):
        super().__init__(provider_name, model, config)
        
        # Set capabilities (local models typically support basic text generation)
        self.capabilities = [
            ProviderCapability.TEXT_GENERATION,
            ProviderCapability.CONVERSATION,
            ProviderCapability.STREAMING
        ]
        
        self.client = None
        self.endpoint = None
    
    async def initialize(self) -> None:
        """Initialize the local LLM provider."""
        try:
            # Import local LLM dependencies
            from langchain_community.llms import Ollama
            
            # Get endpoint
            self.endpoint = self.config.get("endpoint", "http://localhost:11434")
            
            # Create client
            self.client = Ollama(
                base_url=self.endpoint,
                model=self.model,
                temperature=self.config.get("temperature", 0.1),
                timeout=self.config.get("timeout", 60)
            )
            
            self.is_initialized = True
            
            self.logger.info(
                "Local LLM provider initialized",
                model=self.model,
                endpoint=self.endpoint,
                capabilities=len(self.capabilities)
            )
            
        except ImportError as e:
            raise ConfigurationError(f"Local LLM dependencies not installed: {e}") from e
        except Exception as e:
            raise LLMError(f"Failed to initialize local LLM provider: {e}") from e
    
    @with_correlation_id
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using local LLM."""
        if not self.is_initialized or not self.client:
            raise LLMError("Local LLM provider not initialized")
        
        correlation_id = request.metadata.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Generating local LLM response",
            model=self.model,
            endpoint=self.endpoint,
            prompt_length=len(request.prompt),
            temperature=request.temperature,
            correlation_id=correlation_id
        )
        
        try:
            # Use the prompt directly for local LLM
            response = await self.client.ainvoke(request.prompt)
            
            # Extract content
            content = str(response) if response else ""
            
            # Estimate token usage (local models don't provide exact counts)
            prompt_tokens = self.get_token_count(request.prompt)
            completion_tokens = self.get_token_count(content)
            
            usage = {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens
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
                    "endpoint": self.endpoint,
                    "estimated_usage": True
                }
            )
            
            self.logger.info(
                "Local LLM response generated successfully",
                response_length=len(content),
                estimated_usage=usage,
                correlation_id=correlation_id
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(
                "Local LLM generation failed",
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=correlation_id
            )
            raise LLMError(f"Local LLM generation failed: {e}") from e
    
    async def health_check(self) -> bool:
        """Check if local LLM provider is healthy."""
        if not self.is_initialized or not self.client:
            return False
        
        try:
            # Make a simple test request
            response = await self.client.ainvoke("test")
            return response is not None
            
        except Exception as e:
            self.logger.warning(f"Local LLM health check failed: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """Get token count for text (estimated for local models)."""
        # Local models don't provide exact token counting
        # Use a rough estimation based on character count
        return len(text) // 4
    
    async def cleanup(self) -> None:
        """Cleanup local LLM provider resources."""
        # Local LLM client doesn't need explicit cleanup
        self.is_initialized = False
        
        self.logger.info("Local LLM provider cleaned up")
