# Complete Testing Workflow Guide

## 🎯 Overview

This guide provides a comprehensive workflow for using the Browser Automation Framework's testing system, from initial setup to advanced test orchestration. It covers the complete testing lifecycle and best practices for different scenarios.

## 📋 Table of Contents

- [Getting Started](#getting-started)
- [Basic Testing Workflow](#basic-testing-workflow)
- [Advanced Testing Scenarios](#advanced-testing-scenarios)
- [Production Testing Workflow](#production-testing-workflow)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

## 🚀 Getting Started

### 1. Environment Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Setup test environment
cp .env.example .env.test
# Edit .env.test with your configuration

# Initialize test database
python -m src.testing.setup --init-database

# Verify setup
python -m src.testing.setup --verify
```

### 2. Create Your First Test

```python
# tests/my_first_test.py
import pytest
from src.testing.test_framework import TestCase
from src.testing.fixtures import browser_fixture

class TestMyFirstFeature(TestCase):
    """My first test using the framework."""
    
    def __init__(self):
        super().__init__(
            name="My First Test",
            description="Testing basic functionality",
            tags=["basic", "smoke"],
            priority="high"
        )
    
    @pytest.fixture(autouse=True)
    async def setup(self, browser_fixture):
        self.browser = browser_fixture
        self.page = await self.browser.new_page()
        
    async def test_homepage_loads(self):
        """Test that homepage loads correctly."""
        await self.page.goto("https://example.com")
        title = await self.page.title()
        assert "Example" in title
        
        # Capture evidence
        await self.capture_screenshot("homepage_loaded")
```

### 3. Run Your First Test

```bash
# Run the test
python -m src.testing.runner --file tests/my_first_test.py

# Run with verbose output
python -m src.testing.runner --file tests/my_first_test.py --verbose

# Run with HTML report
python -m src.testing.runner \
    --file tests/my_first_test.py \
    --report-format html \
    --output-dir results/
```

## 🔄 Basic Testing Workflow

### Step 1: Plan Your Tests

```python
# tests/test_plan.py
"""
Test Plan for E-commerce Application

1. User Authentication
   - Registration
   - Login/Logout
   - Password reset

2. Product Catalog
   - Browse products
   - Search functionality
   - Product details

3. Shopping Cart
   - Add/remove items
   - Update quantities
   - Checkout process

4. Order Management
   - Order placement
   - Order tracking
   - Order history
"""

# Create test structure
tests/
├── authentication/
│   ├── test_registration.py
│   ├── test_login.py
│   └── test_password_reset.py
├── catalog/
│   ├── test_product_browse.py
│   ├── test_search.py
│   └── test_product_details.py
├── cart/
│   ├── test_cart_operations.py
│   └── test_checkout.py
└── orders/
    ├── test_order_placement.py
    └── test_order_tracking.py
```

### Step 2: Create Test Cases

```python
# tests/authentication/test_login.py
from src.testing.test_framework import TestCase
from src.testing.data_generators import UserDataGenerator

class TestUserLogin(TestCase):
    """User login functionality tests."""
    
    def __init__(self):
        super().__init__(
            name="User Login Tests",
            description="Test user authentication functionality",
            tags=["authentication", "critical"],
            priority="high"
        )
    
    async def setup(self):
        """Setup test data and environment."""
        self.user_generator = UserDataGenerator()
        self.test_user = self.user_generator.generate_user()
        
        # Pre-register user for login tests
        await self._register_test_user()
    
    async def test_valid_login(self):
        """Test login with valid credentials."""
        await self.page.goto("https://example.com/login")
        
        # Fill login form
        await self.page.fill("#email", self.test_user["email"])
        await self.page.fill("#password", self.test_user["password"])
        await self.page.click("button[type='submit']")
        
        # Verify successful login
        await self.page.wait_for_selector(".dashboard")
        assert await self.page.is_visible(".user-menu")
        
        # Capture evidence
        await self.capture_screenshot("successful_login")
    
    async def test_invalid_credentials(self):
        """Test login with invalid credentials."""
        await self.page.goto("https://example.com/login")
        
        # Fill with invalid credentials
        await self.page.fill("#email", "invalid@example.com")
        await self.page.fill("#password", "wrongpassword")
        await self.page.click("button[type='submit']")
        
        # Verify error message
        await self.page.wait_for_selector(".error-message")
        error_text = await self.page.text_content(".error-message")
        assert "invalid credentials" in error_text.lower()
```

### Step 3: Create Test Suites

```python
# tests/suites/authentication_suite.py
from src.testing.test_framework import TestSuite
from tests.authentication.test_registration import TestUserRegistration
from tests.authentication.test_login import TestUserLogin
from tests.authentication.test_password_reset import TestPasswordReset

class AuthenticationTestSuite(TestSuite):
    """Complete authentication test suite."""
    
    def __init__(self):
        super().__init__(
            name="Authentication Test Suite",
            description="Complete user authentication testing",
            tags=["authentication", "critical"],
            execution_mode="sequential",  # Sequential for auth tests
            timeout=1800
        )
        
        # Add test cases in order
        self.add_test_case(TestUserRegistration())
        self.add_test_case(TestUserLogin())
        self.add_test_case(TestPasswordReset())
        
        # Define dependencies
        self.add_dependency(
            "TestUserRegistration.test_valid_registration",
            "TestUserLogin.test_valid_login"
        )
    
    async def setup_suite(self):
        """Setup authentication test environment."""
        # Clear any existing test users
        await self._cleanup_test_users()
        
        # Setup test database state
        await self._setup_clean_auth_state()
    
    async def teardown_suite(self):
        """Cleanup after authentication tests."""
        await self._cleanup_test_users()
```

### Step 4: Execute Tests

```bash
# Run authentication suite
python -m src.testing.runner --suite authentication

# Run with parallel execution (where safe)
python -m src.testing.runner \
    --suite authentication \
    --parallel \
    --workers 2

# Run full regression suite
python -m src.testing.runner \
    --suite regression \
    --parallel \
    --workers 4 \
    --timeout 3600 \
    --retry-failed
```

## 🎯 Advanced Testing Scenarios

### Scenario 1: Cross-Browser Testing

```python
# tests/cross_browser/test_compatibility.py
from src.testing.test_framework import TestCase
import pytest

class TestCrossBrowserCompatibility(TestCase):
    """Cross-browser compatibility tests."""
    
    def __init__(self):
        super().__init__(
            name="Cross-Browser Compatibility",
            description="Test functionality across different browsers",
            tags=["compatibility", "cross-browser"],
            priority="medium"
        )
    
    @pytest.mark.parametrize("browser_type", ["chromium", "firefox", "webkit"])
    async def test_login_across_browsers(self, browser_type):
        """Test login functionality across different browsers."""
        # Get browser-specific instance
        browser = await self.get_browser(browser_type)
        page = await browser.new_page()
        
        try:
            # Perform login test
            await page.goto("https://example.com/login")
            await page.fill("#email", "test@example.com")
            await page.fill("#password", "password123")
            await page.click("button[type='submit']")
            
            # Verify success
            await page.wait_for_selector(".dashboard")
            assert await page.is_visible(".user-menu")
            
            # Capture browser-specific screenshot
            await page.screenshot(path=f"screenshots/login_{browser_type}.png")
            
        finally:
            await page.close()
            await browser.close()

# Run cross-browser tests
python -m src.testing.runner \
    --file tests/cross_browser/test_compatibility.py \
    --browsers chromium,firefox,webkit \
    --parallel
```

### Scenario 2: Performance Testing Workflow

```python
# tests/performance/test_load_scenarios.py
from src.testing.test_framework import PerformanceTestCase
from src.testing.performance import LoadGenerator

class TestApplicationLoad(PerformanceTestCase):
    """Application load testing scenarios."""
    
    def __init__(self):
        super().__init__(
            name="Application Load Tests",
            description="Test application under various load conditions",
            tags=["performance", "load"],
            priority="medium",
            performance_config={
                "max_response_time": 2000,
                "max_memory_usage": 512,
                "min_throughput": 100
            }
        )
    
    async def test_homepage_under_load(self):
        """Test homepage performance under load."""
        load_generator = LoadGenerator(
            target_url="https://example.com",
            concurrent_users=50,
            test_duration=300,  # 5 minutes
            ramp_up_time=60     # 1 minute ramp-up
        )
        
        # Define user scenario
        async def user_scenario(user_id: int):
            page = await self.browser.new_page()
            try:
                start_time = time.time()
                await page.goto("https://example.com")
                await page.wait_for_load_state("networkidle")
                response_time = (time.time() - start_time) * 1000
                
                return {
                    "success": True,
                    "response_time": response_time,
                    "user_id": user_id
                }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "user_id": user_id
                }
            finally:
                await page.close()
        
        # Execute load test
        results = await load_generator.run_load_test(user_scenario)
        
        # Analyze results
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        avg_response_time = sum(
            r["response_time"] for r in results if r["success"]
        ) / len([r for r in results if r["success"]])
        
        # Assert performance requirements
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} below threshold"
        assert avg_response_time < 2000, f"Average response time {avg_response_time}ms too high"

# Run performance tests
python -m src.testing.runner \
    --suite performance \
    --environment staging \
    --capture-metrics \
    --report-format html,json
```

### Scenario 3: AI-Powered Testing

```python
# tests/ai_powered/test_adaptive_scenarios.py
from src.testing.test_framework import AITestCase
from src.testing.ai_helpers import AIFormFiller, AIContentValidator

class TestAIAdaptiveScenarios(AITestCase):
    """AI-powered adaptive test scenarios."""
    
    def __init__(self):
        super().__init__(
            name="AI Adaptive Tests",
            description="Tests that adapt to UI changes using AI",
            tags=["ai", "adaptive"],
            priority="medium",
            ai_config={
                "llm_provider": "openai",
                "model": "gpt-4-vision-preview",
                "enable_vision": True,
                "enable_self_healing": True
            }
        )
    
    async def test_adaptive_form_interaction(self):
        """Test that adapts to form changes using AI."""
        await self.page.goto("https://example.com/contact")
        
        # Use AI to understand and fill the form
        form_filler = AIFormFiller(self.page, self.ai_provider)
        
        form_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Test Inquiry",
            "message": "This is a test message from AI-powered testing"
        }
        
        # AI figures out how to fill the form even if structure changes
        success = await form_filler.fill_form_intelligently(form_data)
        assert success, "AI failed to fill the form"
        
        # Submit and verify using AI
        await form_filler.submit_form()
        
        validator = AIContentValidator(self.page, self.ai_provider)
        success_detected = await validator.verify_success_state(
            expected_outcome="form submission successful"
        )
        assert success_detected, "Form submission not detected as successful"

# Run AI-powered tests
python -m src.testing.runner \
    --suite ai_powered \
    --enable-ai \
    --llm-provider openai \
    --auto-heal-failures
```
