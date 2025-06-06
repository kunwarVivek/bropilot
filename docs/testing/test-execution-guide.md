# Test Execution Guide

## 🚀 Overview

This comprehensive guide covers everything you need to know about executing tests and managing test suites in the Browser Automation Framework. From running individual tests to orchestrating complex test suites with dependencies and parallel execution.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Test Execution Methods](#test-execution-methods)
- [Test Suite Management](#test-suite-management)
- [Parallel Execution](#parallel-execution)
- [Test Dependencies](#test-dependencies)
- [Advanced Execution](#advanced-execution)
- [Monitoring and Reporting](#monitoring-and-reporting)

## ⚡ Quick Start

### 1. Run a Single Test

```bash
# Run a specific test file
pytest tests/test_navigation.py -v

# Run a specific test method
pytest tests/test_navigation.py::TestNavigation::test_homepage_loads -v

# Run with the framework's test runner
python -m src.testing.runner --file tests/test_navigation.py
```

### 2. Run Test Suites

```bash
# Run a predefined test suite
python -m src.testing.runner --suite smoke

# Run multiple suites
python -m src.testing.runner --suite smoke,regression

# Run with custom configuration
python -m src.testing.runner \
    --suite regression \
    --parallel \
    --workers 4 \
    --timeout 1800 \
    --retry-failed
```

### 3. Run Tests by Tags

```bash
# Run tests with specific tags
python -m src.testing.runner --tags "smoke,critical"

# Exclude tests with certain tags
python -m src.testing.runner --exclude-tags "slow,manual"

# Combine inclusion and exclusion
python -m src.testing.runner \
    --tags "regression,ui" \
    --exclude-tags "slow" \
    --priority "high,critical"
```

## 🎯 Test Execution Methods

### Method 1: Using pytest (Standard)

```bash
# Basic pytest execution
pytest

# Run with coverage
pytest --cov=src --cov-report=html --cov-report=term

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m e2e           # End-to-end tests only

# Run tests in parallel
pytest -n auto

# Run with live logging
pytest -s --log-cli-level=INFO

# Run failed tests only
pytest --lf  # Last failed
pytest --ff  # Failed first
```

### Method 2: Using Framework Test Runner

```bash
# Basic framework execution
python -m src.testing.runner

# Run specific suite
python -m src.testing.runner --suite smoke

# Run with AI assistance
python -m src.testing.runner \
    --suite regression \
    --enable-ai \
    --llm-provider openai \
    --auto-heal-failures

# Run with custom browser configuration
python -m src.testing.runner \
    --browser-pool-size 10 \
    --headless \
    --viewport 1920x1080 \
    --disable-images
```

### Method 3: Programmatic Execution

```python
# tests/run_custom_suite.py
import asyncio
from src.testing.test_runner import TestRunner
from src.testing.test_framework import TestSuite
from tests.test_navigation import TestNavigation
from tests.test_forms import TestForms

async def run_custom_test_suite():
    """Run a custom test suite programmatically."""
    
    # Create test runner
    runner = TestRunner(
        parallel=True,
        max_workers=4,
        timeout=1800,
        retry_failed=True,
        capture_screenshots=True,
        output_dir="results/custom_suite"
    )
    
    # Create custom test suite
    suite = TestSuite(
        name="Custom Test Suite",
        description="Custom combination of tests",
        tags=["custom", "smoke"],
        execution_mode="parallel"
    )
    
    # Add test cases
    suite.add_test_case(TestNavigation())
    suite.add_test_case(TestForms())
    
    # Run the suite
    results = await runner.run_suite(suite)
    
    # Process results
    print(f"Tests run: {results.total_tests}")
    print(f"Passed: {results.passed}")
    print(f"Failed: {results.failed}")
    print(f"Skipped: {results.skipped}")
    
    return results

# Run the custom suite
if __name__ == "__main__":
    asyncio.run(run_custom_test_suite())
```

## 🏗️ Test Suite Management

### Creating Test Suites

```python
# tests/suites/smoke_test_suite.py
from src.testing.test_framework import TestSuite
from tests.test_navigation import TestNavigation
from tests.test_authentication import TestAuthentication
from tests.test_core_functionality import TestCoreFunctionality

class SmokeTestSuite(TestSuite):
    """Smoke test suite for critical functionality."""
    
    def __init__(self):
        super().__init__(
            name="Smoke Test Suite",
            description="Critical functionality tests that must pass",
            tags=["smoke", "critical"],
            execution_mode="sequential",  # or "parallel"
            timeout=1800,  # 30 minutes
            retry_failed=True,
            max_retries=2,
            
            # Environment setup
            setup_requirements={
                "database": "clean_state",
                "cache": "cleared",
                "services": ["api", "database", "redis"]
            },
            
            # Reporting configuration
            generate_report=True,
            report_format=["html", "junit", "json"],
            capture_evidence=True
        )
        
        # Add test cases to suite
        self.add_test_case(TestAuthentication())
        self.add_test_case(TestNavigation())
        self.add_test_case(TestCoreFunctionality())
        
        # Define test dependencies
        self.add_dependency(
            "TestAuthentication.test_login",
            "TestCoreFunctionality.test_user_dashboard"
        )
    
    async def setup_suite(self):
        """Setup before running the entire suite."""
        # Initialize test environment
        await self.initialize_test_database()
        await self.setup_test_users()
        await self.configure_test_environment()
        
        # Verify prerequisites
        await self.verify_services_running()
        await self.verify_test_data_available()
    
    async def teardown_suite(self):
        """Cleanup after running the entire suite."""
        await self.cleanup_test_data()
        await self.reset_test_environment()
        await self.archive_test_artifacts()
    
    def get_execution_plan(self):
        """Define custom execution plan."""
        return {
            "phases": [
                {
                    "name": "Authentication Tests",
                    "tests": ["TestAuthentication.*"],
                    "parallel": False,
                    "timeout": 300
                },
                {
                    "name": "Core Functionality",
                    "tests": ["TestCoreFunctionality.*"],
                    "parallel": True,
                    "max_workers": 3,
                    "timeout": 600
                },
                {
                    "name": "Navigation Tests",
                    "tests": ["TestNavigation.*"],
                    "parallel": True,
                    "max_workers": 2,
                    "timeout": 300
                }
            ]
        }
```

### Regression Test Suite

```python
# tests/suites/regression_test_suite.py
from src.testing.test_framework import TestSuite, TestGroup

class RegressionTestSuite(TestSuite):
    """Comprehensive regression test suite."""
    
    def __init__(self):
        super().__init__(
            name="Regression Test Suite",
            description="Complete application regression testing",
            tags=["regression", "comprehensive"],
            execution_mode="parallel",
            max_workers=8,
            timeout=7200,  # 2 hours
            
            # Advanced configuration
            load_balancing=True,
            resource_optimization=True,
            auto_retry_flaky_tests=True,
            failure_threshold=0.05  # Stop if >5% of tests fail
        )
        
        # Organize tests into logical groups
        self.add_test_group(self._create_ui_tests())
        self.add_test_group(self._create_api_tests())
        self.add_test_group(self._create_integration_tests())
        self.add_test_group(self._create_performance_tests())
    
    def _create_ui_tests(self):
        """Create UI test group."""
        ui_group = TestGroup(
            name="UI Tests",
            description="User interface regression tests",
            tags=["ui", "frontend"],
            parallel=True,
            max_workers=4
        )
        
        # Add UI test cases
        ui_group.add_test_cases([
            "tests.test_navigation",
            "tests.test_forms",
            "tests.test_user_interface",
            "tests.test_responsive_design"
        ])
        
        return ui_group
    
    def _create_api_tests(self):
        """Create API test group."""
        api_group = TestGroup(
            name="API Tests",
            description="Backend API regression tests",
            tags=["api", "backend"],
            parallel=True,
            max_workers=6
        )
        
        # Add API test cases
        api_group.add_test_cases([
            "tests.test_user_api",
            "tests.test_product_api",
            "tests.test_order_api",
            "tests.test_authentication_api"
        ])
        
        return api_group

## ⚡ Parallel Execution

### Configuring Parallel Execution

```python
# tests/config/parallel_config.py
from src.testing.parallel_executor import ParallelExecutionConfig

# Basic parallel configuration
parallel_config = ParallelExecutionConfig(
    enabled=True,
    max_workers=4,
    worker_type="process",  # or "thread"
    load_balancing=True,
    resource_sharing=False,

    # Resource limits per worker
    memory_limit_mb=512,
    cpu_limit_percent=25,

    # Coordination settings
    shared_state=True,
    result_aggregation="real_time",
    failure_handling="continue"  # or "stop_on_first_failure"
)

# Advanced parallel configuration
advanced_parallel_config = ParallelExecutionConfig(
    enabled=True,
    max_workers=8,
    worker_type="process",

    # Dynamic scaling
    auto_scaling=True,
    min_workers=2,
    scale_up_threshold=0.8,  # Scale up when 80% busy
    scale_down_threshold=0.3,  # Scale down when 30% busy

    # Resource optimization
    resource_pooling=True,
    browser_pool_size=10,
    database_pool_size=5,

    # Fault tolerance
    worker_restart_on_failure=True,
    max_worker_failures=3,
    circuit_breaker_enabled=True
)
```

### Running Tests in Parallel

```bash
# Basic parallel execution
python -m src.testing.runner --parallel --workers 4

# Advanced parallel execution with resource management
python -m src.testing.runner \
    --parallel \
    --workers 8 \
    --auto-scaling \
    --resource-pooling \
    --load-balancing

# Parallel execution with custom configuration
python -m src.testing.runner \
    --config tests/config/parallel_config.yaml \
    --suite regression
```

### Parallel-Safe Test Design

```python
# tests/test_parallel_safe.py
from src.testing.test_framework import TestCase
from src.testing.isolation import TestIsolation

class TestParallelSafe(TestCase):
    """Example of parallel-safe test design."""

    def __init__(self):
        super().__init__(
            name="Parallel Safe Tests",
            description="Tests designed for parallel execution",
            tags=["parallel", "safe"],
            parallel_safe=True,

            # Isolation requirements
            isolation_level="full",  # full, partial, none
            shared_resources=[],     # No shared resources
            exclusive_resources=["test_user_pool"]
        )

    async def setup(self):
        """Setup with proper isolation."""
        # Use test isolation utilities
        self.isolation = TestIsolation()

        # Get isolated test data
        self.test_user = await self.isolation.get_isolated_user()
        self.test_database = await self.isolation.get_isolated_database()

        # Setup isolated browser context
        self.browser_context = await self.isolation.get_isolated_browser_context()
        self.page = await self.browser_context.new_page()

    async def teardown(self):
        """Cleanup isolated resources."""
        await self.isolation.cleanup_isolated_resources()
        await self.browser_context.close()

    async def test_isolated_user_workflow(self):
        """Test that uses isolated resources."""
        # This test can run in parallel because it uses isolated resources
        await self.page.goto(f"https://example.com/user/{self.test_user.id}")

        # Perform test actions with isolated data
        await self.page.fill("#username", self.test_user.username)
        await self.page.fill("#password", self.test_user.password)
        await self.page.click("button[type='submit']")

        # Verify results
        await self.page.wait_for_selector(".dashboard")
        assert await self.page.is_visible(".welcome-message")
```

## 🔗 Test Dependencies

### Defining Test Dependencies

```python
# tests/test_user_workflow.py
from src.testing.test_framework import ChainedTestCase
from src.testing.dependencies import TestDependency

class TestUserWorkflow(ChainedTestCase):
    """Test case with dependencies between test methods."""

    def __init__(self):
        super().__init__(
            name="User Workflow Chain",
            description="Complete user journey with dependencies",
            tags=["workflow", "e2e", "chained"]
        )

        # Define test dependencies
        self.dependencies = [
            TestDependency(
                test="test_user_registration",
                depends_on=[],
                provides=["user_credentials", "user_id"]
            ),
            TestDependency(
                test="test_email_verification",
                depends_on=["test_user_registration"],
                requires=["user_credentials"],
                provides=["verified_user"]
            ),
            TestDependency(
                test="test_user_login",
                depends_on=["test_email_verification"],
                requires=["verified_user"],
                provides=["authenticated_session"]
            ),
            TestDependency(
                test="test_profile_setup",
                depends_on=["test_user_login"],
                requires=["authenticated_session"],
                provides=["complete_profile"]
            )
        ]

        # Shared state between tests
        self.shared_state = {}

    async def test_user_registration(self):
        """Step 1: User registration."""
        # Generate unique user data
        user_data = self.generate_unique_user_data()

        # Perform registration
        await self.page.goto("https://example.com/register")
        await self.fill_registration_form(user_data)
        await self.page.click("button[type='submit']")

        # Verify registration success
        await self.page.wait_for_selector(".registration-success")

        # Store data for dependent tests
        self.shared_state["user_credentials"] = user_data
        self.shared_state["user_id"] = await self.extract_user_id()

        return {"status": "success", "user_id": self.shared_state["user_id"]}

    async def test_email_verification(self):
        """Step 2: Email verification (depends on registration)."""
        # Get user credentials from previous test
        user_credentials = self.shared_state["user_credentials"]

        # Simulate email verification
        verification_token = await self.get_verification_token(user_credentials["email"])

        # Verify email
        await self.page.goto(f"https://example.com/verify?token={verification_token}")
        await self.page.wait_for_selector(".verification-success")

        # Update shared state
        self.shared_state["verified_user"] = True

        return {"status": "success", "verified": True}

    async def test_user_login(self):
        """Step 3: User login (depends on email verification)."""
        # Ensure previous steps completed successfully
        assert self.shared_state.get("verified_user"), "User must be verified before login"

        user_credentials = self.shared_state["user_credentials"]

        # Perform login
        await self.page.goto("https://example.com/login")
        await self.page.fill("#email", user_credentials["email"])
        await self.page.fill("#password", user_credentials["password"])
        await self.page.click("button[type='submit']")

        # Verify login success
        await self.page.wait_for_selector(".dashboard")

        # Store session information
        session_token = await self.page.evaluate("localStorage.getItem('session_token')")
        self.shared_state["authenticated_session"] = session_token

        return {"status": "success", "session_token": session_token}
```
```
