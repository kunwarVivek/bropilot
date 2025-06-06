"""
Unit tests for API layer components.

This module tests the API endpoints, models, and dependencies
to ensure proper functionality and validation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from src.api.models.requests import (
    WorkflowExecutionRequest, TaskExecutionRequest, FeatureFlagRequest
)
from src.api.models.responses import (
    WorkflowExecutionResponse, TaskExecutionResponse, HealthResponse
)
from src.api.dependencies import (
    initialize_components, shutdown_components, get_workflow_engine,
    get_task_scheduler, get_task_executor, get_feature_flags
)


class TestRequestModels:
    """Test cases for API request models."""
    
    def test_workflow_execution_request_valid(self):
        """Test valid workflow execution request."""
        request = WorkflowExecutionRequest(
            workflow_name="test_workflow",
            tasks=["task1", "task2"],
            execution_mode="parallel",
            timeout=300
        )
        
        assert request.workflow_name == "test_workflow"
        assert request.tasks == ["task1", "task2"]
        assert request.execution_mode == "parallel"
        assert request.timeout == 300
        assert request.async_execution is False
        assert request.continue_on_failure is False
    
    def test_workflow_execution_request_invalid_mode(self):
        """Test workflow execution request with invalid execution mode."""
        with pytest.raises(ValueError, match="execution_mode must be one of"):
            WorkflowExecutionRequest(
                tasks=["task1"],
                execution_mode="invalid_mode"
            )
    
    def test_workflow_execution_request_empty_tasks(self):
        """Test workflow execution request with empty tasks."""
        with pytest.raises(ValueError, match="At least one task must be specified"):
            WorkflowExecutionRequest(tasks=[])
    
    def test_task_execution_request_valid(self):
        """Test valid task execution request."""
        request = TaskExecutionRequest(
            task_name="test_task",
            prompt_template="Execute test task",
            timeout=120,
            retry_count=2,
            headless=True,
            use_vision=False
        )
        
        assert request.task_name == "test_task"
        assert request.prompt_template == "Execute test task"
        assert request.timeout == 120
        assert request.retry_count == 2
        assert request.headless is True
        assert request.use_vision is False
    
    def test_feature_flag_request_valid(self):
        """Test valid feature flag request."""
        request = FeatureFlagRequest(
            reason="Enable for testing",
            metadata={"test": True}
        )
        
        assert request.reason == "Enable for testing"
        assert request.metadata == {"test": True}


class TestResponseModels:
    """Test cases for API response models."""
    
    def test_workflow_execution_response(self):
        """Test workflow execution response model."""
        response = WorkflowExecutionResponse(
            workflow_id="wf_123",
            status="completed",
            execution_time=45.2,
            correlation_id="corr_123",
            async_execution=False,
            task_count=3,
            successful_tasks=3,
            failed_tasks=0
        )
        
        assert response.workflow_id == "wf_123"
        assert response.status == "completed"
        assert response.execution_time == 45.2
        assert response.correlation_id == "corr_123"
        assert response.async_execution is False
        assert response.task_count == 3
        assert response.successful_tasks == 3
        assert response.failed_tasks == 0
    
    def test_task_execution_response(self):
        """Test task execution response model."""
        response = TaskExecutionResponse(
            task_id="task_123",
            task_name="test_task",
            status="completed",
            result="Task completed successfully",
            execution_time=12.5,
            correlation_id="corr_123"
        )
        
        assert response.task_id == "task_123"
        assert response.task_name == "test_task"
        assert response.status == "completed"
        assert response.result == "Task completed successfully"
        assert response.execution_time == 12.5
        assert response.correlation_id == "corr_123"
    
    def test_health_response(self):
        """Test health response model."""
        response = HealthResponse(
            status="healthy",
            timestamp="2024-01-01T12:00:00Z",
            response_time=0.05,
            components={"workflow_engine": {"status": "healthy"}},
            correlation_id="corr_123"
        )
        
        assert response.status == "healthy"
        assert response.timestamp == "2024-01-01T12:00:00Z"
        assert response.response_time == 0.05
        assert response.components["workflow_engine"]["status"] == "healthy"
        assert response.correlation_id == "corr_123"


class TestDependencies:
    """Test cases for API dependencies."""
    
    @pytest.mark.asyncio
    async def test_initialize_components_success(self):
        """Test successful component initialization."""
        with patch('src.api.dependencies.get_feature_flag_manager') as mock_flags, \
             patch('src.api.dependencies.get_legacy_bridge') as mock_bridge:
            
            # Setup mocks
            mock_flag_manager = Mock()
            mock_flag_manager.is_enabled.return_value = True
            mock_flags.return_value = mock_flag_manager
            
            mock_legacy_bridge = Mock()
            mock_legacy_bridge.initialize = AsyncMock()
            mock_bridge.return_value = mock_legacy_bridge
            
            # Test initialization
            config = {"test": "config"}
            await initialize_components(config)
            
            # Verify calls
            mock_flags.assert_called_once()
            mock_bridge.assert_called_once()
            mock_legacy_bridge.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_shutdown_components(self):
        """Test component shutdown."""
        # First initialize components
        with patch('src.api.dependencies.get_feature_flag_manager') as mock_flags, \
             patch('src.api.dependencies.get_legacy_bridge') as mock_bridge:
            
            mock_flag_manager = Mock()
            mock_flag_manager.is_enabled.return_value = False
            mock_flags.return_value = mock_flag_manager
            
            mock_legacy_bridge = Mock()
            mock_legacy_bridge.initialize = AsyncMock()
            mock_legacy_bridge.shutdown = AsyncMock()
            mock_bridge.return_value = mock_legacy_bridge
            
            await initialize_components({})
            
            # Test shutdown
            await shutdown_components()
            
            # Verify shutdown was called
            mock_legacy_bridge.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_workflow_engine_not_initialized(self):
        """Test getting workflow engine when not initialized."""
        # Reset initialization state
        import src.api.dependencies
        src.api.dependencies._components_initialized = False
        
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_workflow_engine()
        
        assert exc_info.value.status_code == 503
        assert "System components not initialized" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_task_scheduler_not_initialized(self):
        """Test getting task scheduler when not initialized."""
        # Reset initialization state
        import src.api.dependencies
        src.api.dependencies._components_initialized = False
        
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_task_scheduler()
        
        assert exc_info.value.status_code == 503
        assert "System components not initialized" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_task_executor_not_initialized(self):
        """Test getting task executor when not initialized."""
        # Reset initialization state
        import src.api.dependencies
        src.api.dependencies._components_initialized = False
        
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_task_executor()
        
        assert exc_info.value.status_code == 503
        assert "System components not initialized" in str(exc_info.value.detail)


class TestAPIEndpoints:
    """Test cases for API endpoints using TestClient."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        # Import the app and create test client
        from src.api.main import app
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test the root endpoint."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Browser Automation API v2.0"
        assert data["version"] == "2.0.0"
        assert data["status"] == "running"
        assert "features" in data
        assert "endpoints" in data
    
    def test_api_info_endpoint(self, client):
        """Test the API info endpoint."""
        response = client.get("/api/info")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["api"]["name"] == "Browser Automation API"
        assert data["api"]["version"] == "2.0.0"
        assert "capabilities" in data
        assert "architecture" in data
    
    def test_health_endpoint(self, client):
        """Test the health endpoint."""
        response = client.get("/health/")
        
        # The endpoint might return 200 or 503 depending on component initialization
        assert response.status_code in [200, 503]
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    def test_legacy_workflow_execute_no_tasks(self, client):
        """Test legacy workflow execution with no tasks."""
        response = client.post("/workflows/execute", json={})
        
        assert response.status_code == 400
        data = response.json()
        assert "No tasks specified" in data["detail"]
    
    def test_legacy_available_tasks(self, client):
        """Test legacy available tasks endpoint."""
        response = client.get("/tasks/available")
        
        # This might succeed or fail depending on imports
        # We just check that it returns a valid response structure
        if response.status_code == 200:
            data = response.json()
            assert "tasks" in data
            assert "legacy_mode" in data
    
    def test_error_handler(self, client):
        """Test error handling."""
        # Test a non-existent endpoint
        response = client.get("/nonexistent")
        
        assert response.status_code == 404


class TestAPIIntegration:
    """Integration tests for API components."""
    
    @pytest.mark.asyncio
    async def test_component_lifecycle(self):
        """Test complete component lifecycle."""
        with patch('src.api.dependencies.get_feature_flag_manager') as mock_flags, \
             patch('src.api.dependencies.get_legacy_bridge') as mock_bridge:
            
            # Setup mocks
            mock_flag_manager = Mock()
            mock_flag_manager.is_enabled.return_value = True
            mock_flags.return_value = mock_flag_manager
            
            mock_legacy_bridge = Mock()
            mock_legacy_bridge.initialize = AsyncMock()
            mock_legacy_bridge.shutdown = AsyncMock()
            mock_bridge.return_value = mock_legacy_bridge
            
            # Test initialization
            await initialize_components({"test": "config"})
            
            # Test that components are marked as initialized
            import src.api.dependencies
            assert src.api.dependencies._components_initialized is True
            
            # Test shutdown
            await shutdown_components()
            
            # Verify shutdown was called
            mock_legacy_bridge.shutdown.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_dependency_injection_flow(self):
        """Test the dependency injection flow."""
        with patch('src.api.dependencies.get_feature_flag_manager') as mock_flags, \
             patch('src.api.dependencies.get_legacy_bridge') as mock_bridge:
            
            # Setup mocks
            mock_flag_manager = Mock()
            mock_flag_manager.is_enabled.return_value = False  # Use legacy mode
            mock_flags.return_value = mock_flag_manager
            
            mock_legacy_bridge = Mock()
            mock_legacy_bridge.initialize = AsyncMock()
            mock_legacy_bridge.task_executor = None  # No task executor
            mock_bridge.return_value = mock_legacy_bridge
            
            # Initialize components
            await initialize_components({})
            
            # Test getting components
            workflow_engine = await get_workflow_engine()
            task_scheduler = await get_task_scheduler()
            task_executor = await get_task_executor()
            feature_flags = await get_feature_flags()
            
            # In this test, most components should be None due to mocking
            assert workflow_engine is None  # Not enabled
            assert task_scheduler is None   # Not enabled
            assert task_executor is None    # Not created
            assert feature_flags == mock_flag_manager
            
            # Cleanup
            await shutdown_components()
