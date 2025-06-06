"""
Custom exceptions for the browser automation framework.

This module defines all custom exceptions used throughout the framework
to provide clear error handling and debugging information.
"""

from typing import Optional, Dict, Any


class FrameworkException(Exception):
    """Base exception for all framework-related errors."""
    
    def __init__(
        self, 
        message: str, 
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.context = context or {}
    
    def __str__(self) -> str:
        if self.error_code:
            return f"[{self.error_code}] {self.message}"
        return self.message


class ConfigurationError(FrameworkException):
    """Raised when there's an issue with configuration."""
    pass


class BrowserError(FrameworkException):
    """Raised when there's an issue with browser operations."""
    pass


class TaskExecutionError(FrameworkException):
    """Raised when a task fails to execute properly."""
    pass


class WorkflowExecutionError(FrameworkException):
    """Raised when a workflow fails to execute properly."""
    pass


class LLMProviderError(FrameworkException):
    """Raised when there's an issue with the LLM provider."""
    pass


# Alias for backward compatibility
LLMError = LLMProviderError


class StateManagementError(FrameworkException):
    """Raised when there's an issue with state management operations."""
    pass


class ValidationError(FrameworkException):
    """Raised when input validation fails."""
    pass


class TimeoutError(FrameworkException):
    """Raised when an operation times out."""
    pass


class RetryExhaustedError(FrameworkException):
    """Raised when all retry attempts have been exhausted."""
    pass


class AuthenticationError(FrameworkException):
    """Raised when authentication fails."""
    pass


class AuthorizationError(FrameworkException):
    """Raised when authorization fails."""
    pass


class ResourceNotFoundError(FrameworkException):
    """Raised when a requested resource is not found."""
    pass


class ResourceConflictError(FrameworkException):
    """Raised when there's a conflict with resource state."""
    pass


class ExternalServiceError(FrameworkException):
    """Raised when an external service is unavailable or returns an error."""
    pass


class DataIntegrityError(FrameworkException):
    """Raised when data integrity checks fail."""
    pass


class ConcurrencyError(FrameworkException):
    """Raised when there's a concurrency-related issue."""
    pass


class CircuitBreakerError(FrameworkException):
    """Raised when circuit breaker is open and rejecting calls."""
    pass


class TransactionError(FrameworkException):
    """Raised when there's an issue with transaction management."""
    pass


class OperationCancelledError(FrameworkException):
    """Raised when an operation is cancelled."""
    pass


class RecoveryError(FrameworkException):
    """Raised when error recovery operations fail."""
    pass


class ExecutionError(FrameworkException):
    """Raised when execution operations fail."""
    pass


class ResourceError(FrameworkException):
    """Raised when resource operations fail."""
    pass


class ResourceError(FrameworkException):
    """Raised when there's an issue with resource management."""
    pass
