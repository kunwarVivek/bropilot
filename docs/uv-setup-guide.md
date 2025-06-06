# UV Setup Guide for Browser Use Automation

This guide explains how to set up and use the browser-use-automation project with `uv`, a fast Python package manager and virtual environment tool.

## Why UV?

`uv` is significantly faster than traditional Python package managers:
- **10-100x faster** than pip for package installation
- **Built-in virtual environment management**
- **Lock file support** for reproducible builds
- **Compatible with pip and pyproject.toml**
- **Cross-platform support**

## Prerequisites

### Install UV

#### macOS/Linux
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows (PowerShell)
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

#### Alternative Methods
- **Homebrew**: `brew install uv`
- **Cargo**: `cargo install uv`
- **pip**: `pip install uv`

### Verify Installation
```bash
uv --version
```

## Quick Setup

### Automated Setup (Recommended)

#### Unix/macOS
```bash
./scripts/setup-uv.sh
```

#### Windows
```cmd
scripts\setup-uv.bat
```

### Manual Setup

1. **Clone and navigate to the project**:
   ```bash
   git clone <repository-url>
   cd browser-use-automation
   ```

2. **Create virtual environment and install dependencies**:
   ```bash
   uv sync
   ```

3. **Install Playwright browsers**:
   ```bash
   uv run playwright install
   ```

4. **Create environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Project Structure

```
browser-use-automation/
├── pyproject.toml          # Project configuration and dependencies
├── uv.lock                 # Lock file for reproducible builds
├── .venv/                  # Virtual environment (created by uv)
├── src/                    # Source code
├── tests/                  # Test files
├── scripts/                # Setup and utility scripts
└── docs/                   # Documentation
```

## UV Commands Reference

### Environment Management

```bash
# Create/sync virtual environment
uv sync

# Activate virtual environment (traditional way)
source .venv/bin/activate  # Unix/macOS
.venv\Scripts\activate     # Windows

# Run commands in virtual environment (uv way)
uv run python main.py
uv run pytest
```

### Package Management

```bash
# Add a new dependency
uv add requests
uv add pytest --dev  # Development dependency

# Add with version constraints
uv add "fastapi>=0.100.0"
uv add "pydantic~=2.0"

# Remove a dependency
uv remove requests

# Update dependencies
uv sync --upgrade

# Install from requirements.txt
uv pip install -r requirements.txt
```

### Development Workflow

```bash
# Run the main application
uv run python main.py

# Run tests
uv run pytest
uv run pytest tests/unit/  # Specific directory
uv run pytest -v          # Verbose output

# Run with coverage
uv run pytest --cov=src

# Format code
uv run black src/
uv run isort src/

# Type checking
uv run mypy src/

# Run linting
uv run flake8 src/
```

### Temporary Dependencies

```bash
# Run with temporary dependencies (not added to project)
uv run --with requests python script.py
uv run --with "pandas>=1.5" python analysis.py
```

## Configuration

### pyproject.toml Structure

```toml
[project]
name = "browser-use-automation"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "browser-use>=0.1.40",
    "playwright>=1.52.0",
    # ... other dependencies
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "black>=23.0.0",
    # ... dev dependencies
]

[tool.uv]
dev-dependencies = [
    # Alternative way to specify dev dependencies
]
```

### Lock File (uv.lock)

The `uv.lock` file ensures reproducible builds:
- **Commit to version control**
- **Contains exact versions** of all dependencies
- **Automatically updated** when dependencies change

## Environment Variables

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
```

## Common Tasks

### Running the Application

```bash
# Main application
uv run python main.py

# Task runner
uv run python -m utils.task_runner

# Specific workflow
uv run python workflows/sample_workflow.py
```

### Testing

```bash
# All tests
uv run pytest

# Unit tests only
uv run pytest tests/unit/

# Integration tests
uv run pytest tests/integration/

# With coverage
uv run pytest --cov=src --cov-report=html
```

### Development Tools

```bash
# Code formatting
uv run black .
uv run isort .

# Linting
uv run flake8 src/ tests/

# Type checking
uv run mypy src/

# Pre-commit hooks
uv run pre-commit run --all-files
```

## Troubleshooting

### Common Issues

1. **UV not found**:
   ```bash
   # Add to PATH (usually automatic)
   export PATH="$HOME/.local/bin:$PATH"
   ```

2. **Permission errors on Windows**:
   - Run PowerShell as Administrator
   - Or use `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

3. **Virtual environment issues**:
   ```bash
   # Remove and recreate
   rm -rf .venv
   uv sync
   ```

4. **Dependency conflicts**:
   ```bash
   # Check for conflicts
   uv pip check
   
   # Force update
   uv sync --upgrade
   ```

### Performance Tips

1. **Use uv run** instead of activating environment
2. **Keep uv.lock** in version control
3. **Use --no-dev** for production installs:
   ```bash
   uv sync --no-dev
   ```

## Migration from pip/conda

### From pip + venv

```bash
# Old way
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# New way with uv
uv sync
```

### From conda

```bash
# Export conda environment
conda env export > environment.yml

# Convert to pyproject.toml (manual process)
# Then use uv
uv sync
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v1
      - name: Set up Python
        run: uv python install 3.12
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest
```

## Best Practices

1. **Always use uv.lock** for reproducible builds
2. **Separate dev and production dependencies**
3. **Use uv run** for consistent environment
4. **Keep pyproject.toml organized** with clear sections
5. **Use version constraints** appropriately
6. **Commit uv.lock** to version control

## Resources

- [UV Documentation](https://docs.astral.sh/uv/)
- [UV GitHub Repository](https://github.com/astral-sh/uv)
- [Python Packaging Guide](https://packaging.python.org/)
- [pyproject.toml Specification](https://peps.python.org/pep-0621/)

## Support

If you encounter issues:
1. Check this guide first
2. Review the [UV documentation](https://docs.astral.sh/uv/)
3. Search existing issues in the project repository
4. Create a new issue with detailed information
