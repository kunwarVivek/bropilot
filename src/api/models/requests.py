"""
API request models.

This module contains Pydantic models for validating API request payloads.
All models include proper validation, documentation, and examples.
"""

from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field, validator
from datetime import datetime


class WorkflowExecutionRequest(BaseModel):
    """Request model for workflow execution."""
    
    workflow_name: Optional[str] = Field(
        None,
        description="Name of the workflow",
        example="user_registration_workflow"
    )
    
    workflow_id: Optional[str] = Field(
        None,
        description="Optional workflow ID for tracking",
        example="wf_12345"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the workflow",
        example="Complete user registration process"
    )
    
    tasks: List[str] = Field(
        ...,
        description="List of task names to execute",
        example=["auth", "fill_form", "submit"]
    )
    
    execution_mode: str = Field(
        "dependency_based",
        description="Execution mode for the workflow",
        example="parallel"
    )
    
    async_execution: bool = Field(
        False,
        description="Whether to execute workflow asynchronously",
        example=False
    )
    
    timeout: int = Field(
        300,
        description="Workflow timeout in seconds",
        ge=1,
        le=3600,
        example=300
    )
    
    continue_on_failure: bool = Field(
        False,
        description="Whether to continue execution if a task fails",
        example=False
    )
    
    max_concurrent_tasks: int = Field(
        5,
        description="Maximum number of concurrent tasks",
        ge=1,
        le=20,
        example=5
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for workflow execution",
        example={"target_url": "https://example.com", "headless": True}
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the workflow",
        example={"priority": "high", "department": "qa"}
    )
    
    @validator('execution_mode')
    def validate_execution_mode(cls, v):
        valid_modes = ["sequential", "parallel", "dependency_based", "hybrid"]
        if v not in valid_modes:
            raise ValueError(f"execution_mode must be one of {valid_modes}")
        return v
    
    @validator('tasks')
    def validate_tasks(cls, v):
        if not v:
            raise ValueError("At least one task must be specified")
        return v


class WorkflowControlRequest(BaseModel):
    """Request model for workflow control operations."""
    
    action: str = Field(
        ...,
        description="Control action to perform",
        example="pause"
    )
    
    reason: Optional[str] = Field(
        None,
        description="Reason for the control action",
        example="System maintenance"
    )
    
    @validator('action')
    def validate_action(cls, v):
        valid_actions = ["pause", "resume", "cancel"]
        if v not in valid_actions:
            raise ValueError(f"action must be one of {valid_actions}")
        return v


class WorkflowScheduleRequest(BaseModel):
    """Request model for workflow scheduling."""
    
    workflow_name: str = Field(
        ...,
        description="Name of the workflow to schedule",
        example="daily_report_workflow"
    )
    
    schedule: str = Field(
        ...,
        description="Cron expression for scheduling",
        example="0 9 * * 1-5"
    )
    
    tasks: List[str] = Field(
        ...,
        description="List of task names to execute",
        example=["generate_report", "send_email"]
    )
    
    enabled: bool = Field(
        True,
        description="Whether the schedule is enabled",
        example=True
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Context for scheduled workflow execution"
    )


class TaskExecutionRequest(BaseModel):
    """Request model for individual task execution."""
    
    task_name: str = Field(
        ...,
        description="Name of the task to execute",
        example="login_task"
    )
    
    task_id: Optional[str] = Field(
        None,
        description="Optional task ID for tracking",
        example="task_12345"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the task",
        example="Login to the application"
    )
    
    prompt_template: str = Field(
        ...,
        description="Task prompt template",
        example="Navigate to login page and enter credentials"
    )
    
    timeout: int = Field(
        300,
        description="Task timeout in seconds",
        ge=1,
        le=1800,
        example=300
    )
    
    retry_count: int = Field(
        3,
        description="Number of retry attempts",
        ge=0,
        le=10,
        example=3
    )
    
    target_url: Optional[str] = Field(
        None,
        description="Target URL for browser tasks",
        example="https://example.com/login"
    )
    
    headless: bool = Field(
        True,
        description="Whether to run browser in headless mode",
        example=True
    )
    
    use_vision: bool = Field(
        True,
        description="Whether to use vision capabilities",
        example=True
    )
    
    browser_config: Optional[Dict[str, Any]] = Field(
        None,
        description="Browser configuration options",
        example={"viewport": {"width": 1920, "height": 1080}}
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for task execution"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the task"
    )


class TaskScheduleRequest(BaseModel):
    """Request model for task scheduling."""
    
    task_name: str = Field(
        ...,
        description="Name of the task to schedule",
        example="data_backup_task"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the task",
        example="Backup database data"
    )
    
    prompt_template: str = Field(
        ...,
        description="Task prompt template",
        example="Perform database backup operation"
    )
    
    priority: str = Field(
        "medium",
        description="Task priority level",
        example="high"
    )
    
    timeout: int = Field(
        300,
        description="Task timeout in seconds",
        ge=1,
        le=1800,
        example=300
    )
    
    retry_count: int = Field(
        3,
        description="Number of retry attempts",
        ge=0,
        le=10,
        example=3
    )
    
    estimated_duration: Optional[float] = Field(
        None,
        description="Estimated execution time in seconds",
        ge=1,
        example=120.0
    )
    
    dependencies: Optional[List[str]] = Field(
        None,
        description="List of task IDs this task depends on",
        example=["task_001", "task_002"]
    )
    
    resource_requirements: Optional[Dict[str, Any]] = Field(
        None,
        description="Resource requirements for the task",
        example={"memory": 1.0, "cpu": 0.5, "browsers": 1}
    )
    
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context for task execution"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the task"
    )
    
    @validator('priority')
    def validate_priority(cls, v):
        valid_priorities = ["low", "medium", "high", "critical"]
        if v.lower() not in valid_priorities:
            raise ValueError(f"priority must be one of {valid_priorities}")
        return v.lower()


class TaskTemplateRequest(BaseModel):
    """Request model for task template operations."""
    
    template_name: str = Field(
        ...,
        description="Name of the task template",
        example="login_template"
    )
    
    template_content: str = Field(
        ...,
        description="Content of the task template",
        example="Navigate to {url} and login with {username} and {password}"
    )
    
    description: Optional[str] = Field(
        None,
        description="Description of the template",
        example="Generic login template"
    )
    
    variables: Optional[List[str]] = Field(
        None,
        description="List of template variables",
        example=["url", "username", "password"]
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the template"
    )


class FeatureFlagRequest(BaseModel):
    """Request model for feature flag operations."""
    
    reason: Optional[str] = Field(
        None,
        description="Reason for the feature flag change",
        example="Enable new execution layer for testing"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the change"
    )


class SystemConfigRequest(BaseModel):
    """Request model for system configuration updates."""
    
    config_section: str = Field(
        ...,
        description="Configuration section to update",
        example="execution"
    )
    
    config_data: Dict[str, Any] = Field(
        ...,
        description="Configuration data to update",
        example={"max_concurrent_tasks": 10, "default_timeout": 600}
    )
    
    reason: Optional[str] = Field(
        None,
        description="Reason for the configuration change",
        example="Increase performance limits"
    )


class MigrationRequest(BaseModel):
    """Request model for migration operations."""
    
    reason: Optional[str] = Field(
        None,
        description="Reason for the migration",
        example="Enable phase 2 features for production"
    )
    
    force: bool = Field(
        False,
        description="Force migration even if there are warnings",
        example=False
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata for the migration"
    )
