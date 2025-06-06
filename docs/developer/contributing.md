# Contributing Guide

Welcome to the Browser Automation Framework! This guide will help you contribute effectively to the project.

## 🎯 Getting Started

### Prerequisites

- **Python 3.11+** with pip and virtualenv
- **Docker & Docker Compose** for testing
- **Git** with SSH keys configured
- **Node.js 18+** for frontend development (if applicable)
- **Basic knowledge** of async Python, Playwright, and FastAPI

### Development Setup

```bash
# Fork and clone the repository
git clone git@github.com:your-username/browser-automation-framework.git
cd browser-automation-framework

# Set up development environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt
pip install -e .

# Set up pre-commit hooks
pre-commit install

# Copy environment template
cp .env.example .env
# Edit .env with your development configuration
```

## 🏗️ Project Structure

Understanding the codebase architecture:

```
browser-automation-framework/
├── core/                    # Core interfaces and base classes
├── src/                     # Main application code
│   ├── api/                # FastAPI application and routes
│   ├── intelligence/       # AI and LLM integration
│   ├── orchestration/      # Workflow orchestration
│   ├── infrastructure/     # Infrastructure components
│   └── llm/               # LLM providers and processing
├── tests/                  # Test suite
├── docs/                   # Documentation
├── examples/              # Example workflows and usage
└── scripts/               # Development and deployment scripts
```

## 🔄 Development Workflow

### 1. Issue Selection

- Browse [open issues](https://github.com/your-org/browser-automation-framework/issues)
- Look for `good first issue` or `help wanted` labels
- Comment on the issue to indicate you're working on it
- For new features, create an issue first to discuss the approach

### 2. Branch Creation

```bash
# Create feature branch from main
git checkout main
git pull origin main
git checkout -b feature/your-feature-name

# For bug fixes
git checkout -b fix/issue-description

# For documentation
git checkout -b docs/documentation-update
```

### 3. Development Process

```bash
# Make your changes
# Write tests for new functionality
# Update documentation as needed

# Run tests frequently
pytest tests/ -v

# Check code quality
make quality-check

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v
```

### 4. Commit Guidelines

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
# Feature commits
git commit -m "feat: add intelligent error recovery system"

# Bug fix commits  
git commit -m "fix: resolve browser pool memory leak"

# Documentation commits
git commit -m "docs: update API reference for new endpoints"

# Test commits
git commit -m "test: add integration tests for LLM providers"

# Refactor commits
git commit -m "refactor: improve orchestrator performance"
```

### 5. Pull Request Process

```bash
# Push your branch
git push origin feature/your-feature-name

# Create pull request on GitHub
# Fill out the PR template completely
# Link related issues
# Add appropriate labels
```

## 🧪 Testing Guidelines

### Test Structure

```python
# tests/unit/test_orchestrator.py
import pytest
from unittest.mock import AsyncMock, patch
from src.intelligence.advanced_orchestrator import AdvancedOrchestrator

class TestAdvancedOrchestrator:
    """Test suite for AdvancedOrchestrator."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator instance for testing."""
        return AdvancedOrchestrator()
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self, orchestrator):
        """Test successful workflow execution."""
        # Arrange
        workflow = {
            "type": "test_workflow",
            "tasks": [{"id": "task1", "type": "navigate"}]
        }
        
        # Act
        result = await orchestrator.execute_workflow(workflow)
        
        # Assert
        assert result["success"] is True
        assert "execution_id" in result
    
    @pytest.mark.asyncio
    async def test_workflow_execution_failure(self, orchestrator):
        """Test workflow execution with errors."""
        # Test error handling scenarios
        pass
```

### Test Categories

1. **Unit Tests** (`tests/unit/`)
   - Test individual functions and classes
   - Mock external dependencies
   - Fast execution (<1s per test)

2. **Integration Tests** (`tests/integration/`)
   - Test component interactions
   - Use real databases/services in containers
   - Medium execution time (1-10s per test)

3. **End-to-End Tests** (`tests/e2e/`)
   - Test complete workflows
   - Use real browsers and external services
   - Slower execution (10s+ per test)

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/ -v
pytest tests/integration/ -v --docker
pytest tests/e2e/ -v --slow

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run tests in parallel
pytest -n auto

# Run specific test file
pytest tests/unit/test_orchestrator.py -v

# Run specific test method
pytest tests/unit/test_orchestrator.py::TestAdvancedOrchestrator::test_workflow_execution_success -v
```

## 📝 Code Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some modifications:

```python
# Good: Clear, descriptive names
async def execute_intelligent_workflow(
    self,
    workflow: Dict[str, Any],
    config: IntelligentWorkflowConfig
) -> WorkflowResult:
    """Execute workflow with AI assistance."""
    
# Good: Type hints
from typing import Dict, List, Optional, Union, Any

# Good: Docstrings
def process_multimodal_content(
    content: Union[str, bytes],
    content_type: str
) -> ProcessedContent:
    """
    Process multi-modal content with AI analysis.
    
    Args:
        content: Raw content data
        content_type: MIME type of content
        
    Returns:
        ProcessedContent: Analyzed and structured content
        
    Raises:
        ProcessingError: If content cannot be processed
    """
```

### Code Quality Tools

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/
pylint src/

# Type checking
mypy src/ --strict

# Security scanning
bandit -r src/

# All quality checks
make quality-check
```

### Error Handling

```python
# Good: Specific exception handling
try:
    result = await llm_provider.generate_response(prompt)
except LLMTimeoutError as e:
    logger.warning(f"LLM timeout: {e}")
    return await self._handle_llm_timeout(prompt)
except LLMQuotaExceededError as e:
    logger.error(f"LLM quota exceeded: {e}")
    raise WorkflowExecutionError("LLM quota exceeded") from e
except Exception as e:
    logger.error(f"Unexpected LLM error: {e}")
    raise

# Good: Custom exceptions
class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""
    
    def __init__(self, message: str, execution_id: Optional[str] = None):
        super().__init__(message)
        self.execution_id = execution_id
```

## 🏗️ Architecture Guidelines

### Adding New Components

1. **Define Interface** (in `core/interfaces.py`)
```python
from abc import ABC, abstractmethod

class INewComponent(ABC):
    """Interface for new component."""
    
    @abstractmethod
    async def process(self, data: Any) -> Any:
        """Process data."""
        pass
```

2. **Implement Component** (in appropriate `src/` subdirectory)
```python
from core.interfaces import INewComponent

class NewComponent(INewComponent):
    """Implementation of new component."""
    
    async def process(self, data: Any) -> Any:
        """Process data implementation."""
        # Implementation here
        pass
```

3. **Add Tests**
```python
# tests/unit/test_new_component.py
class TestNewComponent:
    """Test suite for NewComponent."""
    pass
```

### Dependency Injection

```python
# Use dependency injection for testability
class WorkflowEngine:
    def __init__(
        self,
        task_executor: ITaskExecutor,
        llm_provider: ILLMProvider,
        state_manager: IStateManager
    ):
        self.task_executor = task_executor
        self.llm_provider = llm_provider
        self.state_manager = state_manager
```

### Async/Await Patterns

```python
# Good: Proper async patterns
async def execute_tasks_parallel(self, tasks: List[Task]) -> List[TaskResult]:
    """Execute tasks in parallel."""
    async with asyncio.TaskGroup() as tg:
        task_futures = [
            tg.create_task(self._execute_task(task))
            for task in tasks
        ]
    
    return [future.result() for future in task_futures]

# Good: Context managers for resources
async def with_browser_context(self):
    """Provide browser context."""
    browser = await self.browser_pool.acquire()
    try:
        yield browser
    finally:
        await self.browser_pool.release(browser)
```

## 📚 Documentation Standards

### Code Documentation

```python
class AdvancedOrchestrator:
    """
    Advanced workflow orchestrator with AI capabilities.
    
    This orchestrator provides intelligent workflow execution with:
    - AI-powered error recovery
    - Multi-modal processing
    - Parallel execution optimization
    - Real-time monitoring
    
    Example:
        >>> orchestrator = AdvancedOrchestrator()
        >>> config = IntelligentWorkflowConfig(enable_llm_assistance=True)
        >>> result = await orchestrator.execute_intelligent_workflow(workflow, config)
    """
    
    async def execute_intelligent_workflow(
        self,
        workflow: Dict[str, Any],
        config: IntelligentWorkflowConfig
    ) -> WorkflowResult:
        """
        Execute workflow with AI assistance.
        
        Args:
            workflow: Workflow definition with tasks and dependencies
            config: Configuration for AI features and execution
            
        Returns:
            WorkflowResult: Execution results with metrics and outputs
            
        Raises:
            ValidationError: If workflow definition is invalid
            OrchestrationError: If execution fails
            
        Example:
            >>> workflow = {"type": "web_scraping", "tasks": [...]}
            >>> config = IntelligentWorkflowConfig(enable_llm_assistance=True)
            >>> result = await orchestrator.execute_intelligent_workflow(workflow, config)
            >>> print(f"Success: {result.success}")
        """
```

### API Documentation

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class WorkflowRequest(BaseModel):
    """Request model for workflow execution."""
    workflow: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None

@router.post("/workflows/execute")
async def execute_workflow(request: WorkflowRequest):
    """
    Execute a workflow with optional AI assistance.
    
    This endpoint allows you to execute complex browser automation workflows
    with intelligent features like error recovery and optimization.
    
    - **workflow**: Complete workflow definition
    - **config**: Optional configuration for AI features
    
    Returns the execution results including success status, outputs, and metrics.
    """
```

## 🚀 Performance Guidelines

### Optimization Principles

1. **Async First**: Use async/await for I/O operations
2. **Resource Pooling**: Reuse expensive resources (browsers, connections)
3. **Intelligent Caching**: Cache expensive computations and API calls
4. **Parallel Execution**: Execute independent tasks concurrently
5. **Memory Management**: Clean up resources promptly

### Performance Testing

```python
# tests/performance/test_orchestrator_performance.py
import pytest
import time
from src.intelligence.advanced_orchestrator import AdvancedOrchestrator

class TestOrchestratorPerformance:
    """Performance tests for orchestrator."""
    
    @pytest.mark.performance
    async def test_workflow_execution_performance(self):
        """Test workflow execution performance."""
        orchestrator = AdvancedOrchestrator()
        
        start_time = time.time()
        result = await orchestrator.execute_workflow(test_workflow)
        execution_time = time.time() - start_time
        
        # Assert performance requirements
        assert execution_time < 30.0  # Should complete in under 30 seconds
        assert result["success"] is True
```

## 🔍 Debugging Guidelines

### Logging

```python
from src.infrastructure.logging.logger import StructuredLogger

class MyComponent:
    def __init__(self):
        self.logger = StructuredLogger("my_component")
    
    async def process(self, data):
        self.logger.info(
            "Processing started",
            data_size=len(data),
            component="my_component"
        )
        
        try:
            result = await self._do_processing(data)
            self.logger.info(
                "Processing completed successfully",
                result_size=len(result)
            )
            return result
        except Exception as e:
            self.logger.error(
                "Processing failed",
                error=str(e),
                error_type=type(e).__name__
            )
            raise
```

### Debug Configuration

```python
# For development debugging
debug_config = {
    "enable_debug_mode": True,
    "capture_screenshots": True,
    "save_page_source": True,
    "pause_on_error": True,
    "verbose_logging": True
}
```

## 📋 Pull Request Checklist

Before submitting a pull request:

- [ ] **Code Quality**
  - [ ] Code follows style guidelines
  - [ ] All tests pass
  - [ ] Code coverage maintained/improved
  - [ ] No linting errors

- [ ] **Documentation**
  - [ ] Code is properly documented
  - [ ] API changes documented
  - [ ] README updated if needed
  - [ ] Changelog updated

- [ ] **Testing**
  - [ ] Unit tests added/updated
  - [ ] Integration tests added if needed
  - [ ] Manual testing completed
  - [ ] Performance impact assessed

- [ ] **Review**
  - [ ] Self-review completed
  - [ ] Breaking changes identified
  - [ ] Migration guide provided if needed

## 🏆 Recognition

Contributors are recognized in:

- **README.md** - All contributors listed
- **CHANGELOG.md** - Major contributions highlighted  
- **GitHub Releases** - Contributors thanked in release notes
- **Discord** - Special contributor role

## 🔗 Resources

- **[Architecture Guide](architecture.md)** - Detailed system architecture
- **[API Reference](api-reference.md)** - Complete API documentation
- **[Testing Guide](testing.md)** - Comprehensive testing strategies
- **[Performance Guide](performance.md)** - Performance optimization techniques

## 📞 Getting Help

- **GitHub Discussions**: [Ask questions](https://github.com/your-org/browser-automation-framework/discussions)
- **Discord**: [Real-time chat](https://discord.gg/automation-framework)
- **Email**: [maintainers@automation-framework.com](mailto:maintainers@automation-framework.com)

Thank you for contributing to the Browser Automation Framework! 🚀
