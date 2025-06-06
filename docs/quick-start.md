# Quick Start Guide

Get up and running with Browser Use Automation in under 5 minutes!

## 🚀 Installation

### Option 1: Automated Setup (Recommended)

**Unix/macOS:**
```bash
git clone <repository-url>
cd browser-use-automation
./scripts/setup-uv.sh
```

**Windows:**
```cmd
git clone <repository-url>
cd browser-use-automation
scripts\setup-uv.bat
```

### Option 2: Manual Setup

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Setup project
git clone <repository-url>
cd browser-use-automation
uv sync
uv run playwright install
cp .env.example .env
```

## ⚙️ Configuration

Edit `.env` file with your API keys:

```bash
# At least one LLM provider API key is required
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
GOOGLE_API_KEY=your_google_api_key_here

# Optional: Adjust settings
HEADLESS=false
DAILY_BUDGET_LIMIT=100.0
```

## 🎯 First Task

### Simple Example

```python
# simple_task.py
import asyncio
from utils.task_runner import run_task
from src.execution.llm_provider import create_llm_provider

async def main():
    # Create LLM provider
    llm = await create_llm_provider("openai", "gpt-4")
    
    # Run task
    result = await run_task(
        "Navigate to google.com and search for 'browser automation'",
        llm,
        "logs/first_task"
    )
    
    print("Task result:", result)

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
uv run python simple_task.py
```

## 📋 Common Tasks

### Web Scraping
```python
task = """
Navigate to https://example.com
Extract all links from the page
Save them to a JSON file
"""
```

### Form Automation
```python
task = """
Navigate to https://forms.example.com
Fill out the contact form:
- Name: John Doe
- Email: john@example.com
- Message: Test message
Submit the form
"""
```

### Testing
```python
task = """
Navigate to https://app.example.com/login
Test the login functionality:
- Enter valid credentials
- Verify successful login
- Take screenshot of dashboard
"""
```

## 🔧 Key Commands

```bash
# Run main application
uv run python main.py

# Run examples
uv run python examples/basic_usage.py

# Run tests
uv run pytest

# Check system status
uv run python scripts/verify-setup.py

# Add new dependency
uv add requests

# Format code
uv run black .
```

## 📊 Monitoring

Check system health:
```python
from src.monitoring.system_monitor import SystemMonitor

monitor = SystemMonitor()
health = monitor.get_health_summary()
print(health)
```

Check costs:
```python
from src.infrastructure.cost_management import CostManager

cost_manager = CostManager()
usage = cost_manager.get_usage_summary("daily")
print(f"Daily cost: ${usage['total_cost']:.2f}")
```

## 🚨 Troubleshooting

### Common Issues

1. **API Key Error**: Check your `.env` file has valid API keys
2. **Browser Error**: Run `uv run playwright install`
3. **Import Error**: Run `uv sync` to install dependencies
4. **Permission Error**: Check file permissions on scripts

### Get Help

```bash
# Verify setup
uv run python scripts/verify-setup.py

# Check logs
ls logs/

# Run diagnostics
uv run python -c "
from utils.task_runner import get_execution_status
print(get_execution_status())
"
```

## 📚 Next Steps

1. **Read the User Guide**: `docs/user-guide.md`
2. **Explore Examples**: `examples/` directory
3. **Check API Reference**: `docs/api-reference.md`
4. **For Development**: `docs/developer-guide.md`

## 🎉 You're Ready!

Your Browser Use Automation platform is now set up and ready to use. Start with the examples and gradually build more complex automation workflows.

**Happy Automating! 🤖**
