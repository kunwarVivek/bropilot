"""
Unit tests for orchestration components.

This module tests the workflow engine, task scheduler, and their integration
with other orchestration components.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from core.interfaces import (
    TaskDefinition, WorkflowDefinition, ExecutionResult, 
    TaskStatus, WorkflowStatus
)
from core.exceptions import WorkflowExecutionError, SchedulingError, ValidationError
from src.orchestration.workflow_engine import WorkflowEngine, WorkflowExecutionMode
from src.orchestration.task_scheduler import (
    TaskScheduler, SchedulingStrategy, TaskState, ScheduledTask,
    ResourcePool, create_task_scheduler
)
from src.orchestration.dependency_graph import TaskPriority


@pytest.fixture
def mock_task_executor():
    """Create a mock task executor."""
    executor = Mock()
    executor.execute_task = AsyncMock()
    return executor


@pytest.fixture
def mock_state_manager():
    """Create a mock state manager."""
    manager = Mock()
    manager.initialize = AsyncMock()
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    manager.shutdown = AsyncMock()
    return manager


@pytest.fixture
def mock_parallel_executor():
    """Create a mock parallel executor."""
    executor = Mock()
    executor.initialize = AsyncMock()
    executor.execute_tasks = AsyncMock()
    executor.execute_dependency_graph = AsyncMock()
    executor.health_check = AsyncMock(return_value={"status": "healthy"})
    executor.shutdown = AsyncMock()
    return executor


@pytest.fixture
def mock_workflow_controller():
    """Create a mock workflow controller."""
    controller = Mock()
    controller.pause_workflow = AsyncMock(return_value=True)
    controller.resume_workflow = AsyncMock(return_value=True)
    controller.cancel_workflow = AsyncMock(return_value=True)
    controller.get_workflow_status = AsyncMock(return_value=WorkflowStatus.RUNNING)
    return controller


@pytest.fixture
def sample_task_definition():
    """Create a sample task definition."""
    return TaskDefinition(
        name="test_task",
        description="A test task",
        prompt_template="Execute test task",
        timeout=60,
        retry_count=3,
        metadata={"test": True}
    )


@pytest.fixture
def sample_workflow_definition():
    """Create a sample workflow definition."""
    return WorkflowDefinition(
        name="test_workflow",
        description="A test workflow",
        tasks=["task1", "task2", "task3"],
        metadata={"test": True}
    )


class TestWorkflowEngine:
    """Test cases for WorkflowEngine."""
    
    def test_init(
        self, 
        mock_task_executor, 
        mock_state_manager, 
        mock_parallel_executor,
        mock_workflow_controller
    ):
        """Test WorkflowEngine initialization."""
        engine = WorkflowEngine(
            task_executor=mock_task_executor,
            state_manager=mock_state_manager,
            parallel_executor=mock_parallel_executor,
            workflow_controller=mock_workflow_controller,
            default_execution_mode=WorkflowExecutionMode.PARALLEL
        )
        
        assert engine.task_executor == mock_task_executor
        assert engine.state_manager == mock_state_manager
        assert engine.parallel_executor == mock_parallel_executor
        assert engine.workflow_controller == mock_workflow_controller
        assert engine.default_execution_mode == WorkflowExecutionMode.PARALLEL
        assert len(engine.active_workflows) == 0
        assert engine.total_workflows == 0
    
    @pytest.mark.asyncio
    async def test_initialize(
        self, 
        mock_task_executor, 
        mock_state_manager, 
        mock_parallel_executor
    ):
        """Test WorkflowEngine initialization."""
        engine = WorkflowEngine(
            task_executor=mock_task_executor,
            state_manager=mock_state_manager,
            parallel_executor=mock_parallel_executor
        )
        
        await engine.initialize()
        
        mock_state_manager.initialize.assert_called_once()
        mock_parallel_executor.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_workflow_sequential(
        self, 
        mock_task_executor, 
        sample_workflow_definition
    ):
        """Test sequential workflow execution."""
        # Setup mock task executor
        mock_result = ExecutionResult(
            status=TaskStatus.COMPLETED,
            result="Task completed",
            execution_time=5.0,
            metadata={}
        )
        mock_task_executor.execute_task.return_value = mock_result
        
        engine = WorkflowEngine(task_executor=mock_task_executor)
        
        context = {
            "execution_mode": "sequential",
            "workflow_id": "test_workflow_123"
        }
        
        results = await engine.execute_workflow(sample_workflow_definition, context)
        
        assert len(results) == 3
        assert all(result.status == TaskStatus.COMPLETED for result in results.values())
        assert mock_task_executor.execute_task.call_count == 3
        assert engine.total_workflows == 1
        assert engine.successful_workflows == 1
    
    @pytest.mark.asyncio
    async def test_execute_workflow_parallel(
        self, 
        mock_task_executor, 
        mock_parallel_executor,
        sample_workflow_definition
    ):
        """Test parallel workflow execution."""
        # Setup mock parallel executor
        mock_results = {
            "task1": ExecutionResult(status=TaskStatus.COMPLETED, result="Result 1"),
            "task2": ExecutionResult(status=TaskStatus.COMPLETED, result="Result 2"),
            "task3": ExecutionResult(status=TaskStatus.COMPLETED, result="Result 3")
        }
        mock_parallel_executor.execute_tasks.return_value = mock_results
        
        engine = WorkflowEngine(
            task_executor=mock_task_executor,
            parallel_executor=mock_parallel_executor
        )
        
        context = {
            "execution_mode": "parallel",
            "workflow_id": "test_workflow_456"
        }
        
        results = await engine.execute_workflow(sample_workflow_definition, context)
        
        assert len(results) == 3
        assert all(result.status == TaskStatus.COMPLETED for result in results.values())
        mock_parallel_executor.execute_tasks.assert_called_once()
        assert engine.successful_workflows == 1
    
    @pytest.mark.asyncio
    async def test_execute_workflow_validation_error(
        self, 
        mock_task_executor
    ):
        """Test workflow execution with validation error."""
        engine = WorkflowEngine(task_executor=mock_task_executor)
        
        # Invalid workflow (no tasks)
        invalid_workflow = WorkflowDefinition(
            name="invalid_workflow",
            description="Invalid workflow",
            tasks=[],
            metadata={}
        )
        
        context = {"workflow_id": "invalid_123"}
        
        with pytest.raises(WorkflowExecutionError):
            await engine.execute_workflow(invalid_workflow, context)
        
        assert engine.failed_workflows == 1
    
    @pytest.mark.asyncio
    async def test_pause_resume_cancel_workflow(
        self, 
        mock_task_executor, 
        mock_workflow_controller
    ):
        """Test workflow control operations."""
        engine = WorkflowEngine(
            task_executor=mock_task_executor,
            workflow_controller=mock_workflow_controller
        )
        
        workflow_id = "test_workflow_789"
        
        # Test pause
        result = await engine.pause_workflow(workflow_id)
        assert result is True
        mock_workflow_controller.pause_workflow.assert_called_with(workflow_id)
        
        # Test resume
        result = await engine.resume_workflow(workflow_id)
        assert result is True
        mock_workflow_controller.resume_workflow.assert_called_with(workflow_id)
        
        # Test cancel
        result = await engine.cancel_workflow(workflow_id)
        assert result is True
        mock_workflow_controller.cancel_workflow.assert_called_with(workflow_id)
    
    @pytest.mark.asyncio
    async def test_get_workflow_status(
        self, 
        mock_task_executor, 
        mock_workflow_controller
    ):
        """Test getting workflow status."""
        engine = WorkflowEngine(
            task_executor=mock_task_executor,
            workflow_controller=mock_workflow_controller
        )
        
        workflow_id = "test_workflow_status"
        
        status = await engine.get_workflow_status(workflow_id)
        assert status == WorkflowStatus.RUNNING
        mock_workflow_controller.get_workflow_status.assert_called_with(workflow_id)
    
    def test_get_statistics(self, mock_task_executor):
        """Test getting workflow engine statistics."""
        engine = WorkflowEngine(task_executor=mock_task_executor)
        
        # Simulate some activity
        engine.total_workflows = 10
        engine.successful_workflows = 8
        engine.failed_workflows = 2
        
        stats = engine.get_statistics()
        
        assert stats["total_workflows"] == 10
        assert stats["successful_workflows"] == 8
        assert stats["failed_workflows"] == 2
        assert stats["success_rate"] == 0.8
        assert stats["active_workflows"] == 0
        assert stats["default_execution_mode"] == "dependency_based"
    
    @pytest.mark.asyncio
    async def test_health_check(
        self, 
        mock_task_executor, 
        mock_state_manager, 
        mock_parallel_executor
    ):
        """Test workflow engine health check."""
        engine = WorkflowEngine(
            task_executor=mock_task_executor,
            state_manager=mock_state_manager,
            parallel_executor=mock_parallel_executor
        )
        
        health = await engine.health_check()
        
        assert health["status"] == "healthy"
        assert health["engine"] == "workflow_engine"
        assert "statistics" in health
        assert "state_manager" in health
        assert "parallel_executor" in health
    
    @pytest.mark.asyncio
    async def test_shutdown(
        self, 
        mock_task_executor, 
        mock_state_manager, 
        mock_parallel_executor,
        mock_workflow_controller
    ):
        """Test workflow engine shutdown."""
        engine = WorkflowEngine(
            task_executor=mock_task_executor,
            state_manager=mock_state_manager,
            parallel_executor=mock_parallel_executor,
            workflow_controller=mock_workflow_controller
        )
        
        # Add some active workflows
        engine.active_workflows["workflow1"] = {"test": "data"}
        engine.active_workflows["workflow2"] = {"test": "data"}
        
        await engine.shutdown()
        
        # Should attempt to cancel active workflows
        assert mock_workflow_controller.cancel_workflow.call_count == 2
        mock_parallel_executor.shutdown.assert_called_once()
        mock_state_manager.shutdown.assert_called_once()


class TestTaskScheduler:
    """Test cases for TaskScheduler."""
    
    def test_init(self):
        """Test TaskScheduler initialization."""
        resource_pool = ResourcePool(
            max_concurrent_tasks=3,
            available_memory=4.0,
            available_cpu=2.0,
            available_browsers=2
        )
        
        scheduler = TaskScheduler(
            strategy=SchedulingStrategy.PRIORITY,
            resource_pool=resource_pool
        )
        
        assert scheduler.strategy == SchedulingStrategy.PRIORITY
        assert scheduler.resource_pool == resource_pool
        assert len(scheduler.task_queue) == 0
        assert len(scheduler.running_tasks) == 0
        assert scheduler.total_scheduled == 0
        assert scheduler.is_running is False
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test scheduler start and stop."""
        scheduler = TaskScheduler()
        
        # Test start
        await scheduler.start()
        assert scheduler.is_running is True
        assert scheduler.scheduler_task is not None
        
        # Test stop
        await scheduler.stop()
        assert scheduler.is_running is False
    
    @pytest.mark.asyncio
    async def test_schedule_task(self, sample_task_definition):
        """Test task scheduling."""
        scheduler = TaskScheduler()
        
        task_id = await scheduler.schedule_task(
            task_definition=sample_task_definition,
            priority=TaskPriority.HIGH,
            estimated_duration=30.0
        )
        
        assert task_id is not None
        assert scheduler.total_scheduled == 1
        assert len(scheduler.task_queue) == 1
        
        # Check task in queue
        scheduled_task = scheduler.task_queue[0]
        assert scheduled_task.task_id == task_id
        assert scheduled_task.priority == TaskPriority.HIGH
        assert scheduled_task.estimated_duration == 30.0
        assert scheduled_task.state == TaskState.QUEUED
    
    @pytest.mark.asyncio
    async def test_schedule_task_with_dependencies(self, sample_task_definition):
        """Test task scheduling with dependencies."""
        scheduler = TaskScheduler()
        
        # Schedule first task
        task1_id = await scheduler.schedule_task(sample_task_definition)
        
        # Schedule second task with dependency on first
        task2_id = await scheduler.schedule_task(
            sample_task_definition,
            dependencies={task1_id}
        )
        
        assert scheduler.total_scheduled == 2
        
        # Find the dependent task
        dependent_task = None
        for task in scheduler.task_queue:
            if task.task_id == task2_id:
                dependent_task = task
                break
        
        assert dependent_task is not None
        assert dependent_task.state == TaskState.WAITING_DEPENDENCIES
        assert task1_id in dependent_task.dependencies
    
    @pytest.mark.asyncio
    async def test_cancel_task(self, sample_task_definition):
        """Test task cancellation."""
        scheduler = TaskScheduler()
        
        # Schedule a task
        task_id = await scheduler.schedule_task(sample_task_definition)
        assert len(scheduler.task_queue) == 1
        
        # Cancel the task
        result = await scheduler.cancel_task(task_id)
        assert result is True
        assert len(scheduler.task_queue) == 0
        assert task_id in scheduler.failed_tasks
        assert scheduler.failed_tasks[task_id].state == TaskState.CANCELLED
    
    def test_get_task_status(self, sample_task_definition):
        """Test getting task status."""
        scheduler = TaskScheduler()
        
        # Test non-existent task
        status = scheduler.get_task_status("non_existent")
        assert status is None
        
        # Add a task to queue
        task = ScheduledTask(
            task_id="test_task_123",
            task_definition=sample_task_definition,
            priority=TaskPriority.MEDIUM,
            estimated_duration=60.0,
            dependencies=set(),
            resource_requirements={}
        )
        scheduler.task_queue.append(task)
        
        # Test queued task
        status = scheduler.get_task_status("test_task_123")
        assert status == TaskState.QUEUED
    
    def test_get_queue_status(self):
        """Test getting queue status."""
        scheduler = TaskScheduler()
        
        # Simulate some activity
        scheduler.total_scheduled = 10
        scheduler.total_completed = 7
        scheduler.total_failed = 2
        
        status = scheduler.get_queue_status()
        
        assert status["total_scheduled"] == 10
        assert status["total_completed"] == 7
        assert status["total_failed"] == 2
        assert status["success_rate"] == 0.7
        assert status["strategy"] == SchedulingStrategy.INTELLIGENT.value
        assert status["is_running"] is False
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test scheduler health check."""
        scheduler = TaskScheduler()
        
        health = await scheduler.health_check()
        
        assert health["status"] == "stopped"  # Not running
        assert health["scheduler"] == "task_scheduler"
        assert "queue_status" in health
        assert "resource_pool" in health


class TestResourcePool:
    """Test cases for ResourcePool."""
    
    def test_can_allocate(self):
        """Test resource allocation checking."""
        pool = ResourcePool(
            max_concurrent_tasks=5,
            available_memory=4.0,
            available_cpu=2.0,
            available_browsers=3
        )
        
        # Test valid allocation
        requirements = {"memory": 1.0, "cpu": 0.5, "browsers": 1}
        assert pool.can_allocate(requirements) is True
        
        # Test invalid allocation (too much memory)
        requirements = {"memory": 5.0, "cpu": 0.5, "browsers": 1}
        assert pool.can_allocate(requirements) is False
    
    def test_allocate_deallocate(self):
        """Test resource allocation and deallocation."""
        pool = ResourcePool(
            max_concurrent_tasks=5,
            available_memory=4.0,
            available_cpu=2.0,
            available_browsers=3
        )
        
        requirements = {"memory": 1.0, "cpu": 0.5, "browsers": 1}
        
        # Test allocation
        pool.allocate(requirements)
        assert pool.available_memory == 3.0
        assert pool.available_cpu == 1.5
        assert pool.available_browsers == 2
        
        # Test deallocation
        pool.deallocate(requirements)
        assert pool.available_memory == 4.0
        assert pool.available_cpu == 2.0
        assert pool.available_browsers == 3


class TestFactoryFunctions:
    """Test cases for factory functions."""
    
    def test_create_task_scheduler(self):
        """Test task scheduler factory function."""
        scheduler = create_task_scheduler(
            strategy=SchedulingStrategy.PRIORITY,
            max_concurrent_tasks=10,
            available_memory=16.0,
            available_cpu=8.0,
            available_browsers=5
        )
        
        assert isinstance(scheduler, TaskScheduler)
        assert scheduler.strategy == SchedulingStrategy.PRIORITY
        assert scheduler.resource_pool.max_concurrent_tasks == 10
        assert scheduler.resource_pool.available_memory == 16.0
        assert scheduler.resource_pool.available_cpu == 8.0
        assert scheduler.resource_pool.available_browsers == 5
