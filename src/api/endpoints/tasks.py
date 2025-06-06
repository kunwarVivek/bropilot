"""
Task-related API endpoints.

This module provides REST API endpoints for task management including
individual task execution, scheduling, monitoring, and template management.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from core.interfaces import TaskDefinition, TaskStatus
from core.exceptions import TaskExecutionError, ValidationError, SchedulingError
from src.api.models.requests import (
    TaskExecutionRequest, TaskScheduleRequest, TaskTemplateRequest
)
from src.api.models.responses import (
    TaskExecutionResponse, TaskStatusResponse, TaskListResponse,
    TaskScheduleResponse, TaskTemplateResponse
)
from src.api.dependencies import (
    get_task_executor, get_task_scheduler, get_logger, get_feature_flags
)
from src.infrastructure.logging.logger import with_correlation_id
from src.orchestration.dependency_graph import TaskPriority


# Create router
router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/execute", response_model=TaskExecutionResponse)
@with_correlation_id
async def execute_task(
    request: TaskExecutionRequest,
    task_executor=Depends(get_task_executor),
    logger=Depends(get_logger)
) -> TaskExecutionResponse:
    """
    Execute a single task.
    
    This endpoint executes an individual task with the specified configuration
    and returns the execution result.
    """
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Task execution request received",
        correlation_id=correlation_id,
        task_name=request.task_name,
        timeout=request.timeout,
        retry_count=request.retry_count
    )
    
    try:
        # Create task definition
        task_definition = TaskDefinition(
            name=request.task_name,
            description=request.description or f"API task: {request.task_name}",
            prompt_template=request.prompt_template,
            timeout=request.timeout,
            retry_count=request.retry_count,
            metadata={
                "source": "api",
                "correlation_id": correlation_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **request.metadata
            }
        )
        
        # Create execution context
        execution_context = {
            "task_id": request.task_id or str(uuid.uuid4()),
            "correlation_id": correlation_id,
            "target_url": request.target_url,
            "headless": request.headless,
            "use_vision": request.use_vision,
            "browser_config": request.browser_config or {},
            **request.context
        }
        
        # Execute task
        start_time = datetime.now(timezone.utc)
        
        result = await task_executor.execute_task(task_definition, execution_context)
        
        execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        logger.info(
            "Task execution completed",
            correlation_id=correlation_id,
            task_id=execution_context["task_id"],
            status=result.status.value,
            execution_time=execution_time
        )
        
        return TaskExecutionResponse(
            task_id=execution_context["task_id"],
            task_name=request.task_name,
            status=result.status.value,
            result=result.result,
            error_message=result.error_message,
            execution_time=result.execution_time,
            metadata=result.metadata,
            correlation_id=correlation_id
        )
        
    except ValidationError as e:
        logger.error(
            "Task validation failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except TaskExecutionError as e:
        logger.error(
            "Task execution failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Task execution failed: {str(e)}")
        
    except Exception as e:
        logger.error(
            "Unexpected error during task execution",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/schedule", response_model=TaskScheduleResponse)
@with_correlation_id
async def schedule_task(
    request: TaskScheduleRequest,
    task_scheduler=Depends(get_task_scheduler),
    logger=Depends(get_logger)
) -> TaskScheduleResponse:
    """
    Schedule a task for execution.
    
    This endpoint schedules a task for execution using the task scheduler
    with specified priority and resource requirements.
    """
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Task scheduling request received",
        correlation_id=correlation_id,
        task_name=request.task_name,
        priority=request.priority,
        estimated_duration=request.estimated_duration
    )
    
    try:
        # Create task definition
        task_definition = TaskDefinition(
            name=request.task_name,
            description=request.description or f"Scheduled task: {request.task_name}",
            prompt_template=request.prompt_template,
            timeout=request.timeout,
            retry_count=request.retry_count,
            metadata={
                "source": "api_scheduled",
                "correlation_id": correlation_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                **request.metadata
            }
        )
        
        # Convert priority string to enum
        try:
            priority = TaskPriority(request.priority.lower())
        except ValueError:
            priority = TaskPriority.MEDIUM
        
        # Schedule task
        task_id = await task_scheduler.schedule_task(
            task_definition=task_definition,
            priority=priority,
            dependencies=set(request.dependencies) if request.dependencies else None,
            resource_requirements=request.resource_requirements,
            estimated_duration=request.estimated_duration,
            correlation_id=correlation_id,
            **request.context
        )
        
        logger.info(
            "Task scheduled successfully",
            correlation_id=correlation_id,
            task_id=task_id,
            priority=priority.value
        )
        
        return TaskScheduleResponse(
            task_id=task_id,
            task_name=request.task_name,
            status="scheduled",
            priority=priority.value,
            estimated_duration=request.estimated_duration,
            dependencies=request.dependencies or [],
            correlation_id=correlation_id
        )
        
    except ValidationError as e:
        logger.error(
            "Task scheduling validation failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=400, detail=str(e))
        
    except SchedulingError as e:
        logger.error(
            "Task scheduling failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail=f"Task scheduling failed: {str(e)}")
        
    except Exception as e:
        logger.error(
            "Unexpected error during task scheduling",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    task_scheduler=Depends(get_task_scheduler),
    logger=Depends(get_logger)
) -> TaskStatusResponse:
    """Get the current status of a scheduled task."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Task status request",
        task_id=task_id,
        correlation_id=correlation_id
    )
    
    try:
        # Get task status from scheduler
        status = task_scheduler.get_task_status(task_id)
        
        if status is None:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskStatusResponse(
            task_id=task_id,
            status=status.value,
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting task status",
            task_id=task_id,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get task status")


@router.delete("/{task_id}")
async def cancel_task(
    task_id: str,
    task_scheduler=Depends(get_task_scheduler),
    logger=Depends(get_logger)
) -> Dict[str, Any]:
    """Cancel a scheduled task."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Task cancellation request",
        task_id=task_id,
        correlation_id=correlation_id
    )
    
    try:
        success = await task_scheduler.cancel_task(task_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
        
        logger.info(
            "Task cancelled successfully",
            task_id=task_id,
            correlation_id=correlation_id
        )
        
        return {
            "task_id": task_id,
            "status": "cancelled",
            "message": "Task cancelled successfully",
            "correlation_id": correlation_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error cancelling task",
            task_id=task_id,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to cancel task")


@router.get("/", response_model=TaskListResponse)
async def list_available_tasks(
    logger=Depends(get_logger)
) -> TaskListResponse:
    """Get list of available task templates."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Available tasks request",
        correlation_id=correlation_id
    )
    
    try:
        # Import task templates
        from tasks.definitions import get_task_templates
        from dotenv import dotenv_values
        
        env_vars = dotenv_values(".env")
        task_templates = get_task_templates(env_vars)
        
        # Format task list
        tasks = [
            {
                "name": name,
                "description": f"Task template: {name}",
                "template": template[:200] + "..." if len(template) > 200 else template
            }
            for name, template in task_templates.items()
        ]
        
        logger.info(
            "Available tasks retrieved",
            correlation_id=correlation_id,
            task_count=len(tasks)
        )
        
        return TaskListResponse(
            tasks=tasks,
            total_count=len(tasks),
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Error retrieving available tasks",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve tasks")


@router.get("/queue/status")
async def get_queue_status(
    task_scheduler=Depends(get_task_scheduler),
    logger=Depends(get_logger)
) -> Dict[str, Any]:
    """Get current task queue status and statistics."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.debug(
        "Queue status request",
        correlation_id=correlation_id
    )
    
    try:
        status = task_scheduler.get_queue_status()
        status["correlation_id"] = correlation_id
        
        return status
        
    except Exception as e:
        logger.error(
            "Error getting queue status",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get queue status")
