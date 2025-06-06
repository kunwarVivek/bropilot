# Test Case Creation Guide

## 🧪 Overview

This comprehensive guide covers everything you need to know about creating test cases using the Browser Automation Framework's testing system. From basic test cases to advanced AI-powered scenarios, this guide will help you build robust, maintainable test suites.

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Test Case Fundamentals](#test-case-fundamentals)
- [Creating Basic Test Cases](#creating-basic-test-cases)
- [Advanced Test Cases](#advanced-test-cases)
- [Test Data Management](#test-data-management)
- [Test Organization](#test-organization)
- [Best Practices](#best-practices)

## ⚡ Quick Start

### 1. Create Your First Test Case

```python
# tests/test_my_first_test.py
import pytest
from src.testing.test_framework import TestCase
from src.testing.assertions import WebAssertions
from src.testing.fixtures import browser_fixture

class TestMyFirstTest(TestCase):
    """My first test case using the framework."""
    
    def __init__(self):
        super().__init__(
            name="My First Test",
            description="A simple test to verify basic functionality",
            tags=["basic", "smoke"],
            priority="high"
        )
    
    @pytest.fixture(autouse=True)
    async def setup(self, browser_fixture):
        """Setup test environment."""
        self.browser = browser_fixture
        self.page = await self.browser.new_page()
        self.assertions = WebAssertions(self.page)
        
    async def test_page_loads(self):
        """Test that a page loads successfully."""
        await self.page.goto("https://example.com")
        await self.assertions.assert_title_contains("Example")
        await self.assertions.assert_element_visible("h1")
```

### 2. Run Your Test

```bash
# Run your specific test
pytest tests/test_my_first_test.py -v

# Run with the framework's test runner
python -m src.testing.runner --file tests/test_my_first_test.py
```

## 🏗️ Test Case Fundamentals

### Test Case Structure

Every test case in the framework follows this structure:

```python
from src.testing.test_framework import TestCase

class TestMyFeature(TestCase):
    """Test case for my feature."""
    
    def __init__(self):
        super().__init__(
            name="Feature Test Suite",
            description="Tests for my specific feature",
            tags=["feature", "regression"],
            priority="medium",
            timeout=300,  # 5 minutes
            retry_count=2,
            parallel_safe=True
        )
    
    # Setup and teardown methods
    async def setup(self):
        """Setup before each test method."""
        pass
    
    async def teardown(self):
        """Cleanup after each test method."""
        pass
    
    async def setup_class(self):
        """Setup before all test methods in this class."""
        pass
    
    async def teardown_class(self):
        """Cleanup after all test methods in this class."""
        pass
    
    # Test methods
    async def test_feature_functionality(self):
        """Test the main functionality."""
        pass
    
    async def test_feature_edge_cases(self):
        """Test edge cases and error conditions."""
        pass
```

### Test Case Configuration

```python
class TestAdvancedConfiguration(TestCase):
    """Example of advanced test configuration."""
    
    def __init__(self):
        super().__init__(
            name="Advanced Configuration Test",
            description="Demonstrates advanced configuration options",
            
            # Basic metadata
            tags=["advanced", "configuration", "regression"],
            priority="high",  # high, medium, low, critical
            
            # Execution settings
            timeout=600,  # Test timeout in seconds
            retry_count=3,  # Number of retries on failure
            retry_delay=5,  # Delay between retries in seconds
            parallel_safe=True,  # Can run in parallel with other tests
            
            # Environment requirements
            required_env_vars=["API_KEY", "TEST_DATABASE_URL"],
            required_services=["database", "redis", "api_server"],
            
            # Browser requirements
            browser_requirements={
                "headless": False,
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "custom-test-agent",
                "disable_images": True,
                "disable_javascript": False
            },
            
            # Data requirements
            test_data_requirements={
                "users": 5,
                "products": 10,
                "orders": 20
            },
            
            # Reporting settings
            capture_screenshots=True,
            capture_network_logs=True,
            capture_console_logs=True,
            
            # Dependencies
            depends_on=["TestUserAuthentication.test_login"],
            blocks=["TestUserDeletion.*"]  # This test blocks user deletion tests
        )
```

## 🧪 Creating Basic Test Cases

### Simple Navigation Test

```python
# tests/test_navigation.py
from src.testing.test_framework import TestCase
from src.testing.assertions import WebAssertions
from src.testing.fixtures import browser_fixture

class TestNavigation(TestCase):
    """Basic navigation test cases."""
    
    def __init__(self):
        super().__init__(
            name="Navigation Tests",
            description="Test basic website navigation",
            tags=["navigation", "smoke"],
            priority="high"
        )
    
    @pytest.fixture(autouse=True)
    async def setup(self, browser_fixture):
        """Setup test environment."""
        self.browser = browser_fixture
        self.page = await self.browser.new_page()
        self.assertions = WebAssertions(self.page)
        
        # Configure page settings
        await self.page.set_viewport_size({"width": 1920, "height": 1080})
        await self.page.set_extra_http_headers({"User-Agent": "Test-Agent"})
        
    async def teardown(self):
        """Cleanup after each test."""
        if hasattr(self, 'page'):
            await self.page.close()
    
    async def test_homepage_loads(self):
        """Test that homepage loads correctly."""
        await self.page.goto("https://example.com")
        
        # Verify page loaded
        await self.assertions.assert_title_equals("Example Domain")
        await self.assertions.assert_url_contains("example.com")
        await self.assertions.assert_element_visible("h1")
        
        # Verify content
        heading_text = await self.page.text_content("h1")
        assert "Example Domain" in heading_text
        
        # Capture evidence
        await self.capture_screenshot("homepage_loaded")
    
    async def test_navigation_menu(self):
        """Test navigation menu functionality."""
        await self.page.goto("https://example.com")
        
        # Check if navigation menu exists
        await self.assertions.assert_element_visible("nav")
        
        # Get all navigation links
        nav_links = await self.page.query_selector_all("nav a")
        assert len(nav_links) > 0, "No navigation links found"
        
        # Test each navigation link
        for link in nav_links:
            href = await link.get_attribute("href")
            text = await link.text_content()
            
            if href and not href.startswith("#"):
                # Click the link
                await link.click()
                
                # Wait for navigation
                await self.page.wait_for_load_state("networkidle")
                
                # Verify navigation worked
                current_url = self.page.url
                assert href in current_url, f"Navigation to {href} failed"
                
                # Go back for next iteration
                await self.page.go_back()
                await self.page.wait_for_load_state("networkidle")
```

### Form Testing

```python
# tests/test_forms.py
from src.testing.test_framework import TestCase
from src.testing.assertions import WebAssertions
from src.testing.data_generators import UserDataGenerator

class TestForms(TestCase):
    """Form interaction test cases."""
    
    def __init__(self):
        super().__init__(
            name="Form Tests",
            description="Test form interactions and submissions",
            tags=["forms", "interaction"],
            priority="high"
        )
    
    @pytest.fixture(autouse=True)
    async def setup(self, browser_fixture):
        """Setup test environment."""
        self.browser = browser_fixture
        self.page = await self.browser.new_page()
        self.assertions = WebAssertions(self.page)
        self.user_generator = UserDataGenerator()
        
    async def test_contact_form_submission(self):
        """Test contact form submission."""
        await self.page.goto("https://example.com/contact")
        
        # Generate test data
        user_data = self.user_generator.generate_user()
        
        # Fill out the form
        await self.page.fill("#name", user_data["name"])
        await self.page.fill("#email", user_data["email"])
        await self.page.fill("#subject", "Test Subject")
        await self.page.fill("#message", "This is a test message")
        
        # Submit the form
        await self.page.click("button[type='submit']")
        
        # Wait for response
        await self.page.wait_for_selector(".success-message", timeout=10000)
        
        # Verify success
        await self.assertions.assert_element_visible(".success-message")
        success_text = await self.page.text_content(".success-message")
        assert "thank you" in success_text.lower()
        
        # Capture evidence
        await self.capture_screenshot("form_submitted")
    
    @pytest.mark.parametrize("field,value,expected_error", [
        ("email", "invalid-email", "Please enter a valid email"),
        ("name", "", "Name is required"),
        ("message", "", "Message is required")
    ])
    async def test_form_validation(self, field, value, expected_error):
        """Test form validation errors."""
        await self.page.goto("https://example.com/contact")
        
        # Fill form with invalid data
        if field == "email":
            await self.page.fill("#email", value)
        elif field == "name":
            await self.page.fill("#name", value)
        elif field == "message":
            await self.page.fill("#message", value)
        
        # Submit form
        await self.page.click("button[type='submit']")
        
        # Check for validation error
        await self.page.wait_for_selector(".error-message", timeout=5000)
        error_text = await self.page.text_content(".error-message")
        assert expected_error.lower() in error_text.lower()

## 🚀 Advanced Test Cases

### AI-Powered Test Cases

```python
# tests/test_ai_powered.py
from src.testing.test_framework import AITestCase
from src.testing.ai_helpers import AIFormFiller, AIContentValidator, AIElementFinder

class TestAIPowered(AITestCase):
    """AI-powered test cases that adapt to page changes."""

    def __init__(self):
        super().__init__(
            name="AI-Powered Tests",
            description="Tests that use AI to adapt to page changes",
            tags=["ai", "adaptive", "intelligent"],
            priority="medium",
            ai_config={
                "llm_provider": "openai",
                "model": "gpt-4-vision-preview",
                "enable_vision": True,
                "enable_self_healing": True,
                "confidence_threshold": 0.8
            }
        )

    async def test_adaptive_form_filling(self):
        """Test that adapts to form structure changes."""
        await self.page.goto("https://example.com/dynamic-form")

        # Use AI to understand the form structure
        form_analyzer = AIFormFiller(self.page, self.ai_provider)

        # Define the data we want to fill
        form_data = {
            "user_name": "John Doe",
            "email_address": "john@example.com",
            "phone_number": "+1234567890",
            "message": "This is a test message"
        }

        # Let AI figure out how to fill the form
        success = await form_analyzer.fill_form_intelligently(form_data)
        assert success, "AI failed to fill the form"

        # Submit and verify
        await form_analyzer.submit_form()

        # Use AI to verify success
        validator = AIContentValidator(self.page, self.ai_provider)
        success_detected = await validator.verify_success_state(
            expected_outcome="form submission successful"
        )
        assert success_detected, "Form submission success not detected"

    async def test_intelligent_element_interaction(self):
        """Test that finds and interacts with elements intelligently."""
        await self.page.goto("https://example.com/complex-page")

        # Use AI to find elements by description
        element_finder = AIElementFinder(self.page, self.ai_provider)

        # Find the "Add to Cart" button even if its selector changes
        add_to_cart_button = await element_finder.find_element_by_description(
            "button that adds the product to shopping cart"
        )
        assert add_to_cart_button, "Could not find add to cart button"

        # Click the button
        await add_to_cart_button.click()

        # Verify the action worked using AI
        validator = AIContentValidator(self.page, self.ai_provider)
        cart_updated = await validator.verify_state_change(
            description="product was added to shopping cart",
            timeout=10000
        )
        assert cart_updated, "Product was not added to cart"
```

### Performance Test Cases

```python
# tests/test_performance.py
from src.testing.test_framework import PerformanceTestCase
from src.testing.performance import PerformanceMonitor, LoadGenerator

class TestPerformance(PerformanceTestCase):
    """Performance and load testing."""

    def __init__(self):
        super().__init__(
            name="Performance Tests",
            description="Test application performance under various loads",
            tags=["performance", "load", "stress"],
            priority="medium",
            performance_config={
                "max_response_time": 2000,  # 2 seconds
                "max_memory_usage": 512,    # 512 MB
                "min_throughput": 100,      # 100 requests/second
                "error_rate_threshold": 0.01  # 1% error rate
            }
        )

    async def test_page_load_performance(self):
        """Test page load performance."""
        monitor = PerformanceMonitor(self.page)

        # Start monitoring
        await monitor.start_monitoring()

        # Load the page
        await self.page.goto("https://example.com")
        await self.page.wait_for_load_state("networkidle")

        # Stop monitoring and get metrics
        metrics = await monitor.stop_monitoring()

        # Assert performance requirements
        assert metrics.page_load_time < 2000, f"Page load too slow: {metrics.page_load_time}ms"
        assert metrics.first_contentful_paint < 1000, f"FCP too slow: {metrics.first_contentful_paint}ms"
        assert metrics.largest_contentful_paint < 2500, f"LCP too slow: {metrics.largest_contentful_paint}ms"

        # Check resource loading
        assert len(metrics.failed_requests) == 0, f"Failed requests: {metrics.failed_requests}"

        # Log performance data
        await self.log_performance_metrics(metrics)

    async def test_concurrent_user_simulation(self):
        """Test with multiple concurrent users."""
        load_generator = LoadGenerator(
            target_url="https://example.com",
            concurrent_users=10,
            test_duration=60,  # 60 seconds
            ramp_up_time=10    # 10 seconds to reach full load
        )

        # Define user scenarios
        async def user_scenario(user_id: int):
            """Define what each user does."""
            page = await self.browser.new_page()
            try:
                # Navigate to homepage
                await page.goto("https://example.com")
                await page.wait_for_load_state("networkidle")

                # Browse products
                await page.click("a[href*='products']")
                await page.wait_for_load_state("networkidle")

                # View product details
                product_links = await page.query_selector_all(".product-link")
                if product_links:
                    await product_links[0].click()
                    await page.wait_for_load_state("networkidle")

                return {"success": True, "user_id": user_id}
            except Exception as e:
                return {"success": False, "user_id": user_id, "error": str(e)}
            finally:
                await page.close()

        # Run load test
        results = await load_generator.run_load_test(user_scenario)

        # Analyze results
        success_rate = sum(1 for r in results if r["success"]) / len(results)
        assert success_rate >= 0.95, f"Success rate too low: {success_rate:.2%}"

        # Check response times
        response_times = [r.get("response_time", 0) for r in results if r["success"]]
        avg_response_time = sum(response_times) / len(response_times)
        assert avg_response_time < 2000, f"Average response time too high: {avg_response_time}ms"
```
```
