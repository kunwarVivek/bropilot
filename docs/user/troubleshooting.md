# Troubleshooting Guide

Comprehensive solutions for common issues, debugging techniques, and performance optimization for the Browser Automation Framework.

## 🎯 Quick Diagnosis

### System Health Check

```bash
# Run comprehensive health check
python -m src.cli health-check --verbose

# Check specific components
python -m src.cli health-check --component browser
python -m src.cli health-check --component llm
python -m src.cli health-check --component database
```

### Common Issues Quick Reference

| Issue | Quick Fix | Details |
|-------|-----------|---------|
| **Workflow Timeout** | Increase timeout values | [Timeout Issues](#timeout-issues) |
| **Browser Crashes** | Update browser drivers | [Browser Issues](#browser-issues) |
| **LLM API Errors** | Check API keys/quotas | [LLM Issues](#llm-issues) |
| **Memory Leaks** | Restart browser pool | [Memory Issues](#memory-issues) |
| **Network Errors** | Check connectivity | [Network Issues](#network-issues) |
| **Database Locks** | Clear stale connections | [Database Issues](#database-issues) |

## 🔧 Installation & Setup Issues

### Docker Issues

```bash
# Common Docker problems and solutions

# Issue: Port already in use
docker-compose down
sudo lsof -i :8000  # Find process using port
sudo kill -9 <PID>  # Kill the process
docker-compose up -d

# Issue: Permission denied
sudo chown -R $USER:$USER .
sudo chmod +x scripts/*.sh

# Issue: Out of disk space
docker system prune -a  # Clean up unused containers/images
docker volume prune     # Clean up unused volumes
```

### Environment Configuration

```bash
# Validate environment setup
python -m src.cli validate-env

# Common .env issues
cp .env.example .env
# Ensure all required variables are set:
# - LLM_API_KEY
# - DATABASE_URL  
# - REDIS_URL
# - BROWSER_POOL_SIZE
```

### Dependency Issues

```bash
# Resolve Python dependency conflicts
pip install --upgrade pip
pip install -r requirements.txt --force-reinstall

# Clear pip cache if needed
pip cache purge

# For development dependencies
pip install -r requirements-dev.txt
```

## 🌐 Browser Issues

### Browser Pool Problems

```python
# Diagnose browser pool issues
from src.infrastructure.browser_pool import BrowserPool

pool = BrowserPool()
status = await pool.get_pool_status()

print(f"Active browsers: {status['active']}")
print(f"Available browsers: {status['available']}")
print(f"Failed browsers: {status['failed']}")

# Reset browser pool if needed
await pool.reset_pool()
```

### Browser Crashes

```python
# Handle browser crashes gracefully
browser_config = {
    "auto_restart": True,
    "max_restart_attempts": 3,
    "crash_detection": True,
    "memory_monitoring": True,
    "timeout_handling": "graceful"
}

# Monitor browser health
health_check = await pool.check_browser_health()
if health_check['status'] == 'unhealthy':
    await pool.restart_unhealthy_browsers()
```

### Playwright Issues

```bash
# Common Playwright problems

# Issue: Browser not found
playwright install chromium
playwright install firefox
playwright install webkit

# Issue: Permissions on Linux
sudo apt-get update
sudo apt-get install -y libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 libgbm1 libxss1 libasound2

# Issue: Headless mode problems
# Add to workflow config:
browser_config = {
    "headless": False,  # For debugging
    "devtools": True,   # Enable dev tools
    "slow_mo": 1000     # Slow down actions
}
```

## 🤖 LLM Issues

### API Connection Problems

```python
# Diagnose LLM connectivity
from src.llm.llm_manager import LLMManager

llm_manager = LLMManager()

# Test connection
try:
    test_response = await llm_manager.test_connection()
    print(f"LLM Status: {test_response['status']}")
except Exception as e:
    print(f"LLM Error: {e}")
    
    # Common fixes:
    # 1. Check API key
    # 2. Verify quota/billing
    # 3. Check network connectivity
    # 4. Validate model name
```

### Rate Limiting

```python
# Handle rate limiting gracefully
rate_limit_config = {
    "max_requests_per_minute": 50,
    "backoff_strategy": "exponential",
    "max_retries": 3,
    "retry_delay": 1.0,
    "queue_requests": True
}

# Monitor rate limits
rate_limit_status = await llm_manager.get_rate_limit_status()
print(f"Remaining requests: {rate_limit_status['remaining']}")
print(f"Reset time: {rate_limit_status['reset_time']}")
```

### Model Performance Issues

```python
# Optimize LLM performance
optimization_config = {
    "temperature": 0.1,      # Lower for consistency
    "max_tokens": 1000,      # Limit response length
    "timeout": 30,           # Reasonable timeout
    "streaming": True,       # For long responses
    "caching": True          # Cache similar requests
}

# Monitor LLM performance
performance_metrics = await llm_manager.get_performance_metrics()
print(f"Average response time: {performance_metrics['avg_response_time']}ms")
print(f"Success rate: {performance_metrics['success_rate']}%")
```

## ⏱️ Timeout Issues

### Workflow Timeouts

```python
# Configure appropriate timeouts
timeout_config = {
    "workflow_timeout": 1800,    # 30 minutes
    "task_timeout": 300,         # 5 minutes
    "browser_timeout": 60,       # 1 minute
    "llm_timeout": 30,           # 30 seconds
    "network_timeout": 15        # 15 seconds
}

# Implement progressive timeouts
progressive_config = {
    "initial_timeout": 30,
    "max_timeout": 300,
    "timeout_multiplier": 2.0,
    "max_attempts": 3
}
```

### Network Timeouts

```python
# Handle network timeouts
network_config = {
    "connect_timeout": 10,
    "read_timeout": 30,
    "total_timeout": 60,
    "retry_on_timeout": True,
    "max_retries": 3
}

# Monitor network performance
network_stats = await monitor.get_network_stats()
if network_stats['avg_latency'] > 1000:  # ms
    print("High network latency detected")
    # Consider adjusting timeouts or switching endpoints
```

## 💾 Memory Issues

### Memory Leaks

```python
# Monitor memory usage
import psutil
import gc

def check_memory_usage():
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"RSS Memory: {memory_info.rss / 1024 / 1024:.2f} MB")
    print(f"VMS Memory: {memory_info.vms / 1024 / 1024:.2f} MB")
    
    # Force garbage collection
    gc.collect()
    
    return memory_info

# Set memory limits
memory_config = {
    "max_memory_per_browser": "512MB",
    "max_total_memory": "2GB",
    "memory_check_interval": 60,  # seconds
    "auto_restart_on_limit": True
}
```

### Browser Memory Management

```python
# Optimize browser memory usage
browser_memory_config = {
    "max_pages_per_browser": 5,
    "close_unused_pages": True,
    "page_timeout": 300,
    "disable_images": False,  # Set True to save memory
    "disable_javascript": False,  # Set True to save memory
    "memory_pressure_handling": True
}

# Monitor browser memory
browser_stats = await pool.get_memory_stats()
for browser_id, stats in browser_stats.items():
    if stats['memory_usage'] > 500 * 1024 * 1024:  # 500MB
        await pool.restart_browser(browser_id)
```

## 🗄️ Database Issues

### Connection Problems

```python
# Diagnose database connectivity
from src.infrastructure.database import DatabaseManager

db_manager = DatabaseManager()

try:
    await db_manager.test_connection()
    print("Database connection: OK")
except Exception as e:
    print(f"Database error: {e}")
    
    # Common fixes:
    # 1. Check connection string
    # 2. Verify database is running
    # 3. Check network connectivity
    # 4. Validate credentials
```

### Performance Issues

```sql
-- Check for slow queries
SELECT query, mean_exec_time, calls 
FROM pg_stat_statements 
WHERE mean_exec_time > 1000 
ORDER BY mean_exec_time DESC;

-- Check for locks
SELECT * FROM pg_locks 
WHERE NOT granted;

-- Check database size
SELECT pg_size_pretty(pg_database_size('automation_db'));
```

### Migration Issues

```bash
# Database migration problems
alembic current  # Check current version
alembic history  # View migration history
alembic upgrade head  # Apply migrations

# If migrations fail:
alembic downgrade -1  # Rollback one version
# Fix the issue
alembic upgrade head  # Try again
```

## 🔍 Debugging Techniques

### Enable Debug Logging

```python
# Configure detailed logging
logging_config = {
    "level": "DEBUG",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "handlers": {
        "file": {
            "filename": "debug.log",
            "max_bytes": 10485760,  # 10MB
            "backup_count": 5
        },
        "console": {
            "level": "INFO"
        }
    }
}
```

### Workflow Debugging

```python
# Debug workflow execution
debug_config = {
    "enable_step_by_step": True,
    "capture_screenshots": True,
    "save_page_source": True,
    "record_network_traffic": True,
    "pause_on_error": True
}

# Add debug breakpoints
async def debug_task(task_context):
    print(f"Executing task: {task_context['task_name']}")
    print(f"Current state: {task_context['state']}")
    
    # Pause for inspection
    if debug_config['pause_on_error'] and task_context.get('error'):
        input("Press Enter to continue...")
```

### Performance Profiling

```python
# Profile workflow performance
import cProfile
import pstats

def profile_workflow(workflow_func):
    profiler = cProfile.Profile()
    profiler.enable()
    
    # Execute workflow
    result = workflow_func()
    
    profiler.disable()
    
    # Analyze results
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 functions
    
    return result
```

## 📊 Monitoring & Alerts

### Health Monitoring

```python
# Set up comprehensive health monitoring
health_checks = {
    "browser_pool": {
        "check_interval": 30,
        "healthy_threshold": 0.8,  # 80% browsers healthy
        "alert_on_failure": True
    },
    "database": {
        "check_interval": 60,
        "max_connections": 100,
        "alert_on_slow_queries": True
    },
    "llm_service": {
        "check_interval": 120,
        "max_response_time": 10000,  # 10 seconds
        "alert_on_rate_limit": True
    }
}
```

### Error Tracking

```python
# Implement error tracking and analysis
error_tracking = {
    "capture_stack_traces": True,
    "group_similar_errors": True,
    "error_rate_alerting": True,
    "auto_error_reporting": True,
    "error_trend_analysis": True
}

# Analyze error patterns
error_analysis = await analytics.analyze_errors(
    time_range="last_24_hours",
    group_by=["error_type", "workflow_type"],
    include_trends=True
)
```

## 🚀 Performance Optimization

### Workflow Optimization

```python
# Optimize workflow performance
optimization_strategies = {
    "parallel_execution": True,
    "resource_pooling": True,
    "intelligent_caching": True,
    "load_balancing": True,
    "auto_scaling": True
}

# Performance tuning
performance_config = {
    "max_concurrent_workflows": 10,
    "browser_pool_size": 5,
    "task_timeout": 300,
    "retry_attempts": 3,
    "cache_ttl": 3600
}
```

### Resource Management

```python
# Monitor and optimize resource usage
resource_monitoring = {
    "cpu_threshold": 80,      # Percent
    "memory_threshold": 85,   # Percent
    "disk_threshold": 90,     # Percent
    "network_threshold": 100, # Mbps
    "auto_scaling": True
}

# Resource cleanup
async def cleanup_resources():
    # Close unused browser instances
    await browser_pool.cleanup_idle_browsers()
    
    # Clear caches
    await cache_manager.clear_expired()
    
    # Garbage collection
    gc.collect()
```

## 🔗 Getting Help

### Support Channels

- **GitHub Issues**: [Report bugs](https://github.com/your-org/browser-automation-framework/issues)
- **Discussions**: [Community Q&A](https://github.com/your-org/browser-automation-framework/discussions)
- **Documentation**: [Complete docs](https://docs.automation-framework.com)
- **Discord**: [Real-time chat](https://discord.gg/automation-framework)

### Diagnostic Information

When reporting issues, include:

```bash
# Generate diagnostic report
python -m src.cli generate-diagnostic-report

# The report includes:
# - System information
# - Configuration details
# - Recent logs
# - Performance metrics
# - Error traces
```

## 📚 Additional Resources

- **[Performance Tuning Guide](../developer/performance.md)** - Advanced optimization techniques
- **[Monitoring Setup](../operations/monitoring.md)** - Production monitoring configuration
- **[Security Guide](../operations/security.md)** - Security troubleshooting
