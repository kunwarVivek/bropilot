"""
Core interfaces and abstract base classes for the browser automation framework.

This module defines the contracts that all components must follow to ensure
proper separation of concerns and maintainability.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class TaskStatus(Enum):
    """Enumeration of possible task execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowStatus(Enum):
    """Enumeration of possible workflow execution states."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ExecutionResult:
    """Standard result structure for task and workflow execution."""
    status: TaskStatus
    result: Optional[Any] = None
    error_message: Optional[str] = None
    execution_time: Optional[float] = None
    logs: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class TaskDefinition:
    """Definition of a task that can be executed."""
    name: str
    description: str
    prompt_template: str
    timeout: int = 300  # 5 minutes default
    retry_count: int = 3
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class WorkflowDefinition:
    """Definition of a workflow containing multiple tasks."""
    name: str
    description: str
    tasks: List[str]  # Task names in execution order
    metadata: Optional[Dict[str, Any]] = None


class IBrowserManager(ABC):
    """Interface for browser management operations."""
    
    @abstractmethod
    async def create_browser(self, config: Dict[str, Any]) -> Any:
        """Create and configure a new browser instance."""
        pass
    
    @abstractmethod
    async def close_browser(self, browser: Any) -> None:
        """Close a browser instance safely."""
        pass
    
    @abstractmethod
    async def get_browser_status(self, browser: Any) -> Dict[str, Any]:
        """Get the current status of a browser instance."""
        pass


class ILLMProvider(ABC):
    """Interface for Language Model providers."""
    
    @abstractmethod
    async def invoke(self, prompt: str, **kwargs) -> str:
        """Invoke the LLM with a prompt and return the response."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is available and healthy."""
        pass
    
    @abstractmethod
    def get_token_count(self, text: str) -> int:
        """Get the token count for a given text."""
        pass


class ITaskExecutor(ABC):
    """Interface for task execution."""
    
    @abstractmethod
    async def execute_task(
        self, 
        task_definition: TaskDefinition, 
        context: Dict[str, Any]
    ) -> ExecutionResult:
        """Execute a single task with the given context."""
        pass
    
    @abstractmethod
    async def pause_task(self, task_id: str) -> bool:
        """Pause a running task."""
        pass
    
    @abstractmethod
    async def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or paused task."""
        pass


class IWorkflowEngine(ABC):
    """Interface for workflow execution and management."""
    
    @abstractmethod
    async def execute_workflow(
        self, 
        workflow_definition: WorkflowDefinition, 
        context: Dict[str, Any]
    ) -> Dict[str, ExecutionResult]:
        """Execute a complete workflow."""
        pass
    
    @abstractmethod
    async def pause_workflow(self, workflow_id: str) -> bool:
        """Pause a running workflow."""
        pass
    
    @abstractmethod
    async def resume_workflow(self, workflow_id: str) -> bool:
        """Resume a paused workflow."""
        pass
    
    @abstractmethod
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        pass
    
    @abstractmethod
    async def get_workflow_status(self, workflow_id: str) -> WorkflowStatus:
        """Get the current status of a workflow."""
        pass


class IStateManager(ABC):
    """Interface for execution state management."""
    
    @abstractmethod
    async def save_state(self, execution_id: str, state: Dict[str, Any]) -> bool:
        """Save execution state for later restoration."""
        pass
    
    @abstractmethod
    async def load_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Load previously saved execution state."""
        pass
    
    @abstractmethod
    async def delete_state(self, execution_id: str) -> bool:
        """Delete saved execution state."""
        pass
    
    @abstractmethod
    async def create_checkpoint(self, execution_id: str, checkpoint_name: str) -> bool:
        """Create a named checkpoint for the execution state."""
        pass


class IConfigurationManager(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        pass
    
    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        pass
    
    @abstractmethod
    def get_environment_config(self, environment: str) -> Dict[str, Any]:
        """Get configuration for a specific environment."""
        pass
    
    @abstractmethod
    def reload_config(self) -> None:
        """Reload configuration from source."""
        pass


class ILogger(ABC):
    """Interface for structured logging."""
    
    @abstractmethod
    def log(
        self, 
        level: str, 
        message: str, 
        correlation_id: Optional[str] = None,
        **kwargs
    ) -> None:
        """Log a message with optional correlation ID and metadata."""
        pass
    
    @abstractmethod
    def info(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log an info message."""
        pass
    
    @abstractmethod
    def warning(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log a warning message."""
        pass
    
    @abstractmethod
    def error(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log an error message."""
        pass
    
    @abstractmethod
    def debug(self, message: str, correlation_id: Optional[str] = None, **kwargs) -> None:
        """Log a debug message."""
        pass


class IMetricsCollector(ABC):
    """Interface for metrics collection and monitoring."""
    
    @abstractmethod
    def increment_counter(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        pass
    
    @abstractmethod
    def record_gauge(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a gauge metric."""
        pass
    
    @abstractmethod
    def record_histogram(self, metric_name: str, value: float, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a histogram metric."""
        pass
    
    @abstractmethod
    def start_timer(self, metric_name: str, tags: Optional[Dict[str, str]] = None) -> Any:
        """Start a timer for measuring execution time."""
        pass


class IHealthMonitor(ABC):
    """Interface for health monitoring."""
    
    @abstractmethod
    async def check_health(self) -> Dict[str, Any]:
        """Perform a comprehensive health check."""
        pass
    
    @abstractmethod
    async def check_component_health(self, component_name: str) -> bool:
        """Check the health of a specific component."""
        pass
    
    @abstractmethod
    def register_health_check(self, component_name: str, check_function: callable) -> None:
        """Register a health check function for a component."""
        pass
