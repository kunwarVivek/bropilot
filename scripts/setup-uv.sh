#!/bin/bash

# Setup script for browser-use-automation using uv
# This script sets up the development environment using uv for package management

set -e  # Exit on any error

echo "🚀 Setting up browser-use-automation with uv..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    print_error "uv is not installed. Please install it first:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    echo "  or visit: https://docs.astral.sh/uv/getting-started/installation/"
    exit 1
fi

print_success "uv is installed: $(uv --version)"

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

print_status "Working in project directory: $PROJECT_ROOT"

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    print_error "pyproject.toml not found. Are you in the correct directory?"
    exit 1
fi

# Remove existing virtual environment if it exists and is not uv-managed
if [[ -d ".venv" ]]; then
    print_warning "Existing .venv directory found"
    
    # Check if it's a uv-managed environment
    if [[ ! -f ".venv/pyvenv.cfg" ]] || ! grep -q "uv" ".venv/pyvenv.cfg" 2>/dev/null; then
        print_status "Removing existing non-uv virtual environment..."
        rm -rf .venv
    else
        print_status "Existing uv virtual environment detected, keeping it"
    fi
fi

# Create/sync virtual environment with uv
print_status "Creating/syncing virtual environment with uv..."
uv sync

print_success "Virtual environment created/synced successfully"

# Install playwright browsers
print_status "Installing Playwright browsers..."
uv run playwright install

print_success "Playwright browsers installed"

# Create .env file if it doesn't exist
if [[ ! -f ".env" ]]; then
    if [[ -f ".env.example" ]]; then
        print_status "Creating .env file from .env.example..."
        cp .env.example .env
        print_warning "Please edit .env file with your API keys and configuration"
    else
        print_status "Creating basic .env file..."
        cat > .env << EOF
# Browser Use Automation Environment Configuration

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
EOF
        print_warning "Please edit .env file with your API keys and configuration"
    fi
fi

# Run basic tests to verify installation
print_status "Running basic verification tests..."

# Test core imports
uv run python -c "
import sys
sys.path.append('.')

try:
    # Test enhanced error recovery
    from src.execution.enhanced_error_recovery import EnhancedErrorRecovery
    print('✅ Enhanced error recovery system')
    
    # Test cost management
    from src.infrastructure.cost_management import CostManager, AdvancedRateLimiter
    print('✅ Cost management and rate limiting')
    
    # Test LLM abstraction
    from src.execution.llm_abstraction import UnifiedLLMProvider, LLMProviderRegistry
    print('✅ Unified LLM abstraction')
    
    # Test task runner
    from utils.task_runner import get_execution_status
    status = get_execution_status()
    print('✅ Unified task runner')
    
    print('\\n🎉 All core components loaded successfully!')
    
except Exception as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"

if [[ $? -eq 0 ]]; then
    print_success "Core components verification passed"
else
    print_error "Core components verification failed"
    exit 1
fi

# Display helpful information
print_success "Setup completed successfully!"
echo ""
echo "📋 Next steps:"
echo "  1. Edit .env file with your API keys"
echo "  2. Activate the virtual environment: source .venv/bin/activate"
echo "  3. Or use uv to run commands: uv run python main.py"
echo ""
echo "🔧 Useful commands:"
echo "  uv run python main.py                    # Run the main application"
echo "  uv run pytest                           # Run tests"
echo "  uv add <package>                        # Add a new dependency"
echo "  uv remove <package>                     # Remove a dependency"
echo "  uv sync                                 # Sync dependencies"
echo "  uv run --with <package> python script.py # Run with additional package"
echo ""
echo "📚 Documentation:"
echo "  uv docs: https://docs.astral.sh/uv/"
echo "  Project docs: ./docs/"
echo ""
print_success "Happy automating! 🤖"
