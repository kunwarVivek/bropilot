# Testing Best Practices and Troubleshooting Guide

## 🎯 Overview

This guide provides comprehensive best practices for creating maintainable, reliable, and efficient tests using the Browser Automation Framework. It also includes troubleshooting guidance for common issues.

## 📋 Table of Contents

- [Test Design Best Practices](#test-design-best-practices)
- [Code Organization](#code-organization)
- [Performance Optimization](#performance-optimization)
- [Reliability Patterns](#reliability-patterns)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Common Pitfalls](#common-pitfalls)
- [Maintenance Guidelines](#maintenance-guidelines)

## 🏗️ Test Design Best Practices

### 1. Follow the Test Pyramid

```python
# Good: Balanced test pyramid
tests/
├── unit/           # 70% - Fast, isolated tests
│   ├── test_utils.py
│   ├── test_validators.py
│   └── test_data_processors.py
├── integration/    # 20% - Component interaction tests
│   ├── test_api_integration.py
│   ├── test_database_operations.py
│   └── test_service_communication.py
└── e2e/           # 10% - Full workflow tests
    ├── test_user_journeys.py
    ├── test_critical_paths.py
    └── test_business_scenarios.py
```

### 2. Write Independent Tests

```python
# Good: Independent test that sets up its own data
class TestUserProfile(TestCase):
    async def test_update_profile(self):
        # Create test user for this specific test
        test_user = await self.create_test_user()
        
        # Perform test actions
        await self.login_as_user(test_user)
        await self.update_profile({"name": "Updated Name"})
        
        # Verify results
        profile = await self.get_user_profile(test_user.id)
        assert profile.name == "Updated Name"
        
        # Cleanup
        await self.cleanup_test_user(test_user)

# Bad: Test depends on external state
class TestUserProfileBad(TestCase):
    async def test_update_profile(self):
        # Assumes user with ID 123 exists - fragile!
        await self.login_as_user_id(123)
        await self.update_profile({"name": "Updated Name"})
        # No verification of actual state change
```

### 3. Use Descriptive Test Names

```python
# Good: Descriptive test names
class TestShoppingCart(TestCase):
    async def test_add_product_to_empty_cart_increases_count_by_one(self):
        pass
    
    async def test_remove_last_product_from_cart_shows_empty_cart_message(self):
        pass
    
    async def test_apply_valid_discount_code_reduces_total_price(self):
        pass

# Bad: Vague test names
class TestShoppingCartBad(TestCase):
    async def test_cart(self):
        pass
    
    async def test_products(self):
        pass
    
    async def test_discount(self):
        pass
```

### 4. Implement Proper Wait Strategies

```python
# Good: Explicit waits with meaningful conditions
class TestDynamicContent(TestCase):
    async def test_load_dynamic_content(self):
        await self.page.goto("https://example.com/dynamic")
        
        # Wait for specific content to load
        await self.page.wait_for_selector(
            ".content-loaded",
            state="visible",
            timeout=10000
        )
        
        # Wait for network to be idle
        await self.page.wait_for_load_state("networkidle")
        
        # Wait for custom condition
        await self.page.wait_for_function(
            "document.querySelectorAll('.item').length >= 5"
        )

# Bad: Hard-coded sleeps
class TestDynamicContentBad(TestCase):
    async def test_load_dynamic_content(self):
        await self.page.goto("https://example.com/dynamic")
        
        # Bad: Arbitrary wait time
        await asyncio.sleep(5)
        
        # May fail if content takes longer to load
        content = await self.page.text_content(".content")
```

## 📁 Code Organization

### 1. Organize Tests by Feature

```python
# Good: Feature-based organization
tests/
├── authentication/
│   ├── __init__.py
│   ├── test_login.py
│   ├── test_registration.py
│   ├── test_password_reset.py
│   └── fixtures/
│       ├── user_fixtures.py
│       └── auth_data.py
├── shopping_cart/
│   ├── __init__.py
│   ├── test_add_items.py
│   ├── test_remove_items.py
│   ├── test_checkout.py
│   └── fixtures/
│       ├── product_fixtures.py
│       └── cart_data.py
└── shared/
    ├── __init__.py
    ├── base_test.py
    ├── common_fixtures.py
    └── test_utilities.py
```

### 2. Create Reusable Components

```python
# shared/page_objects.py
class LoginPage:
    """Page object for login functionality."""
    
    def __init__(self, page):
        self.page = page
        self.email_input = "#email"
        self.password_input = "#password"
        self.login_button = "button[type='submit']"
        self.error_message = ".error-message"
    
    async def login(self, email: str, password: str):
        """Perform login with given credentials."""
        await self.page.fill(self.email_input, email)
        await self.page.fill(self.password_input, password)
        await self.page.click(self.login_button)
    
    async def get_error_message(self) -> str:
        """Get error message text."""
        await self.page.wait_for_selector(self.error_message)
        return await self.page.text_content(self.error_message)

# shared/test_utilities.py
class TestDataManager:
    """Utility for managing test data."""
    
    @staticmethod
    async def create_test_user(**overrides):
        """Create a test user with optional overrides."""
        default_user = {
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
            "name": "Test User"
        }
        default_user.update(overrides)
        return default_user
    
    @staticmethod
    async def cleanup_test_data(test_id: str):
        """Clean up test data by test ID."""
        # Implementation for cleaning up test data
        pass
```

### 3. Use Configuration Management

```python
# config/test_config.py
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class TestEnvironmentConfig:
    """Test environment configuration."""
    base_url: str
    database_url: str
    api_key: str
    browser_config: Dict[str, Any]
    timeout_config: Dict[str, int]
    
    @classmethod
    def from_environment(cls, env: str):
        """Create config from environment name."""
        configs = {
            "development": cls(
                base_url="http://localhost:3000",
                database_url="postgresql://localhost/test_dev",
                api_key="dev_api_key",
                browser_config={"headless": False},
                timeout_config={"default": 30000, "long": 60000}
            ),
            "staging": cls(
                base_url="https://staging.example.com",
                database_url="postgresql://staging-db/test",
                api_key="staging_api_key",
                browser_config={"headless": True},
                timeout_config={"default": 30000, "long": 120000}
            ),
            "production": cls(
                base_url="https://example.com",
                database_url="postgresql://prod-db/test",
                api_key="prod_api_key",
                browser_config={"headless": True},
                timeout_config={"default": 60000, "long": 300000}
            )
        }
        return configs[env]

# Usage in tests
class TestWithConfig(TestCase):
    def __init__(self):
        super().__init__()
        self.config = TestEnvironmentConfig.from_environment(
            os.getenv("TEST_ENV", "development")
        )
    
    async def setup(self):
        await self.page.goto(self.config.base_url)
```

## ⚡ Performance Optimization

### 1. Optimize Browser Usage

```python
# Good: Reuse browser contexts
class OptimizedTestSuite(TestSuite):
    async def setup_suite(self):
        """Setup shared browser context."""
        self.browser = await playwright.chromium.launch()
        self.context = await self.browser.new_context()
    
    async def teardown_suite(self):
        """Cleanup browser resources."""
        await self.context.close()
        await self.browser.close()

class TestWithSharedContext(TestCase):
    async def setup(self):
        # Reuse context, create new page
        self.page = await self.suite.context.new_page()
    
    async def teardown(self):
        # Close page, keep context
        await self.page.close()

# Bad: Create new browser for each test
class UnoptimizedTest(TestCase):
    async def setup(self):
        # Expensive: New browser for each test
        self.browser = await playwright.chromium.launch()
        self.page = await self.browser.new_page()
    
    async def teardown(self):
        await self.browser.close()
```

### 2. Implement Smart Waiting

```python
# Good: Smart waiting strategies
class SmartWaitingTest(TestCase):
    async def wait_for_element_with_retry(self, selector: str, max_attempts: int = 3):
        """Wait for element with intelligent retry."""
        for attempt in range(max_attempts):
            try:
                await self.page.wait_for_selector(selector, timeout=5000)
                return True
            except TimeoutError:
                if attempt < max_attempts - 1:
                    # Refresh page and retry
                    await self.page.reload()
                    await self.page.wait_for_load_state("networkidle")
                else:
                    raise
    
    async def wait_for_stable_element(self, selector: str):
        """Wait for element to be stable (not moving)."""
        element = await self.page.wait_for_selector(selector)
        
        # Wait for element to stop moving
        previous_box = None
        stable_count = 0
        
        while stable_count < 3:
            current_box = await element.bounding_box()
            if previous_box and current_box == previous_box:
                stable_count += 1
            else:
                stable_count = 0
            previous_box = current_box
            await asyncio.sleep(0.1)
```

### 3. Optimize Test Data

```python
# Good: Efficient test data management
class EfficientDataTest(TestCase):
    @classmethod
    async def setup_class(cls):
        """Setup shared test data once per class."""
        cls.shared_test_data = await cls.create_bulk_test_data()
    
    async def setup(self):
        """Get isolated subset of shared data."""
        self.test_user = self.shared_test_data.get_unused_user()
        self.test_products = self.shared_test_data.get_product_subset(5)
    
    async def teardown(self):
        """Mark data as available for reuse."""
        self.shared_test_data.release_user(self.test_user)

# Bad: Create data for each test
class InefficientDataTest(TestCase):
    async def setup(self):
        # Expensive: Create new data for each test
        self.test_user = await self.create_test_user()
        self.test_products = await self.create_test_products(10)
    
    async def teardown(self):
        await self.delete_test_user(self.test_user)
        await self.delete_test_products(self.test_products)
```

## 🛡️ Reliability Patterns

### 1. Implement Retry Logic

```python
# Good: Intelligent retry with exponential backoff
class ReliableTest(TestCase):
    async def retry_with_backoff(self, operation, max_retries=3, base_delay=1):
        """Retry operation with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await operation()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                
                delay = base_delay * (2 ** attempt)
                self.logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay}s: {e}")
                await asyncio.sleep(delay)
    
    async def test_with_retry(self):
        """Test with automatic retry on failure."""
        async def flaky_operation():
            await self.page.goto("https://example.com")
            await self.page.wait_for_selector(".content", timeout=5000)
            return await self.page.text_content(".content")
        
        content = await self.retry_with_backoff(flaky_operation)
        assert content is not None
```

### 2. Handle Dynamic Content

```python
# Good: Robust handling of dynamic content
class DynamicContentTest(TestCase):
    async def wait_for_dynamic_content(self, selector: str, expected_count: int):
        """Wait for dynamic content to reach expected state."""
        async def check_content():
            elements = await self.page.query_selector_all(selector)
            return len(elements) >= expected_count
        
        # Wait up to 30 seconds for content to load
        for _ in range(30):
            if await check_content():
                return True
            await asyncio.sleep(1)
        
        raise TimeoutError(f"Dynamic content did not reach expected state")
    
    async def test_dynamic_list(self):
        """Test dynamic list loading."""
        await self.page.goto("https://example.com/dynamic-list")
        
        # Wait for at least 5 items to load
        await self.wait_for_dynamic_content(".list-item", 5)
        
        # Verify content
        items = await self.page.query_selector_all(".list-item")
        assert len(items) >= 5
```

## 🔧 Troubleshooting Guide

### Common Issues and Solutions

#### 1. Element Not Found Errors

```python
# Problem: Element not found
# await self.page.click(".button")  # Fails if element doesn't exist

# Solution: Add proper waits and error handling
async def safe_click(self, selector: str, timeout: int = 30000):
    """Safely click element with proper error handling."""
    try:
        # Wait for element to be visible and enabled
        await self.page.wait_for_selector(
            selector, 
            state="visible", 
            timeout=timeout
        )
        
        # Ensure element is clickable
        element = await self.page.query_selector(selector)
        if not element:
            raise Exception(f"Element {selector} not found")
        
        # Check if element is enabled
        is_enabled = await element.is_enabled()
        if not is_enabled:
            raise Exception(f"Element {selector} is disabled")
        
        await element.click()
        
    except TimeoutError:
        # Capture screenshot for debugging
        await self.page.screenshot(path=f"debug_element_not_found_{int(time.time())}.png")
        
        # Get page content for analysis
        content = await self.page.content()
        self.logger.error(f"Element {selector} not found. Page content: {content[:500]}...")
        
        raise Exception(f"Element {selector} not found within {timeout}ms")
```

#### 2. Timing Issues

```python
# Problem: Race conditions and timing issues
# Solution: Use proper synchronization

class TimingIssuesSolution(TestCase):
    async def wait_for_ajax_complete(self):
        """Wait for all AJAX requests to complete."""
        await self.page.wait_for_function(
            "window.jQuery && jQuery.active === 0",
            timeout=30000
        )
    
    async def wait_for_page_ready(self):
        """Wait for page to be fully ready."""
        # Wait for DOM to be ready
        await self.page.wait_for_load_state("domcontentloaded")
        
        # Wait for all resources to load
        await self.page.wait_for_load_state("networkidle")
        
        # Wait for custom ready state
        await self.page.wait_for_function(
            "document.readyState === 'complete'"
        )
    
    async def test_with_proper_timing(self):
        """Test with proper timing controls."""
        await self.page.goto("https://example.com")
        await self.wait_for_page_ready()
        
        # Trigger AJAX request
        await self.page.click(".load-data-button")
        await self.wait_for_ajax_complete()
        
        # Now safe to interact with loaded content
        await self.page.wait_for_selector(".loaded-content")
```

#### 3. Memory Leaks

```python
# Problem: Memory leaks from unclosed resources
# Solution: Proper resource management

class ResourceManagementTest(TestCase):
    def __init__(self):
        super().__init__()
        self.resources = []  # Track resources for cleanup
    
    async def create_page(self):
        """Create page with proper tracking."""
        page = await self.browser.new_page()
        self.resources.append(page)
        return page
    
    async def teardown(self):
        """Ensure all resources are cleaned up."""
        for resource in self.resources:
            try:
                if hasattr(resource, 'close'):
                    await resource.close()
            except Exception as e:
                self.logger.warning(f"Error closing resource: {e}")
        
        self.resources.clear()
        await super().teardown()
```
