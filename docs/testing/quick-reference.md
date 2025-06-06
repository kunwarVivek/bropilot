# Testing Framework Quick Reference

## 🚀 Quick Commands

### Basic Test Execution
```bash
# Run single test file
python -m src.testing.runner --file tests/test_example.py

# Run test suite
python -m src.testing.runner --suite smoke

# Run with tags
python -m src.testing.runner --tags "critical,regression"

# Run with parallel execution
python -m src.testing.runner --suite regression --parallel --workers 4
```

### Advanced Execution
```bash
# AI-powered testing with self-healing
python -m src.testing.runner --enable-ai --auto-heal-failures

# Performance testing with monitoring
python -m src.testing.runner --suite performance --capture-metrics

# Cross-browser testing
python -m src.testing.runner --browsers chromium,firefox,webkit

# Environment-specific testing
python -m src.testing.runner --environment staging --suite smoke
```

## 🧪 Test Case Templates

### Basic Test Case
```python
from src.testing.test_framework import TestCase

class TestExample(TestCase):
    def __init__(self):
        super().__init__(
            name="Example Test",
            description="Basic test example",
            tags=["basic", "smoke"],
            priority="high"
        )
    
    async def test_functionality(self):
        await self.page.goto("https://example.com")
        assert await self.page.is_visible("h1")
```

### AI-Powered Test Case
```python
from src.testing.test_framework import AITestCase

class TestAIExample(AITestCase):
    def __init__(self):
        super().__init__(
            name="AI Test Example",
            ai_config={
                "llm_provider": "openai",
                "enable_self_healing": True,
                "enable_vision": True
            }
        )
    
    async def test_adaptive_interaction(self):
        # AI adapts to UI changes automatically
        await self.ai_interact_with_form({
            "name": "John Doe",
            "email": "john@example.com"
        })
```

### Performance Test Case
```python
from src.testing.test_framework import PerformanceTestCase

class TestPerformanceExample(PerformanceTestCase):
    def __init__(self):
        super().__init__(
            performance_config={
                "max_response_time": 2000,
                "max_memory_usage": 512
            }
        )
    
    async def test_page_performance(self):
        await self.execute_with_performance_monitoring(
            self.load_page_and_measure
        )
```

### Chained Test Case
```python
from src.testing.test_framework import ChainedTestCase

class TestWorkflowExample(ChainedTestCase):
    def __init__(self):
        super().__init__()
        self.test_chain = [
            self.test_step_1,
            self.test_step_2,
            self.test_step_3
        ]
        self.shared_state = {}
    
    async def test_step_1(self):
        # First step
        self.shared_state["data"] = "value"
    
    async def test_step_2(self):
        # Uses data from step 1
        data = self.shared_state["data"]
```

## 🏗️ Test Suite Templates

### Basic Test Suite
```python
from src.testing.test_framework import TestSuite

class ExampleTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="Example Suite",
            description="Example test suite",
            tags=["example"],
            execution_mode="parallel",
            max_workers=4
        )
        
        self.add_test_case(TestExample())
        self.add_test_case(TestAnotherExample())
```

### Suite with Dependencies
```python
class DependentTestSuite(TestSuite):
    def __init__(self):
        super().__init__(
            name="Dependent Suite",
            execution_mode="sequential"
        )
        
        self.add_test_case(TestSetup())
        self.add_test_case(TestMain())
        
        # Define dependency
        self.add_dependency(
            "TestSetup.test_initialize",
            "TestMain.test_functionality"
        )
```

## 🔧 Configuration Examples

### Environment Configuration
```python
# config/test_config.py
from src.testing.config import TestConfig

config = TestConfig(
    default_timeout=30000,
    retry_count=2,
    parallel_workers=4,
    browser_pool_size=10,
    headless=True,
    capture_screenshots=True
)
```

### Browser Configuration
```python
browser_config = {
    "headless": True,
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": "Test-Agent",
    "disable_images": True,
    "disable_javascript": False
}
```

## 📊 Common Patterns

### Page Object Pattern
```python
class LoginPage:
    def __init__(self, page):
        self.page = page
        self.email_input = "#email"
        self.password_input = "#password"
        self.login_button = "button[type='submit']"
    
    async def login(self, email, password):
        await self.page.fill(self.email_input, email)
        await self.page.fill(self.password_input, password)
        await self.page.click(self.login_button)
```

### Data Factory Pattern
```python
class UserFactory:
    @staticmethod
    def create_user(**overrides):
        default = {
            "email": f"test_{uuid.uuid4()}@example.com",
            "password": "TestPassword123!",
            "name": "Test User"
        }
        default.update(overrides)
        return default
```

### Assertion Helpers
```python
from src.testing.assertions import WebAssertions

class TestWithAssertions(TestCase):
    async def setup(self):
        self.assertions = WebAssertions(self.page)
    
    async def test_with_assertions(self):
        await self.assertions.assert_title_contains("Example")
        await self.assertions.assert_element_visible("h1")
        await self.assertions.assert_text_equals(".message", "Success")
```

## 🔍 Debugging Helpers

### Screenshot Capture
```python
async def test_with_screenshots(self):
    await self.page.goto("https://example.com")
    await self.capture_screenshot("page_loaded")
    
    # Perform actions
    await self.page.click(".button")
    await self.capture_screenshot("after_click")
```

### Console Log Capture
```python
async def test_with_console_logs(self):
    # Enable console log capture
    self.page.on("console", lambda msg: print(f"Console: {msg.text}"))
    
    await self.page.goto("https://example.com")
    # Console logs will be captured automatically
```

### Network Monitoring
```python
async def test_with_network_monitoring(self):
    # Monitor network requests
    requests = []
    self.page.on("request", lambda req: requests.append(req.url))
    
    await self.page.goto("https://example.com")
    
    # Analyze requests
    api_requests = [r for r in requests if "/api/" in r]
    assert len(api_requests) > 0
```

## ⚡ Performance Optimization

### Browser Reuse
```python
class OptimizedTestSuite(TestSuite):
    async def setup_suite(self):
        self.browser = await playwright.chromium.launch()
        self.context = await self.browser.new_context()
    
    async def teardown_suite(self):
        await self.context.close()
        await self.browser.close()
```

### Parallel Execution
```python
# Run tests in parallel
python -m src.testing.runner \
    --suite regression \
    --parallel \
    --workers 8 \
    --load-balancing
```

### Resource Pooling
```python
# Enable resource pooling
python -m src.testing.runner \
    --suite regression \
    --resource-pooling \
    --browser-pool-size 10
```

## 🚨 Error Handling

### Retry Logic
```python
async def retry_operation(self, operation, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await operation()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            await asyncio.sleep(2 ** attempt)
```

### Graceful Failure
```python
async def test_with_graceful_failure(self):
    try:
        await self.page.goto("https://example.com")
        await self.page.wait_for_selector(".content", timeout=5000)
    except TimeoutError:
        # Capture debug information
        await self.capture_screenshot("timeout_error")
        content = await self.page.content()
        self.logger.error(f"Page content: {content[:500]}")
        raise
```

## 📈 Reporting

### Custom Metrics
```python
from src.testing.analytics import MetricsCollector

async def test_with_metrics(self):
    metrics = MetricsCollector()
    
    metrics.start_timer("operation_time")
    await self.perform_operation()
    metrics.end_timer("operation_time")
    
    metrics.record_metric("success_rate", 0.95)
```

### Report Generation
```bash
# Generate HTML report
python -m src.testing.runner \
    --suite regression \
    --report-format html \
    --output-dir results/

# Generate multiple formats
python -m src.testing.runner \
    --suite regression \
    --report-format html,junit,json
```

## 🔗 Useful Links

- [Complete Testing Workflow](complete-testing-workflow.md)
- [Test Case Creation Guide](test-case-creation-guide.md)
- [Test Execution Guide](test-execution-guide.md)
- [Test Suite Chaining Guide](test-suite-chaining-guide.md)
- [Framework Implementation Guide](framework-implementation-guide.md)
- [Testing Best Practices](testing-best-practices.md)
