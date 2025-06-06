"""
Health and monitoring API endpoints.

This module provides REST API endpoints for system health monitoring,
diagnostics, and operational status checks.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from src.api.models.responses import (
    HealthResponse, ComponentHealthResponse, SystemStatusResponse,
    MetricsResponse
)
from src.api.dependencies import (
    get_workflow_engine, get_task_scheduler, get_task_executor,
    get_browser_manager, get_llm_provider, get_logger, get_feature_flags
)
from src.infrastructure.logging.logger import with_correlation_id


# Create router
router = APIRouter(prefix="/health", tags=["health"])


@router.get("/", response_model=HealthResponse)
async def health_check(
    detailed: bool = Query(False, description="Include detailed component information"),
    workflow_engine=Depends(get_workflow_engine),
    task_scheduler=Depends(get_task_scheduler),
    task_executor=Depends(get_task_executor),
    browser_manager=Depends(get_browser_manager),
    llm_provider=Depends(get_llm_provider),
    logger=Depends(get_logger)
) -> HealthResponse:
    """
    Comprehensive health check of all system components.
    
    This endpoint performs health checks on all major system components
    and returns an overall health status.
    """
    correlation_id = str(uuid.uuid4())
    
    logger.debug(
        "Health check request",
        correlation_id=correlation_id,
        detailed=detailed
    )
    
    start_time = datetime.now(timezone.utc)
    components = {}
    overall_status = "healthy"
    
    try:
        # Check workflow engine
        try:
            if workflow_engine and hasattr(workflow_engine, 'health_check'):
                engine_health = await workflow_engine.health_check()
                components["workflow_engine"] = engine_health
                if engine_health.get("status") != "healthy":
                    overall_status = "degraded"
            else:
                components["workflow_engine"] = {"status": "not_available"}
                overall_status = "degraded"
        except Exception as e:
            components["workflow_engine"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"
        
        # Check task scheduler
        try:
            if task_scheduler and hasattr(task_scheduler, 'health_check'):
                scheduler_health = await task_scheduler.health_check()
                components["task_scheduler"] = scheduler_health
                if scheduler_health.get("status") not in ["healthy", "stopped"]:
                    overall_status = "degraded"
            else:
                components["task_scheduler"] = {"status": "not_available"}
        except Exception as e:
            components["task_scheduler"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"
        
        # Check task executor
        try:
            if task_executor and hasattr(task_executor, 'health_check'):
                executor_health = await task_executor.health_check()
                components["task_executor"] = executor_health
                if executor_health.get("status") != "healthy":
                    overall_status = "degraded"
            else:
                components["task_executor"] = {"status": "not_available"}
        except Exception as e:
            components["task_executor"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"
        
        # Check browser manager
        try:
            if browser_manager and hasattr(browser_manager, 'health_check'):
                browser_health = await browser_manager.health_check()
                components["browser_manager"] = browser_health
                if browser_health.get("status") != "healthy":
                    overall_status = "degraded"
            else:
                components["browser_manager"] = {"status": "not_available"}
        except Exception as e:
            components["browser_manager"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"
        
        # Check LLM provider
        try:
            if llm_provider and hasattr(llm_provider, 'health_check'):
                llm_health = await llm_provider.health_check()
                components["llm_provider"] = {"status": "healthy" if llm_health else "unhealthy"}
            else:
                components["llm_provider"] = {"status": "not_available"}
        except Exception as e:
            components["llm_provider"] = {"status": "unhealthy", "error": str(e)}
            overall_status = "unhealthy"
        
        # Calculate response time
        response_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        
        # Create response
        response = HealthResponse(
            status=overall_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            response_time=response_time,
            components=components if detailed else {},
            correlation_id=correlation_id
        )
        
        logger.debug(
            "Health check completed",
            correlation_id=correlation_id,
            status=overall_status,
            response_time=response_time,
            component_count=len(components)
        )
        
        return response
        
    except Exception as e:
        logger.error(
            "Health check failed",
            correlation_id=correlation_id,
            error=str(e)
        )
        
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.now(timezone.utc).isoformat(),
            response_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
            components={"error": str(e)},
            correlation_id=correlation_id
        )


@router.get("/ready")
async def readiness_check(
    workflow_engine=Depends(get_workflow_engine),
    task_executor=Depends(get_task_executor),
    logger=Depends(get_logger)
) -> Dict[str, str]:
    """
    Kubernetes readiness probe endpoint.
    
    This endpoint checks if the service is ready to accept traffic.
    Returns 200 if ready, 503 if not ready.
    """
    try:
        # Check critical components
        ready = True
        
        # Check if task executor is available
        if not task_executor:
            ready = False
        
        # Check if workflow engine is available
        if not workflow_engine:
            ready = False
        
        if ready:
            return {"status": "ready"}
        else:
            raise HTTPException(status_code=503, detail="Service not ready")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Readiness check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service not ready")


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes liveness probe endpoint.
    
    This endpoint checks if the service is alive and responsive.
    Always returns 200 unless the service is completely down.
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/components", response_model=List[ComponentHealthResponse])
async def get_component_health(
    component: Optional[str] = Query(None, description="Specific component to check"),
    workflow_engine=Depends(get_workflow_engine),
    task_scheduler=Depends(get_task_scheduler),
    task_executor=Depends(get_task_executor),
    browser_manager=Depends(get_browser_manager),
    llm_provider=Depends(get_llm_provider),
    logger=Depends(get_logger)
) -> List[ComponentHealthResponse]:
    """Get detailed health information for individual components."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.debug(
        "Component health request",
        correlation_id=correlation_id,
        component_filter=component
    )
    
    components = []
    
    # Define component checkers
    component_checkers = {
        "workflow_engine": (workflow_engine, "Workflow Engine"),
        "task_scheduler": (task_scheduler, "Task Scheduler"),
        "task_executor": (task_executor, "Task Executor"),
        "browser_manager": (browser_manager, "Browser Manager"),
        "llm_provider": (llm_provider, "LLM Provider")
    }
    
    # Filter components if specific component requested
    if component:
        if component not in component_checkers:
            raise HTTPException(status_code=404, detail=f"Component '{component}' not found")
        component_checkers = {component: component_checkers[component]}
    
    # Check each component
    for comp_name, (comp_instance, comp_display_name) in component_checkers.items():
        try:
            if comp_instance and hasattr(comp_instance, 'health_check'):
                health_data = await comp_instance.health_check()
                
                components.append(ComponentHealthResponse(
                    name=comp_name,
                    display_name=comp_display_name,
                    status=health_data.get("status", "unknown"),
                    details=health_data,
                    last_check=datetime.now(timezone.utc).isoformat(),
                    correlation_id=correlation_id
                ))
            else:
                components.append(ComponentHealthResponse(
                    name=comp_name,
                    display_name=comp_display_name,
                    status="not_available",
                    details={"message": "Component not available or no health check method"},
                    last_check=datetime.now(timezone.utc).isoformat(),
                    correlation_id=correlation_id
                ))
                
        except Exception as e:
            components.append(ComponentHealthResponse(
                name=comp_name,
                display_name=comp_display_name,
                status="unhealthy",
                details={"error": str(e)},
                last_check=datetime.now(timezone.utc).isoformat(),
                correlation_id=correlation_id
            ))
    
    return components


@router.get("/metrics", response_model=MetricsResponse)
async def get_system_metrics(
    workflow_engine=Depends(get_workflow_engine),
    task_scheduler=Depends(get_task_scheduler),
    task_executor=Depends(get_task_executor),
    logger=Depends(get_logger)
) -> MetricsResponse:
    """Get system performance metrics and statistics."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.debug(
        "Metrics request",
        correlation_id=correlation_id
    )
    
    try:
        metrics = {}
        
        # Get workflow engine metrics
        if workflow_engine and hasattr(workflow_engine, 'get_statistics'):
            metrics["workflow_engine"] = workflow_engine.get_statistics()
        
        # Get task scheduler metrics
        if task_scheduler and hasattr(task_scheduler, 'get_queue_status'):
            metrics["task_scheduler"] = task_scheduler.get_queue_status()
        
        # Get task executor metrics
        if task_executor and hasattr(task_executor, 'get_statistics'):
            metrics["task_executor"] = task_executor.get_statistics()
        
        return MetricsResponse(
            metrics=metrics,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Error getting system metrics",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get system metrics")


@router.get("/status", response_model=SystemStatusResponse)
async def get_system_status(
    feature_flags=Depends(get_feature_flags),
    workflow_engine=Depends(get_workflow_engine),
    task_scheduler=Depends(get_task_scheduler),
    logger=Depends(get_logger)
) -> SystemStatusResponse:
    """Get comprehensive system status including feature flags and configuration."""
    
    correlation_id = str(uuid.uuid4())
    
    try:
        # Get feature flag status
        migration_status = {}
        enabled_flags = []
        
        if feature_flags:
            migration_status = feature_flags.get_migration_status()
            enabled_flags = feature_flags.get_enabled_flags()
        
        # Get active workflows
        active_workflows = 0
        if workflow_engine and hasattr(workflow_engine, 'get_active_workflows'):
            active_workflows = len(workflow_engine.get_active_workflows())
        
        # Get queue status
        queue_status = {}
        if task_scheduler and hasattr(task_scheduler, 'get_queue_status'):
            queue_status = task_scheduler.get_queue_status()
        
        return SystemStatusResponse(
            system_status="operational",
            migration_status=migration_status,
            enabled_features=enabled_flags,
            active_workflows=active_workflows,
            queue_status=queue_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Error getting system status",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get system status")
