# Coding Standards and Patterns

## Overview

This document establishes coding standards, patterns, and best practices for the browser automation framework to ensure consistency, maintainability, and quality across the codebase.

## General Principles

1. **Readability**: Code should be self-documenting and easy to understand
2. **Consistency**: Follow established patterns throughout the codebase
3. **Simplicity**: Prefer simple, clear solutions over complex ones
4. **Testability**: Write code that is easy to test
5. **Performance**: Consider performance implications of design decisions
6. **Security**: Follow secure coding practices

## Python Style Guide

### Code Formatting

- Follow PEP 8 style guide
- Use Black for automatic code formatting
- Line length: 88 characters (Black default)
- Use 4 spaces for indentation
- Use double quotes for strings

### Naming Conventions

```python
# Classes: PascalCase
class TaskExecutor:
    pass

# Functions and variables: snake_case
def execute_task():
    task_result = None

# Constants: UPPER_SNAKE_CASE
MAX_RETRY_COUNT = 3

# Private methods: leading underscore
def _internal_method():
    pass

# Interfaces: I prefix
class ITaskExecutor(ABC):
    pass
```

### Import Organization

```python
# Standard library imports
import asyncio
import time
from typing import Any, Dict, List, Optional

# Third-party imports
from fastapi import FastAPI
from pydantic import BaseModel

# Local imports
from core.interfaces import ITaskExecutor
from core.exceptions import TaskExecutionError
```

### Type Hints

- Use type hints for all function parameters and return values
- Use `Optional[T]` for nullable types
- Use `Union[T, U]` for multiple possible types
- Use generic types where appropriate

```python
from typing import Any, Dict, List, Optional, Union

async def execute_task(
    task_definition: TaskDefinition,
    context: Dict[str, Any],
    timeout: Optional[int] = None
) -> ExecutionResult:
    pass
```

## Architecture Patterns

### Interface-Based Design

All major components must implement well-defined interfaces:

```python
from abc import ABC, abstractmethod

class ITaskExecutor(ABC):
    @abstractmethod
    async def execute_task(self, task: TaskDefinition) -> ExecutionResult:
        pass

class ConcreteTaskExecutor(ITaskExecutor):
    async def execute_task(self, task: TaskDefinition) -> ExecutionResult:
        # Implementation here
        pass
```

### Dependency Injection

Use dependency injection for loose coupling:

```python
class WorkflowEngine:
    def __init__(
        self,
        task_executor: ITaskExecutor,
        state_manager: IStateManager,
        logger: ILogger
    ):
        self.task_executor = task_executor
        self.state_manager = state_manager
        self.logger = logger
```

### Factory Pattern

Use factories for complex object creation:

```python
class BrowserFactory:
    @staticmethod
    def create_browser(config: BrowserConfig) -> IBrowser:
        if config.browser_type == "chrome":
            return ChromeBrowser(config)
        elif config.browser_type == "firefox":
            return FirefoxBrowser(config)
        else:
            raise ValueError(f"Unsupported browser type: {config.browser_type}")
```

### Builder Pattern

Use builders for complex configuration:

```python
class WorkflowBuilder:
    def __init__(self):
        self.workflow = WorkflowDefinition()
    
    def add_task(self, task_name: str) -> "WorkflowBuilder":
        self.workflow.tasks.append(task_name)
        return self
    
    def set_timeout(self, timeout: int) -> "WorkflowBuilder":
        self.workflow.timeout = timeout
        return self
    
    def build(self) -> WorkflowDefinition:
        return self.workflow
```

## Error Handling

### Exception Hierarchy

Use a clear exception hierarchy:

```python
class FrameworkException(Exception):
    """Base exception for all framework errors."""
    pass

class TaskExecutionError(FrameworkException):
    """Raised when task execution fails."""
    pass

class BrowserError(FrameworkException):
    """Raised when browser operations fail."""
    pass
```

### Error Context

Provide rich error context:

```python
try:
    result = await execute_task(task)
except Exception as e:
    raise TaskExecutionError(
        message=f"Task {task.name} failed",
        error_code="TASK_EXECUTION_FAILED",
        context={
            "task_name": task.name,
            "execution_id": context.execution_id,
            "original_error": str(e)
        }
    ) from e
```

### Retry Logic

Implement consistent retry patterns:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def execute_with_retry(operation):
    return await operation()
```

## Logging Standards

### Structured Logging

Use structured logging with correlation IDs:

```python
logger.info(
    "Task execution started",
    correlation_id=context.correlation_id,
    task_name=task.name,
    execution_id=context.execution_id
)
```

### Log Levels

- **DEBUG**: Detailed diagnostic information
- **INFO**: General operational information
- **WARNING**: Something unexpected happened but system continues
- **ERROR**: Serious problem that prevented operation completion
- **CRITICAL**: System failure requiring immediate attention

### Sensitive Data

Never log sensitive information:

```python
# Bad
logger.info(f"Login with password: {password}")

# Good
logger.info("Login attempt", user_id=user_id, masked_password="***")
```

## Testing Standards

### Test Organization

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
├── fixtures/      # Test fixtures
└── conftest.py    # Pytest configuration
```

### Test Naming

```python
class TestTaskExecutor:
    async def test_execute_task_success(self):
        """Test successful task execution."""
        pass
    
    async def test_execute_task_with_timeout_raises_timeout_error(self):
        """Test that task execution raises TimeoutError when timeout exceeded."""
        pass
```

### Mocking

Use dependency injection to make testing easier:

```python
@pytest.fixture
def mock_browser_manager():
    return Mock(spec=IBrowserManager)

async def test_task_execution(mock_browser_manager):
    executor = TaskExecutor(browser_manager=mock_browser_manager)
    # Test implementation
```

## Configuration Management

### Environment Variables

Use environment variables for configuration:

```python
import os
from pydantic import BaseSettings

class Settings(BaseSettings):
    database_url: str
    api_key: str
    debug: bool = False
    
    class Config:
        env_file = ".env"
```

### Configuration Validation

Validate configuration at startup:

```python
def validate_config(config: Settings) -> None:
    if not config.api_key:
        raise ConfigurationError("API key is required")
    
    if config.timeout <= 0:
        raise ConfigurationError("Timeout must be positive")
```

## Documentation Standards

### Docstrings

Use Google-style docstrings:

```python
async def execute_task(
    task_definition: TaskDefinition,
    context: ExecutionContext
) -> ExecutionResult:
    """Execute a single task with the given context.
    
    Args:
        task_definition: The task to execute
        context: Execution context with variables and metadata
        
    Returns:
        ExecutionResult containing the task outcome
        
    Raises:
        TaskExecutionError: If task execution fails
        TimeoutError: If task execution times out
    """
    pass
```

### Code Comments

- Explain why, not what
- Use comments sparingly for complex logic
- Keep comments up to date with code changes

```python
# Use exponential backoff to avoid overwhelming the service
# during temporary outages
await asyncio.sleep(2 ** attempt)
```

## Performance Guidelines

### Async/Await

Use async/await for I/O operations:

```python
# Good
async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Bad - blocking
def fetch_data():
    response = requests.get(url)
    return response.json()
```

### Resource Management

Use context managers for resource cleanup:

```python
async def execute_task():
    async with browser_manager.get_browser() as browser:
        # Use browser
        pass
    # Browser automatically closed
```

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache

@lru_cache(maxsize=128)
def get_task_template(task_name: str) -> str:
    # Expensive template loading
    pass
```

## Security Guidelines

### Input Validation

Validate all inputs:

```python
from pydantic import BaseModel, validator

class TaskRequest(BaseModel):
    task_name: str
    parameters: Dict[str, Any]
    
    @validator('task_name')
    def validate_task_name(cls, v):
        if not v.isalnum():
            raise ValueError('Task name must be alphanumeric')
        return v
```

### Secrets Management

Never hardcode secrets:

```python
# Bad
API_KEY = "sk-1234567890abcdef"

# Good
API_KEY = os.environ.get("API_KEY")
if not API_KEY:
    raise ConfigurationError("API_KEY environment variable required")
```

## Code Review Guidelines

### Review Checklist

- [ ] Code follows style guidelines
- [ ] All functions have type hints
- [ ] Error handling is appropriate
- [ ] Tests are included
- [ ] Documentation is updated
- [ ] No hardcoded values
- [ ] Security considerations addressed
- [ ] Performance implications considered

### Review Process

1. Author creates pull request with clear description
2. Automated checks run (linting, tests, security scans)
3. Peer review by at least one team member
4. Address feedback and re-review if needed
5. Merge after approval and passing checks
