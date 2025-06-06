"""
Workflow-related API endpoints.

This module provides REST API endpoints for workflow management including
execution, monitoring, control, and status operations.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse

from core.interfaces import WorkflowDefinition, TaskDefinition, WorkflowStatus
from core.exceptions import WorkflowExecutionError, ValidationError, OrchestrationError
from src.api.models.requests import (
    WorkflowExecutionRequest, WorkflowControlRequest, WorkflowScheduleRequest
)
from src.api.models.responses import (
    WorkflowExecutionResponse, WorkflowStatusResponse, WorkflowListResponse,
    WorkflowControlResponse
)
from src.api.dependencies import (
    get_workflow_engine, get_task_scheduler, get_logger, get_feature_flags
)
from src.infrastructure.logging.logger import with_correlation_id


# Create router
router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("/execute", response_model=WorkflowExecutionResponse)
@with_correlation_id
async def execute_workflow(
    request: WorkflowExecutionRequest,
    background_tasks: BackgroundTasks,
    workflow_engine=Depends(get_workflow_engine),
    logger=Depends(get_logger)
) -> WorkflowExecutionResponse:
    """
    Execute a workflow with the specified tasks.
    
    This endpoint executes a workflow either synchronously or asynchronously
    based on the request configuration.
    """
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Workflow execution request received",
        correlation_id=correlation_id,
        workflow_name=request.workflow_name,
        task_count=len(request.tasks),
        execution_mode=request.execution_mode,
        async_execution=request.async_execution
    )
    
    try:
        # Validate request
        if not request.tasks:
            raise ValidationError("At least one task must be specified")
        
        # Create workflow definition
        workflow_definition = WorkflowDefinition(
            name=request.workflow_name or f"workflow_{int(datetime.now().timestamp())}",
            description=request.description or "API-generated workflow",
            tasks=request.tasks,
            metadata={
                "source": "api",
                "correlation_id": correlation_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **request.metadata
            }
        )
        
        # Create execution context
        execution_context = {
            "workflow_id": request.workflow_id or str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "execution_mode": request.execution_mode,
            "timeout": request.timeout,
            "continue_on_failure": request.continue_on_failure,
            "max_concurrent_tasks": request.max_concurrent_tasks,
            **request.context
        }
        
        # Execute workflow
        if request.async_execution:
            # Execute in background
            background_tasks.add_task(
                _execute_workflow_background,
                workflow_definition,
                execution_context,
                workflow_engine,
                logger,
                correlation_id
            )
            
            return WorkflowExecutionResponse(
                workflow_id=execution_context["workflow_id"],
                status="accepted",
                message="Workflow execution started in background",
                execution_time=0.0,
                correlation_id=correlation_id,
                async_execution=True
            )
        else:
            # Execute synchronously
            start_time = datetime.now(timezone.utc)
            
            results = await workflow_engine.execute_workflow(
                workflow_definition,
                execution_context
            )
            
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Determine overall status
            if all(result.status.value == "completed" for result in results.values()):
                status = "completed"
            elif any(result.status.value == "failed" for result in results.values()):
                status = "failed"
            else:
                status = "partial"
            
            logger.info(
                "Workflow execution completed",
                correlation_id=correlation_id,
                workflow_id=execution_context["workflow_id"],
                status=status,
                execution_time=execution_time,
                task_count=len(results)
            )
            
            return WorkflowExecutionResponse(
                workflow_id=execution_context["workflow_id"],
                status=status,
                results={name: result.dict() for name, result in results.items()},
                execution_time=execution_time,
                correlation_id=correlation_id,
                async_execution=False,
                task_count=len(results),
                successful_tasks=sum(1 for r in results.values() if r.status.value == "completed"),
                failed_tasks=sum(1 for r in results.values() if r.status.value == "failed")
            )
            
    except ValidationError as e:
        logger.error(
            "Workflow validation failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except WorkflowExecutionError as e:
        logger.error(
            "Workflow execution failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {str(e)}")
        
    except Exception as e:
        logger.error(
            "Unexpected error during workflow execution",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{workflow_id}/status", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    workflow_id: str,
    workflow_engine=Depends(get_workflow_engine),
    logger=Depends(get_logger)
) -> WorkflowStatusResponse:
    """Get the current status of a workflow."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Workflow status request",
        workflow_id=workflow_id,
        correlation_id=correlation_id
    )
    
    try:
        # Get workflow status
        status = await workflow_engine.get_workflow_status(workflow_id)
        
        # Get workflow results if available
        results = workflow_engine.get_workflow_results(workflow_id)
        
        # Get active workflow info
        active_workflows = workflow_engine.get_active_workflows()
        workflow_info = active_workflows.get(workflow_id)
        
        return WorkflowStatusResponse(
            workflow_id=workflow_id,
            status=status.value if status else "not_found",
            workflow_info=workflow_info,
            results=results,
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Error getting workflow status",
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get workflow status")


@router.post("/{workflow_id}/control", response_model=WorkflowControlResponse)
async def control_workflow(
    workflow_id: str,
    request: WorkflowControlRequest,
    workflow_engine=Depends(get_workflow_engine),
    logger=Depends(get_logger)
) -> WorkflowControlResponse:
    """Control a running workflow (pause, resume, cancel)."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Workflow control request",
        workflow_id=workflow_id,
        action=request.action,
        correlation_id=correlation_id
    )
    
    try:
        success = False
        message = ""
        
        if request.action == "pause":
            success = await workflow_engine.pause_workflow(workflow_id)
            message = "Workflow paused" if success else "Failed to pause workflow"
            
        elif request.action == "resume":
            success = await workflow_engine.resume_workflow(workflow_id)
            message = "Workflow resumed" if success else "Failed to resume workflow"
            
        elif request.action == "cancel":
            success = await workflow_engine.cancel_workflow(workflow_id)
            message = "Workflow cancelled" if success else "Failed to cancel workflow"
            
        else:
            raise ValidationError(f"Invalid action: {request.action}")
        
        logger.info(
            "Workflow control completed",
            workflow_id=workflow_id,
            action=request.action,
            success=success,
            correlation_id=correlation_id
        )
        
        return WorkflowControlResponse(
            workflow_id=workflow_id,
            action=request.action,
            success=success,
            message=message,
            correlation_id=correlation_id
        )
        
    except ValidationError as e:
        logger.error(
            "Invalid workflow control request",
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except Exception as e:
        logger.error(
            "Error controlling workflow",
            workflow_id=workflow_id,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to control workflow")


@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    status: Optional[str] = Query(None, description="Filter by workflow status"),
    limit: int = Query(50, ge=1, le=1000, description="Maximum number of workflows to return"),
    offset: int = Query(0, ge=0, description="Number of workflows to skip"),
    workflow_engine=Depends(get_workflow_engine),
    logger=Depends(get_logger)
) -> WorkflowListResponse:
    """List workflows with optional filtering."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "List workflows request",
        status_filter=status,
        limit=limit,
        offset=offset,
        correlation_id=correlation_id
    )
    
    try:
        # Get active workflows
        active_workflows = workflow_engine.get_active_workflows()
        
        # Get workflow statistics
        stats = workflow_engine.get_statistics()
        
        # Apply filtering and pagination
        workflows = list(active_workflows.items())
        
        if status:
            workflows = [(wid, info) for wid, info in workflows 
                        if info.get("status") == status]
        
        total_count = len(workflows)
        workflows = workflows[offset:offset + limit]
        
        return WorkflowListResponse(
            workflows=[
                {
                    "workflow_id": workflow_id,
                    "workflow_name": info.get("workflow_name"),
                    "status": info.get("status", "unknown"),
                    "start_time": info.get("start_time"),
                    "task_count": info.get("task_count"),
                    "execution_mode": info.get("execution_mode")
                }
                for workflow_id, info in workflows
            ],
            total_count=total_count,
            limit=limit,
            offset=offset,
            statistics=stats,
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Error listing workflows",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to list workflows")


# Background task execution
async def _execute_workflow_background(
    workflow_definition: WorkflowDefinition,
    execution_context: Dict[str, Any],
    workflow_engine,
    logger,
    correlation_id: str
) -> None:
    """Execute workflow in background task."""
    try:
        logger.info(
            "Starting background workflow execution",
            workflow_id=execution_context["workflow_id"],
            correlation_id=correlation_id
        )
        
        results = await workflow_engine.execute_workflow(
            workflow_definition,
            execution_context
        )
        
        logger.info(
            "Background workflow execution completed",
            workflow_id=execution_context["workflow_id"],
            correlation_id=correlation_id,
            task_count=len(results)
        )
        
    except Exception as e:
        logger.error(
            "Background workflow execution failed",
            workflow_id=execution_context["workflow_id"],
            correlation_id=correlation_id,
            error=str(e)
        )
