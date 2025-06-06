"""
Unified LLM provider implementation for task execution.

This module provides a provider-agnostic LLM interface that eliminates vendor lock-in
and supports multiple LLM providers through a unified abstraction layer.
"""

import uuid
import time
from typing import Dict, Optional, Any

from core.interfaces import ILLMProvider
from core.exceptions import LLMError, ConfigurationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.llm.conversation_manager import ConversationManager
from src.infrastructure.cost_management import CostManager, AdvancedRateLimiter
from .llm_abstraction import create_unified_llm_provider, UnifiedLLMProvider
from .enhanced_error_recovery import EnhancedErrorRecovery


class TaskLLMProvider(ILLMProvider):
    """
    Enhanced LLM provider with cost management and advanced rate limiting.

    This provider uses the unified LLM abstraction with comprehensive cost tracking,
    budget enforcement, and intelligent rate limiting to optimize LLM usage.
    """

    def __init__(
        self,
        primary_provider: str,
        primary_model: str,
        primary_config: Dict[str, Any],
        fallback_provider: Optional[str] = None,
        fallback_model: Optional[str] = None,
        fallback_config: Optional[Dict[str, Any]] = None,
        conversation_manager: Optional[ConversationManager] = None,
        enable_cost_management: bool = True,
        enable_advanced_rate_limiting: bool = True,
        rate_limit_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the enhanced LLM provider.

        Args:
            primary_provider: Primary LLM provider name (e.g., "openai", "gemini")
            primary_model: Primary model name
            primary_config: Primary provider configuration
            fallback_provider: Optional fallback provider name
            fallback_model: Optional fallback model name
            fallback_config: Optional fallback provider configuration
            conversation_manager: Optional conversation manager instance
            enable_cost_management: Enable cost tracking and budget controls
            enable_advanced_rate_limiting: Enable advanced rate limiting
            rate_limit_config: Configuration for rate limiting
        """
        self.primary_provider_name = primary_provider
        self.primary_model = primary_model
        self.primary_config = primary_config
        self.fallback_provider_name = fallback_provider
        self.fallback_model = fallback_model
        self.fallback_config = fallback_config or {}

        # Initialize logger
        self.logger = StructuredLogger("enhanced_llm_provider")

        # Unified provider instance
        self.unified_provider: Optional[UnifiedLLMProvider] = None

        # Conversation manager
        self.conversation_manager = conversation_manager

        # Cost management
        self.cost_manager: Optional[CostManager] = None
        if enable_cost_management:
            self.cost_manager = CostManager()

        # Advanced rate limiting
        self.rate_limiter: Optional[AdvancedRateLimiter] = None
        if enable_advanced_rate_limiting:
            rate_config = rate_limit_config or {}
            self.rate_limiter = AdvancedRateLimiter(
                requests_per_minute=rate_config.get("requests_per_minute", 60),
                tokens_per_minute=rate_config.get("tokens_per_minute", 90000),
                cost_per_minute=rate_config.get("cost_per_minute", 10.0),
                adaptive=rate_config.get("adaptive", True)
            )

        # Error recovery
        self.error_recovery = EnhancedErrorRecovery()

        # Enhanced statistics
        self.request_count = 0
        self.error_count = 0
        self.total_tokens_used = 0
        self.total_cost = 0.0
        self.average_response_time = 0.0

        self.logger.info(
            "Enhanced LLM provider initialized",
            primary_provider=primary_provider,
            primary_model=primary_model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            cost_management_enabled=enable_cost_management,
            rate_limiting_enabled=enable_advanced_rate_limiting
        )
    
    async def initialize(self) -> None:
        """Initialize the unified LLM provider."""
        try:
            self.unified_provider = await create_unified_llm_provider(
                primary_provider=self.primary_provider_name,
                primary_model=self.primary_model,
                primary_config=self.primary_config,
                fallback_provider=self.fallback_provider_name,
                fallback_model=self.fallback_model,
                fallback_config=self.fallback_config
            )
            
            self.logger.info(
                "Unified LLM provider initialized successfully",
                capabilities=self.unified_provider.get_capabilities()
            )
            
        except Exception as e:
            self.logger.error(f"Failed to initialize unified LLM provider: {e}")
            raise ConfigurationError(f"LLM provider initialization failed: {e}") from e
    
    @with_correlation_id
    async def invoke(self, prompt: str, **kwargs) -> str:
        """
        Enhanced LLM invocation with cost management and rate limiting.

        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional parameters for the LLM call

        Returns:
            LLM response as a string

        Raises:
            LLMError: If the LLM call fails
        """
        if not self.unified_provider:
            raise LLMError("LLM provider not initialized")

        correlation_id = kwargs.get("correlation_id", str(uuid.uuid4()))
        start_time = time.time()

        # Estimate tokens and cost
        estimated_prompt_tokens = self.get_token_count(prompt)
        estimated_completion_tokens = kwargs.get("max_tokens", 2000)
        estimated_total_tokens = estimated_prompt_tokens + estimated_completion_tokens

        # Estimate cost (rough calculation)
        estimated_cost = estimated_total_tokens * 0.001 / 1000  # $0.001 per 1K tokens default

        # Check if provider is suspended due to budget
        if self.cost_manager and self.cost_manager.is_provider_suspended(self.primary_provider_name):
            raise LLMError(f"Provider {self.primary_provider_name} is suspended due to budget limits")

        # Apply rate limiting
        if self.rate_limiter:
            priority = kwargs.get("priority", "normal")

            if not await self.rate_limiter.acquire(
                estimated_tokens=estimated_total_tokens,
                estimated_cost=estimated_cost,
                priority=priority
            ):
                raise LLMError("Request rate limited - please try again later")

        self.logger.info(
            "Invoking enhanced LLM provider",
            prompt_length=len(prompt),
            estimated_tokens=estimated_total_tokens,
            estimated_cost=estimated_cost,
            correlation_id=correlation_id
        )

        self.request_count += 1
        success = False
        actual_tokens = 0

        try:
            response = await self.unified_provider.invoke(prompt, **kwargs)

            # Calculate actual tokens (if available from response metadata)
            actual_prompt_tokens = estimated_prompt_tokens  # Use estimate if not available
            actual_completion_tokens = self.get_token_count(response)
            actual_tokens = actual_prompt_tokens + actual_completion_tokens

            # Record usage for cost management
            if self.cost_manager:
                await self.cost_manager.record_usage(
                    provider=self.primary_provider_name,
                    model=self.primary_model,
                    operation="text_generation",
                    prompt_tokens=actual_prompt_tokens,
                    completion_tokens=actual_completion_tokens,
                    correlation_id=correlation_id,
                    user_id=kwargs.get("user_id"),
                    project_id=kwargs.get("project_id")
                )

            # Update statistics
            response_time = time.time() - start_time
            self.total_tokens_used += actual_tokens
            self.average_response_time = (
                (self.average_response_time * (self.request_count - 1) + response_time) /
                self.request_count
            )

            success = True

            self.logger.info(
                "Enhanced LLM invocation successful",
                response_length=len(response),
                actual_tokens=actual_tokens,
                response_time=response_time,
                correlation_id=correlation_id
            )

            return response

        except Exception as e:
            self.error_count += 1

            # Handle error with enhanced recovery
            recovery_result = await self.error_recovery.handle_error(
                e, "llm_provider", "invoke",
                context={
                    "provider": self.primary_provider_name,
                    "model": self.primary_model,
                    "prompt_length": len(prompt),
                    "estimated_tokens": estimated_total_tokens
                },
                correlation_id=correlation_id
            )

            self.logger.error(
                "Enhanced LLM invocation failed",
                error=str(e),
                error_type=type(e).__name__,
                recovery_attempted=recovery_result.get("recovery_attempted", False),
                correlation_id=correlation_id
            )

            raise LLMError(f"LLM invocation failed: {e}") from e

        finally:
            # Update rate limiter performance metrics
            if self.rate_limiter:
                response_time = time.time() - start_time
                self.rate_limiter.update_performance_metrics(
                    success=success,
                    response_time=response_time,
                    error_occurred=not success
                )
    
    async def health_check(self) -> bool:
        """Check if the LLM provider is available and healthy."""
        if not self.unified_provider:
            return False
        
        try:
            return await self.unified_provider.health_check()
        except Exception as e:
            self.logger.warning(f"Health check failed: {e}")
            return False
    
    def get_token_count(self, text: str) -> int:
        """Get the token count for a given text."""
        if self.unified_provider:
            return self.unified_provider.get_token_count(text)
        return len(text) // 4  # Rough estimate
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive provider statistics."""
        stats = {
            "basic_stats": {
                "request_count": self.request_count,
                "error_count": self.error_count,
                "error_rate": self.error_count / max(self.request_count, 1),
                "total_tokens_used": self.total_tokens_used,
                "total_cost": self.total_cost,
                "average_response_time": self.average_response_time
            },
            "provider_info": {
                "primary_provider": self.primary_provider_name,
                "primary_model": self.primary_model,
                "fallback_provider": self.fallback_provider_name,
                "fallback_model": self.fallback_model,
                "capabilities": self.unified_provider.get_capabilities() if self.unified_provider else {}
            }
        }

        # Add cost management stats
        if self.cost_manager:
            stats["cost_management"] = {
                "daily_usage": self.cost_manager.get_usage_summary("daily"),
                "monthly_usage": self.cost_manager.get_usage_summary("monthly"),
                "suspended_providers": list(self.cost_manager.suspended_providers.keys())
            }

        # Add rate limiting stats
        if self.rate_limiter:
            stats["rate_limiting"] = self.rate_limiter.get_status()

        # Add error recovery stats
        stats["error_recovery"] = self.error_recovery.get_recovery_statistics()

        return stats
    
    async def cleanup(self) -> None:
        """Cleanup provider resources."""
        if self.unified_provider:
            await self.unified_provider.cleanup()
        
        self.logger.info("Task LLM provider cleaned up")


# Factory function for easy provider creation
async def create_llm_provider(
    primary_provider: str = "gemini",
    primary_model: str = "models/gemini-2.5-flash-preview-04-17",
    primary_config: Optional[Dict[str, Any]] = None,
    fallback_provider: Optional[str] = None,
    fallback_model: Optional[str] = None,
    fallback_config: Optional[Dict[str, Any]] = None
) -> TaskLLMProvider:
    """
    Factory function to create and initialize a task LLM provider.
    
    Args:
        primary_provider: Primary LLM provider name
        primary_model: Primary model name
        primary_config: Primary provider configuration
        fallback_provider: Optional fallback provider name
        fallback_model: Optional fallback model name
        fallback_config: Optional fallback provider configuration
        
    Returns:
        Initialized TaskLLMProvider instance
    """
    provider = TaskLLMProvider(
        primary_provider=primary_provider,
        primary_model=primary_model,
        primary_config=primary_config or {},
        fallback_provider=fallback_provider,
        fallback_model=fallback_model,
        fallback_config=fallback_config
    )
    
    await provider.initialize()
    return provider
