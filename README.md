# Browser Use Automation Platform

A comprehensive browser automation platform with unified execution layer, advanced cost management, and intelligent error recovery.

## 🚀 Quick Start with UV (Recommended)

This project uses [UV](https://docs.astral.sh/uv/) for fast, reliable package management and virtual environment handling.

### Prerequisites

1. **Install UV** (if not already installed):
   ```bash
   # macOS/Linux
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Windows (PowerShell)
   irm https://astral.sh/uv/install.ps1 | iex

   # Alternative: Homebrew
   brew install uv
   ```

2. **Verify installation**:
   ```bash
   uv --version
   ```

### Automated Setup

#### Unix/macOS
```bash
git clone <repository-url>
cd browser-use-automation
./scripts/setup-uv.sh
```

#### Windows
```cmd
git clone <repository-url>
cd browser-use-automation
scripts\setup-uv.bat
```

### Manual Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd browser-use-automation
   ```

2. **Install dependencies**:
   ```bash
   uv sync
   ```

3. **Install Playwright browsers**:
   ```bash
   uv run playwright install
   ```

4. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. **Verify installation**:
   ```bash
   uv run python -c "from utils.task_runner import get_execution_status; print(get_execution_status())"
   ```

## 🏗️ Architecture Overview

This platform features a modern, consolidated architecture:

- **Unified Execution Layer**: Single execution path (no legacy dual paths)
- **Provider-Agnostic LLM Interface**: Support for OpenAI, Anthropic, Google, and local models
- **Advanced Cost Management**: Budget enforcement and usage monitoring
- **Enhanced Error Recovery**: Intelligent root cause analysis and targeted recovery
- **Resource Optimization**: Automatic browser cleanup and memory management
- **Real-time Monitoring**: Comprehensive system health and performance tracking

## 🔧 Usage

### Running the Application

```bash
# Test Automation Framework (NEW - Recommended)
uv run python examples/complete_framework_demo.py

# Test framework capabilities
uv run python scripts/test_framework_capabilities.py

# Advanced LLM features demo (NEW)
uv run python examples/advanced_llm_features_demo.py

# Legacy task runner
uv run python -m utils.task_runner

# Validation framework demo
uv run python examples/validation_demo.py

# Specific workflow
uv run python workflows/sample_workflow.py
```

### Test Automation Framework Usage (NEW - Recommended)

```python
import asyncio
from src.test_automation_framework import create_test_automation_framework

async def main():
    # Initialize the complete test automation framework
    framework = await create_test_automation_framework(
        workspace_path="my_tests",
        llm_provider="openai",
        llm_model="gpt-4",
        api_key="your-api-key",
        environment="staging"
    )

    # Create a test case from natural language
    test_case = await framework.create_test_case_from_description(
        name="Login Test",
        description="""
        Test the login functionality:
        1. Navigate to the login page
        2. Enter username and password
        3. Click login button
        4. Verify successful login
        """,
        priority="high",
        tags=["login", "authentication"]
    )

    # Generate test data
    user_data_set = await framework.create_test_data_set(
        name="User Test Data",
        data_type="person",
        scope="global"
    )
    await framework.generate_test_data(user_data_set.id, count=10, generator_type="person")

    # Execute the test
    execution = await framework.execute_test_case(test_case.id)

    # Generate comprehensive report
    report = await framework.generate_execution_report(
        execution.id,
        format="html",
        include_screenshots=True,
        include_performance_metrics=True
    )

    print(f"Test completed: {execution.status}")
    print(f"Success rate: {execution.get_success_rate():.2%}")
    print(f"Report generated: {report.file_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Advanced LLM Features (NEW)

```python
import asyncio
from src.test_automation_framework import create_test_automation_framework

async def advanced_llm_demo():
    framework = await create_test_automation_framework(
        workspace_path="my_tests",
        llm_provider="openai",
        llm_model="gpt-4",
        api_key="your-api-key"
    )

    # 1. Generate test cases from requirements
    requirements = """
    E-commerce Platform Requirements:
    - Users can register and login
    - Users can browse and search products
    - Users can add items to cart and checkout
    """

    test_cases = await framework.generate_test_cases_from_requirements(
        requirements_document=requirements,
        test_coverage_level="comprehensive"
    )
    print(f"Generated {len(test_cases)} test cases from requirements")

    # 2. Analyze UI changes impact
    ui_changes = """
    Login page redesign:
    - Email field ID changed from 'email' to 'user-email-input'
    - Login button text changed to 'Sign In'
    - Added social login options
    """

    impact = await framework.analyze_ui_changes_impact(
        ui_changes_description=ui_changes
    )
    print(f"UI changes impact: {impact['overall_impact']}")

    # 3. Update affected test cases
    if test_cases:
        updated_case = await framework.update_test_case_for_changes(
            test_case_id=test_cases[0].id,
            change_description=ui_changes,
            update_strategy="smart"
        )
        print(f"Updated test case: {updated_case.name} (v{updated_case.version})")

asyncio.run(advanced_llm_demo())
```

### Legacy Task Runner Usage

```python
import asyncio
from utils.task_runner import run_task
from src.execution.llm_provider import create_llm_provider
from src.validation import get_validation_config

async def main():
    # Create LLM provider
    llm = await create_llm_provider("openai", "gpt-4")

    # Configure validation (optional)
    validation_config = get_validation_config("standard")

    # Run task with validation
    result = await run_task(
        "Navigate to google.com and search for 'browser automation'",
        llm,
        "logs/first_task",
        validation_config  # Enable comprehensive validation
    )

    print("Task result:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

### Development Commands

```bash
# Run tests
uv run pytest

# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy src/

# Add dependencies
uv add <package-name>
uv add <package-name> --dev  # Development dependency
```

## 📋 Features

### 🧪 **Test Automation Framework (NEW)**
- **📋 Test Case Management**: Complete lifecycle management with natural language generation
- **🗄️ Test Data Management**: Comprehensive data generation, masking, and validation
- **📊 Advanced Test Reporting**: Multi-format reports with trend analysis and dashboards
- **🤖 Requirements-to-Test Generation**: AI-powered test case creation from requirements documents
- **🔧 Intelligent Test Maintenance**: Automated test updates when UI/system changes occur
- **🎯 Comprehensive Coverage**: Basic, standard, comprehensive, and exhaustive test coverage levels
- **📈 Test Analytics**: Trend analysis, failure patterns, and quality metrics

### ✅ Consolidated Architecture
- **Single Execution Path**: Eliminated legacy dual paths
- **Unified Task Runner**: Simplified interface for all automation tasks
- **Clean Separation**: Clear boundaries between components

### ✅ Enhanced LLM Integration
- **Provider Agnostic**: Easy switching between OpenAI, Anthropic, Google, local models
- **Automatic Fallback**: Built-in provider failover
- **Cost Tracking**: Real-time usage and cost monitoring
- **Advanced Rate Limiting**: Adaptive rate limiting with priority support

### ✅ Intelligent Error Recovery
- **Root Cause Analysis**: Intelligent error pattern detection
- **Targeted Recovery**: Specific recovery strategies for different error types
- **System State Capture**: Comprehensive diagnostics for troubleshooting
- **No Error Masking**: Transparent error handling with proper escalation

### ✅ Resource Management
- **Browser Pooling**: Efficient browser instance management
- **Memory Monitoring**: Automatic cleanup when resources are low
- **Leak Detection**: Zombie process detection and cleanup
- **Performance Optimization**: Proactive resource management

### ✅ Cost Management
- **Budget Enforcement**: Automatic provider suspension when limits exceeded
- **Usage Analytics**: Detailed cost breakdown and optimization recommendations
- **Alert System**: Proactive notifications at threshold levels
- **Multi-dimensional Limiting**: Requests, tokens, and cost-based limits

### ✅ Monitoring & Alerting
- **Real-time Metrics**: System resource usage, browser health, LLM performance
- **Performance Trends**: Predictive analysis and optimization recommendations
- **Comprehensive Alerting**: Proactive issue detection and notification
- **Health Dashboards**: Visual system status and performance monitoring

### ✅ Comprehensive Validation Framework
- **Multi-Phase Validation**: Pre-execution, during execution, post-execution, and continuous validation
- **Configurable Validation Levels**: Basic, standard, comprehensive, and paranoid validation modes
- **Evidence Collection**: Automatic collection of screenshots, logs, metrics, and validation artifacts
- **Data Quality Assurance**: Completeness, accuracy, consistency, and format validation
- **Performance Validation**: Execution time, resource usage, and throughput monitoring
- **Security Validation**: URL safety, sensitive data detection, and privacy compliance
- **LLM Validation**: Task understanding verification and response quality assessment
- **Intelligent Error Recovery**: Root cause analysis and targeted recovery strategies

## 🔑 Configuration

### Environment Variables

Create a `.env` file with your configuration:

```bash
# LLM Provider API Keys
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Application Settings
LOG_LEVEL=INFO
ENVIRONMENT=development

# Browser Settings
HEADLESS=false
BROWSER_TIMEOUT=30

# Cost Management
ENABLE_COST_TRACKING=true
DAILY_BUDGET_LIMIT=100.0
MONTHLY_BUDGET_LIMIT=1000.0

# Rate Limiting
REQUESTS_PER_MINUTE=60
TOKENS_PER_MINUTE=90000
COST_PER_MINUTE=10.0

# Monitoring
ENABLE_MONITORING=true
MONITORING_INTERVAL=30
MEMORY_THRESHOLD=0.8
```

## 📚 Documentation

### 🚀 Getting Started
- [Quick Start Guide](docs/quick-start.md) - Get running in 5 minutes
- [User Guide](docs/user-guide.md) - Comprehensive user documentation
- [UV Setup Guide](docs/uv-setup-guide.md) - Package management with UV

### 🔧 Development
- [Developer Guide](docs/developer-guide.md) - Complete development guide
- [API Reference](docs/api-reference.md) - Detailed API documentation
- [Architecture Fixes Summary](docs/architecture-fixes-summary.md) - Recent improvements

### 📖 Examples
- [Basic Usage Examples](examples/basic_usage.py) - Common automation patterns
- [Advanced Workflows](examples/) - Complex automation scenarios

## 🧪 Testing

```bash
# Run all tests
uv run pytest

# Run specific test categories
uv run pytest tests/unit/           # Unit tests
uv run pytest tests/integration/    # Integration tests
uv run pytest tests/e2e/           # End-to-end tests

# Run with coverage
uv run pytest --cov=src --cov-report=html

# Run performance tests
uv run pytest tests/performance/
```

## 🚀 Deployment

### Docker

```bash
# Build image
docker build -t browser-use-automation .

# Run container
docker run -p 8000:8000 browser-use-automation
```

### Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Install development dependencies: `uv sync --dev`
4. Make your changes
5. Run tests: `uv run pytest`
6. Format code: `uv run black . && uv run isort .`
7. Commit changes: `git commit -m 'Add amazing feature'`
8. Push to branch: `git push origin feature/amazing-feature`
9. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Report bugs and request features via GitHub Issues
- **Discussions**: Join community discussions in GitHub Discussions

## 🙏 Acknowledgments

- [UV](https://github.com/astral-sh/uv) for fast Python package management
- [Browser Use](https://github.com/browser-use/browser-use) for browser automation
- [Playwright](https://playwright.dev/) for reliable browser testing
- All the amazing open-source libraries that make this project possible