"""
Repository layer for data access.

This module provides repository classes for accessing and manipulating
database entities with proper abstraction and error handling.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.interfaces import TaskStatus, WorkflowStatus
from core.exceptions import ResourceNotFoundError, DataIntegrityError
from .models import (
    WorkflowExecution, TaskExecution, ExecutionCheckpoint,
    TaskTemplate, WorkflowTemplate, ExecutionMetrics, ExecutionStatus
)


class BaseRepository:
    """Base repository with common functionality."""
    
    def __init__(self, session: AsyncSession):
        """Initialize repository with database session."""
        self.session = session


class WorkflowExecutionRepository(BaseRepository):
    """Repository for workflow execution data."""
    
    async def create(
        self,
        workflow_name: str,
        correlation_id: str,
        configuration: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        environment: Optional[str] = None
    ) -> WorkflowExecution:
        """Create a new workflow execution."""
        
        workflow_execution = WorkflowExecution(
            workflow_name=workflow_name,
            correlation_id=correlation_id,
            configuration=configuration,
            context=context,
            environment=environment,
            status=ExecutionStatus.PENDING
        )
        
        self.session.add(workflow_execution)
        await self.session.flush()
        return workflow_execution
    
    async def get_by_id(self, execution_id: uuid.UUID) -> Optional[WorkflowExecution]:
        """Get workflow execution by ID."""
        
        stmt = select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_correlation_id(self, correlation_id: str) -> Optional[WorkflowExecution]:
        """Get workflow execution by correlation ID."""
        
        stmt = select(WorkflowExecution).where(
            WorkflowExecution.correlation_id == correlation_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_tasks(self, execution_id: uuid.UUID) -> Optional[WorkflowExecution]:
        """Get workflow execution with all task executions."""
        
        stmt = select(WorkflowExecution).options(
            selectinload(WorkflowExecution.task_executions)
        ).where(WorkflowExecution.id == execution_id)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        execution_id: uuid.UUID,
        status: ExecutionStatus,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update workflow execution status."""
        
        update_data = {"status": status}
        
        if status == ExecutionStatus.RUNNING and not await self._get_started_at(execution_id):
            update_data["started_at"] = datetime.utcnow()
        elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]:
            update_data["completed_at"] = datetime.utcnow()
        
        if error_message:
            update_data["error_message"] = error_message
        
        if result:
            update_data["result"] = result
        
        stmt = update(WorkflowExecution).where(
            WorkflowExecution.id == execution_id
        ).values(**update_data)
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def _get_started_at(self, execution_id: uuid.UUID) -> Optional[datetime]:
        """Get the started_at timestamp for a workflow execution."""
        stmt = select(WorkflowExecution.started_at).where(
            WorkflowExecution.id == execution_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_recent(
        self,
        limit: int = 50,
        status: Optional[ExecutionStatus] = None,
        workflow_name: Optional[str] = None
    ) -> List[WorkflowExecution]:
        """List recent workflow executions."""
        
        stmt = select(WorkflowExecution).order_by(WorkflowExecution.created_at.desc())
        
        if status:
            stmt = stmt.where(WorkflowExecution.status == status)
        
        if workflow_name:
            stmt = stmt.where(WorkflowExecution.workflow_name == workflow_name)
        
        stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def get_execution_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get execution statistics."""
        
        base_query = select(WorkflowExecution)
        
        if start_date:
            base_query = base_query.where(WorkflowExecution.created_at >= start_date)
        
        if end_date:
            base_query = base_query.where(WorkflowExecution.created_at <= end_date)
        
        # Count by status
        status_counts = {}
        for status in ExecutionStatus:
            stmt = select(func.count()).select_from(
                base_query.where(WorkflowExecution.status == status).subquery()
            )
            result = await self.session.execute(stmt)
            status_counts[status.value] = result.scalar()
        
        # Average execution time
        avg_time_stmt = select(func.avg(WorkflowExecution.execution_time_seconds)).select_from(
            base_query.where(WorkflowExecution.execution_time_seconds.isnot(None)).subquery()
        )
        avg_time_result = await self.session.execute(avg_time_stmt)
        avg_execution_time = avg_time_result.scalar()
        
        return {
            "status_counts": status_counts,
            "average_execution_time_seconds": avg_execution_time,
            "total_executions": sum(status_counts.values())
        }


class TaskExecutionRepository(BaseRepository):
    """Repository for task execution data."""
    
    async def create(
        self,
        workflow_execution_id: uuid.UUID,
        task_name: str,
        task_order: int,
        correlation_id: str,
        task_definition: Optional[Dict[str, Any]] = None,
        task_parameters: Optional[Dict[str, Any]] = None
    ) -> TaskExecution:
        """Create a new task execution."""
        
        task_execution = TaskExecution(
            workflow_execution_id=workflow_execution_id,
            task_name=task_name,
            task_order=task_order,
            correlation_id=correlation_id,
            task_definition=task_definition,
            task_parameters=task_parameters,
            status=ExecutionStatus.PENDING
        )
        
        self.session.add(task_execution)
        await self.session.flush()
        return task_execution
    
    async def get_by_id(self, execution_id: uuid.UUID) -> Optional[TaskExecution]:
        """Get task execution by ID."""
        
        stmt = select(TaskExecution).where(TaskExecution.id == execution_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_workflow(self, workflow_execution_id: uuid.UUID) -> List[TaskExecution]:
        """Get all task executions for a workflow."""
        
        stmt = select(TaskExecution).where(
            TaskExecution.workflow_execution_id == workflow_execution_id
        ).order_by(TaskExecution.task_order)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_status(
        self,
        execution_id: uuid.UUID,
        status: ExecutionStatus,
        error_message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        execution_time: Optional[float] = None
    ) -> bool:
        """Update task execution status."""
        
        update_data = {"status": status}
        
        if status == ExecutionStatus.RUNNING:
            update_data["started_at"] = datetime.utcnow()
        elif status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.TIMEOUT]:
            update_data["completed_at"] = datetime.utcnow()
        
        if error_message:
            update_data["error_message"] = error_message
        
        if result:
            update_data["result"] = result
        
        if execution_time:
            update_data["execution_time_seconds"] = execution_time
        
        stmt = update(TaskExecution).where(
            TaskExecution.id == execution_id
        ).values(**update_data)
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def increment_retry_count(self, execution_id: uuid.UUID) -> bool:
        """Increment retry count for a task execution."""
        
        stmt = update(TaskExecution).where(
            TaskExecution.id == execution_id
        ).values(retry_count=TaskExecution.retry_count + 1)
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def get_failed_tasks(
        self,
        workflow_execution_id: Optional[uuid.UUID] = None,
        limit: int = 50
    ) -> List[TaskExecution]:
        """Get failed task executions."""
        
        stmt = select(TaskExecution).where(
            TaskExecution.status == ExecutionStatus.FAILED
        ).order_by(TaskExecution.created_at.desc())
        
        if workflow_execution_id:
            stmt = stmt.where(TaskExecution.workflow_execution_id == workflow_execution_id)
        
        stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()


class ExecutionCheckpointRepository(BaseRepository):
    """Repository for execution checkpoints."""
    
    async def create(
        self,
        workflow_execution_id: uuid.UUID,
        checkpoint_name: str,
        checkpoint_type: str,
        execution_state: Dict[str, Any],
        browser_state: Optional[Dict[str, Any]] = None,
        context_variables: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None
    ) -> ExecutionCheckpoint:
        """Create a new execution checkpoint."""
        
        checkpoint = ExecutionCheckpoint(
            workflow_execution_id=workflow_execution_id,
            checkpoint_name=checkpoint_name,
            checkpoint_type=checkpoint_type,
            execution_state=execution_state,
            browser_state=browser_state,
            context_variables=context_variables,
            description=description
        )
        
        self.session.add(checkpoint)
        await self.session.flush()
        return checkpoint
    
    async def get_latest(
        self,
        workflow_execution_id: uuid.UUID
    ) -> Optional[ExecutionCheckpoint]:
        """Get the latest checkpoint for a workflow execution."""
        
        stmt = select(ExecutionCheckpoint).where(
            ExecutionCheckpoint.workflow_execution_id == workflow_execution_id
        ).order_by(ExecutionCheckpoint.created_at.desc()).limit(1)
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_name(
        self,
        workflow_execution_id: uuid.UUID,
        checkpoint_name: str
    ) -> Optional[ExecutionCheckpoint]:
        """Get checkpoint by name."""
        
        stmt = select(ExecutionCheckpoint).where(
            and_(
                ExecutionCheckpoint.workflow_execution_id == workflow_execution_id,
                ExecutionCheckpoint.checkpoint_name == checkpoint_name
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_for_workflow(
        self,
        workflow_execution_id: uuid.UUID
    ) -> List[ExecutionCheckpoint]:
        """List all checkpoints for a workflow execution."""
        
        stmt = select(ExecutionCheckpoint).where(
            ExecutionCheckpoint.workflow_execution_id == workflow_execution_id
        ).order_by(ExecutionCheckpoint.created_at.desc())
        
        result = await self.session.execute(stmt)
        return result.scalars().all()


class ExecutionMetricsRepository(BaseRepository):
    """Repository for execution metrics."""
    
    async def record_metric(
        self,
        metric_name: str,
        metric_type: str,
        value: float,
        workflow_execution_id: Optional[uuid.UUID] = None,
        task_execution_id: Optional[uuid.UUID] = None,
        unit: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> ExecutionMetrics:
        """Record a new metric."""
        
        metric = ExecutionMetrics(
            workflow_execution_id=workflow_execution_id,
            task_execution_id=task_execution_id,
            metric_name=metric_name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            tags=tags
        )
        
        self.session.add(metric)
        await self.session.flush()
        return metric
    
    async def get_metrics(
        self,
        metric_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        workflow_execution_id: Optional[uuid.UUID] = None,
        limit: int = 1000
    ) -> List[ExecutionMetrics]:
        """Get metrics with optional filtering."""
        
        stmt = select(ExecutionMetrics).order_by(ExecutionMetrics.timestamp.desc())
        
        if metric_name:
            stmt = stmt.where(ExecutionMetrics.metric_name == metric_name)
        
        if start_time:
            stmt = stmt.where(ExecutionMetrics.timestamp >= start_time)
        
        if end_time:
            stmt = stmt.where(ExecutionMetrics.timestamp <= end_time)
        
        if workflow_execution_id:
            stmt = stmt.where(ExecutionMetrics.workflow_execution_id == workflow_execution_id)
        
        stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
