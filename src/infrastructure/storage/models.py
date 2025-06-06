"""
Database models for test execution and results.

This module defines the database schema for storing workflow executions,
task results, and related metadata.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, Text, JSON, Boolean,
    ForeignKey, Float, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import sqlalchemy as sa

# Import the ExecutionStatus from core interfaces to maintain consistency
from core.interfaces import TaskStatus


Base = declarative_base()


class ExecutionStatus(str, Enum):
    """Execution status enumeration (mirrors TaskStatus from core)."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class WorkflowExecution(Base):
    """Workflow execution record."""
    
    __tablename__ = "workflow_executions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Workflow identification
    workflow_name = Column(String(255), nullable=False)
    workflow_version = Column(String(50), default="1.0.0")
    
    # Execution metadata
    status = Column(sa.Enum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    correlation_id = Column(String(255), nullable=False, index=True)
    
    # Timing information
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Configuration and context
    configuration = Column(JSON, nullable=True)
    context = Column(JSON, nullable=True)
    
    # Results and metadata
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Performance metrics
    execution_time_seconds = Column(Float, nullable=True)
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    
    # Environment information
    environment = Column(String(50), nullable=True)
    executor_node = Column(String(255), nullable=True)
    
    # Relationships
    task_executions = relationship("TaskExecution", back_populates="workflow_execution", cascade="all, delete-orphan")
    checkpoints = relationship("ExecutionCheckpoint", back_populates="workflow_execution", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_workflow_status', 'status'),
        Index('idx_workflow_created_at', 'created_at'),
        Index('idx_workflow_name_status', 'workflow_name', 'status'),
        Index('idx_correlation_id', 'correlation_id'),
    )
    
    def __repr__(self):
        return f"<WorkflowExecution(id={self.id}, name={self.workflow_name}, status={self.status})>"


class TaskExecution(Base):
    """Task execution record."""
    
    __tablename__ = "task_executions"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to workflow
    workflow_execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    
    # Task identification
    task_name = Column(String(255), nullable=False)
    task_order = Column(Integer, nullable=False)
    
    # Execution metadata
    status = Column(sa.Enum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    correlation_id = Column(String(255), nullable=False, index=True)
    
    # Timing information
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Task configuration
    task_definition = Column(JSON, nullable=True)
    task_parameters = Column(JSON, nullable=True)
    
    # Results and metadata
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Performance metrics
    execution_time_seconds = Column(Float, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # Browser and LLM information
    browser_session_id = Column(String(255), nullable=True)
    llm_provider = Column(String(50), nullable=True)
    llm_model = Column(String(100), nullable=True)
    llm_token_usage = Column(JSON, nullable=True)
    
    # Logs and artifacts
    log_file_path = Column(String(500), nullable=True)
    screenshot_paths = Column(JSON, nullable=True)  # Array of screenshot file paths
    conversation_path = Column(String(500), nullable=True)
    
    # Relationships
    workflow_execution = relationship("WorkflowExecution", back_populates="task_executions")
    
    # Indexes
    __table_args__ = (
        Index('idx_task_workflow_id', 'workflow_execution_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_created_at', 'created_at'),
        Index('idx_task_name_status', 'task_name', 'status'),
        UniqueConstraint('workflow_execution_id', 'task_order', name='uq_workflow_task_order'),
    )
    
    def __repr__(self):
        return f"<TaskExecution(id={self.id}, name={self.task_name}, status={self.status})>"


class ExecutionCheckpoint(Base):
    """Execution checkpoint for state persistence."""
    
    __tablename__ = "execution_checkpoints"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign key to workflow
    workflow_execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    
    # Checkpoint metadata
    checkpoint_name = Column(String(255), nullable=False)
    checkpoint_type = Column(String(50), nullable=False)  # 'automatic', 'manual', 'error'
    
    # Timing information
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # State data
    execution_state = Column(JSON, nullable=False)
    browser_state = Column(JSON, nullable=True)
    context_variables = Column(JSON, nullable=True)
    
    # Metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags for categorization
    
    # Relationships
    workflow_execution = relationship("WorkflowExecution", back_populates="checkpoints")
    
    # Indexes
    __table_args__ = (
        Index('idx_checkpoint_workflow_id', 'workflow_execution_id'),
        Index('idx_checkpoint_created_at', 'created_at'),
        Index('idx_checkpoint_name', 'checkpoint_name'),
        UniqueConstraint('workflow_execution_id', 'checkpoint_name', name='uq_workflow_checkpoint_name'),
    )
    
    def __repr__(self):
        return f"<ExecutionCheckpoint(id={self.id}, name={self.checkpoint_name})>"


class TaskTemplate(Base):
    """Task template definitions."""
    
    __tablename__ = "task_templates"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template identification
    name = Column(String(255), nullable=False, unique=True)
    version = Column(String(50), default="1.0.0")
    
    # Template metadata
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags
    
    # Template definition
    prompt_template = Column(Text, nullable=False)
    default_parameters = Column(JSON, nullable=True)
    
    # Configuration
    default_timeout = Column(Integer, default=300)
    default_retry_count = Column(Integer, default=3)
    required_capabilities = Column(JSON, nullable=True)  # Array of required capabilities
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_deprecated = Column(Boolean, default=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_task_template_name', 'name'),
        Index('idx_task_template_category', 'category'),
        Index('idx_task_template_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<TaskTemplate(id={self.id}, name={self.name}, version={self.version})>"


class WorkflowTemplate(Base):
    """Workflow template definitions."""
    
    __tablename__ = "workflow_templates"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Template identification
    name = Column(String(255), nullable=False, unique=True)
    version = Column(String(50), default="1.0.0")
    
    # Template metadata
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    tags = Column(JSON, nullable=True)  # Array of tags
    
    # Workflow definition
    task_sequence = Column(JSON, nullable=False)  # Array of task names in order
    default_configuration = Column(JSON, nullable=True)
    
    # Configuration
    default_timeout = Column(Integer, default=1800)  # 30 minutes
    parallel_execution = Column(Boolean, default=False)
    checkpoint_interval = Column(Integer, default=60)  # seconds
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(String(255), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    is_deprecated = Column(Boolean, default=False)
    
    # Indexes
    __table_args__ = (
        Index('idx_workflow_template_name', 'name'),
        Index('idx_workflow_template_category', 'category'),
        Index('idx_workflow_template_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<WorkflowTemplate(id={self.id}, name={self.name}, version={self.version})>"


class ExecutionMetrics(Base):
    """Execution metrics and performance data."""
    
    __tablename__ = "execution_metrics"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign keys
    workflow_execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=True)
    task_execution_id = Column(UUID(as_uuid=True), ForeignKey("task_executions.id"), nullable=True)
    
    # Metric identification
    metric_name = Column(String(255), nullable=False)
    metric_type = Column(String(50), nullable=False)  # 'counter', 'gauge', 'histogram', 'timer'
    
    # Metric data
    value = Column(Float, nullable=False)
    unit = Column(String(50), nullable=True)
    tags = Column(JSON, nullable=True)  # Key-value pairs for metric tags
    
    # Timing
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('idx_metrics_workflow_id', 'workflow_execution_id'),
        Index('idx_metrics_task_id', 'task_execution_id'),
        Index('idx_metrics_name', 'metric_name'),
        Index('idx_metrics_timestamp', 'timestamp'),
        Index('idx_metrics_name_timestamp', 'metric_name', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<ExecutionMetrics(id={self.id}, name={self.metric_name}, value={self.value})>"
