# Development Setup Guide

Complete guide for setting up a development environment for the Browser Automation Framework.

## 🎯 Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows with WSL2
- **Memory**: 8GB+ RAM (16GB recommended)
- **Storage**: 10GB+ free space
- **CPU**: Multi-core processor (4+ cores recommended)

### Required Software

```mermaid
graph TB
    subgraph "Core Requirements"
        PYTHON[Python 3.11+]
        DOCKER[Docker & Docker Compose]
        GIT[Git]
        NODE[Node.js 18+ (optional)]
    end
    
    subgraph "Development Tools"
        IDE[VS Code / PyCharm]
        BROWSER[Chrome/Chromium]
        POSTMAN[Postman/Insomnia]
        TERM[Terminal/Shell]
    end
    
    subgraph "Optional Tools"
        REDIS_CLI[Redis CLI]
        PSQL[PostgreSQL Client]
        K9S[k9s (for Kubernetes)]
        HELM[Helm (for deployment)]
    end
    
    PYTHON --> IDE
    DOCKER --> BROWSER
    GIT --> POSTMAN
    NODE --> TERM
```

## 🚀 Quick Setup

### 1. Clone Repository
```bash
# Clone the main repository
git clone https://github.com/your-org/browser-automation-framework.git
cd browser-automation-framework

# Clone with all submodules (if any)
git clone --recursive https://github.com/your-org/browser-automation-framework.git
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env.development

# Edit development configuration
nano .env.development
```

**Development Environment Variables:**
```bash
# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=1

# Database (Docker will handle this)
DATABASE_URL=postgresql://automation:dev_password@localhost:5432/automation_dev
REDIS_URL=redis://localhost:6379/0

# LLM Configuration
LLM_PROVIDER=openai
OPENAI_API_KEY=your_development_api_key
# ANTHROPIC_API_KEY=your_anthropic_key  # Alternative

# Feature Flags
ENABLE_LLM_INTEGRATION=true
ENABLE_MULTIMODAL=true
ENABLE_ERROR_RECOVERY=true
ENABLE_ANALYTICS=true

# Development Features
ENABLE_DEBUG_TOOLBAR=true
ENABLE_HOT_RELOAD=true
ENABLE_PROFILING=true
MOCK_EXTERNAL_SERVICES=false

# Testing
TEST_DATABASE_URL=postgresql://automation:test_password@localhost:5433/automation_test
PYTEST_TIMEOUT=300
```

### 3. Docker Development Setup
```bash
# Start development services
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps
```

**Development Docker Compose:**
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  # Development database
  postgres-dev:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: automation_dev
      POSTGRES_USER: automation
      POSTGRES_PASSWORD: dev_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_dev_data:/var/lib/postgresql/data
      - ./database/init:/docker-entrypoint-initdb.d

  # Test database
  postgres-test:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: automation_test
      POSTGRES_USER: automation
      POSTGRES_PASSWORD: test_password
    ports:
      - "5433:5433"
    command: -p 5433

  # Redis for development
  redis-dev:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_dev_data:/data

  # Browser service for testing
  browserless:
    image: browserless/chrome:latest
    ports:
      - "3001:3000"
    environment:
      MAX_CONCURRENT_SESSIONS: 5
      CONNECTION_TIMEOUT: 60000

volumes:
  postgres_dev_data:
  redis_dev_data:
```

## 🐍 Python Development Environment

### 1. Virtual Environment Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 2. Install Dependencies
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Install package in editable mode
pip install -e .

# Install pre-commit hooks
pre-commit install
```

**Development Dependencies (requirements-dev.txt):**
```txt
# Core dependencies
-r requirements.txt

# Development tools
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-xdist>=3.3.0

# Code quality
black>=23.7.0
flake8>=6.0.0
mypy>=1.5.0
isort>=5.12.0
bandit>=1.7.5

# Documentation
sphinx>=7.1.0
sphinx-rtd-theme>=1.3.0
myst-parser>=2.0.0

# Debugging
ipdb>=0.13.13
ipython>=8.14.0

# Performance profiling
py-spy>=0.3.14
memory-profiler>=0.61.0

# API testing
httpx>=0.24.0
respx>=0.20.0

# Database tools
alembic>=1.11.0
psycopg2-binary>=2.9.7

# Monitoring
prometheus-client>=0.17.0
```

### 3. Database Setup
```bash
# Run database migrations
alembic upgrade head

# Create test data (optional)
python scripts/create_test_data.py

# Verify database connection
python -c "
from src.config.database import get_database_connection
import asyncio

async def test_db():
    async with get_database_connection() as conn:
        result = await conn.fetchval('SELECT 1')
        print(f'Database connection successful: {result}')

asyncio.run(test_db())
"
```

## 🛠️ IDE Configuration

### VS Code Setup

**Extensions (.vscode/extensions.json):**
```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.black-formatter",
    "ms-python.flake8",
    "ms-python.mypy-type-checker",
    "ms-python.isort",
    "charliermarsh.ruff",
    "ms-vscode.vscode-json",
    "redhat.vscode-yaml",
    "ms-vscode.vscode-typescript-next",
    "bradlc.vscode-tailwindcss",
    "esbenp.prettier-vscode",
    "ms-vscode.test-adapter-converter",
    "littlefoxteam.vscode-python-test-adapter"
  ]
}
```

**Settings (.vscode/settings.json):**
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests",
    "--tb=short",
    "--strict-markers"
  ],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    ".pytest_cache": true,
    ".mypy_cache": true,
    "*.egg-info": true
  },
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

**Launch Configuration (.vscode/launch.json):**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Main Application",
      "type": "python",
      "request": "launch",
      "module": "src.main",
      "args": ["--debug"],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env.development"
    },
    {
      "name": "Debug Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["tests/", "-v", "--tb=short"],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env.development"
    },
    {
      "name": "Debug Specific Test",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v", "-s"],
      "console": "integratedTerminal",
      "envFile": "${workspaceFolder}/.env.development"
    }
  ]
}
```

### PyCharm Setup

**Run Configurations:**
1. **Main Application**
   - Script path: `src/main.py`
   - Parameters: `--debug`
   - Environment variables: Load from `.env.development`

2. **Tests**
   - Target: `tests/`
   - Pattern: `test_*.py`
   - Options: `-v --tb=short`

## 🧪 Development Workflow

### Development Flow

```mermaid
flowchart TD
    START([Start Development]) --> BRANCH[Create Feature Branch]
    BRANCH --> CODE[Write Code]
    CODE --> TEST[Run Tests]
    
    TEST --> PASS{Tests Pass?}
    PASS -->|No| FIX[Fix Issues]
    FIX --> CODE
    
    PASS -->|Yes| LINT[Run Linting]
    LINT --> LINT_PASS{Linting Pass?}
    LINT_PASS -->|No| FIX_LINT[Fix Linting Issues]
    FIX_LINT --> CODE
    
    LINT_PASS -->|Yes| COMMIT[Commit Changes]
    COMMIT --> PUSH[Push to Remote]
    PUSH --> PR[Create Pull Request]
    
    PR --> REVIEW[Code Review]
    REVIEW --> APPROVED{Approved?}
    APPROVED -->|No| ADDRESS[Address Feedback]
    ADDRESS --> CODE
    
    APPROVED -->|Yes| MERGE[Merge to Main]
    MERGE --> DEPLOY[Deploy to Dev]
    DEPLOY --> END([Complete])
```

### Daily Development Commands

```bash
# Start development environment
make dev-start

# Run application in development mode
make dev-run

# Run tests
make test

# Run specific test file
make test-file FILE=tests/test_orchestrator.py

# Run linting and formatting
make lint
make format

# Run type checking
make type-check

# Run all quality checks
make quality-check

# Stop development environment
make dev-stop
```

**Makefile for Development:**
```makefile
.PHONY: dev-start dev-stop dev-run test lint format type-check quality-check

# Development environment
dev-start:
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Development environment started"

dev-stop:
	docker-compose -f docker-compose.dev.yml down
	@echo "Development environment stopped"

dev-run:
	python -m src.main --debug --reload

# Testing
test:
	pytest tests/ -v --tb=short --cov=src --cov-report=html

test-file:
	pytest $(FILE) -v -s

test-integration:
	pytest tests/integration/ -v --tb=short

test-e2e:
	pytest tests/e2e/ -v --tb=short

# Code quality
lint:
	flake8 src/ tests/
	mypy src/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/ --strict

quality-check: format lint type-check test
	@echo "All quality checks passed"

# Database
db-migrate:
	alembic upgrade head

db-reset:
	alembic downgrade base
	alembic upgrade head

# Documentation
docs-build:
	sphinx-build -b html docs/ docs/_build/html

docs-serve:
	python -m http.server 8080 --directory docs/_build/html
```

## 🧪 Testing Setup

### Test Configuration

**pytest.ini:**
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --tb=short
    --cov=src
    --cov-report=term-missing
    --cov-report=html:htmlcov
    --cov-fail-under=80
markers =
    unit: Unit tests
    integration: Integration tests
    e2e: End-to-end tests
    slow: Slow tests
    performance: Performance tests
    llm: Tests requiring LLM API
asyncio_mode = auto
```

### Test Structure

```
tests/
├── unit/                   # Unit tests
│   ├── test_orchestrator.py
│   ├── test_conversation.py
│   └── test_multimodal.py
├── integration/            # Integration tests
│   ├── test_workflow_execution.py
│   └── test_api_endpoints.py
├── e2e/                   # End-to-end tests
│   ├── test_complete_workflows.py
│   └── test_user_scenarios.py
├── performance/           # Performance tests
│   ├── test_load_testing.py
│   └── test_benchmarks.py
├── fixtures/              # Test fixtures
│   ├── workflows/
│   ├── data/
│   └── mocks/
└── conftest.py           # Pytest configuration
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m unit
pytest -m integration
pytest -m e2e

# Run tests with coverage
pytest --cov=src --cov-report=html

# Run tests in parallel
pytest -n auto

# Run tests with live logging
pytest -s --log-cli-level=INFO

# Run performance tests
pytest -m performance --benchmark-only
```

## 🔧 Debugging

### Debug Configuration

**Debug Environment Variables:**
```bash
# Enable debug mode
DEBUG=true
LOG_LEVEL=DEBUG

# Enable profiling
ENABLE_PROFILING=true
PROFILE_OUTPUT_DIR=./profiles

# Enable debug toolbar
ENABLE_DEBUG_TOOLBAR=true

# Mock external services for debugging
MOCK_LLM_PROVIDER=true
MOCK_BROWSER_POOL=true
```

### Debugging Tools

```python
# Using ipdb for debugging
import ipdb; ipdb.set_trace()

# Using logging for debugging
import logging
logger = logging.getLogger(__name__)
logger.debug("Debug message with context", extra={"context": data})

# Using async debugging
import asyncio
import ipdb

async def debug_async_function():
    await asyncio.sleep(0)  # Allow other tasks to run
    ipdb.set_trace()  # Debug point
```

### Performance Profiling

```bash
# Profile application startup
py-spy record -o profile.svg -- python -m src.main

# Memory profiling
mprof run python -m src.main
mprof plot

# Line profiling
kernprof -l -v src/orchestration/parallel_executor.py
```

## 📚 Documentation Development

### Building Documentation

```bash
# Install documentation dependencies
pip install -r docs/requirements.txt

# Build documentation
sphinx-build -b html docs/ docs/_build/html

# Serve documentation locally
python -m http.server 8080 --directory docs/_build/html

# Auto-rebuild on changes
sphinx-autobuild docs/ docs/_build/html
```

### Documentation Structure

```
docs/
├── user/                  # User documentation
├── developer/             # Developer documentation
├── operations/            # Operations documentation
├── api/                   # API documentation
├── _static/              # Static assets
├── _templates/           # Sphinx templates
├── conf.py              # Sphinx configuration
└── requirements.txt     # Documentation dependencies
```

## 🚀 Next Steps

Once your development environment is set up:

1. **Explore the Codebase**: Start with `src/main.py` and follow the imports
2. **Run the Test Suite**: Ensure everything works with `make test`
3. **Create a Simple Workflow**: Follow the [Quick Start Guide](../user/quick-start.md)
4. **Read the Architecture**: Understand the system design in [Architecture Overview](architecture.md)
5. **Contribute**: Check the [Contributing Guide](contributing.md) for contribution guidelines

## 🆘 Troubleshooting

### Common Issues

**Database Connection Issues:**
```bash
# Check if PostgreSQL is running
docker-compose -f docker-compose.dev.yml ps postgres-dev

# Reset database
make db-reset

# Check connection manually
psql postgresql://automation:dev_password@localhost:5432/automation_dev
```

**Import Errors:**
```bash
# Reinstall in editable mode
pip install -e .

# Check Python path
python -c "import sys; print(sys.path)"
```

**Test Failures:**
```bash
# Run tests with more verbose output
pytest -vvv --tb=long

# Run specific failing test
pytest tests/test_specific.py::test_function -vvv
```

**Performance Issues:**
```bash
# Profile the application
py-spy top --pid $(pgrep -f "python -m src.main")

# Check resource usage
docker stats
```

For more help, check the [Troubleshooting Guide](../user/troubleshooting.md) or ask in [GitHub Discussions](https://github.com/your-org/browser-automation-framework/discussions).
