"""
Circuit breaker pattern for external services.

This module implements the circuit breaker pattern to prevent cascading failures
and provide fast failure detection for external service dependencies.
"""

import asyncio
import time
from typing import Any, Callable, Optional, Dict, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import functools

from core.exceptions import CircuitBreakerError, ExternalServiceError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class CircuitState(str, Enum):
    """Circuit breaker state enumeration."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Number of failures to open circuit
    recovery_timeout: float = 60.0  # Seconds to wait before trying half-open
    success_threshold: int = 3  # Successful calls needed to close circuit from half-open
    timeout: float = 30.0  # Request timeout in seconds
    expected_exception: type = Exception  # Exception type that counts as failure
    monitor_window: float = 300.0  # Time window for failure monitoring (seconds)
    half_open_max_calls: int = 5  # Max calls allowed in half-open state


@dataclass
class CallResult:
    """Result of a circuit breaker call."""
    success: bool
    timestamp: datetime
    duration: float
    exception: Optional[Exception] = None


class CircuitBreakerStatistics:
    """Statistics for circuit breaker operations."""
    
    def __init__(self, monitor_window: float = 300.0):
        self.monitor_window = monitor_window
        self.call_history: List[CallResult] = []
        self.state_changes: List[Dict[str, Any]] = []
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0
        self.rejected_calls = 0
    
    def record_call(self, result: CallResult) -> None:
        """Record a call result."""
        self.call_history.append(result)
        self.total_calls += 1
        
        if result.success:
            self.successful_calls += 1
        else:
            self.failed_calls += 1
        
        # Clean old entries outside monitor window
        self._cleanup_old_entries()
    
    def record_rejection(self) -> None:
        """Record a rejected call."""
        self.rejected_calls += 1
    
    def record_state_change(self, from_state: CircuitState, to_state: CircuitState, reason: str) -> None:
        """Record a state change."""
        self.state_changes.append({
            "from_state": from_state.value,
            "to_state": to_state.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def get_recent_failures(self) -> int:
        """Get number of recent failures within monitor window."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.monitor_window)
        return sum(1 for call in self.call_history 
                  if not call.success and call.timestamp >= cutoff_time)
    
    def get_recent_successes(self) -> int:
        """Get number of recent successes."""
        return sum(1 for call in self.call_history if call.success)
    
    def get_failure_rate(self) -> float:
        """Get current failure rate within monitor window."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.monitor_window)
        recent_calls = [call for call in self.call_history if call.timestamp >= cutoff_time]
        
        if not recent_calls:
            return 0.0
        
        failures = sum(1 for call in recent_calls if not call.success)
        return failures / len(recent_calls)
    
    def _cleanup_old_entries(self) -> None:
        """Remove entries outside the monitor window."""
        cutoff_time = datetime.utcnow() - timedelta(seconds=self.monitor_window)
        self.call_history = [call for call in self.call_history if call.timestamp >= cutoff_time]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get statistics summary."""
        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "rejected_calls": self.rejected_calls,
            "recent_failures": self.get_recent_failures(),
            "recent_successes": self.get_recent_successes(),
            "failure_rate": self.get_failure_rate(),
            "state_changes": len(self.state_changes),
            "last_state_change": self.state_changes[-1] if self.state_changes else None
        }


class CircuitBreaker:
    """Circuit breaker implementation for external service calls."""
    
    def __init__(self, name: str, config: CircuitBreakerConfig):
        """Initialize circuit breaker.
        
        Args:
            name: Name of the circuit breaker
            config: Configuration for the circuit breaker
        """
        self.name = name
        self.config = config
        self.logger = StructuredLogger(f"circuit_breaker.{name}")
        
        # State management
        self.state = CircuitState.CLOSED
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
        self.consecutive_successes = 0
        
        # Statistics
        self.statistics = CircuitBreakerStatistics(config.monitor_window)
        
        # Thread safety
        self.lock = asyncio.Lock()
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker."""
        
        async with self.lock:
            # Check if call should be rejected
            if self._should_reject_call():
                self.statistics.record_rejection()
                self.logger.warning(
                    "Call rejected by circuit breaker",
                    circuit_name=self.name,
                    state=self.state.value,
                    recent_failures=self.statistics.get_recent_failures()
                )
                raise CircuitBreakerError(
                    f"Circuit breaker '{self.name}' is {self.state.value}",
                    context={
                        "circuit_name": self.name,
                        "state": self.state.value,
                        "recent_failures": self.statistics.get_recent_failures(),
                        "failure_rate": self.statistics.get_failure_rate()
                    }
                )
            
            # Increment half-open call counter
            if self.state == CircuitState.HALF_OPEN:
                self.half_open_calls += 1
        
        # Execute the function
        start_time = time.time()
        success = False
        exception = None
        
        try:
            # Apply timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs), 
                    timeout=self.config.timeout
                )
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(func, *args, **kwargs),
                    timeout=self.config.timeout
                )
            
            success = True
            
            # Record successful call
            duration = time.time() - start_time
            call_result = CallResult(
                success=True,
                timestamp=datetime.utcnow(),
                duration=duration
            )
            
            async with self.lock:
                self.statistics.record_call(call_result)
                await self._handle_success()
            
            self.logger.debug(
                "Circuit breaker call succeeded",
                circuit_name=self.name,
                duration=duration,
                state=self.state.value
            )
            
            return result
            
        except Exception as e:
            exception = e
            duration = time.time() - start_time
            
            # Determine if this exception should count as a failure
            is_failure = isinstance(e, self.config.expected_exception)
            
            call_result = CallResult(
                success=not is_failure,
                timestamp=datetime.utcnow(),
                duration=duration,
                exception=e
            )
            
            async with self.lock:
                self.statistics.record_call(call_result)
                if is_failure:
                    await self._handle_failure()
            
            self.logger.warning(
                "Circuit breaker call failed",
                circuit_name=self.name,
                duration=duration,
                state=self.state.value,
                exception=str(e),
                is_failure=is_failure
            )
            
            raise
    
    def _should_reject_call(self) -> bool:
        """Determine if a call should be rejected."""
        
        if self.state == CircuitState.CLOSED:
            return False
        
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.last_failure_time:
                time_since_failure = datetime.utcnow() - self.last_failure_time
                if time_since_failure.total_seconds() >= self.config.recovery_timeout:
                    self._transition_to_half_open()
                    return False
            return True
        
        elif self.state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            return self.half_open_calls >= self.config.half_open_max_calls
        
        return False
    
    async def _handle_success(self) -> None:
        """Handle a successful call."""
        
        if self.state == CircuitState.HALF_OPEN:
            self.consecutive_successes += 1
            
            if self.consecutive_successes >= self.config.success_threshold:
                await self._transition_to_closed()
        
        elif self.state == CircuitState.CLOSED:
            # Reset failure tracking on success
            self.consecutive_successes += 1
    
    async def _handle_failure(self) -> None:
        """Handle a failed call."""
        
        self.last_failure_time = datetime.utcnow()
        self.consecutive_successes = 0
        
        if self.state == CircuitState.CLOSED:
            recent_failures = self.statistics.get_recent_failures()
            if recent_failures >= self.config.failure_threshold:
                await self._transition_to_open()
        
        elif self.state == CircuitState.HALF_OPEN:
            await self._transition_to_open()
    
    async def _transition_to_open(self) -> None:
        """Transition circuit breaker to open state."""
        
        old_state = self.state
        self.state = CircuitState.OPEN
        self.half_open_calls = 0
        self.consecutive_successes = 0
        
        self.statistics.record_state_change(
            old_state, 
            CircuitState.OPEN, 
            f"Failure threshold exceeded: {self.statistics.get_recent_failures()}"
        )
        
        self.logger.warning(
            "Circuit breaker opened",
            circuit_name=self.name,
            recent_failures=self.statistics.get_recent_failures(),
            failure_rate=self.statistics.get_failure_rate()
        )
    
    def _transition_to_half_open(self) -> None:
        """Transition circuit breaker to half-open state."""
        
        old_state = self.state
        self.state = CircuitState.HALF_OPEN
        self.half_open_calls = 0
        self.consecutive_successes = 0
        
        self.statistics.record_state_change(
            old_state, 
            CircuitState.HALF_OPEN, 
            f"Recovery timeout elapsed: {self.config.recovery_timeout}s"
        )
        
        self.logger.info(
            "Circuit breaker half-opened",
            circuit_name=self.name,
            recovery_timeout=self.config.recovery_timeout
        )
    
    async def _transition_to_closed(self) -> None:
        """Transition circuit breaker to closed state."""
        
        old_state = self.state
        self.state = CircuitState.CLOSED
        self.half_open_calls = 0
        self.consecutive_successes = 0
        
        self.statistics.record_state_change(
            old_state, 
            CircuitState.CLOSED, 
            f"Success threshold reached: {self.config.success_threshold}"
        )
        
        self.logger.info(
            "Circuit breaker closed",
            circuit_name=self.name,
            consecutive_successes=self.consecutive_successes
        )
    
    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        return self.state
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
                "timeout": self.config.timeout,
                "monitor_window": self.config.monitor_window
            },
            "statistics": self.statistics.get_summary(),
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
            "consecutive_successes": self.consecutive_successes,
            "half_open_calls": self.half_open_calls
        }
    
    async def reset(self) -> None:
        """Reset circuit breaker to closed state."""
        
        async with self.lock:
            old_state = self.state
            self.state = CircuitState.CLOSED
            self.last_failure_time = None
            self.half_open_calls = 0
            self.consecutive_successes = 0
            
            self.statistics.record_state_change(
                old_state, 
                CircuitState.CLOSED, 
                "Manual reset"
            )
            
            self.logger.info(
                "Circuit breaker manually reset",
                circuit_name=self.name
            )


class CircuitBreakerManager:
    """Manager for multiple circuit breakers."""
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.logger = StructuredLogger("circuit_breaker_manager")
    
    def get_circuit_breaker(
        self, 
        name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        
        if name not in self.circuit_breakers:
            if config is None:
                config = CircuitBreakerConfig()
            
            self.circuit_breakers[name] = CircuitBreaker(name, config)
            
            self.logger.info(
                "Circuit breaker created",
                circuit_name=name,
                config=config.__dict__
            )
        
        return self.circuit_breakers[name]
    
    def get_all_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all circuit breakers."""
        return {
            name: cb.get_statistics() 
            for name, cb in self.circuit_breakers.items()
        }
    
    async def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for circuit_breaker in self.circuit_breakers.values():
            await circuit_breaker.reset()
        
        self.logger.info("All circuit breakers reset")


def circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    success_threshold: int = 3,
    timeout: float = 30.0,
    expected_exception: type = Exception,
    monitor_window: float = 300.0,
    half_open_max_calls: int = 5
):
    """Decorator for adding circuit breaker functionality to functions."""
    
    def decorator(func: Callable) -> Callable:
        config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
            success_threshold=success_threshold,
            timeout=timeout,
            expected_exception=expected_exception,
            monitor_window=monitor_window,
            half_open_max_calls=half_open_max_calls
        )
        
        cb = circuit_breaker_manager.get_circuit_breaker(name, config)
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)
        
        return wrapper
    
    return decorator


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()
