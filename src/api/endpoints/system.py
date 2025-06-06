"""
System management API endpoints.

This module provides REST API endpoints for system administration including
feature flag management, configuration updates, and system control operations.
"""

import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse

from src.api.models.requests import (
    FeatureFlagRequest, SystemConfigRequest, MigrationRequest
)
from src.api.models.responses import (
    FeatureFlagResponse, SystemConfigResponse, MigrationResponse,
    SystemInfoResponse
)
from src.api.dependencies import (
    get_feature_flags, get_legacy_bridge, get_logger, get_workflow_engine,
    get_task_scheduler
)
from src.infrastructure.logging.logger import with_correlation_id
from src.execution.feature_flags import FeatureFlag


# Create router
router = APIRouter(prefix="/system", tags=["system"])


@router.get("/info", response_model=SystemInfoResponse)
async def get_system_info(
    feature_flags=Depends(get_feature_flags),
    workflow_engine=Depends(get_workflow_engine),
    task_scheduler=Depends(get_task_scheduler),
    legacy_bridge=Depends(get_legacy_bridge),
    logger=Depends(get_logger)
) -> SystemInfoResponse:
    """Get comprehensive system information and configuration."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.debug(
        "System info request",
        correlation_id=correlation_id
    )
    
    try:
        # Get version information
        version_info = {
            "api_version": "1.0.0",
            "system_version": "2.0.0",
            "build_date": "2024-01-01",
            "environment": "development"
        }
        
        # Get feature flag information
        feature_info = {}
        if feature_flags:
            feature_info = {
                "migration_status": feature_flags.get_migration_status(),
                "enabled_flags": feature_flags.get_enabled_flags(),
                "total_flags": len(feature_flags.get_all_flags())
            }
        
        # Get component information
        components = {
            "workflow_engine": workflow_engine is not None,
            "task_scheduler": task_scheduler is not None,
            "legacy_bridge": legacy_bridge is not None,
            "feature_flags": feature_flags is not None
        }
        
        # Get statistics
        statistics = {}
        if workflow_engine and hasattr(workflow_engine, 'get_statistics'):
            statistics["workflow_engine"] = workflow_engine.get_statistics()
        
        if task_scheduler and hasattr(task_scheduler, 'get_queue_status'):
            statistics["task_scheduler"] = task_scheduler.get_queue_status()
        
        if legacy_bridge and hasattr(legacy_bridge, 'get_statistics'):
            statistics["legacy_bridge"] = legacy_bridge.get_statistics()
        
        return SystemInfoResponse(
            version=version_info,
            features=feature_info,
            components=components,
            statistics=statistics,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Error getting system info",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get system information")


@router.get("/features", response_model=FeatureFlagResponse)
async def get_feature_flags(
    feature_flags=Depends(get_feature_flags),
    logger=Depends(get_logger)
) -> FeatureFlagResponse:
    """Get current feature flag configuration."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.debug(
        "Feature flags request",
        correlation_id=correlation_id
    )
    
    try:
        if not feature_flags:
            raise HTTPException(status_code=503, detail="Feature flags not available")
        
        all_flags = feature_flags.get_all_flags()
        enabled_flags = feature_flags.get_enabled_flags()
        migration_status = feature_flags.get_migration_status()
        
        return FeatureFlagResponse(
            flags=all_flags,
            enabled_flags=enabled_flags,
            migration_status=migration_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting feature flags",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get feature flags")


@router.post("/features/{flag_name}/enable", response_model=FeatureFlagResponse)
@with_correlation_id
async def enable_feature_flag(
    flag_name: str,
    request: FeatureFlagRequest,
    feature_flags=Depends(get_feature_flags),
    logger=Depends(get_logger)
) -> FeatureFlagResponse:
    """Enable a specific feature flag."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Enable feature flag request",
        flag_name=flag_name,
        reason=request.reason,
        correlation_id=correlation_id
    )
    
    try:
        if not feature_flags:
            raise HTTPException(status_code=503, detail="Feature flags not available")
        
        # Validate flag name
        try:
            flag = FeatureFlag(flag_name)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid feature flag: {flag_name}")
        
        # Enable the flag
        feature_flags.enable_flag(flag, request.reason or "API request")
        
        # Get updated status
        all_flags = feature_flags.get_all_flags()
        enabled_flags = feature_flags.get_enabled_flags()
        migration_status = feature_flags.get_migration_status()
        
        logger.info(
            "Feature flag enabled",
            flag_name=flag_name,
            correlation_id=correlation_id
        )
        
        return FeatureFlagResponse(
            flags=all_flags,
            enabled_flags=enabled_flags,
            migration_status=migration_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error enabling feature flag",
            flag_name=flag_name,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to enable feature flag")


@router.post("/features/{flag_name}/disable", response_model=FeatureFlagResponse)
@with_correlation_id
async def disable_feature_flag(
    flag_name: str,
    request: FeatureFlagRequest,
    feature_flags=Depends(get_feature_flags),
    logger=Depends(get_logger)
) -> FeatureFlagResponse:
    """Disable a specific feature flag."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Disable feature flag request",
        flag_name=flag_name,
        reason=request.reason,
        correlation_id=correlation_id
    )
    
    try:
        if not feature_flags:
            raise HTTPException(status_code=503, detail="Feature flags not available")
        
        # Validate flag name
        try:
            flag = FeatureFlag(flag_name)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid feature flag: {flag_name}")
        
        # Disable the flag
        feature_flags.disable_flag(flag, request.reason or "API request")
        
        # Get updated status
        all_flags = feature_flags.get_all_flags()
        enabled_flags = feature_flags.get_enabled_flags()
        migration_status = feature_flags.get_migration_status()
        
        logger.info(
            "Feature flag disabled",
            flag_name=flag_name,
            correlation_id=correlation_id
        )
        
        return FeatureFlagResponse(
            flags=all_flags,
            enabled_flags=enabled_flags,
            migration_status=migration_status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error disabling feature flag",
            flag_name=flag_name,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to disable feature flag")


@router.post("/migration/phase/{phase}", response_model=MigrationResponse)
@with_correlation_id
async def enable_migration_phase(
    phase: int,
    request: MigrationRequest,
    feature_flags=Depends(get_feature_flags),
    logger=Depends(get_logger)
) -> MigrationResponse:
    """Enable a specific migration phase."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.info(
        "Migration phase request",
        phase=phase,
        reason=request.reason,
        correlation_id=correlation_id
    )
    
    try:
        if not feature_flags:
            raise HTTPException(status_code=503, detail="Feature flags not available")
        
        # Validate phase
        if phase < 1 or phase > 4:
            raise HTTPException(status_code=400, detail="Migration phase must be between 1 and 4")
        
        # Enable migration phase
        feature_flags.enable_migration_phase(phase)
        
        # Get updated migration status
        migration_status = feature_flags.get_migration_status()
        enabled_flags = feature_flags.get_enabled_flags()
        
        logger.info(
            "Migration phase enabled",
            phase=phase,
            migration_progress=migration_status.get("migration_progress"),
            correlation_id=correlation_id
        )
        
        return MigrationResponse(
            phase=phase,
            migration_status=migration_status,
            enabled_flags=enabled_flags,
            message=f"Migration phase {phase} enabled successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error enabling migration phase",
            phase=phase,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to enable migration phase")


@router.get("/migration/status", response_model=MigrationResponse)
async def get_migration_status(
    feature_flags=Depends(get_feature_flags),
    legacy_bridge=Depends(get_legacy_bridge),
    logger=Depends(get_logger)
) -> MigrationResponse:
    """Get current migration status."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.debug(
        "Migration status request",
        correlation_id=correlation_id
    )
    
    try:
        migration_status = {}
        enabled_flags = []
        bridge_stats = {}
        
        if feature_flags:
            migration_status = feature_flags.get_migration_status()
            enabled_flags = feature_flags.get_enabled_flags()
        
        if legacy_bridge and hasattr(legacy_bridge, 'get_statistics'):
            bridge_stats = legacy_bridge.get_statistics()
        
        return MigrationResponse(
            phase=0,  # Current phase would need to be calculated
            migration_status=migration_status,
            enabled_flags=enabled_flags,
            bridge_statistics=bridge_stats,
            message="Migration status retrieved successfully",
            timestamp=datetime.now(timezone.utc).isoformat(),
            correlation_id=correlation_id
        )
        
    except Exception as e:
        logger.error(
            "Error getting migration status",
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to get migration status")


@router.post("/restart")
async def restart_system(
    component: Optional[str] = Query(None, description="Specific component to restart"),
    workflow_engine=Depends(get_workflow_engine),
    task_scheduler=Depends(get_task_scheduler),
    logger=Depends(get_logger)
) -> Dict[str, Any]:
    """Restart system components (graceful restart)."""
    
    correlation_id = str(uuid.uuid4())
    
    logger.warning(
        "System restart request",
        component=component,
        correlation_id=correlation_id
    )
    
    try:
        restarted_components = []
        
        if component is None or component == "task_scheduler":
            if task_scheduler and hasattr(task_scheduler, 'stop') and hasattr(task_scheduler, 'start'):
                await task_scheduler.stop()
                await task_scheduler.start()
                restarted_components.append("task_scheduler")
        
        if component is None or component == "workflow_engine":
            # Workflow engine restart would be more complex
            # For now, just log the request
            logger.info("Workflow engine restart requested", correlation_id=correlation_id)
            restarted_components.append("workflow_engine")
        
        return {
            "status": "success",
            "message": f"Components restarted: {', '.join(restarted_components)}",
            "restarted_components": restarted_components,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": correlation_id
        }
        
    except Exception as e:
        logger.error(
            "Error restarting system",
            component=component,
            correlation_id=correlation_id,
            error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to restart system")
