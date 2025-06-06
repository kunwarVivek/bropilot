"""
Main API application with structured endpoints and component management.

This module provides the FastAPI application with all endpoints
for workflow and task management using the new structured API architecture.
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Dict, List, Any
from datetime import datetime

# Import structured endpoints
from src.api.endpoints import (
    workflows_router, tasks_router, health_router, system_router
)
from src.api.dependencies import initialize_components, shutdown_components, get_api_config


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown of system components.
    """
    # Startup
    try:
        config = {
            "llm_provider": "gemini",
            "llm_config": {},
            "browser_config": {"headless": True},
            "default_timeout": 300,
            "save_logs": True,
            "logs_base_path": "logs",
            "max_concurrent_tasks": 5,
            "available_memory": 8.0,
            "available_cpu": 4.0,
            "available_browsers": 3
        }
        
        await initialize_components(config)
        print("✅ API components initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize API components: {e}")
        # Don't raise here to allow the API to start in degraded mode
    
    yield
    
    # Shutdown
    try:
        await shutdown_components()
        print("✅ API components shutdown successfully")
    except Exception as e:
        print(f"❌ Error during component shutdown: {e}")


# Create FastAPI application with lifespan management
app = FastAPI(
    title="Browser Automation API v2.0",
    description="Advanced API for automated browser workflows and task execution with orchestration capabilities",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Get API configuration
api_config = get_api_config()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=api_config.get("cors_origins", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(workflows_router)
app.include_router(tasks_router)
app.include_router(health_router)
app.include_router(system_router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Browser Automation API v2.0",
        "description": "Advanced browser automation with orchestration capabilities",
        "version": "2.0.0",
        "status": "running",
        "features": [
            "Workflow orchestration",
            "Task scheduling",
            "Feature flag management",
            "Health monitoring",
            "Legacy system integration"
        ],
        "endpoints": {
            "workflows": "/workflows",
            "tasks": "/tasks", 
            "health": "/health",
            "system": "/system",
            "docs": "/docs"
        },
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/info")
async def api_info():
    """Get detailed API information and capabilities."""
    return {
        "api": {
            "name": "Browser Automation API",
            "version": "2.0.0",
            "description": "Advanced browser automation with orchestration capabilities"
        },
        "capabilities": {
            "workflow_execution": {
                "modes": ["sequential", "parallel", "dependency_based", "hybrid"],
                "features": ["pause/resume", "cancellation", "status_tracking"]
            },
            "task_management": {
                "execution": "Individual task execution",
                "scheduling": "Priority-based task scheduling",
                "templates": "Task template management"
            },
            "system_management": {
                "feature_flags": "Dynamic feature flag management",
                "migration": "Gradual system migration support",
                "health_monitoring": "Comprehensive health checks"
            }
        },
        "architecture": {
            "execution_layer": "Task execution with browser automation",
            "orchestration_layer": "Workflow and task orchestration",
            "api_layer": "RESTful API with structured endpoints",
            "infrastructure": "Logging, monitoring, and feature flags"
        },
        "timestamp": datetime.now().isoformat()
    }


# Legacy compatibility endpoints
@app.post("/workflows/execute")
async def legacy_execute_workflow(request: Dict[str, Any]):
    """
    Legacy workflow execution endpoint for backward compatibility.
    
    This endpoint maintains compatibility with the old API while
    redirecting to the new structured endpoints internally.
    """
    try:
        # Import the enhanced workflow for backward compatibility
        from workflows.enhanced_workflow import run_workflow
        
        tasks = request.get("tasks", [])
        if not tasks:
            raise HTTPException(status_code=400, detail="No tasks specified")
        
        # Execute using enhanced workflow
        results = await run_workflow(tasks)
        
        return {
            "workflow_id": f"legacy_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "completed" if isinstance(results, dict) else "failed",
            "results": results,
            "tasks": tasks,
            "legacy_mode": True,
            "message": "Executed via legacy compatibility mode"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/available")
async def legacy_get_available_tasks():
    """
    Legacy available tasks endpoint for backward compatibility.
    """
    try:
        # Import the enhanced workflow for backward compatibility
        from workflows.enhanced_workflow import get_available_tasks
        
        tasks = get_available_tasks()
        
        return {
            "tasks": tasks.get("tasks", []),
            "count": len(tasks.get("tasks", [])),
            "legacy_mode": True,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        # Fallback to original implementation
        try:
            from workflows.sample_workflow import get_available_tasks as legacy_get_tasks
            tasks = legacy_get_tasks()
            return {
                "tasks": tasks["tasks"],
                "count": len(tasks["tasks"]),
                "legacy_mode": True,
                "fallback": True,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as fallback_error:
            raise HTTPException(status_code=500, detail=str(fallback_error))


# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions with structured error responses."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions with structured error responses."""
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "detail": str(exc),
                "timestamp": datetime.now().isoformat(),
                "path": str(request.url)
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level=api_config.get("log_level", "info").lower()
    )
