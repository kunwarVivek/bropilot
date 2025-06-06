"""
Unit tests for TaskExecutor implementation.

This module tests the core functionality of the TaskExecutor class
to ensure it properly implements the ITaskExecutor interface.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from core.interfaces import TaskDefinition, ExecutionResult, TaskStatus
from core.exceptions import TaskExecutionError, OperationCancelledError
from src.execution.task_executor import TaskExecutor


@pytest.fixture
def task_definition():
    """Create a sample task definition for testing."""
    return TaskDefinition(
        name="test_task",
        description="A test task for unit testing",
        prompt_template="Navigate to https://example.com and click the login button",
        timeout=60,
        retry_count=3,
        metadata={"test": True}
    )


@pytest.fixture
def execution_context():
    """Create a sample execution context for testing."""
    return {
        "task_id": "test_task_123",
        "correlation_id": "test_correlation_456",
        "target_url": "https://example.com",
        "headless": True,
        "use_vision": True
    }


@pytest.fixture
def mock_browser():
    """Create a mock browser instance."""
    browser = Mock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_agent():
    """Create a mock agent instance."""
    agent = Mock()
    agent.run = AsyncMock()
    
    # Mock agent history
    mock_history = Mock()
    mock_history.final_result = Mock(return_value="Task completed successfully")
    mock_history.save_to_file = Mock()
    agent.run.return_value = mock_history
    
    return agent


@pytest.fixture
def mock_llm():
    """Create a mock LLM provider."""
    llm = Mock()
    return llm


class TestTaskExecutor:
    """Test cases for TaskExecutor class."""
    
    def test_init(self):
        """Test TaskExecutor initialization."""
        executor = TaskExecutor(
            default_timeout=120,
            save_logs=False,
            logs_base_path="test_logs"
        )
        
        assert executor.default_timeout == 120
        assert executor.save_logs is False
        assert executor.logs_base_path == "test_logs"
        assert len(executor.active_tasks) == 0
        assert len(executor.paused_tasks) == 0
        assert len(executor.cancelled_tasks) == 0
    
    @pytest.mark.asyncio
    async def test_execute_task_success(
        self, 
        task_definition, 
        execution_context, 
        mock_browser, 
        mock_agent, 
        mock_llm
    ):
        """Test successful task execution."""
        executor = TaskExecutor(save_logs=False)
        
        with patch.object(executor, '_create_browser', return_value=mock_browser), \
             patch.object(executor, '_get_llm_provider', return_value=mock_llm), \
             patch.object(executor, '_create_agent', return_value=mock_agent), \
             patch.object(executor, '_execute_with_pause_support', return_value="Success"):
            
            result = await executor.execute_task(task_definition, execution_context)
            
            assert isinstance(result, ExecutionResult)
            assert result.status == TaskStatus.COMPLETED
            assert result.result == "Success"
            assert result.execution_time is not None
            assert result.execution_time > 0
            assert result.metadata["task_id"] == "test_task_123"
            assert result.metadata["task_name"] == "test_task"
    
    @pytest.mark.asyncio
    async def test_execute_task_timeout(
        self, 
        task_definition, 
        execution_context, 
        mock_browser, 
        mock_agent, 
        mock_llm
    ):
        """Test task execution timeout."""
        # Set a very short timeout
        task_definition.timeout = 1
        executor = TaskExecutor(save_logs=False)
        
        # Mock a slow execution
        async def slow_execution(*args, **kwargs):
            await asyncio.sleep(2)  # Sleep longer than timeout
            return "Should not reach here"
        
        with patch.object(executor, '_create_browser', return_value=mock_browser), \
             patch.object(executor, '_get_llm_provider', return_value=mock_llm), \
             patch.object(executor, '_create_agent', return_value=mock_agent), \
             patch.object(executor, '_execute_with_pause_support', side_effect=slow_execution):
            
            result = await executor.execute_task(task_definition, execution_context)
            
            assert result.status == TaskStatus.TIMEOUT
            assert "timed out" in result.error_message
            assert result.execution_time is not None
    
    @pytest.mark.asyncio
    async def test_execute_task_failure(
        self, 
        task_definition, 
        execution_context, 
        mock_browser, 
        mock_agent, 
        mock_llm
    ):
        """Test task execution failure."""
        executor = TaskExecutor(save_logs=False)
        
        with patch.object(executor, '_create_browser', return_value=mock_browser), \
             patch.object(executor, '_get_llm_provider', return_value=mock_llm), \
             patch.object(executor, '_create_agent', return_value=mock_agent), \
             patch.object(executor, '_execute_with_pause_support', side_effect=Exception("Test error")):
            
            result = await executor.execute_task(task_definition, execution_context)
            
            assert result.status == TaskStatus.FAILED
            assert "Test error" in result.error_message
            assert result.execution_time is not None
    
    @pytest.mark.asyncio
    async def test_pause_resume_task(self):
        """Test task pause and resume functionality."""
        executor = TaskExecutor()
        task_id = "test_task_123"
        
        # Add a mock active task
        executor.active_tasks[task_id] = {
            "definition": Mock(),
            "context": {},
            "start_time": datetime.now(timezone.utc),
            "status": TaskStatus.RUNNING,
            "browser": None,
            "agent": None
        }
        
        # Test pause
        result = await executor.pause_task(task_id)
        assert result is True
        assert task_id in executor.paused_tasks
        assert executor.active_tasks[task_id]["status"] == TaskStatus.PAUSED
        
        # Test resume
        result = await executor.resume_task(task_id)
        assert result is True
        assert task_id not in executor.paused_tasks
        assert executor.active_tasks[task_id]["status"] == TaskStatus.RUNNING
    
    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test task cancellation."""
        executor = TaskExecutor()
        task_id = "test_task_123"
        
        # Add a mock active task
        executor.active_tasks[task_id] = {
            "definition": Mock(),
            "context": {},
            "start_time": datetime.now(timezone.utc),
            "status": TaskStatus.RUNNING,
            "browser": None,
            "agent": None
        }
        
        # Test cancel
        result = await executor.cancel_task(task_id)
        assert result is True
        assert task_id in executor.cancelled_tasks
        assert executor.active_tasks[task_id]["status"] == TaskStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_pause_nonexistent_task(self):
        """Test pausing a non-existent task."""
        executor = TaskExecutor()
        
        result = await executor.pause_task("nonexistent_task")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_resume_nonexistent_task(self):
        """Test resuming a non-existent task."""
        executor = TaskExecutor()
        
        result = await executor.resume_task("nonexistent_task")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self):
        """Test cancelling a non-existent task."""
        executor = TaskExecutor()
        
        result = await executor.cancel_task("nonexistent_task")
        assert result is False
    
    def test_get_active_tasks(self):
        """Test getting active tasks information."""
        executor = TaskExecutor()
        task_id = "test_task_123"
        
        # Add a mock active task
        mock_definition = Mock()
        mock_definition.name = "test_task"
        
        executor.active_tasks[task_id] = {
            "definition": mock_definition,
            "context": {},
            "start_time": datetime.now(timezone.utc),
            "status": TaskStatus.RUNNING,
            "browser": None,
            "agent": None
        }
        
        active_tasks = executor.get_active_tasks()
        
        assert task_id in active_tasks
        assert active_tasks[task_id]["task_name"] == "test_task"
        assert active_tasks[task_id]["status"] == "running"
        assert active_tasks[task_id]["is_paused"] is False
        assert active_tasks[task_id]["is_cancelled"] is False
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality."""
        executor = TaskExecutor()
        
        health = await executor.health_check()
        
        assert health["status"] == "healthy"
        assert health["active_tasks_count"] == 0
        assert health["paused_tasks_count"] == 0
        assert health["cancelled_tasks_count"] == 0
        assert health["browser_manager_available"] is False
        assert health["llm_provider_available"] is False
        assert "timestamp" in health
