"""
Main FastAPI service with improved architecture.

This module provides the REST API endpoints for the browser automation framework
following the new architectural patterns.
"""

from typing import List, Dict, Any
from fastapi import FastAPI, APIRouter, HTTPException, Depends
from pydantic import BaseModel
import asyncio
import uuid
from datetime import datetime

from core.interfaces import IWorkflowEngine, ILogger, IHealthMonitor
from core.exceptions import FrameworkException, ValidationError
from core.base import BaseLogger, BaseHealthMonitor


class WorkflowRequest(BaseModel):
    """Request model for workflow execution."""
    flows: List[str]
    context: Dict[str, Any] = {}
    timeout: int = 300


class WorkflowResponse(BaseModel):
    """Response model for workflow execution."""
    workflow_id: str
    status: str
    results: Dict[str, Any]
    execution_time: float
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str
    timestamp: str
    components: Dict[str, Any]


class TaskListResponse(BaseModel):
    """Response model for available tasks."""
    status: str
    tasks: List[str]


# Dependency injection setup (will be properly configured later)
def get_logger() -> ILogger:
    """Get logger instance."""
    return BaseLogger("api")


def get_health_monitor() -> IHealthMonitor:
    """Get health monitor instance."""
    return BaseHealthMonitor()


def get_workflow_engine() -> IWorkflowEngine:
    """Get workflow engine instance (placeholder)."""
    # This will be replaced with proper dependency injection
    from workflows.sample_workflow import run_workflow, get_available_tasks
    
    class LegacyWorkflowAdapter:
        """Temporary adapter for legacy workflow system."""
        
        async def execute_workflow(self, workflow_request: WorkflowRequest) -> WorkflowResponse:
            start_time = datetime.utcnow()
            workflow_id = str(uuid.uuid4())
            
            try:
                # Use legacy workflow system for now
                results = await run_workflow(workflow_request.flows)
                
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                return WorkflowResponse(
                    workflow_id=workflow_id,
                    status="completed",
                    results=results,
                    execution_time=execution_time,
                    timestamp=datetime.utcnow().isoformat()
                )
                
            except Exception as e:
                execution_time = (datetime.utcnow() - start_time).total_seconds()
                
                return WorkflowResponse(
                    workflow_id=workflow_id,
                    status="failed",
                    results={"error": str(e)},
                    execution_time=execution_time,
                    timestamp=datetime.utcnow().isoformat()
                )
        
        def get_available_tasks(self) -> List[str]:
            """Get list of available tasks."""
            tasks_data = get_available_tasks()
            return tasks_data.get("tasks", [])
    
    return LegacyWorkflowAdapter()


# Create FastAPI app
app = FastAPI(
    title="Browser Automation Framework",
    description="A robust browser automation framework with LLM integration",
    version="1.0.0"
)

# Create API router
api_router = APIRouter(prefix="/api/v1")


@api_router.post("/workflows/execute", response_model=WorkflowResponse)
async def execute_workflow(
    request: WorkflowRequest,
    workflow_engine: IWorkflowEngine = Depends(get_workflow_engine),
    logger: ILogger = Depends(get_logger)
) -> WorkflowResponse:
    """Execute a workflow with the specified tasks."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Workflow execution request received",
        correlation_id=correlation_id,
        flows=request.flows,
        timeout=request.timeout
    )
    
    try:
        # Validate request
        if not request.flows:
            raise ValidationError("At least one flow must be specified")
        
        # Execute workflow
        response = await workflow_engine.execute_workflow(request)
        
        logger.info(
            "Workflow execution completed",
            correlation_id=correlation_id,
            workflow_id=response.workflow_id,
            status=response.status,
            execution_time=response.execution_time
        )
        
        return response
        
    except ValidationError as e:
        logger.error(
            "Workflow validation failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except FrameworkException as e:
        logger.error(
            "Framework error during workflow execution",
            correlation_id=correlation_id,
            error=str(e),
            error_code=e.error_code
        )
        raise HTTPException(status_code=500, detail=str(e))
        
    except Exception as e:
        logger.error(
            "Unexpected error during workflow execution",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@api_router.get("/tasks", response_model=TaskListResponse)
async def get_available_tasks(
    workflow_engine: IWorkflowEngine = Depends(get_workflow_engine),
    logger: ILogger = Depends(get_logger)
) -> TaskListResponse:
    """Get list of available tasks."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info("Available tasks request received", correlation_id=correlation_id)
    
    try:
        tasks = workflow_engine.get_available_tasks()
        
        logger.info(
            "Available tasks retrieved",
            correlation_id=correlation_id,
            task_count=len(tasks)
        )
        
        return TaskListResponse(
            status="success",
            tasks=tasks
        )
        
    except Exception as e:
        logger.error(
            "Error retrieving available tasks",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


@api_router.get("/health", response_model=HealthResponse)
async def health_check(
    health_monitor: IHealthMonitor = Depends(get_health_monitor),
    logger: ILogger = Depends(get_logger)
) -> HealthResponse:
    """Perform health check of all system components."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.debug("Health check request received", correlation_id=correlation_id)
    
    try:
        health_data = await health_monitor.check_health()
        
        return HealthResponse(
            status=health_data["status"],
            timestamp=health_data["timestamp"],
            components=health_data["components"]
        )
        
    except Exception as e:
        logger.error(
            "Error during health check",
            correlation_id=correlation_id,
            error=str(e)
        )
        
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow().isoformat(),
            components={"error": str(e)}
        )


@api_router.get("/health/ready")
async def readiness_check(
    health_monitor: IHealthMonitor = Depends(get_health_monitor)
) -> Dict[str, str]:
    """Kubernetes readiness probe endpoint."""
    
    try:
        health_data = await health_monitor.check_health()
        
        if health_data["status"] == "healthy":
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
            
    except Exception:
        raise HTTPException(status_code=503, detail="Service not ready")


@api_router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive"}


# Include API router
app.include_router(api_router)

# Add root endpoint
@app.get("/")
async def root():
    """Root endpoint with basic service information."""
    return {
        "service": "Browser Automation Framework",
        "version": "1.0.0",
        "status": "running",
        "timestamp": datetime.utcnow().isoformat()
    }


# Add startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger = get_logger()
    logger.info("Browser Automation Framework starting up")
    
    # Initialize health checks
    health_monitor = get_health_monitor()
    
    # Register component health checks
    health_monitor.register_health_check(
        "api", 
        lambda: True  # API is healthy if this code runs
    )
    
    logger.info("Browser Automation Framework startup complete")


# Add shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger = get_logger()
    logger.info("Browser Automation Framework shutting down")
    
    # Cleanup resources here
    
    logger.info("Browser Automation Framework shutdown complete")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
