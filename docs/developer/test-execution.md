# Test Execution Guide

## 🚀 Overview

This guide provides step-by-step instructions for executing tests in the Browser Automation Framework, covering everything from basic test runs to advanced testing scenarios and troubleshooting.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Test Execution Workflows](#test-execution-workflows)
- [Environment Setup](#environment-setup)
- [Test Categories](#test-categories)
- [Advanced Execution](#advanced-execution)
- [Debugging and Troubleshooting](#debugging-and-troubleshooting)
- [Performance Testing](#performance-testing)
- [Continuous Integration](#continuous-integration)

## ⚡ Quick Start

### 1. Basic Test Execution

```bash
# Run all tests (recommended for first-time setup)
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test category
pytest -m unit
```

### 2. Verify Test Environment

```bash
# Check test environment health
python -c "
import sys
sys.path.append('.')
from tests.conftest import verify_test_environment
verify_test_environment()
print('✅ Test environment is ready')
"
```

## 🔧 Environment Setup

### Development Environment

```bash
# 1. Clone and setup
git clone https://github.com/your-org/browser-automation-framework.git
cd browser-automation-framework

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 4. Install browser dependencies
playwright install chromium
playwright install-deps

# 5. Setup test environment
cp .env.example .env.test
```

### Test Environment Configuration

```bash
# .env.test configuration
APP_ENVIRONMENT=testing
LOG_LEVEL=DEBUG
DATABASE_URL=postgresql://test_user:test_pass@localhost:5433/test_db
REDIS_URL=redis://localhost:6380/0
BROWSER_HEADLESS=true
BROWSER_TIMEOUT=30
MOCK_LLM_PROVIDER=true
```

### Docker Test Environment

```bash
# Start test services
docker-compose -f docker-compose.test.yml up -d

# Verify services are running
docker-compose -f docker-compose.test.yml ps

# Run tests in Docker
docker-compose -f docker-compose.test.yml run --rm test pytest
```

## 🎯 Test Execution Workflows

### Workflow 1: Development Testing

```mermaid
graph LR
    A[Code Changes] --> B[Run Unit Tests]
    B --> C{Tests Pass?}
    C -->|Yes| D[Run Integration Tests]
    C -->|No| E[Fix Issues]
    E --> B
    D --> F{Tests Pass?}
    F -->|Yes| G[Commit Changes]
    F -->|No| E
    G --> H[Push to Repository]
```

```bash
# Development workflow commands
# 1. Run unit tests for quick feedback
pytest -m unit --tb=short

# 2. Run integration tests for affected components
pytest tests/integration/test_orchestrator.py -v

# 3. Run full test suite before commit
pytest --cov=src --cov-report=term-missing
```

### Workflow 2: Pre-Release Testing

```bash
# 1. Run all test categories
pytest -m "unit or integration or e2e" --tb=short

# 2. Run performance tests
pytest -m performance --benchmark-only

# 3. Run security tests
pytest -m security

# 4. Generate comprehensive report
pytest --cov=src --cov-report=html --junitxml=test-results.xml
```

### Workflow 3: Debugging Workflow

```bash
# 1. Run failing test with detailed output
pytest tests/unit/test_orchestrator.py::test_specific_function -vvv -s

# 2. Run with debugger
pytest --pdb tests/unit/test_orchestrator.py::test_specific_function

# 3. Run with logging
pytest --log-cli-level=DEBUG tests/unit/test_orchestrator.py -s
```

## 📊 Test Categories

### Unit Tests

```bash
# Run all unit tests
pytest -m unit

# Run specific component unit tests
pytest tests/unit/test_orchestrator.py
pytest tests/unit/test_conversation.py
pytest tests/unit/test_multimodal.py

# Run unit tests with coverage
pytest -m unit --cov=src.intelligence --cov-report=term-missing

# Fast unit test execution
pytest -m unit --tb=line -q
```

### Integration Tests

```bash
# Run all integration tests
pytest -m integration

# Run API integration tests
pytest tests/integration/test_api_endpoints.py

# Run workflow integration tests
pytest tests/integration/test_workflow_execution.py

# Run with test database
export DATABASE_URL=postgresql://test_user:test_pass@localhost:5433/test_db
pytest -m integration
```

### End-to-End Tests

```bash
# Run all E2E tests
pytest -m e2e

# Run specific E2E scenarios
pytest tests/e2e/test_complete_workflows.py::TestCompleteWorkflows::test_web_scraping_workflow

# Run E2E tests with browser visible (for debugging)
export BROWSER_HEADLESS=false
pytest -m e2e -s

# Run E2E tests with slow motion
export BROWSER_SLOW_MO=1000
pytest -m e2e
```

### Performance Tests

```bash
# Run performance test suite
pytest -m performance

# Run load testing
pytest tests/performance/test_load_testing.py

# Run benchmark tests
pytest -m performance --benchmark-only --benchmark-sort=mean

# Run memory profiling tests
pytest -m performance --profile
```

## 🔍 Advanced Execution

### Parallel Test Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (auto-detect CPU cores)
pytest -n auto

# Run tests with specific number of workers
pytest -n 4

# Run specific categories in parallel
pytest -m unit -n auto
pytest -m integration -n 2  # Fewer workers for integration tests
```

### Selective Test Execution

```bash
# Run tests by keyword
pytest -k "test_workflow"
pytest -k "test_orchestrator and not slow"

# Run tests by file pattern
pytest tests/unit/test_*orchestrator*.py

# Run tests modified in last commit
pytest --lf  # Last failed
pytest --ff  # Failed first

# Run tests for specific module
pytest --cov=src.intelligence.advanced_orchestrator tests/unit/test_orchestrator.py
```

### Custom Test Execution

```bash
# Run tests with custom markers
pytest -m "unit and not slow"
pytest -m "(integration or e2e) and not llm"

# Run tests with environment variables
MOCK_LLM_PROVIDER=false pytest -m llm
BROWSER_HEADLESS=false pytest -m browser

# Run tests with timeout
pytest --timeout=300  # 5 minute timeout per test
```

## 🐛 Debugging and Troubleshooting

### Common Issues and Solutions

#### Issue 1: Database Connection Errors

```bash
# Problem: Tests fail with database connection errors
# Solution: Ensure test database is running
docker-compose -f docker-compose.test.yml up -d postgres

# Verify connection
psql postgresql://test_user:test_pass@localhost:5433/test_db -c "SELECT 1;"

# Reset test database
docker-compose -f docker-compose.test.yml down
docker-compose -f docker-compose.test.yml up -d postgres
sleep 5
alembic upgrade head
```

#### Issue 2: Browser Tests Failing

```bash
# Problem: Browser tests fail with timeout or connection errors
# Solution: Reinstall browser dependencies
playwright install chromium
playwright install-deps

# Run browser tests with visible browser for debugging
export BROWSER_HEADLESS=false
export BROWSER_SLOW_MO=1000
pytest -m browser -s
```

#### Issue 3: LLM Tests Failing

```bash
# Problem: LLM tests fail due to API issues
# Solution: Use mock LLM provider for testing
export MOCK_LLM_PROVIDER=true
pytest -m llm

# Or skip LLM tests entirely
pytest -m "not llm"
```

### Debug Test Execution

```bash
# Run single test with maximum verbosity
pytest tests/unit/test_orchestrator.py::test_specific_function -vvv -s --tb=long

# Run test with debugger
pytest --pdb tests/unit/test_orchestrator.py::test_specific_function

# Run test with profiling
pytest --profile tests/unit/test_orchestrator.py

# Run test with memory monitoring
pytest --memray tests/unit/test_orchestrator.py
```

### Test Environment Debugging

```python
# Create debug test script: debug_test_env.py
import os
import sys
sys.path.append('.')

def debug_environment():
    """Debug test environment setup."""
    print("=== Environment Debug ===")
    
    # Check Python path
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path}")
    
    # Check environment variables
    env_vars = ['APP_ENVIRONMENT', 'DATABASE_URL', 'REDIS_URL', 'LOG_LEVEL']
    for var in env_vars:
        print(f"{var}: {os.getenv(var, 'NOT SET')}")
    
    # Test imports
    try:
        from src.intelligence.advanced_orchestrator import AdvancedOrchestrator
        print("✅ Core imports successful")
    except ImportError as e:
        print(f"❌ Import error: {e}")
    
    # Test database connection
    try:
        from src.infrastructure.config.settings import Settings
        settings = Settings()
        print(f"✅ Settings loaded: {settings.app_environment}")
    except Exception as e:
        print(f"❌ Settings error: {e}")

if __name__ == "__main__":
    debug_environment()
```

```bash
# Run debug script
python debug_test_env.py
```

## 📈 Performance Testing

### Load Testing Workflow

```bash
# 1. Start performance test environment
docker-compose -f docker-compose.perf.yml up -d

# 2. Run baseline performance tests
pytest -m performance --benchmark-only --benchmark-save=baseline

# 3. Run load tests with different user counts
for users in 1 5 10 20; do
    export PERFORMANCE_MAX_USERS=$users
    pytest tests/performance/test_load_testing.py --benchmark-save=load_$users
done

# 4. Compare results
pytest-benchmark compare baseline load_*
```

### Memory and Resource Testing

```bash
# Install memory profiling tools
pip install memory-profiler psutil

# Run memory profiling
pytest --memray tests/performance/

# Monitor resource usage during tests
pytest tests/performance/ --monitor-resources

# Generate performance report
pytest -m performance --benchmark-only --benchmark-html=performance_report.html
```

## 🔄 Continuous Integration

### Local CI Simulation

```bash
# Simulate CI environment locally
export CI=true
export APP_ENVIRONMENT=testing
export BROWSER_HEADLESS=true

# Run CI test suite
pytest --cov=src --cov-report=xml --junitxml=test-results.xml

# Check coverage requirements
pytest --cov=src --cov-fail-under=80
```

### Pre-commit Testing

```bash
# Install pre-commit hooks
pip install pre-commit
pre-commit install

# Run pre-commit checks manually
pre-commit run --all-files

# Test commit workflow
git add .
git commit -m "Test commit"  # This will run tests automatically
```

### Branch Testing Workflow

```bash
# Test current branch against main
git checkout main
git pull origin main
pytest --co -q > main_tests.txt  # Collect test list

git checkout feature-branch
pytest --co -q > branch_tests.txt  # Collect test list

# Compare test coverage
diff main_tests.txt branch_tests.txt

# Run tests for changed files only
pytest $(git diff --name-only main...HEAD | grep "\.py$" | sed 's/src/tests\/unit/' | sed 's/\.py$/test_&/')
```

## 📊 Test Reporting

### Generate Comprehensive Reports

```bash
# Generate all reports
pytest \
  --cov=src \
  --cov-report=html:htmlcov \
  --cov-report=xml:coverage.xml \
  --cov-report=term-missing \
  --junitxml=test-results.xml \
  --html=test-report.html \
  --self-contained-html

# View reports
open htmlcov/index.html      # Coverage report
open test-report.html        # Test execution report
```

### Custom Test Reports

```python
# Create custom test reporter: conftest.py
import pytest
import json
from datetime import datetime

@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Create custom test report."""
    if call.when == "call":
        # Custom reporting logic
        report_data = {
            "test_name": item.name,
            "outcome": call.excinfo is None,
            "duration": call.duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Save to custom report file
        with open("custom_test_report.json", "a") as f:
            json.dump(report_data, f)
            f.write("\n")
```

## 🎯 Best Practices

### Test Execution Guidelines

1. **Run Tests Frequently**: Execute unit tests after every change
2. **Use Appropriate Test Categories**: Don't run E2E tests for unit-level changes
3. **Monitor Test Performance**: Keep track of test execution times
4. **Maintain Test Environment**: Regularly update test dependencies and data
5. **Use Parallel Execution**: Leverage parallel testing for faster feedback

### Troubleshooting Checklist

- [ ] Virtual environment activated
- [ ] Dependencies installed and up-to-date
- [ ] Test database running and accessible
- [ ] Environment variables properly set
- [ ] Browser dependencies installed
- [ ] No conflicting processes running on test ports
- [ ] Sufficient disk space and memory available

---

For more information, see:
- [Testing Guide](testing.md)
- [Testing Best Practices](testing-best-practices.md)
- [Test Configuration Guide](test-configuration.md)
