# Testing Guide

## 🧪 Overview

This guide provides comprehensive information about testing the Browser Automation Framework, including test execution, configuration, and best practices for ensuring robust and reliable automation workflows.

## 📋 Table of Contents

- [Testing Strategy](#testing-strategy)
- [Test Categories](#test-categories)
- [Test Setup](#test-setup)
- [Running Tests](#running-tests)
- [Test Configuration](#test-configuration)
- [Writing Tests](#writing-tests)
- [Debugging Tests](#debugging-tests)
- [Performance Testing](#performance-testing)
- [CI/CD Integration](#cicd-integration)

## 🎯 Testing Strategy

### Testing Pyramid

```mermaid
graph TB
    subgraph "Testing Pyramid"
        E2E[End-to-End Tests<br/>10%<br/>High-level user scenarios]
        INT[Integration Tests<br/>20%<br/>Component interactions]
        UNIT[Unit Tests<br/>70%<br/>Individual components]
    end
    
    subgraph "Test Types"
        PERF[Performance Tests<br/>Load & Stress Testing]
        SEC[Security Tests<br/>Vulnerability Scanning]
        COMP[Compatibility Tests<br/>Browser & Platform Testing]
    end
    
    E2E --> PERF
    INT --> SEC
    UNIT --> COMP
```

### Test Categories

| Category | Purpose | Coverage | Execution Time |
|----------|---------|----------|----------------|
| **Unit Tests** | Test individual components in isolation | 70% of test suite | < 5 minutes |
| **Integration Tests** | Test component interactions | 20% of test suite | 5-15 minutes |
| **End-to-End Tests** | Test complete user workflows | 10% of test suite | 15-30 minutes |
| **Performance Tests** | Validate performance requirements | On-demand | 30-60 minutes |

## 🏗️ Test Setup

### Prerequisites

```bash
# System requirements
Python 3.11+
Docker & Docker Compose
PostgreSQL 14+
Redis 6+
Chrome/Chromium browser

# Development tools
pytest
pytest-asyncio
pytest-cov
pytest-mock
playwright
```

### Environment Setup

```bash
# Clone repository
git clone https://github.com/your-org/browser-automation-framework.git
cd browser-automation-framework

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps

# Set up test environment
cp .env.example .env.test
# Edit .env.test with test-specific configuration
```

### Test Database Setup

```bash
# Start test database
docker-compose -f docker-compose.test.yml up -d postgres redis

# Run migrations
export DATABASE_URL="postgresql://test_user:test_pass@localhost:5433/test_db"
alembic upgrade head

# Verify setup
python -c "
from src.infrastructure.config.settings import Settings
settings = Settings(_env_file='.env.test')
print('✅ Test environment configured successfully')
"
```

## 🚀 Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e           # End-to-end tests only
pytest -m performance   # Performance tests only
```

### Advanced Test Execution

```bash
# Run tests in parallel
pytest -n auto

# Run tests with live logging
pytest -s --log-cli-level=INFO

# Run specific test file
pytest tests/unit/test_orchestrator.py -v

# Run specific test method
pytest tests/unit/test_orchestrator.py::TestOrchestrator::test_workflow_execution -v

# Run tests matching pattern
pytest -k "test_workflow" -v

# Run tests with debugging
pytest --pdb tests/unit/test_orchestrator.py::test_specific_function
```

### Test Markers

```bash
# Available test markers
pytest --markers

# Run tests by marker
pytest -m "unit and not slow"
pytest -m "integration or e2e"
pytest -m "llm"  # Tests requiring LLM API
pytest -m "slow"  # Long-running tests
```

## ⚙️ Test Configuration

### pytest.ini Configuration

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --tb=short
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests (>30s)
    performance: Performance tests
    llm: Tests requiring LLM API
    browser: Tests requiring browser
asyncio_mode = auto
```

### Environment Variables

```bash
# Test environment configuration
export APP_ENVIRONMENT=testing
export LOG_LEVEL=DEBUG
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5433/test_db
export REDIS_URL=redis://localhost:6380/0

# Browser configuration
export BROWSER_HEADLESS=true
export BROWSER_TIMEOUT=30
export BROWSER_POOL_SIZE=2

# LLM configuration (for LLM tests)
export OPENAI_API_KEY=your_test_api_key
export MOCK_LLM_PROVIDER=true  # Use mock for most tests

# Performance testing
export PERFORMANCE_TEST_DURATION=60
export PERFORMANCE_MAX_USERS=10
```

## 📝 Writing Tests

### Unit Test Example

```python
import pytest
from unittest.mock import Mock, AsyncMock
from src.intelligence.advanced_orchestrator import AdvancedOrchestrator
from src.intelligence.config import IntelligentWorkflowConfig

class TestAdvancedOrchestrator:
    """Test suite for Advanced Orchestrator."""
    
    @pytest.fixture
    async def orchestrator(self):
        """Create orchestrator with mocks."""
        mock_workflow_engine = Mock()
        mock_task_executor = Mock()
        mock_llm_provider = Mock()
        
        orchestrator = AdvancedOrchestrator(
            workflow_engine=mock_workflow_engine,
            task_executor=mock_task_executor,
            llm_provider=mock_llm_provider
        )
        
        await orchestrator.start()
        yield orchestrator
        await orchestrator.stop()
    
    @pytest.mark.asyncio
    async def test_workflow_execution_success(self, orchestrator):
        """Test successful workflow execution."""
        # Arrange
        workflow = {
            "type": "test_workflow",
            "name": "Test Workflow",
            "tasks": [
                {
                    "id": "task_1",
                    "name": "Test Task",
                    "type": "browser_action",
                    "definition": {"action": "navigate", "url": "https://example.com"}
                }
            ]
        }
        
        config = IntelligentWorkflowConfig(
            enable_llm_assistance=False,
            enable_analytics=False
        )
        
        # Act
        result = await orchestrator.execute_intelligent_workflow(workflow, config)
        
        # Assert
        assert result["success"] is True
        assert "results" in result
        assert "statistics" in result
```

### Integration Test Example

```python
import pytest
from src.api.main_service import app
from fastapi.testclient import TestClient

class TestWorkflowAPI:
    """Integration tests for workflow API."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_create_workflow_endpoint(self, client):
        """Test workflow creation endpoint."""
        # Arrange
        workflow_data = {
            "name": "Test Workflow",
            "type": "web_scraping",
            "tasks": [
                {
                    "id": "navigate",
                    "type": "navigate",
                    "definition": {"url": "https://example.com"}
                }
            ]
        }
        
        # Act
        response = client.post("/api/v1/workflows", json=workflow_data)
        
        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Workflow"
        assert "id" in data
```

### End-to-End Test Example

```python
import pytest
from playwright.async_api import async_playwright

class TestCompleteWorkflow:
    """End-to-end workflow tests."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_web_scraping_workflow(self):
        """Test complete web scraping workflow."""
        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                # Execute workflow steps
                await page.goto("https://example.com")
                title = await page.title()
                
                # Verify results
                assert title == "Example Domain"
                
            finally:
                await browser.close()
```

## 🐛 Debugging Tests

### Debug Configuration

```python
# Enable debug mode in tests
import logging
logging.basicConfig(level=logging.DEBUG)

# Use ipdb for debugging
import ipdb; ipdb.set_trace()

# Pytest debugging options
pytest --pdb                    # Drop into debugger on failures
pytest --pdb-trace             # Drop into debugger at start
pytest --capture=no            # Disable output capturing
pytest -s                      # Shorthand for --capture=no
```

### Common Debugging Scenarios

```python
# Debug async tests
@pytest.mark.asyncio
async def test_async_function():
    import ipdb; ipdb.set_trace()
    result = await some_async_function()
    assert result is not None

# Debug with logging
def test_with_logging(caplog):
    with caplog.at_level(logging.DEBUG):
        function_under_test()
    
    assert "Expected log message" in caplog.text

# Debug browser tests
@pytest.mark.asyncio
async def test_browser_interaction():
    browser = await playwright.chromium.launch(headless=False, slow_mo=1000)
    # Browser will run slowly for easier debugging
```

## 📊 Performance Testing

### Load Testing Example

```python
import pytest
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """Performance test suite."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_concurrent_workflow_execution(self):
        """Test concurrent workflow execution performance."""
        
        async def execute_workflow():
            # Simulate workflow execution
            start_time = time.time()
            await asyncio.sleep(0.1)  # Simulate work
            return time.time() - start_time
        
        # Execute multiple workflows concurrently
        tasks = [execute_workflow() for _ in range(10)]
        execution_times = await asyncio.gather(*tasks)
        
        # Performance assertions
        avg_time = sum(execution_times) / len(execution_times)
        assert avg_time < 0.5  # Average execution time should be < 500ms
        assert max(execution_times) < 1.0  # No execution should take > 1s
```

### Memory Testing

```python
import psutil
import pytest

@pytest.mark.performance
def test_memory_usage():
    """Test memory usage during workflow execution."""
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Execute memory-intensive operation
    execute_large_workflow()
    
    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    
    # Memory should not increase by more than 100MB
    assert memory_increase < 100 * 1024 * 1024
```

## 🔄 CI/CD Integration

### GitHub Actions Configuration

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_PASSWORD: test_pass
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        playwright install chromium
    
    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## 📈 Test Metrics and Reporting

### Coverage Reports

```bash
# Generate HTML coverage report
pytest --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html

# Generate XML coverage for CI
pytest --cov=src --cov-report=xml
```

### Test Results

```bash
# Generate JUnit XML for CI integration
pytest --junitxml=test-results.xml

# Generate test report with timing
pytest --durations=10
```

## 🎯 Best Practices

### Test Organization

1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Descriptive Names**: Test names should describe what is being tested
3. **Keep Tests Independent**: Each test should be able to run in isolation
4. **Use Fixtures**: Share common setup code using pytest fixtures
5. **Mock External Dependencies**: Use mocks for external services and APIs

### Performance Guidelines

1. **Fast Unit Tests**: Unit tests should complete in < 1 second
2. **Reasonable Integration Tests**: Integration tests should complete in < 30 seconds
3. **Efficient E2E Tests**: End-to-end tests should complete in < 5 minutes
4. **Parallel Execution**: Use pytest-xdist for parallel test execution

### Maintenance

1. **Regular Test Reviews**: Review and update tests regularly
2. **Remove Flaky Tests**: Identify and fix or remove unreliable tests
3. **Update Test Data**: Keep test data current and relevant
4. **Monitor Test Performance**: Track test execution times and optimize slow tests

---

For more detailed information, see:
- [Test Execution Guide](test-execution.md)
- [Testing Best Practices](testing-best-practices.md)
- [Test Configuration Guide](test-configuration.md)
