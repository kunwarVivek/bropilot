# Test Case Creation Guide

Comprehensive guide for creating, organizing, and executing test cases using the Browser Automation Framework.

## 🎯 Test Creation Overview

### Test Architecture

```mermaid
graph TB
    subgraph "Test Structure"
        TC[Test Cases]
        TS[Test Suites]
        TF[Test Fixtures]
        TD[Test Data]
    end
    
    subgraph "Test Types"
        UNIT[Unit Tests]
        INTEGRATION[Integration Tests]
        E2E[End-to-End Tests]
        SMOKE[Smoke Tests]
        REGRESSION[Regression Tests]
    end
    
    subgraph "Test Execution"
        RUNNER[Test Runner]
        PARALLEL[Parallel Execution]
        REPORTING[Test Reporting]
        CI[CI/CD Integration]
    end
    
    subgraph "Test Management"
        TAGS[Test Tags]
        GROUPS[Test Groups]
        DEPS[Dependencies]
        CONFIG[Configuration]
    end
    
    TC --> TS
    TS --> TF
    TF --> TD
    
    TC --> UNIT
    TC --> INTEGRATION
    TC --> E2E
    
    TS --> RUNNER
    RUNNER --> PARALLEL
    PARALLEL --> REPORTING
    
    TAGS --> GROUPS
    GROUPS --> DEPS
    DEPS --> CONFIG
```

### Test Case Lifecycle

1. **Design** - Define test objectives and scenarios
2. **Create** - Write test cases using framework APIs
3. **Organize** - Group tests into suites and categories
4. **Execute** - Run tests individually or in batches
5. **Report** - Generate and analyze test results
6. **Maintain** - Update tests as application evolves

## 🧪 Creating Basic Test Cases

### Simple Test Case Structure

```python
# tests/test_basic_navigation.py
import pytest
from src.testing.test_framework import TestCase, TestSuite
from src.testing.assertions import WebAssertions
from src.testing.fixtures import browser_fixture

class TestBasicNavigation(TestCase):
    """Basic navigation test cases."""
    
    def __init__(self):
        super().__init__(
            name="Basic Navigation Tests",
            description="Test basic website navigation functionality",
            tags=["navigation", "smoke", "basic"],
            priority="high"
        )
    
    @pytest.fixture(autouse=True)
    async def setup(self, browser_fixture):
        """Setup test environment."""
        self.browser = browser_fixture
        self.page = await self.browser.new_page()
        self.assertions = WebAssertions(self.page)
        
        # Set default timeouts
        self.page.set_default_timeout(30000)
        
    async def teardown(self):
        """Cleanup after test."""
        if hasattr(self, 'page'):
            await self.page.close()
    
    @pytest.mark.smoke
    async def test_homepage_loads(self):
        """Test that homepage loads successfully."""
        # Navigate to homepage
        await self.page.goto("https://example.com")
        
        # Assert page loaded
        await self.assertions.assert_page_loaded()
        await self.assertions.assert_title_contains("Example")
        await self.assertions.assert_url_equals("https://example.com/")
        
        # Take screenshot for evidence
        await self.capture_screenshot("homepage_loaded")
    
    @pytest.mark.regression
    async def test_navigation_menu(self):
        """Test navigation menu functionality."""
        await self.page.goto("https://example.com")
        
        # Test menu items
        menu_items = [
            {"selector": "nav a[href='/about']", "text": "About"},
            {"selector": "nav a[href='/services']", "text": "Services"},
            {"selector": "nav a[href='/contact']", "text": "Contact"}
        ]
        
        for item in menu_items:
            # Assert menu item exists and is visible
            await self.assertions.assert_element_visible(item["selector"])
            await self.assertions.assert_element_text(item["selector"], item["text"])
            
            # Click and verify navigation
            await self.page.click(item["selector"])
            await self.assertions.assert_url_contains(item["selector"].split("'")[1])
            
            # Navigate back
            await self.page.go_back()
    
    @pytest.mark.parametrize("url,expected_title", [
        ("https://example.com/about", "About Us"),
        ("https://example.com/services", "Our Services"),
        ("https://example.com/contact", "Contact Us")
    ])
    async def test_page_titles(self, url, expected_title):
        """Test page titles for different pages."""
        await self.page.goto(url)
        await self.assertions.assert_title_equals(expected_title)
```

### Advanced Test Case with AI Integration

```python
# tests/test_ai_powered_form.py
from src.testing.test_framework import AITestCase
from src.testing.ai_helpers import AIFormFiller, AIContentValidator

class TestAIPoweredForm(AITestCase):
    """AI-powered form testing."""
    
    def __init__(self):
        super().__init__(
            name="AI Form Testing",
            description="Test form functionality using AI assistance",
            tags=["forms", "ai", "integration"],
            ai_config={
                "enable_smart_waiting": True,
                "enable_content_validation": True,
                "enable_error_recovery": True
            }
        )
    
    async def test_contact_form_submission(self):
        """Test contact form with AI assistance."""
        await self.page.goto("https://example.com/contact")
        
        # Use AI to identify and fill form
        form_filler = AIFormFiller(self.page, self.llm_provider)
        
        form_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "subject": "Test Inquiry",
            "message": "This is a test message for form validation."
        }
        
        # AI will intelligently identify form fields
        await form_filler.fill_form(form_data)
        
        # Submit form
        await form_filler.submit_form()
        
        # Use AI to validate success message
        validator = AIContentValidator(self.page, self.llm_provider)
        success_detected = await validator.validate_success_message(
            expected_context="form submission successful"
        )
        
        assert success_detected, "Form submission success not detected"
        
        # Capture evidence
        await self.capture_screenshot("form_submitted")
        await self.save_page_content("form_submission_result")
```

## 🏗️ Test Suite Organization

### Creating Test Suites

```python
# tests/suites/smoke_test_suite.py
from src.testing.test_framework import TestSuite
from tests.test_basic_navigation import TestBasicNavigation
from tests.test_user_authentication import TestUserAuthentication
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
            max_retries=2
        )
        
        # Add test cases to suite
        self.add_test_case(TestBasicNavigation())
        self.add_test_case(TestUserAuthentication())
        self.add_test_case(TestCoreFunctionality())
        
        # Define test dependencies
        self.add_dependency(
            "TestUserAuthentication.test_login",
            "TestCoreFunctionality.test_user_dashboard"
        )
    
    async def setup_suite(self):
        """Setup before running the entire suite."""
        # Initialize test environment
        await self.initialize_test_database()
        await self.setup_test_users()
        await self.configure_test_environment()
    
    async def teardown_suite(self):
        """Cleanup after running the entire suite."""
        await self.cleanup_test_data()
        await self.reset_test_environment()
    
    def get_execution_plan(self):
        """Define custom execution plan."""
        return {
            "phases": [
                {
                    "name": "Authentication Tests",
                    "tests": ["TestUserAuthentication.*"],
                    "parallel": False
                },
                {
                    "name": "Core Functionality",
                    "tests": ["TestCoreFunctionality.*"],
                    "parallel": True,
                    "max_workers": 3
                },
                {
                    "name": "Navigation Tests",
                    "tests": ["TestBasicNavigation.*"],
                    "parallel": True,
                    "max_workers": 2
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
            max_workers=5,
            timeout=7200  # 2 hours
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
            description="User interface testing",
            tags=["ui", "frontend"],
            parallel=True,
            max_workers=3
        )
        
        # Add UI test cases
        ui_group.add_test_cases([
            "tests.ui.test_navigation",
            "tests.ui.test_forms",
            "tests.ui.test_responsive_design",
            "tests.ui.test_accessibility"
        ])
        
        return ui_group
    
    def _create_api_tests(self):
        """Create API test group."""
        api_group = TestGroup(
            name="API Tests",
            description="API endpoint testing",
            tags=["api", "backend"],
            parallel=True,
            max_workers=4
        )
        
        api_group.add_test_cases([
            "tests.api.test_authentication",
            "tests.api.test_user_management",
            "tests.api.test_workflow_api",
            "tests.api.test_error_handling"
        ])
        
        return api_group
```

## 🔗 Test Case Chaining and Dependencies

### Sequential Test Execution

```python
# tests/test_user_workflow.py
from src.testing.test_framework import ChainedTestCase

class TestUserWorkflow(ChainedTestCase):
    """Chained test case for complete user workflow."""
    
    def __init__(self):
        super().__init__(
            name="User Workflow Chain",
            description="Complete user journey from registration to task completion",
            tags=["workflow", "e2e", "chained"]
        )
        
        # Define test chain
        self.test_chain = [
            self.test_user_registration,
            self.test_email_verification,
            self.test_user_login,
            self.test_profile_setup,
            self.test_create_workflow,
            self.test_execute_workflow,
            self.test_view_results,
            self.test_user_logout
        ]
        
        # Shared state between tests
        self.shared_state = {}
    
    async def test_user_registration(self):
        """Step 1: User registration."""
        await self.page.goto("https://example.com/register")
        
        # Generate unique test data
        user_data = self.generate_test_user()
        self.shared_state['user_data'] = user_data
        
        # Fill registration form
        await self.page.fill("#username", user_data['username'])
        await self.page.fill("#email", user_data['email'])
        await self.page.fill("#password", user_data['password'])
        await self.page.click("#register-button")
        
        # Verify registration success
        await self.assertions.assert_text_visible("Registration successful")
        
        # Store user ID for next tests
        user_id = await self.page.get_attribute("#user-id", "value")
        self.shared_state['user_id'] = user_id
    
    async def test_email_verification(self):
        """Step 2: Email verification."""
        # Use shared state from previous test
        user_data = self.shared_state['user_data']
        
        # Simulate email verification (in real scenario, check email)
        verification_token = await self.get_verification_token(user_data['email'])
        
        await self.page.goto(f"https://example.com/verify?token={verification_token}")
        await self.assertions.assert_text_visible("Email verified successfully")
    
    async def test_user_login(self):
        """Step 3: User login."""
        user_data = self.shared_state['user_data']
        
        await self.page.goto("https://example.com/login")
        await self.page.fill("#username", user_data['username'])
        await self.page.fill("#password", user_data['password'])
        await self.page.click("#login-button")
        
        # Verify login success and store session
        await self.assertions.assert_url_contains("/dashboard")
        session_token = await self.page.evaluate("localStorage.getItem('session_token')")
        self.shared_state['session_token'] = session_token
    
    # Continue with remaining test steps...
    
    async def cleanup_chain(self):
        """Cleanup after entire chain completes."""
        if 'user_id' in self.shared_state:
            await self.cleanup_test_user(self.shared_state['user_id'])
```

### Conditional Test Execution

```python
# tests/test_conditional_flow.py
from src.testing.test_framework import ConditionalTestCase

class TestConditionalFlow(ConditionalTestCase):
    """Test case with conditional execution paths."""
    
    async def test_feature_availability(self):
        """Test different paths based on feature availability."""
        await self.page.goto("https://example.com/features")
        
        # Check if premium feature is available
        premium_available = await self.page.is_visible("#premium-features")
        
        if premium_available:
            await self.test_premium_features()
        else:
            await self.test_basic_features()
        
        # Common validation regardless of path
        await self.test_common_functionality()
    
    async def test_premium_features(self):
        """Test premium feature path."""
        await self.page.click("#premium-features")
        await self.assertions.assert_text_visible("Premium Features")
        
        # Test premium-specific functionality
        await self.page.click("#advanced-analytics")
        await self.assertions.assert_element_visible("#analytics-dashboard")
    
    async def test_basic_features(self):
        """Test basic feature path."""
        await self.page.click("#basic-features")
        await self.assertions.assert_text_visible("Basic Features")
        
        # Test basic functionality
        await self.page.click("#simple-reports")
        await self.assertions.assert_element_visible("#basic-reports")
```

## 📊 Data-Driven Testing

### Parameterized Tests

```python
# tests/test_data_driven.py
import pytest
from src.testing.data_providers import CSVDataProvider, JSONDataProvider, DatabaseDataProvider

class TestDataDriven:
    """Data-driven test examples."""
    
    @pytest.mark.parametrize("test_data", CSVDataProvider("test_data/login_data.csv"))
    async def test_login_scenarios(self, browser_fixture, test_data):
        """Test multiple login scenarios from CSV data."""
        page = await browser_fixture.new_page()
        
        await page.goto("https://example.com/login")
        await page.fill("#username", test_data['username'])
        await page.fill("#password", test_data['password'])
        await page.click("#login-button")
        
        if test_data['expected_result'] == 'success':
            await WebAssertions(page).assert_url_contains("/dashboard")
        else:
            await WebAssertions(page).assert_text_visible(test_data['expected_error'])
    
    @pytest.mark.parametrize("form_data", JSONDataProvider("test_data/form_data.json"))
    async def test_form_validation(self, browser_fixture, form_data):
        """Test form validation with JSON data."""
        page = await browser_fixture.new_page()
        
        await page.goto("https://example.com/contact")
        
        # Fill form with test data
        for field, value in form_data['input'].items():
            await page.fill(f"#{field}", value)
        
        await page.click("#submit-button")
        
        # Validate expected outcome
        if form_data['valid']:
            await WebAssertions(page).assert_text_visible("Form submitted successfully")
        else:
            for error in form_data['expected_errors']:
                await WebAssertions(page).assert_text_visible(error)
    
    @pytest.mark.parametrize("user_data", DatabaseDataProvider(
        query="SELECT * FROM test_users WHERE active = true",
        connection_string="postgresql://test:test@localhost/testdb"
    ))
    async def test_user_profiles(self, browser_fixture, user_data):
        """Test user profiles with database data."""
        page = await browser_fixture.new_page()
        
        # Login as test user
        await self.login_as_user(page, user_data['username'], user_data['password'])
        
        # Navigate to profile
        await page.goto("https://example.com/profile")
        
        # Verify profile data
        await WebAssertions(page).assert_input_value("#name", user_data['full_name'])
        await WebAssertions(page).assert_input_value("#email", user_data['email'])
```

### Dynamic Test Generation

```python
# tests/test_dynamic_generation.py
from src.testing.test_framework import DynamicTestGenerator

class TestDynamicGeneration:
    """Dynamically generated tests."""
    
    @classmethod
    def generate_api_tests(cls):
        """Generate API tests for all endpoints."""
        endpoints = [
            {"path": "/api/users", "method": "GET", "auth_required": True},
            {"path": "/api/workflows", "method": "GET", "auth_required": True},
            {"path": "/api/health", "method": "GET", "auth_required": False}
        ]
        
        tests = []
        for endpoint in endpoints:
            test_func = cls._create_api_test(endpoint)
            test_func.__name__ = f"test_api_{endpoint['path'].replace('/', '_')}"
            tests.append(test_func)
        
        return tests
    
    @classmethod
    def _create_api_test(cls, endpoint):
        """Create individual API test function."""
        async def test_function(self, api_client):
            if endpoint['auth_required']:
                api_client.set_auth_token(await self.get_auth_token())
            
            response = await api_client.request(
                method=endpoint['method'],
                url=endpoint['path']
            )
            
            assert response.status_code == 200
            assert 'application/json' in response.headers.get('content-type', '')
        
        return test_function

# Register dynamically generated tests
for test_func in TestDynamicGeneration.generate_api_tests():
    setattr(TestDynamicGeneration, test_func.__name__, test_func)
```

## 🎯 Test Execution Strategies

### Parallel Test Execution

```python
# tests/execution/parallel_execution.py
from src.testing.execution import ParallelTestRunner
import asyncio

class ParallelTestExecution:
    """Configure and run tests in parallel."""
    
    def __init__(self):
        self.runner = ParallelTestRunner(
            max_workers=5,
            browser_pool_size=10,
            isolation_level="test",  # test, suite, or session
            resource_management="shared"  # shared or isolated
        )
    
    async def run_smoke_tests_parallel(self):
        """Run smoke tests in parallel."""
        test_config = {
            "test_selection": {
                "tags": ["smoke"],
                "priority": ["high", "critical"]
            },
            "execution": {
                "parallel": True,
                "max_workers": 3,
                "timeout_per_test": 300,
                "retry_failed": True,
                "max_retries": 2
            },
            "reporting": {
                "real_time": True,
                "detailed_logs": True,
                "screenshots_on_failure": True
            }
        }
        
        results = await self.runner.run_tests(test_config)
        return results
    
    async def run_regression_tests_staged(self):
        """Run regression tests in stages."""
        stages = [
            {
                "name": "Critical Path Tests",
                "tests": {"tags": ["critical", "smoke"]},
                "parallel": False,
                "stop_on_failure": True
            },
            {
                "name": "Core Functionality",
                "tests": {"tags": ["core", "regression"]},
                "parallel": True,
                "max_workers": 4
            },
            {
                "name": "Extended Features",
                "tests": {"tags": ["extended", "regression"]},
                "parallel": True,
                "max_workers": 6
            }
        ]
        
        for stage in stages:
            print(f"Running stage: {stage['name']}")
            
            stage_results = await self.runner.run_tests({
                "test_selection": stage["tests"],
                "execution": {
                    "parallel": stage["parallel"],
                    "max_workers": stage.get("max_workers", 1),
                    "stop_on_failure": stage.get("stop_on_failure", False)
                }
            })
            
            if stage.get("stop_on_failure") and stage_results.failed_count > 0:
                print(f"Stage {stage['name']} failed, stopping execution")
                break
        
        return stage_results
```

### Test Execution Configuration

```yaml
# test_config.yaml
test_execution:
  # Global settings
  timeout: 3600  # 1 hour
  retry_failed: true
  max_retries: 2
  parallel_execution: true
  max_workers: 5
  
  # Browser settings
  browser:
    pool_size: 10
    headless: true
    viewport:
      width: 1920
      height: 1080
    
  # Test selection
  selection:
    include_tags: ["smoke", "regression"]
    exclude_tags: ["manual", "slow"]
    priority: ["critical", "high"]
    
  # Reporting
  reporting:
    formats: ["html", "json", "junit"]
    output_dir: "test_results"
    screenshots: true
    videos: false
    detailed_logs: true
    
  # Environment
  environment:
    base_url: "https://staging.example.com"
    api_base_url: "https://api.staging.example.com"
    database_url: "postgresql://test:test@localhost/testdb"
    
  # Test data
  test_data:
    cleanup_after_run: true
    seed_data: true
    data_providers:
      - type: "csv"
        path: "test_data/"
      - type: "json"
        path: "test_data/"
      - type: "database"
        connection: "test_db"

# Suite-specific configurations
suites:
  smoke:
    timeout: 600  # 10 minutes
    parallel: false
    stop_on_failure: true
    
  regression:
    timeout: 7200  # 2 hours
    parallel: true
    max_workers: 8
    
  performance:
    timeout: 1800  # 30 minutes
    parallel: false
    browser:
      headless: true
      disable_images: true
```

## 🔗 Next Steps

- **[Test Execution Guide](test-execution.md)** - Advanced execution strategies and CI/CD integration
- **[Test Data Management](test-data-management.md)** - Managing test data and environments
- **[Test Reporting](test-reporting.md)** - Comprehensive test reporting and analysis
- **[Performance Testing](performance-testing.md)** - Load and performance testing strategies

## 📚 Additional Resources

- **[Test Framework API Reference](../developer/api-reference.md#testing-api)** - Complete API documentation
- **[Best Practices Guide](test-best-practices.md)** - Testing best practices and patterns
- **[Troubleshooting Tests](../user/troubleshooting.md#test-issues)** - Common test issues and solutions
