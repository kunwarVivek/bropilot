# API Reference Guide

This document provides detailed API reference for the Browser Use Automation platform.

## 🏗️ Core APIs

### Task Runner API

#### `run_task(task: str, llm: ILLMProvider, save_path: str) -> str`

Execute a browser automation task using the unified execution layer.

**Parameters:**
- `task` (str): Natural language description of the task to execute
- `llm` (ILLMProvider): LLM provider instance for task processing
- `save_path` (str): Path to save execution logs and artifacts

**Returns:**
- `str`: Task execution result

**Example:**
```python
from utils.task_runner import run_task
from src.execution.llm_provider import create_llm_provider

llm = await create_llm_provider("openai", "gpt-4")
result = await run_task(
    "Navigate to google.com and search for 'automation'",
    llm,
    "logs/search_task"
)
```

**Raises:**
- `TaskExecutionError`: If task execution fails
- `LLMError`: If LLM provider encounters an error
- `BrowserError`: If browser automation fails

---

### LLM Provider API

#### `create_llm_provider(**kwargs) -> TaskLLMProvider`

Factory function to create and initialize an LLM provider.

**Parameters:**
- `primary_provider` (str): Primary LLM provider name ("openai", "anthropic", "gemini", "local")
- `primary_model` (str): Primary model name
- `primary_config` (Dict[str, Any]): Primary provider configuration
- `fallback_provider` (str, optional): Fallback provider name
- `fallback_model` (str, optional): Fallback model name
- `fallback_config` (Dict[str, Any], optional): Fallback provider configuration

**Example:**
```python
# Single provider
llm = await create_llm_provider(
    primary_provider="openai",
    primary_model="gpt-4",
    primary_config={"api_key": "your-key"}
)

# With fallback
llm = await create_llm_provider(
    primary_provider="openai",
    primary_model="gpt-4",
    primary_config={"api_key": "openai-key"},
    fallback_provider="anthropic",
    fallback_model="claude-3-sonnet",
    fallback_config={"api_key": "anthropic-key"}
)
```

#### `TaskLLMProvider.invoke(prompt: str, **kwargs) -> str`

Invoke the LLM with a prompt and return the response.

**Parameters:**
- `prompt` (str): The prompt to send to the LLM
- `temperature` (float, optional): Sampling temperature (0.0-1.0)
- `max_tokens` (int, optional): Maximum tokens to generate
- `priority` (str, optional): Request priority ("low", "normal", "high", "critical")
- `user_id` (str, optional): User ID for cost tracking
- `project_id` (str, optional): Project ID for cost tracking

**Example:**
```python
response = await llm.invoke(
    "Explain browser automation",
    temperature=0.7,
    max_tokens=500,
    priority="normal",
    user_id="user123"
)
```

---

### Browser Manager API

#### `EnhancedBrowserManager`

Advanced browser lifecycle management with resource monitoring.

**Constructor Parameters:**
- `memory_threshold` (float): Memory usage threshold for cleanup (0.0-1.0)
- `cleanup_interval` (int): Cleanup interval in seconds
- `max_session_duration` (int): Maximum session duration in seconds
- `enable_pooling` (bool): Enable browser pooling

**Example:**
```python
from src.execution.browser_manager import EnhancedBrowserManager

browser_manager = EnhancedBrowserManager(
    memory_threshold=0.8,
    cleanup_interval=300,
    max_session_duration=3600,
    enable_pooling=True
)

await browser_manager.initialize()
```

#### `create_browser(config: Dict[str, Any], correlation_id: str) -> str`

Create a new browser session.

**Parameters:**
- `config` (Dict[str, Any]): Browser configuration
- `correlation_id` (str): Correlation ID for tracking

**Returns:**
- `str`: Browser session ID

**Example:**
```python
session_id = await browser_manager.create_browser(
    config={
        "headless": False,
        "viewport": {"width": 1920, "height": 1080},
        "timeout": 30
    },
    correlation_id="task-123"
)
```

---

### Cost Management API

#### `CostManager`

Comprehensive cost tracking and budget enforcement.

**Methods:**

##### `set_budget(budget_id: str, budget: CostBudget) -> None`

Set a cost budget for monitoring and enforcement.

**Example:**
```python
from src.infrastructure.cost_management import CostManager, CostBudget, CostPeriod

cost_manager = CostManager()
cost_manager.set_budget("daily", CostBudget(
    period=CostPeriod.DAILY,
    limit=100.0,
    warning_threshold=0.8,
    auto_suspend=True
))
```

##### `record_usage(**kwargs) -> UsageRecord`

Record LLM usage for cost tracking.

**Parameters:**
- `provider` (str): LLM provider name
- `model` (str): Model name
- `operation` (str): Operation type
- `prompt_tokens` (int): Number of prompt tokens
- `completion_tokens` (int): Number of completion tokens
- `correlation_id` (str, optional): Request correlation ID
- `user_id` (str, optional): User ID
- `project_id` (str, optional): Project ID

##### `get_usage_summary(period: str) -> Dict[str, Any]`

Get usage summary for a specific period.

**Example:**
```python
daily_usage = cost_manager.get_usage_summary("daily")
monthly_usage = cost_manager.get_usage_summary("monthly")
```

---

### Error Recovery API

#### `EnhancedErrorRecovery`

Intelligent error handling and recovery system.

##### `handle_error(error: Exception, component: str, operation: str, **kwargs) -> Dict[str, Any]`

Handle an error with enhanced recovery logic.

**Parameters:**
- `error` (Exception): The exception that occurred
- `component` (str): Component where error occurred
- `operation` (str): Operation that failed
- `context` (Dict[str, Any], optional): Additional context
- `correlation_id` (str, optional): Request correlation ID

**Example:**
```python
from src.execution.enhanced_error_recovery import EnhancedErrorRecovery

error_recovery = EnhancedErrorRecovery()
result = await error_recovery.handle_error(
    error=exception,
    component="browser_manager",
    operation="create_session",
    context={"session_config": config},
    correlation_id="task-123"
)
```

---

### Monitoring API

#### `SystemMonitor`

Comprehensive system monitoring and alerting.

**Constructor Parameters:**
- `monitoring_interval` (int): Monitoring interval in seconds
- `alert_thresholds` (Dict[str, Any]): Custom alert thresholds

**Example:**
```python
from src.monitoring.system_monitor import SystemMonitor

monitor = SystemMonitor(
    monitoring_interval=30,
    alert_thresholds={
        "memory_usage": 0.85,
        "error_rate": 0.1,
        "response_time": 10.0
    }
)

await monitor.start_monitoring()
```

##### `collect_metrics() -> SystemMetrics`

Collect comprehensive system metrics.

##### `add_alert_callback(callback: Callable) -> None`

Add a callback function for system alerts.

**Example:**
```python
def handle_alert(alert_type: str, alert_data: Dict[str, Any]):
    print(f"ALERT: {alert_type} - {alert_data['message']}")

monitor.add_alert_callback(handle_alert)
```

---

## 🔧 Configuration APIs

### Environment Configuration

The platform uses environment variables for configuration:

```python
import os
from dotenv import load_dotenv

load_dotenv()

# LLM Provider API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Application Settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Browser Settings
HEADLESS = os.getenv("HEADLESS", "false").lower() == "true"
BROWSER_TIMEOUT = int(os.getenv("BROWSER_TIMEOUT", "30"))

# Cost Management
ENABLE_COST_TRACKING = os.getenv("ENABLE_COST_TRACKING", "true").lower() == "true"
DAILY_BUDGET_LIMIT = float(os.getenv("DAILY_BUDGET_LIMIT", "100.0"))
MONTHLY_BUDGET_LIMIT = float(os.getenv("MONTHLY_BUDGET_LIMIT", "1000.0"))
```

---

## 📊 Data Models

### Core Data Structures

#### `TaskDefinition`

```python
@dataclass
class TaskDefinition:
    name: str
    description: str
    prompt_template: str
    timeout: int
    retry_count: int
    metadata: Dict[str, Any]
```

#### `LLMRequest`

```python
@dataclass
class LLMRequest:
    prompt: str
    temperature: float = 0.1
    max_tokens: int = 2000
    messages: List[Dict[str, Any]] = field(default_factory=list)
    functions: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

#### `LLMResponse`

```python
@dataclass
class LLMResponse:
    content: str
    request_id: str
    provider: str
    model: str
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
```

#### `UsageRecord`

```python
@dataclass
class UsageRecord:
    timestamp: datetime
    provider: str
    model: str
    operation: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    actual_cost: Optional[float] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
```

---

## 🚨 Exception Handling

### Custom Exceptions

#### `TaskExecutionError`
Raised when task execution fails.

#### `LLMError`
Raised when LLM provider encounters an error.

#### `BrowserError`
Raised when browser automation fails.

#### `ConfigurationError`
Raised when configuration is invalid.

#### `ResourceError`
Raised when system resources are exhausted.

#### `RetryExhaustedError`
Raised when retry attempts are exhausted.

### Error Handling Patterns

```python
from core.exceptions import TaskExecutionError, LLMError, BrowserError

try:
    result = await run_task(task, llm, save_path)
except TaskExecutionError as e:
    logger.error(f"Task execution failed: {e}")
    # Handle task-specific error
except LLMError as e:
    logger.error(f"LLM error: {e}")
    # Handle LLM-specific error
except BrowserError as e:
    logger.error(f"Browser error: {e}")
    # Handle browser-specific error
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle unexpected errors
```

---

## 🔍 Debugging and Logging

### Structured Logging

```python
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id

logger = StructuredLogger("component_name")

# Basic logging
logger.info("Operation completed", extra_data={"key": "value"})

# With correlation ID
@with_correlation_id
async def my_function(correlation_id: str = None):
    logger.info("Function called", correlation_id=correlation_id)
```

### Performance Monitoring

```python
import time
from src.monitoring.system_monitor import SystemMonitor

# Monitor function performance
start_time = time.time()
result = await some_operation()
execution_time = time.time() - start_time

logger.info("Operation performance", execution_time=execution_time)
```

This API reference provides comprehensive documentation for all major components and interfaces in the Browser Use Automation platform. For implementation examples and advanced usage patterns, refer to the User Guide and Developer Guide.
