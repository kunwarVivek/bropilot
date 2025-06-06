#!/bin/bash

# Entrypoint script for the automation framework
set -e

# Default values
ENVIRONMENT=${ENVIRONMENT:-production}
LOG_LEVEL=${LOG_LEVEL:-INFO}
WORKERS=${WORKERS:-4}

echo "Starting Automation Framework..."
echo "Environment: $ENVIRONMENT"
echo "Log Level: $LOG_LEVEL"
echo "Workers: $WORKERS"

# Function to wait for service
wait_for_service() {
    local host=$1
    local port=$2
    local service_name=$3
    local timeout=${4:-30}
    
    echo "Waiting for $service_name at $host:$port..."
    
    for i in $(seq 1 $timeout); do
        if nc -z "$host" "$port" 2>/dev/null; then
            echo "$service_name is ready!"
            return 0
        fi
        echo "Waiting for $service_name... ($i/$timeout)"
        sleep 1
    done
    
    echo "ERROR: $service_name is not available after $timeout seconds"
    return 1
}

# Function to run database migrations
run_migrations() {
    echo "Running database migrations..."
    python -m alembic upgrade head || {
        echo "ERROR: Database migration failed"
        exit 1
    }
}

# Function to initialize application
initialize_app() {
    echo "Initializing application..."
    
    # Create necessary directories
    mkdir -p /app/logs /app/data /app/temp
    
    # Set proper permissions
    chmod 755 /app/logs /app/data /app/temp
    
    # Initialize configuration
    python -c "
from src.config.config_manager import ConfigManager
config = ConfigManager()
config.validate_configuration()
print('Configuration validated successfully')
" || {
        echo "ERROR: Configuration validation failed"
        exit 1
    }
}

# Function to start health check server
start_health_server() {
    echo "Starting health check server..."
    python -m src.infrastructure.monitoring.health_server &
    HEALTH_PID=$!
    echo "Health server started with PID: $HEALTH_PID"
}

# Function to cleanup on exit
cleanup() {
    echo "Shutting down gracefully..."
    
    # Kill health server if running
    if [ ! -z "$HEALTH_PID" ]; then
        kill $HEALTH_PID 2>/dev/null || true
    fi
    
    # Kill main application if running
    if [ ! -z "$MAIN_PID" ]; then
        kill $MAIN_PID 2>/dev/null || true
        wait $MAIN_PID 2>/dev/null || true
    fi
    
    echo "Shutdown complete"
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Wait for dependencies based on environment
if [ "$ENVIRONMENT" != "test" ]; then
    # Wait for database
    if [ ! -z "$DATABASE_URL" ]; then
        DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        wait_for_service "$DB_HOST" "$DB_PORT" "PostgreSQL" 60
    fi
    
    # Wait for Redis
    if [ ! -z "$REDIS_URL" ]; then
        REDIS_HOST=$(echo $REDIS_URL | sed -n 's/.*\/\/\([^:]*\):.*/\1/p')
        REDIS_PORT=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
        wait_for_service "$REDIS_HOST" "$REDIS_PORT" "Redis" 30
    fi
fi

# Initialize application
initialize_app

# Run migrations in production
if [ "$ENVIRONMENT" = "production" ]; then
    run_migrations
fi

# Start health check server
start_health_server

# Handle different run modes
case "${1:-}" in
    "test")
        echo "Running in test mode..."
        exec python -m pytest tests/ -v
        ;;
    "worker")
        echo "Starting worker process..."
        exec python -m src.worker.main
        ;;
    "scheduler")
        echo "Starting scheduler process..."
        exec python -m src.scheduler.main
        ;;
    "shell")
        echo "Starting interactive shell..."
        exec python -c "
from src.config.config_manager import ConfigManager
from src.intelligence.advanced_orchestrator import AdvancedOrchestrator
print('Automation Framework Shell')
print('Available objects: config, orchestrator')
config = ConfigManager()
# orchestrator = AdvancedOrchestrator(...)
import IPython; IPython.embed()
"
        ;;
    "migrate")
        echo "Running migrations only..."
        run_migrations
        exit 0
        ;;
    *)
        echo "Starting main application..."
        
        # Start main application
        if [ "$ENVIRONMENT" = "development" ]; then
            # Development mode with auto-reload
            exec python -m src.main --debug --reload &
        else
            # Production mode
            exec python -m src.main &
        fi
        
        MAIN_PID=$!
        echo "Main application started with PID: $MAIN_PID"
        
        # Wait for main process
        wait $MAIN_PID
        ;;
esac
