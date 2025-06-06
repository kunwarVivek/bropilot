"""
Retry mechanisms with exponential backoff.

This module provides comprehensive retry functionality with various backoff
strategies, jitter, and configurable retry policies for different scenarios.
"""

import asyncio
import random
import time
from typing import Any, Callable, Optional, Union, Type, Tuple, Dict, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import functools
import inspect

from core.exceptions import RetryExhaustedError, TimeoutError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class BackoffStrategy(str, Enum):
    """Backoff strategy enumeration."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    POLYNOMIAL = "polynomial"
    FIBONACCI = "fibonacci"


class JitterType(str, Enum):
    """Jitter type enumeration."""
    NONE = "none"
    FULL = "full"
    EQUAL = "equal"
    DECORRELATED = "decorrelated"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    backoff_multiplier: float = 2.0
    jitter_type: JitterType = JitterType.EQUAL
    jitter_max: float = 1.0
    timeout: Optional[float] = None
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()
    retry_condition: Optional[Callable[[Exception], bool]] = None
    on_retry: Optional[Callable[[int, Exception, float], None]] = None
    on_success: Optional[Callable[[int, float], None]] = None
    on_failure: Optional[Callable[[int, Exception], None]] = None


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt_number: int
    exception: Optional[Exception]
    delay: float
    timestamp: datetime
    total_elapsed: float


class RetryStatistics:
    """Statistics for retry operations."""
    
    def __init__(self):
        self.total_attempts = 0
        self.successful_attempts = 0
        self.failed_attempts = 0
        self.total_delay = 0.0
        self.max_attempts_used = 0
        self.exception_counts: Dict[str, int] = {}
        self.attempt_history: List[RetryAttempt] = []
    
    def record_attempt(self, attempt: RetryAttempt) -> None:
        """Record a retry attempt."""
        self.total_attempts += 1
        self.total_delay += attempt.delay
        self.max_attempts_used = max(self.max_attempts_used, attempt.attempt_number)
        
        if attempt.exception:
            self.failed_attempts += 1
            exception_name = type(attempt.exception).__name__
            self.exception_counts[exception_name] = self.exception_counts.get(exception_name, 0) + 1
        else:
            self.successful_attempts += 1
        
        self.attempt_history.append(attempt)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get retry statistics summary."""
        return {
            "total_attempts": self.total_attempts,
            "successful_attempts": self.successful_attempts,
            "failed_attempts": self.failed_attempts,
            "success_rate": self.successful_attempts / max(self.total_attempts, 1),
            "total_delay_seconds": self.total_delay,
            "average_delay_seconds": self.total_delay / max(self.total_attempts, 1),
            "max_attempts_used": self.max_attempts_used,
            "exception_counts": self.exception_counts,
            "attempt_count": len(self.attempt_history)
        }


class RetryManager:
    """Manager for retry operations with various strategies."""
    
    def __init__(self):
        """Initialize retry manager."""
        self.logger = StructuredLogger("retry_manager")
        self.statistics = RetryStatistics()
    
    def calculate_delay(
        self,
        attempt: int,
        config: RetryConfig,
        previous_delay: Optional[float] = None
    ) -> float:
        """Calculate delay for a retry attempt."""
        
        if config.backoff_strategy == BackoffStrategy.FIXED:
            delay = config.base_delay
        
        elif config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = config.base_delay * attempt
        
        elif config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = config.base_delay * (config.backoff_multiplier ** (attempt - 1))
        
        elif config.backoff_strategy == BackoffStrategy.POLYNOMIAL:
            delay = config.base_delay * (attempt ** config.backoff_multiplier)
        
        elif config.backoff_strategy == BackoffStrategy.FIBONACCI:
            delay = config.base_delay * self._fibonacci(attempt)
        
        else:
            delay = config.base_delay
        
        # Apply maximum delay limit
        delay = min(delay, config.max_delay)
        
        # Apply jitter
        delay = self._apply_jitter(delay, config, previous_delay)
        
        return max(0, delay)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number for backoff."""
        if n <= 1:
            return 1
        elif n == 2:
            return 1
        else:
            a, b = 1, 1
            for _ in range(3, n + 1):
                a, b = b, a + b
            return b
    
    def _apply_jitter(
        self,
        delay: float,
        config: RetryConfig,
        previous_delay: Optional[float] = None
    ) -> float:
        """Apply jitter to delay."""
        
        if config.jitter_type == JitterType.NONE:
            return delay
        
        elif config.jitter_type == JitterType.FULL:
            return random.uniform(0, delay)
        
        elif config.jitter_type == JitterType.EQUAL:
            jitter = random.uniform(0, config.jitter_max)
            return delay + jitter
        
        elif config.jitter_type == JitterType.DECORRELATED:
            if previous_delay is None:
                previous_delay = config.base_delay
            return random.uniform(config.base_delay, previous_delay * 3)
        
        return delay
    
    def should_retry(self, exception: Exception, config: RetryConfig) -> bool:
        """Determine if an exception should trigger a retry."""
        
        # Check non-retryable exceptions first
        if config.non_retryable_exceptions and isinstance(exception, config.non_retryable_exceptions):
            return False
        
        # Check custom retry condition
        if config.retry_condition:
            return config.retry_condition(exception)
        
        # Check retryable exceptions
        return isinstance(exception, config.retryable_exceptions)
    
    async def execute_with_retry(
        self,
        func: Callable,
        config: RetryConfig,
        *args,
        **kwargs
    ) -> Any:
        """Execute a function with retry logic."""
        
        start_time = time.time()
        last_exception = None
        previous_delay = None
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                # Check timeout
                if config.timeout:
                    elapsed = time.time() - start_time
                    if elapsed >= config.timeout:
                        raise TimeoutError(f"Operation timed out after {elapsed:.2f}s")
                
                # Execute the function
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Success - record statistics and call success callback
                total_elapsed = time.time() - start_time
                
                self.statistics.record_attempt(RetryAttempt(
                    attempt_number=attempt,
                    exception=None,
                    delay=0.0,
                    timestamp=datetime.utcnow(),
                    total_elapsed=total_elapsed
                ))
                
                if config.on_success:
                    config.on_success(attempt, total_elapsed)
                
                self.logger.info(
                    "Operation succeeded",
                    attempt=attempt,
                    total_elapsed=total_elapsed,
                    function=func.__name__ if hasattr(func, '__name__') else str(func)
                )
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # Check if we should retry this exception
                if not self.should_retry(e, config):
                    self.logger.error(
                        "Non-retryable exception occurred",
                        attempt=attempt,
                        exception=str(e),
                        exception_type=type(e).__name__,
                        function=func.__name__ if hasattr(func, '__name__') else str(func)
                    )
                    raise
                
                # Check if this is the last attempt
                if attempt >= config.max_attempts:
                    break
                
                # Calculate delay for next attempt
                delay = self.calculate_delay(attempt + 1, config, previous_delay)
                previous_delay = delay
                
                # Record attempt statistics
                total_elapsed = time.time() - start_time
                self.statistics.record_attempt(RetryAttempt(
                    attempt_number=attempt,
                    exception=e,
                    delay=delay,
                    timestamp=datetime.utcnow(),
                    total_elapsed=total_elapsed
                ))
                
                # Call retry callback
                if config.on_retry:
                    config.on_retry(attempt, e, delay)
                
                self.logger.warning(
                    "Operation failed, retrying",
                    attempt=attempt,
                    max_attempts=config.max_attempts,
                    delay=delay,
                    exception=str(e),
                    exception_type=type(e).__name__,
                    function=func.__name__ if hasattr(func, '__name__') else str(func)
                )
                
                # Wait before retry
                if delay > 0:
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        total_elapsed = time.time() - start_time
        
        if config.on_failure:
            config.on_failure(config.max_attempts, last_exception)
        
        self.logger.error(
            "All retry attempts exhausted",
            max_attempts=config.max_attempts,
            total_elapsed=total_elapsed,
            final_exception=str(last_exception),
            function=func.__name__ if hasattr(func, '__name__') else str(func)
        )
        
        raise RetryExhaustedError(
            f"All {config.max_attempts} retry attempts failed. Last error: {last_exception}",
            context={
                "max_attempts": config.max_attempts,
                "total_elapsed": total_elapsed,
                "final_exception": str(last_exception),
                "statistics": self.statistics.get_summary()
            }
        ) from last_exception


def retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL,
    backoff_multiplier: float = 2.0,
    jitter_type: JitterType = JitterType.EQUAL,
    jitter_max: float = 1.0,
    timeout: Optional[float] = None,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,),
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (),
    retry_condition: Optional[Callable[[Exception], bool]] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
    on_success: Optional[Callable[[int, float], None]] = None,
    on_failure: Optional[Callable[[int, Exception], None]] = None
):
    """Decorator for adding retry functionality to functions."""
    
    def decorator(func: Callable) -> Callable:
        config = RetryConfig(
            max_attempts=max_attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            backoff_strategy=backoff_strategy,
            backoff_multiplier=backoff_multiplier,
            jitter_type=jitter_type,
            jitter_max=jitter_max,
            timeout=timeout,
            retryable_exceptions=retryable_exceptions,
            non_retryable_exceptions=non_retryable_exceptions,
            retry_condition=retry_condition,
            on_retry=on_retry,
            on_success=on_success,
            on_failure=on_failure
        )
        
        retry_manager = RetryManager()
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await retry_manager.execute_with_retry(func, config, *args, **kwargs)
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(retry_manager.execute_with_retry(func, config, *args, **kwargs))
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global retry manager instance
retry_manager = RetryManager()
