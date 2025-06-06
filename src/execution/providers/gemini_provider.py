"""
Google Gemini provider implementation for the unified LLM abstraction.

This module provides a provider-agnostic implementation for Google's Gemini models,
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


class GeminiProvider(AbstractLLMProvider):
    """Provider implementation for Google Gemini models."""
    
    def __init__(self, provider_name: str, model: str, config: Dict[str, Any]):
        super().__init__(provider_name, model, config)
        
        # Set capabilities
        self.capabilities = [
            ProviderCapability.TEXT_GENERATION,
            ProviderCapability.CONVERSATION,
            ProviderCapability.VISION,  # Gemini supports vision
            ProviderCapability.STREAMING
        ]
        
        self.client = None
        self.api_key = None
    
    async def initialize(self) -> None:
        """Initialize the Gemini provider."""
        try:
            # Import Gemini dependencies
            from langchain_google_genai import ChatGoogleGenerativeAI
            
            # Get API key
            self.api_key = self.config.get("api_key") or os.environ.get("GOOGLE_API_KEY")
            if not self.api_key:
                raise ConfigurationError("Google API key not found")
            
            # Create client
            self.client = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=self.api_key,
                temperature=self.config.get("temperature", 0.1),
                max_tokens=self.config.get("max_tokens", 2000),
                timeout=self.config.get("timeout", 30)
            )
            
            self.is_initialized = True
            
            self.logger.info(
                "Gemini provider initialized",
                model=self.model,
                capabilities=len(self.capabilities)
            )
            
        except ImportError as e:
            raise ConfigurationError(f"Gemini dependencies not installed: {e}") from e
        except Exception as e:
            raise LLMError(f"Failed to initialize Gemini provider: {e}") from e
    
    @with_correlation_id
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using Gemini."""
        if not self.is_initialized or not self.client:
            raise LLMError("Gemini provider not initialized")
        
        correlation_id = request.metadata.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Generating Gemini response",
            model=self.model,
            prompt_length=len(request.prompt),
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            correlation_id=correlation_id
        )
        
        try:
            # Use the prompt directly for Gemini
            response = await self.client.ainvoke(
                request.prompt,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            # Extract content
            if hasattr(response, 'content'):
                content = response.content
            else:
                content = str(response)
            
            # Estimate token usage (Gemini doesn't provide exact counts)
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
                    "estimated_usage": True
                }
            )
            
            self.logger.info(
                "Gemini response generated successfully",
                response_length=len(content),
                estimated_usage=usage,
                correlation_id=correlation_id
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(
                "Gemini generation failed",
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=correlation_id
            )
            raise LLMError(f"Gemini generation failed: {e}") from e
    
    async def health_check(self) -> bool:
        """Check if Gemini provider is healthy."""
        if not self.is_initialized or not self.client:
            return False
        
        try:
            # Make a simple test request
            response = await self.client.ainvoke("test")
            return response is not None
            
        except Exception as e:
            self.logger.warning(f"Gemini health check failed: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """Get token count for text (estimated for Gemini)."""
        # Gemini doesn't provide exact token counting
        # Use a rough estimation based on character count
        return len(text) // 4
    
    async def cleanup(self) -> None:
        """Cleanup Gemini provider resources."""
        # Gemini client doesn't need explicit cleanup
        self.is_initialized = False
        
        self.logger.info("Gemini provider cleaned up")
