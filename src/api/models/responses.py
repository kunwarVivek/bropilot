"""
API response models.

This module contains Pydantic models for API response validation and documentation.
All models include proper typing, documentation, and examples.
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime


class WorkflowExecutionResponse(BaseModel):
    """Response model for workflow execution."""
    
    workflow_id: str = Field(
        ...,
        description="Unique workflow identifier",
        example="wf_12345"
    )
    
    status: str = Field(
        ...,
        description="Workflow execution status",
        example="completed"
    )
    
    message: Optional[str] = Field(
        None,
        description="Status message",
        example="Workflow executed successfully"
    )
    
    results: Optional[Dict[str, Any]] = Field(
        None,
        description="Task execution results",
        example={"task1": {"status": "completed", "result": "Success"}}
    )
    
    execution_time: float = Field(
        ...,
        description="Total execution time in seconds",
        example=45.2
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID",
        example="corr_12345"
    )
    
    async_execution: bool = Field(
        ...,
        description="Whether execution was asynchronous",
        example=False
    )
    
    task_count: Optional[int] = Field(
        None,
        description="Total number of tasks",
        example=3
    )
    
    successful_tasks: Optional[int] = Field(
        None,
        description="Number of successful tasks",
        example=3
    )
    
    failed_tasks: Optional[int] = Field(
        None,
        description="Number of failed tasks",
        example=0
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp",
        example="2024-01-01T12:00:00Z"
    )


class WorkflowStatusResponse(BaseModel):
    """Response model for workflow status."""
    
    workflow_id: str = Field(
        ...,
        description="Workflow identifier",
        example="wf_12345"
    )
    
    status: str = Field(
        ...,
        description="Current workflow status",
        example="running"
    )
    
    workflow_info: Optional[Dict[str, Any]] = Field(
        None,
        description="Workflow information",
        example={"name": "test_workflow", "start_time": "2024-01-01T12:00:00Z"}
    )
    
    results: Optional[Dict[str, Any]] = Field(
        None,
        description="Available results",
        example={"task1": {"status": "completed"}}
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID",
        example="corr_12345"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class WorkflowListResponse(BaseModel):
    """Response model for workflow listing."""
    
    workflows: List[Dict[str, Any]] = Field(
        ...,
        description="List of workflows",
        example=[
            {
                "workflow_id": "wf_001",
                "workflow_name": "test_workflow",
                "status": "completed",
                "start_time": "2024-01-01T12:00:00Z"
            }
        ]
    )
    
    total_count: int = Field(
        ...,
        description="Total number of workflows",
        example=1
    )
    
    limit: int = Field(
        ...,
        description="Response limit",
        example=50
    )
    
    offset: int = Field(
        ...,
        description="Response offset",
        example=0
    )
    
    statistics: Optional[Dict[str, Any]] = Field(
        None,
        description="Workflow statistics",
        example={"total_workflows": 10, "successful_workflows": 8}
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class WorkflowControlResponse(BaseModel):
    """Response model for workflow control operations."""
    
    workflow_id: str = Field(
        ...,
        description="Workflow identifier",
        example="wf_12345"
    )
    
    action: str = Field(
        ...,
        description="Control action performed",
        example="pause"
    )
    
    success: bool = Field(
        ...,
        description="Whether the action was successful",
        example=True
    )
    
    message: str = Field(
        ...,
        description="Action result message",
        example="Workflow paused successfully"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class TaskExecutionResponse(BaseModel):
    """Response model for task execution."""
    
    task_id: str = Field(
        ...,
        description="Task identifier",
        example="task_12345"
    )
    
    task_name: str = Field(
        ...,
        description="Task name",
        example="login_task"
    )
    
    status: str = Field(
        ...,
        description="Task execution status",
        example="completed"
    )
    
    result: Optional[Any] = Field(
        None,
        description="Task execution result",
        example="Login successful"
    )
    
    error_message: Optional[str] = Field(
        None,
        description="Error message if task failed",
        example=None
    )
    
    execution_time: float = Field(
        ...,
        description="Execution time in seconds",
        example=12.5
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Task metadata",
        example={"browser_used": "chrome", "screenshots": 3}
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class TaskStatusResponse(BaseModel):
    """Response model for task status."""
    
    task_id: str = Field(
        ...,
        description="Task identifier",
        example="task_12345"
    )
    
    status: str = Field(
        ...,
        description="Current task status",
        example="running"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class TaskListResponse(BaseModel):
    """Response model for task listing."""
    
    tasks: List[Dict[str, Any]] = Field(
        ...,
        description="List of available tasks",
        example=[
            {
                "name": "login",
                "description": "Login task template",
                "template": "Navigate to login page..."
            }
        ]
    )
    
    total_count: int = Field(
        ...,
        description="Total number of tasks",
        example=5
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class TaskScheduleResponse(BaseModel):
    """Response model for task scheduling."""
    
    task_id: str = Field(
        ...,
        description="Scheduled task identifier",
        example="task_12345"
    )
    
    task_name: str = Field(
        ...,
        description="Task name",
        example="backup_task"
    )
    
    status: str = Field(
        ...,
        description="Scheduling status",
        example="scheduled"
    )
    
    priority: str = Field(
        ...,
        description="Task priority",
        example="high"
    )
    
    estimated_duration: Optional[float] = Field(
        None,
        description="Estimated execution time",
        example=120.0
    )
    
    dependencies: List[str] = Field(
        ...,
        description="Task dependencies",
        example=["task_001"]
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class TaskTemplateResponse(BaseModel):
    """Response model for task template operations."""
    
    template_name: str = Field(
        ...,
        description="Template name",
        example="login_template"
    )
    
    template_content: str = Field(
        ...,
        description="Template content",
        example="Navigate to {url} and login"
    )
    
    variables: List[str] = Field(
        ...,
        description="Template variables",
        example=["url", "username", "password"]
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
    
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="Response timestamp"
    )


class HealthResponse(BaseModel):
    """Response model for health checks."""
    
    status: str = Field(
        ...,
        description="Overall health status",
        example="healthy"
    )
    
    timestamp: str = Field(
        ...,
        description="Health check timestamp",
        example="2024-01-01T12:00:00Z"
    )
    
    response_time: float = Field(
        ...,
        description="Health check response time in seconds",
        example=0.05
    )
    
    components: Dict[str, Any] = Field(
        ...,
        description="Component health details",
        example={"workflow_engine": {"status": "healthy"}}
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )


class ComponentHealthResponse(BaseModel):
    """Response model for individual component health."""
    
    name: str = Field(
        ...,
        description="Component name",
        example="workflow_engine"
    )
    
    display_name: str = Field(
        ...,
        description="Component display name",
        example="Workflow Engine"
    )
    
    status: str = Field(
        ...,
        description="Component health status",
        example="healthy"
    )
    
    details: Dict[str, Any] = Field(
        ...,
        description="Detailed health information",
        example={"active_workflows": 2, "total_workflows": 10}
    )
    
    last_check: str = Field(
        ...,
        description="Last health check timestamp",
        example="2024-01-01T12:00:00Z"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )


class SystemStatusResponse(BaseModel):
    """Response model for system status."""
    
    system_status: str = Field(
        ...,
        description="Overall system status",
        example="operational"
    )
    
    migration_status: Dict[str, Any] = Field(
        ...,
        description="Migration status information",
        example={"migration_progress": 0.8, "core_migration": 1.0}
    )
    
    enabled_features: List[str] = Field(
        ...,
        description="List of enabled features",
        example=["use_new_execution_layer", "use_browser_pooling"]
    )
    
    active_workflows: int = Field(
        ...,
        description="Number of active workflows",
        example=3
    )
    
    queue_status: Dict[str, Any] = Field(
        ...,
        description="Task queue status",
        example={"queued_tasks": 5, "running_tasks": 2}
    )
    
    timestamp: str = Field(
        ...,
        description="Status timestamp"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )


class MetricsResponse(BaseModel):
    """Response model for system metrics."""
    
    metrics: Dict[str, Any] = Field(
        ...,
        description="System metrics data",
        example={
            "workflow_engine": {"total_workflows": 100, "success_rate": 0.95},
            "task_scheduler": {"queued_tasks": 10, "completed_tasks": 50}
        }
    )
    
    timestamp: str = Field(
        ...,
        description="Metrics timestamp"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )


class FeatureFlagResponse(BaseModel):
    """Response model for feature flag operations."""
    
    flags: Dict[str, bool] = Field(
        ...,
        description="All feature flags and their states",
        example={"use_new_execution_layer": True, "use_browser_pooling": False}
    )
    
    enabled_flags: List[str] = Field(
        ...,
        description="List of enabled flags",
        example=["use_new_execution_layer", "enable_health_checks"]
    )
    
    migration_status: Dict[str, Any] = Field(
        ...,
        description="Migration status",
        example={"migration_progress": 0.6, "core_migration": 0.8}
    )
    
    timestamp: str = Field(
        ...,
        description="Response timestamp"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )


class SystemConfigResponse(BaseModel):
    """Response model for system configuration."""
    
    config_section: str = Field(
        ...,
        description="Configuration section",
        example="execution"
    )
    
    config_data: Dict[str, Any] = Field(
        ...,
        description="Configuration data",
        example={"max_concurrent_tasks": 10, "default_timeout": 600}
    )
    
    timestamp: str = Field(
        ...,
        description="Configuration timestamp"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )


class MigrationResponse(BaseModel):
    """Response model for migration operations."""
    
    phase: int = Field(
        ...,
        description="Migration phase",
        example=2
    )
    
    migration_status: Dict[str, Any] = Field(
        ...,
        description="Detailed migration status",
        example={"migration_progress": 0.75, "core_migration": 1.0}
    )
    
    enabled_flags: List[str] = Field(
        ...,
        description="Enabled feature flags",
        example=["use_new_execution_layer", "use_new_browser_manager"]
    )
    
    bridge_statistics: Optional[Dict[str, Any]] = Field(
        None,
        description="Legacy bridge statistics",
        example={"new_execution_count": 50, "legacy_execution_count": 10}
    )
    
    message: str = Field(
        ...,
        description="Migration message",
        example="Migration phase 2 enabled successfully"
    )
    
    timestamp: str = Field(
        ...,
        description="Migration timestamp"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )


class SystemInfoResponse(BaseModel):
    """Response model for system information."""
    
    version: Dict[str, str] = Field(
        ...,
        description="Version information",
        example={"api_version": "1.0.0", "system_version": "2.0.0"}
    )
    
    features: Dict[str, Any] = Field(
        ...,
        description="Feature information",
        example={"migration_progress": 0.8, "total_flags": 15}
    )
    
    components: Dict[str, bool] = Field(
        ...,
        description="Component availability",
        example={"workflow_engine": True, "task_scheduler": True}
    )
    
    statistics: Dict[str, Any] = Field(
        ...,
        description="System statistics",
        example={"total_workflows": 100, "success_rate": 0.95}
    )
    
    timestamp: str = Field(
        ...,
        description="Information timestamp"
    )
    
    correlation_id: str = Field(
        ...,
        description="Request correlation ID"
    )
