#!/bin/bash

# Health check script for the automation framework
set -e

# Configuration
HEALTH_URL="http://localhost:8001/health"
TIMEOUT=10
MAX_RETRIES=3

# Function to check HTTP endpoint
check_http_endpoint() {
    local url=$1
    local timeout=${2:-10}
    
    curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1
    return $?
}

# Function to check database connectivity
check_database() {
    if [ -z "$DATABASE_URL" ]; then
        return 0  # Skip if no database configured
    fi
    
    python -c "
import sys
import asyncio
import asyncpg
from urllib.parse import urlparse

async def check_db():
    try:
        url = '$DATABASE_URL'
        parsed = urlparse(url)
        
        conn = await asyncpg.connect(
            host=parsed.hostname,
            port=parsed.port or 5432,
            user=parsed.username,
            password=parsed.password,
            database=parsed.path[1:] if parsed.path else 'postgres',
            command_timeout=5
        )
        
        # Simple query to test connectivity
        result = await conn.fetchval('SELECT 1')
        await conn.close()
        
        if result == 1:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except Exception as e:
        print(f'Database check failed: {e}', file=sys.stderr)
        sys.exit(1)

asyncio.run(check_db())
" 2>/dev/null
    return $?
}

# Function to check Redis connectivity
check_redis() {
    if [ -z "$REDIS_URL" ]; then
        return 0  # Skip if no Redis configured
    fi
    
    python -c "
import sys
import redis
from urllib.parse import urlparse

try:
    url = '$REDIS_URL'
    parsed = urlparse(url)
    
    r = redis.Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        password=parsed.password,
        socket_timeout=5,
        socket_connect_timeout=5
    )
    
    # Test connectivity
    r.ping()
    sys.exit(0)
    
except Exception as e:
    print(f'Redis check failed: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null
    return $?
}

# Function to check application health
check_application_health() {
    python -c "
import sys
import asyncio
import aiohttp
import json

async def check_health():
    try:
        timeout = aiohttp.ClientTimeout(total=$TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get('$HEALTH_URL') as response:
                if response.status == 200:
                    data = await response.json()
                    
                    # Check critical components
                    if data.get('status') == 'healthy':
                        # Check individual component health
                        components = data.get('components', {})
                        
                        critical_components = ['database', 'analytics', 'orchestrator']
                        for component in critical_components:
                            if component in components:
                                if components[component].get('status') != 'healthy':
                                    print(f'Component {component} is unhealthy', file=sys.stderr)
                                    sys.exit(1)
                        
                        sys.exit(0)
                    else:
                        print(f'Application status: {data.get(\"status\")}', file=sys.stderr)
                        sys.exit(1)
                else:
                    print(f'Health endpoint returned status {response.status}', file=sys.stderr)
                    sys.exit(1)
                    
    except Exception as e:
        print(f'Health check failed: {e}', file=sys.stderr)
        sys.exit(1)

asyncio.run(check_health())
" 2>/dev/null
    return $?
}

# Function to check system resources
check_system_resources() {
    # Check memory usage
    MEMORY_USAGE=$(python -c "
import psutil
memory = psutil.virtual_memory()
print(memory.percent)
" 2>/dev/null)
    
    if [ ! -z "$MEMORY_USAGE" ]; then
        if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
            echo "WARNING: High memory usage: ${MEMORY_USAGE}%" >&2
            return 1
        fi
    fi
    
    # Check disk usage
    DISK_USAGE=$(df /app | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ ! -z "$DISK_USAGE" ]; then
        if [ "$DISK_USAGE" -gt 90 ]; then
            echo "WARNING: High disk usage: ${DISK_USAGE}%" >&2
            return 1
        fi
    fi
    
    return 0
}

# Main health check function
main_health_check() {
    local retry_count=0
    
    while [ $retry_count -lt $MAX_RETRIES ]; do
        echo "Health check attempt $((retry_count + 1))/$MAX_RETRIES"
        
        # Check application health endpoint
        if check_application_health; then
            echo "✓ Application health check passed"
        else
            echo "✗ Application health check failed"
            retry_count=$((retry_count + 1))
            if [ $retry_count -lt $MAX_RETRIES ]; then
                sleep 2
                continue
            else
                return 1
            fi
        fi
        
        # Check database connectivity
        if check_database; then
            echo "✓ Database connectivity check passed"
        else
            echo "✗ Database connectivity check failed"
            return 1
        fi
        
        # Check Redis connectivity
        if check_redis; then
            echo "✓ Redis connectivity check passed"
        else
            echo "✗ Redis connectivity check failed"
            return 1
        fi
        
        # Check system resources
        if check_system_resources; then
            echo "✓ System resources check passed"
        else
            echo "⚠ System resources check warning"
            # Don't fail on resource warnings, just log them
        fi
        
        echo "✓ All health checks passed"
        return 0
    done
    
    return 1
}

# Run health check based on mode
case "${1:-full}" in
    "quick")
        # Quick check - just HTTP endpoint
        if check_http_endpoint "$HEALTH_URL" "$TIMEOUT"; then
            echo "✓ Quick health check passed"
            exit 0
        else
            echo "✗ Quick health check failed"
            exit 1
        fi
        ;;
    "database")
        # Database only
        if check_database; then
            echo "✓ Database health check passed"
            exit 0
        else
            echo "✗ Database health check failed"
            exit 1
        fi
        ;;
    "redis")
        # Redis only
        if check_redis; then
            echo "✓ Redis health check passed"
            exit 0
        else
            echo "✗ Redis health check failed"
            exit 1
        fi
        ;;
    "full"|*)
        # Full health check
        if main_health_check; then
            exit 0
        else
            exit 1
        fi
        ;;
esac
