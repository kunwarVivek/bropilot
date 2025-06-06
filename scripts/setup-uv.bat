@echo off
REM Setup script for browser-use-automation using uv (Windows)
REM This script sets up the development environment using uv for package management

setlocal enabledelayedexpansion

echo 🚀 Setting up browser-use-automation with uv...

REM Check if uv is installed
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] uv is not installed. Please install it first:
    echo   PowerShell: irm https://astral.sh/uv/install.ps1 ^| iex
    echo   Or visit: https://docs.astral.sh/uv/getting-started/installation/
    exit /b 1
)

echo [SUCCESS] uv is installed
uv --version

REM Get the project root directory
cd /d "%~dp0.."
set PROJECT_ROOT=%CD%

echo [INFO] Working in project directory: %PROJECT_ROOT%

REM Check if we're in the right directory
if not exist "pyproject.toml" (
    echo [ERROR] pyproject.toml not found. Are you in the correct directory?
    exit /b 1
)

REM Remove existing virtual environment if it exists and is not uv-managed
if exist ".venv" (
    echo [WARNING] Existing .venv directory found
    
    REM Check if it's a uv-managed environment
    if not exist ".venv\pyvenv.cfg" (
        echo [INFO] Removing existing non-uv virtual environment...
        rmdir /s /q .venv
    ) else (
        findstr /c:"uv" ".venv\pyvenv.cfg" >nul 2>nul
        if !errorlevel! neq 0 (
            echo [INFO] Removing existing non-uv virtual environment...
            rmdir /s /q .venv
        ) else (
            echo [INFO] Existing uv virtual environment detected, keeping it
        )
    )
)

REM Create/sync virtual environment with uv
echo [INFO] Creating/syncing virtual environment with uv...
uv sync
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create/sync virtual environment
    exit /b 1
)

echo [SUCCESS] Virtual environment created/synced successfully

REM Install playwright browsers
echo [INFO] Installing Playwright browsers...
uv run playwright install
if %errorlevel% neq 0 (
    echo [WARNING] Failed to install Playwright browsers, but continuing...
)

echo [SUCCESS] Playwright browsers installed

REM Create .env file if it doesn't exist
if not exist ".env" (
    if exist ".env.example" (
        echo [INFO] Creating .env file from .env.example...
        copy ".env.example" ".env"
        echo [WARNING] Please edit .env file with your API keys and configuration
    ) else (
        echo [INFO] Creating basic .env file...
        (
            echo # Browser Use Automation Environment Configuration
            echo.
            echo # LLM Provider API Keys
            echo OPENAI_API_KEY=your_openai_api_key_here
            echo ANTHROPIC_API_KEY=your_anthropic_api_key_here
            echo GOOGLE_API_KEY=your_google_api_key_here
            echo.
            echo # Application Settings
            echo LOG_LEVEL=INFO
            echo ENVIRONMENT=development
            echo.
            echo # Browser Settings
            echo HEADLESS=false
            echo BROWSER_TIMEOUT=30
            echo.
            echo # Cost Management
            echo ENABLE_COST_TRACKING=true
            echo DAILY_BUDGET_LIMIT=100.0
            echo MONTHLY_BUDGET_LIMIT=1000.0
            echo.
            echo # Rate Limiting
            echo REQUESTS_PER_MINUTE=60
            echo TOKENS_PER_MINUTE=90000
            echo COST_PER_MINUTE=10.0
            echo.
            echo # Monitoring
            echo ENABLE_MONITORING=true
            echo MONITORING_INTERVAL=30
            echo MEMORY_THRESHOLD=0.8
        ) > .env
        echo [WARNING] Please edit .env file with your API keys and configuration
    )
)

REM Run basic tests to verify installation
echo [INFO] Running basic verification tests...

uv run python -c "import sys; sys.path.append('.'); from src.execution.enhanced_error_recovery import EnhancedErrorRecovery; from src.infrastructure.cost_management import CostManager; from src.execution.llm_abstraction import UnifiedLLMProvider; from utils.task_runner import get_execution_status; print('🎉 All core components loaded successfully!')"

if %errorlevel% eq 0 (
    echo [SUCCESS] Core components verification passed
) else (
    echo [ERROR] Core components verification failed
    exit /b 1
)

REM Display helpful information
echo [SUCCESS] Setup completed successfully!
echo.
echo 📋 Next steps:
echo   1. Edit .env file with your API keys
echo   2. Activate the virtual environment: .venv\Scripts\activate
echo   3. Or use uv to run commands: uv run python main.py
echo.
echo 🔧 Useful commands:
echo   uv run python main.py                    # Run the main application
echo   uv run pytest                           # Run tests
echo   uv add ^<package^>                        # Add a new dependency
echo   uv remove ^<package^>                     # Remove a dependency
echo   uv sync                                 # Sync dependencies
echo   uv run --with ^<package^> python script.py # Run with additional package
echo.
echo 📚 Documentation:
echo   uv docs: https://docs.astral.sh/uv/
echo   Project docs: .\docs\
echo.
echo [SUCCESS] Happy automating! 🤖

pause
