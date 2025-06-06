#!/bin/bash

# Browser Automation Framework Setup Script
# This script sets up the development environment

set -e

echo "🚀 Setting up Browser Automation Framework..."

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

# Check if Python 3.11+ is installed
check_python() {
    print_status "Checking Python version..."
    
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
        
        if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
            print_success "Python $PYTHON_VERSION found"
        else
            print_error "Python 3.11+ required, found $PYTHON_VERSION"
            exit 1
        fi
    else
        print_error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
}

# Check if Docker is installed
check_docker() {
    print_status "Checking Docker installation..."
    
    if command -v docker &> /dev/null; then
        print_success "Docker found"
    else
        print_warning "Docker not found. Some features may not work."
    fi
    
    if command -v docker-compose &> /dev/null; then
        print_success "Docker Compose found"
    else
        print_warning "Docker Compose not found. Some features may not work."
    fi
}

# Create virtual environment
setup_venv() {
    print_status "Setting up Python virtual environment..."
    
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        print_success "Virtual environment created"
    else
        print_warning "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    print_success "Pip upgraded"
}

# Install Python dependencies
install_dependencies() {
    print_status "Installing Python dependencies..."
    
    # Ensure we're in virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source venv/bin/activate
    fi
    
    # Install main dependencies
    pip install -r requirements.txt
    print_success "Main dependencies installed"
    
    # Install development dependencies if file exists
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
        print_success "Development dependencies installed"
    fi
    
    # Install Playwright browsers
    playwright install
    print_success "Playwright browsers installed"
}

# Setup environment file
setup_env() {
    print_status "Setting up environment configuration..."
    
    if [ ! -f ".env" ]; then
        cp .env.example .env
        print_success "Environment file created from template"
        print_warning "Please edit .env file with your actual configuration values"
    else
        print_warning ".env file already exists"
    fi
}

# Create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p logs
    mkdir -p downloads
    mkdir -p test-results
    mkdir -p config/grafana/dashboards
    mkdir -p config/grafana/datasources
    
    print_success "Directories created"
}

# Setup database (if Docker is available)
setup_database() {
    if command -v docker-compose &> /dev/null; then
        print_status "Setting up database with Docker..."
        
        # Start only the database service
        docker-compose up -d db
        
        # Wait for database to be ready
        print_status "Waiting for database to be ready..."
        sleep 10
        
        print_success "Database setup complete"
    else
        print_warning "Docker Compose not available. Please setup database manually."
        print_warning "Database URL: postgresql://postgres:password@localhost:5432/browser_automation"
    fi
}

# Run initial tests
run_tests() {
    print_status "Running initial tests..."
    
    # Ensure we're in virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source venv/bin/activate
    fi
    
    # Run basic import test
    python -c "
import sys
sys.path.append('.')
try:
    from core.interfaces import ITaskExecutor
    from src.infrastructure.config.settings import Settings
    print('✅ Core imports successful')
except ImportError as e:
    print(f'❌ Import error: {e}')
    sys.exit(1)
"
    
    print_success "Basic tests passed"
}

# Generate secret key
generate_secret_key() {
    print_status "Generating secret key..."
    
    # Ensure we're in virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
        source venv/bin/activate
    fi
    
    SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Update .env file if it exists
    if [ -f ".env" ]; then
        if grep -q "SECRET_KEY=" .env; then
            sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
            print_success "Secret key updated in .env file"
        else
            echo "SECRET_KEY=$SECRET_KEY" >> .env
            print_success "Secret key added to .env file"
        fi
    fi
}

# Main setup function
main() {
    echo "🔧 Browser Automation Framework Setup"
    echo "======================================"
    
    check_python
    check_docker
    setup_venv
    install_dependencies
    setup_env
    create_directories
    generate_secret_key
    
    if command -v docker-compose &> /dev/null; then
        setup_database
    fi
    
    run_tests
    
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit .env file with your configuration"
    echo "2. Start the application:"
    echo "   - Development: docker-compose up"
    echo "   - Or manually: source venv/bin/activate && python -m uvicorn src.api.main_service:app --reload"
    echo "3. Visit http://localhost:8000 to access the API"
    echo "4. Visit http://localhost:8000/docs for API documentation"
    echo ""
    echo "For more information, see docs/README.md"
}

# Run main function
main "$@"
