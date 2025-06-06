"""
OpenAI provider implementation for the unified LLM abstraction.

This module provides a provider-agnostic implementation for OpenAI's GPT models,
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


class OpenAIProvider(AbstractLLMProvider):
    """Provider implementation for OpenAI GPT models."""
    
    def __init__(self, provider_name: str, model: str, config: Dict[str, Any]):
        super().__init__(provider_name, model, config)
        
        # Set capabilities
        self.capabilities = [
            ProviderCapability.TEXT_GENERATION,
            ProviderCapability.CONVERSATION,
            ProviderCapability.FUNCTION_CALLING,
            ProviderCapability.STREAMING
        ]
        
        # Add vision capability for vision models
        if "vision" in model.lower() or "gpt-4" in model.lower():
            self.capabilities.append(ProviderCapability.VISION)
        
        self.client = None
        self.api_key = None
    
    async def initialize(self) -> None:
        """Initialize the OpenAI provider."""
        try:
            # Import OpenAI dependencies
            from openai import AsyncOpenAI
            
            # Get API key
            self.api_key = self.config.get("api_key") or os.environ.get("OPENAI_API_KEY")
            if not self.api_key:
                raise ConfigurationError("OpenAI API key not found")
            
            # Create client
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                organization=self.config.get("organization"),
                base_url=self.config.get("base_url"),
                timeout=self.config.get("timeout", 30),
                max_retries=self.config.get("max_retries", 3)
            )
            
            self.is_initialized = True
            
            self.logger.info(
                "OpenAI provider initialized",
                model=self.model,
                capabilities=len(self.capabilities)
            )
            
        except ImportError as e:
            raise ConfigurationError(f"OpenAI dependencies not installed: {e}") from e
        except Exception as e:
            raise LLMError(f"Failed to initialize OpenAI provider: {e}") from e
    
    @with_correlation_id
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate a response using OpenAI."""
        if not self.is_initialized or not self.client:
            raise LLMError("OpenAI provider not initialized")
        
        correlation_id = request.metadata.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Generating OpenAI response",
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
            
            # Prepare request parameters
            request_params = {
                "model": self.model,
                "messages": messages,
                "temperature": request.temperature,
                "max_tokens": request.max_tokens,
            }
            
            # Add functions if supported and provided
            if request.functions and self.supports_capability(ProviderCapability.FUNCTION_CALLING):
                request_params["functions"] = request.functions
            
            # Make API call
            response = await self.client.chat.completions.create(**request_params)
            
            # Extract content
            content = response.choices[0].message.content or ""
            
            # Extract usage information
            usage = {}
            if response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens
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
                    "finish_reason": response.choices[0].finish_reason
                }
            )
            
            self.logger.info(
                "OpenAI response generated successfully",
                response_length=len(content),
                usage=usage,
                correlation_id=correlation_id
            )
            
            return llm_response
            
        except Exception as e:
            self.logger.error(
                "OpenAI generation failed",
                error=str(e),
                error_type=type(e).__name__,
                correlation_id=correlation_id
            )
            raise LLMError(f"OpenAI generation failed: {e}") from e
    
    async def health_check(self) -> bool:
        """Check if OpenAI provider is healthy."""
        if not self.is_initialized or not self.client:
            return False
        
        try:
            # Make a simple test request
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=1
            )
            return response is not None
            
        except Exception as e:
            self.logger.warning(f"OpenAI health check failed: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """Get token count for text using OpenAI's tokenizer."""
        try:
            import tiktoken
            
            # Get encoding for the model
            if "gpt-4" in self.model:
                encoding = tiktoken.encoding_for_model("gpt-4")
            elif "gpt-3.5" in self.model:
                encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
            else:
                # Fallback to cl100k_base encoding
                encoding = tiktoken.get_encoding("cl100k_base")
            
            return len(encoding.encode(text))
            
        except ImportError:
            # Fallback to rough estimation
            return len(text) // 4
        except Exception:
            # Fallback to rough estimation
            return len(text) // 4
    
    async def cleanup(self) -> None:
        """Cleanup OpenAI provider resources."""
        if self.client:
            await self.client.close()
        self.is_initialized = False
        
        self.logger.info("OpenAI provider cleaned up")
