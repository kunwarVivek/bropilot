# Project Structure

## Overview

This document describes the new project structure for the browser automation framework, designed to provide clear separation of concerns and improved maintainability.

## Directory Structure

```
browser-use-automation/
├── README.md
├── requirements.txt
├── pyproject.toml
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
│
├── core/                           # Core framework interfaces and base classes
│   ├── __init__.py
│   ├── interfaces.py               # Abstract interfaces for all components
│   ├── exceptions.py               # Custom exception hierarchy
│   └── base.py                     # Base implementations
│
├── src/                            # Main source code
│   ├── __init__.py
│   │
│   ├── api/                        # API layer
│   │   ├── __init__.py
│   │   ├── main_service.py         # FastAPI application
│   │   ├── routers/                # API route handlers
│   │   │   ├── __init__.py
│   │   │   ├── workflows.py
│   │   │   ├── tasks.py
│   │   │   └── health.py
│   │   ├── models/                 # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── requests.py
│   │   │   └── responses.py
│   │   └── middleware/             # Custom middleware
│   │       ├── __init__.py
│   │       ├── auth.py
│   │       ├── logging.py
│   │       └── metrics.py
│   │
│   ├── orchestration/              # Orchestration layer
│   │   ├── __init__.py
│   │   ├── workflow_engine.py      # Workflow execution engine
│   │   ├── task_scheduler.py       # Task scheduling and queuing
│   │   ├── state_manager.py        # Execution state management
│   │   └── retry_manager.py        # Retry logic and backoff strategies
│   │
│   ├── execution/                  # Execution layer
│   │   ├── __init__.py
│   │   ├── task_executor.py        # Task execution implementation
│   │   ├── browser_manager.py      # Browser lifecycle management
│   │   ├── llm_provider.py         # LLM integration
│   │   └── adapters/               # External service adapters
│   │       ├── __init__.py
│   │       ├── browser_use.py      # Browser-use library adapter
│   │       ├── gemini.py           # Google Gemini adapter
│   │       └── openai.py           # OpenAI adapter
│   │
│   └── infrastructure/             # Infrastructure layer
│       ├── __init__.py
│       ├── config/                 # Configuration management
│       │   ├── __init__.py
│       │   ├── settings.py         # Application settings
│       │   └── environments/       # Environment-specific configs
│       │       ├── development.py
│       │       ├── staging.py
│       │       └── production.py
│       ├── logging/                # Logging infrastructure
│       │   ├── __init__.py
│       │   ├── logger.py           # Logger implementation
│       │   └── formatters.py       # Log formatters
│       ├── metrics/                # Metrics collection
│       │   ├── __init__.py
│       │   ├── collector.py        # Metrics collector
│       │   └── exporters.py        # Metrics exporters
│       ├── storage/                # Data storage
│       │   ├── __init__.py
│       │   ├── database.py         # Database connections
│       │   ├── models/             # Database models
│       │   └── repositories/       # Data access layer
│       └── security/               # Security components
│           ├── __init__.py
│           ├── auth.py             # Authentication
│           ├── encryption.py       # Encryption utilities
│           └── secrets.py          # Secrets management
│
├── tasks/                          # Task definitions (legacy, to be migrated)
│   ├── __init__.py
│   ├── definitions.py              # Task template definitions
│   └── templates/                  # Task template files
│       ├── auth.yaml
│       ├── ucm.yaml
│       └── ...
│
├── workflows/                      # Workflow definitions (legacy, to be migrated)
│   ├── __init__.py
│   └── sample_workflow.py          # Legacy workflow implementation
│
├── utils/                          # Utilities (legacy, to be migrated)
│   ├── __init__.py
│   ├── task_runner.py              # Legacy task runner
│   └── llm_limiter.py              # LLM rate limiting
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── conftest.py                 # Pytest configuration
│   ├── unit/                       # Unit tests
│   │   ├── test_core/
│   │   ├── test_api/
│   │   ├── test_orchestration/
│   │   ├── test_execution/
│   │   └── test_infrastructure/
│   ├── integration/                # Integration tests
│   │   ├── test_workflows/
│   │   └── test_api_endpoints/
│   ├── e2e/                        # End-to-end tests
│   │   └── test_complete_workflows/
│   └── fixtures/                   # Test fixtures and data
│       ├── tasks/
│       └── workflows/
│
├── docs/                           # Documentation
│   ├── README.md
│   ├── architecture.md             # Architecture documentation
│   ├── coding_standards.md         # Coding standards and patterns
│   ├── project_structure.md        # This file
│   ├── api/                        # API documentation
│   │   ├── openapi.yaml
│   │   └── endpoints.md
│   ├── deployment/                 # Deployment guides
│   │   ├── docker.md
│   │   ├── kubernetes.md
│   │   └── aws.md
│   └── user_guides/                # User documentation
│       ├── getting_started.md
│       ├── task_creation.md
│       └── workflow_management.md
│
├── scripts/                        # Utility scripts
│   ├── setup.sh                    # Environment setup
│   ├── migrate.py                  # Migration scripts
│   ├── test.sh                     # Test runner
│   └── deploy.sh                   # Deployment script
│
├── config/                         # Configuration files
│   ├── logging.yaml                # Logging configuration
│   ├── metrics.yaml                # Metrics configuration
│   └── environments/               # Environment configurations
│       ├── development.yaml
│       ├── staging.yaml
│       └── production.yaml
│
├── deployments/                    # Deployment configurations
│   ├── docker/
│   │   ├── Dockerfile
│   │   └── docker-compose.yml
│   ├── kubernetes/
│   │   ├── namespace.yaml
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   └── terraform/                  # Infrastructure as code
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
│
└── logs/                           # Log files (gitignored)
    ├── application.log
    └── execution/
        └── workflow_*.log
```

## Module Responsibilities

### Core (`core/`)
- **interfaces.py**: Abstract base classes defining contracts for all components
- **exceptions.py**: Custom exception hierarchy for clear error handling
- **base.py**: Base implementations providing common functionality

### API Layer (`src/api/`)
- **main_service.py**: FastAPI application with dependency injection
- **routers/**: Route handlers organized by functionality
- **models/**: Pydantic models for request/response validation
- **middleware/**: Custom middleware for cross-cutting concerns

### Orchestration Layer (`src/orchestration/`)
- **workflow_engine.py**: Manages workflow execution lifecycle
- **task_scheduler.py**: Handles task queuing and parallel execution
- **state_manager.py**: Persists and restores execution state
- **retry_manager.py**: Implements retry logic with backoff strategies

### Execution Layer (`src/execution/`)
- **task_executor.py**: Executes individual tasks
- **browser_manager.py**: Manages browser instances and lifecycle
- **llm_provider.py**: Interfaces with language models
- **adapters/**: Adapters for external services and libraries

### Infrastructure Layer (`src/infrastructure/`)
- **config/**: Configuration management and environment settings
- **logging/**: Structured logging with correlation IDs
- **metrics/**: Performance metrics collection and export
- **storage/**: Database models and data access layer
- **security/**: Authentication, authorization, and encryption

## Migration Strategy

### Phase 1: Foundation (Current)
1. ✅ Create core interfaces and base classes
2. ✅ Establish new project structure
3. ✅ Update main service with new architecture
4. 🔄 Create migration scripts for existing code

### Phase 2: Component Migration
1. Migrate task definitions to new structure
2. Implement new workflow engine
3. Create proper browser manager
4. Implement LLM provider abstraction

### Phase 3: Infrastructure
1. Implement configuration management
2. Set up structured logging
3. Add metrics collection
4. Create database layer

### Phase 4: Testing & Documentation
1. Create comprehensive test suite
2. Add API documentation
3. Write user guides
4. Create deployment documentation

## Import Patterns

### New Import Structure
```python
# Core interfaces
from core.interfaces import ITaskExecutor, IWorkflowEngine
from core.exceptions import TaskExecutionError
from core.base import BaseLogger

# API components
from src.api.models.requests import WorkflowRequest
from src.api.routers.workflows import workflow_router

# Orchestration components
from src.orchestration.workflow_engine import WorkflowEngine
from src.orchestration.task_scheduler import TaskScheduler

# Execution components
from src.execution.task_executor import TaskExecutor
from src.execution.browser_manager import BrowserManager

# Infrastructure components
from src.infrastructure.config.settings import Settings
from src.infrastructure.logging.logger import StructuredLogger
```

### Legacy Import Compatibility
During migration, legacy imports will be maintained:
```python
# Legacy imports (to be deprecated)
from workflows.sample_workflow import run_workflow
from tasks.definitions import get_task_templates
from utils.task_runner import run_task
```

## Configuration Management

### Environment Variables
```bash
# Application
APP_NAME=browser-automation-framework
APP_VERSION=1.0.0
APP_ENVIRONMENT=development

# API
API_HOST=0.0.0.0
API_PORT=8000
API_DEBUG=true

# Database
DATABASE_URL=postgresql://user:pass@localhost/db

# LLM
GEMINI_API_KEY=your_api_key
OPENAI_API_KEY=your_api_key

# Browser
BROWSER_HEADLESS=false
BROWSER_TIMEOUT=30

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Configuration Files
- `config/environments/development.yaml`: Development settings
- `config/environments/staging.yaml`: Staging settings
- `config/environments/production.yaml`: Production settings

## Testing Strategy

### Unit Tests
- Test individual components in isolation
- Mock external dependencies
- Focus on business logic and edge cases

### Integration Tests
- Test component interactions
- Use test databases and services
- Verify end-to-end data flow

### End-to-End Tests
- Test complete user workflows
- Use real browsers and services
- Validate system behavior

## Deployment

### Docker
- Multi-stage builds for optimization
- Security scanning
- Environment-specific configurations

### Kubernetes
- Horizontal pod autoscaling
- Health checks and probes
- ConfigMaps and Secrets

### CI/CD
- Automated testing on pull requests
- Security and dependency scanning
- Automated deployment to staging
- Manual approval for production
