"""
Integration tests for the execution layer.

This module tests the integration between all execution layer components
to ensure they work together correctly in realistic scenarios.
"""

import pytest
import asyncio
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from core.interfaces import TaskDefinition, ExecutionResult, TaskStatus
from core.exceptions import TaskExecutionError, BrowserError, LLMError
from src.execution.task_executor import TaskExecutor
from src.execution.browser_manager import BrowserManager
from src.execution.llm_provider import TaskLLMProvider, LLMProviderType
from src.execution.legacy_bridge import LegacyTaskBridge
from src.execution.feature_flags import FeatureFlagManager, FeatureFlag
from src.execution.adapters.adapter_factory import AdapterFactory, AdapterType


@pytest.fixture
def task_definition():
    """Create a sample task definition for testing."""
    return TaskDefinition(
        name="integration_test_task",
        description="A task for integration testing",
        prompt_template="Navigate to https://example.com and verify the page loads correctly",
        timeout=60,
        retry_count=2,
        metadata={"test_type": "integration"}
    )


@pytest.fixture
def execution_context():
    """Create a sample execution context."""
    return {
        "task_id": "integration_test_123",
        "correlation_id": "integration_correlation_456",
        "target_url": "https://example.com",
        "headless": True,
        "use_vision": True,
        "browser_config": {
            "headless": True,
            "browser_type": "chrome"
        }
    }


@pytest.fixture
def mock_browser():
    """Create a mock browser for testing."""
    browser = Mock()
    browser.close = AsyncMock()
    return browser


@pytest.fixture
def mock_llm():
    """Create a mock LLM for testing."""
    llm = Mock()
    llm.ainvoke = AsyncMock()
    
    # Mock response
    mock_response = Mock()
    mock_response.content = "Task completed successfully"
    llm.ainvoke.return_value = mock_response
    
    return llm


class TestExecutionLayerIntegration:
    """Integration tests for the complete execution layer."""
    
    @pytest.mark.asyncio
    async def test_task_executor_with_mocked_components(
        self, 
        task_definition, 
        execution_context,
        mock_browser,
        mock_llm
    ):
        """Test task executor with mocked browser and LLM components."""
        # Create mock browser manager
        mock_browser_manager = Mock()
        mock_browser_manager.create_browser = AsyncMock(return_value=mock_browser)
        
        # Create mock LLM provider
        mock_llm_provider = Mock()
        mock_llm_provider.invoke = AsyncMock(return_value="Task completed successfully")
        
        # Create task executor
        executor = TaskExecutor(
            browser_manager=mock_browser_manager,
            llm_provider=mock_llm_provider,
            save_logs=False
        )
        
        # Mock the agent creation and execution
        with patch('src.execution.task_executor.Agent') as mock_agent_class:
            mock_agent = Mock()
            mock_history = Mock()
            mock_history.final_result = Mock(return_value="Integration test successful")
            mock_agent.run = AsyncMock(return_value=mock_history)
            mock_agent_class.return_value = mock_agent
            
            # Execute task
            result = await executor.execute_task(task_definition, execution_context)
            
            # Verify result
            assert isinstance(result, ExecutionResult)
            assert result.status == TaskStatus.COMPLETED
            assert result.result == "Integration test successful"
            assert result.execution_time > 0
            assert result.metadata["task_id"] == "integration_test_123"
            
            # Verify interactions
            mock_browser_manager.create_browser.assert_called_once()
            mock_agent_class.assert_called_once()
            mock_agent.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_browser_manager_integration(self):
        """Test browser manager integration with pooling disabled."""
        # Create browser manager without pooling
        browser_manager = BrowserManager(enable_pooling=False)
        
        # Mock browser creation
        with patch('src.execution.browser_manager.Browser') as mock_browser_class:
            mock_browser = Mock()
            mock_browser.close = AsyncMock()
            mock_browser_class.return_value = mock_browser
            
            # Test browser creation
            config = {"headless": True, "browser_type": "chrome"}
            browser = await browser_manager.create_browser(config)
            
            assert browser == mock_browser
            assert "test_session_123" in browser_manager.active_sessions
            
            # Test browser status
            status = await browser_manager.get_browser_status(browser)
            assert status["status"] == "active"
            assert status["type"] == "direct"
            
            # Test browser closing
            await browser_manager.close_browser(browser)
            mock_browser.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_provider_integration(self):
        """Test LLM provider integration with mocked dependencies."""
        # Mock the LangChain provider
        with patch('src.execution.llm_provider.ChatGoogleGenerativeAI') as mock_chat, \
             patch('src.execution.llm_provider.InMemoryRateLimiter') as mock_limiter, \
             patch.dict('os.environ', {'GEMINI_API_KEY': 'test_key'}):
            
            mock_provider = Mock()
            mock_response = Mock()
            mock_response.content = "Test LLM response"
            mock_provider.ainvoke = AsyncMock(return_value=mock_response)
            mock_chat.return_value = mock_provider
            
            mock_rate_limiter = Mock()
            mock_limiter.return_value = mock_rate_limiter
            
            # Create and initialize LLM provider
            llm_provider = TaskLLMProvider(
                provider_type=LLMProviderType.GEMINI,
                config={"api_key": "test_key"}
            )
            await llm_provider.initialize()
            
            # Test invocation
            response = await llm_provider.invoke("Test prompt")
            assert response == "Test LLM response"
            
            # Test structured response
            messages = [{"role": "user", "content": "Hello"}]
            structured_response = await llm_provider.generate_response(messages)
            
            assert structured_response["content"] == "Test LLM response"
            assert structured_response["role"] == "assistant"
            assert "usage" in structured_response
            assert "metadata" in structured_response
    
    @pytest.mark.asyncio
    async def test_adapter_factory_integration(self):
        """Test adapter factory integration with different adapter types."""
        factory = AdapterFactory()
        
        # Test browser-use adapter creation
        browser_adapter = await factory.create_adapter(
            AdapterType.BROWSER_USE,
            "test_browser_adapter",
            {"save_logs": False}
        )
        
        assert browser_adapter is not None
        assert "test_browser_adapter" in factory.adapters
        
        # Test adapter info retrieval
        adapter_info = factory.get_adapter_info("test_browser_adapter")
        assert adapter_info is not None
        assert adapter_info["type"] == "browser_use"
        
        # Test health check
        health_results = await factory.health_check_all()
        assert "test_browser_adapter" in health_results
        
        # Test adapter removal
        removed = await factory.remove_adapter("test_browser_adapter")
        assert removed is True
        assert "test_browser_adapter" not in factory.adapters
    
    @pytest.mark.asyncio
    async def test_legacy_bridge_integration(self):
        """Test legacy bridge integration with feature flags."""
        # Create feature flag manager
        flag_manager = FeatureFlagManager()
        
        # Enable new execution layer
        flag_manager.enable_flag(FeatureFlag.USE_NEW_EXECUTION_LAYER, "Integration test")
        
        # Create bridge with mocked components
        with patch('src.execution.legacy_bridge.BrowserManager') as mock_browser_manager_class, \
             patch('src.execution.legacy_bridge.create_llm_provider') as mock_create_llm, \
             patch('src.execution.legacy_bridge.TaskExecutor') as mock_task_executor_class:
            
            # Setup mocks
            mock_browser_manager = Mock()
            mock_browser_manager.initialize = AsyncMock()
            mock_browser_manager_class.return_value = mock_browser_manager
            
            mock_llm_provider = Mock()
            mock_create_llm.return_value = mock_llm_provider
            
            mock_task_executor = Mock()
            mock_result = ExecutionResult(
                status=TaskStatus.COMPLETED,
                result="Bridge integration successful",
                execution_time=5.0,
                metadata={"bridge": True}
            )
            mock_task_executor.execute_task = AsyncMock(return_value=mock_result)
            mock_task_executor_class.return_value = mock_task_executor
            
            # Create and initialize bridge
            bridge = LegacyTaskBridge(
                use_new_execution=True,
                fallback_to_legacy=True,
                config={"test": "config"}
            )
            await bridge.initialize()
            
            # Test task execution
            result = await bridge.run_task(
                "Test integration task",
                Mock(),
                "test_logs"
            )
            
            assert result == "Bridge integration successful"
            assert bridge.new_execution_count == 1
            assert bridge.legacy_execution_count == 0
            
            # Test health check
            health = await bridge.health_check()
            assert health["bridge_status"] == "healthy"
            assert health["use_new_execution"] is True
    
    @pytest.mark.asyncio
    async def test_feature_flag_integration(self):
        """Test feature flag integration with execution components."""
        flag_manager = FeatureFlagManager()
        
        # Test initial state
        assert flag_manager.is_enabled(FeatureFlag.USE_NEW_EXECUTION_LAYER) is False
        assert flag_manager.is_enabled(FeatureFlag.FALLBACK_TO_LEGACY) is True
        
        # Test migration phase enablement
        flag_manager.enable_migration_phase(1)
        
        # Verify phase 1 flags
        assert flag_manager.is_enabled(FeatureFlag.USE_BROWSER_USE_ADAPTER) is True
        assert flag_manager.is_enabled(FeatureFlag.USE_GEMINI_ADAPTER) is True
        assert flag_manager.is_enabled(FeatureFlag.ENABLE_HEALTH_CHECKS) is True
        
        # Test migration status
        status = flag_manager.get_migration_status()
        assert status["migration_progress"] > 0
        assert status["adapter_migration"] > 0
        assert status["fallback_enabled"] is True
        
        # Enable more phases
        flag_manager.enable_migration_phase(2)
        flag_manager.enable_migration_phase(3)
        
        # Verify advanced flags
        assert flag_manager.is_enabled(FeatureFlag.USE_NEW_LLM_PROVIDER) is True
        assert flag_manager.is_enabled(FeatureFlag.USE_NEW_EXECUTION_LAYER) is True
        
        # Check final migration status
        final_status = flag_manager.get_migration_status()
        assert final_status["migration_progress"] > status["migration_progress"]
        assert final_status["core_migration"] > 0
    
    @pytest.mark.asyncio
    async def test_end_to_end_workflow_simulation(self):
        """Test end-to-end workflow simulation with all components."""
        # This test simulates a complete workflow execution using mocked components
        
        # Setup feature flags for new execution
        flag_manager = FeatureFlagManager()
        flag_manager.enable_migration_phase(3)  # Enable new execution layer
        
        # Mock all external dependencies
        with patch('src.execution.legacy_bridge.BrowserManager') as mock_browser_manager_class, \
             patch('src.execution.legacy_bridge.create_llm_provider') as mock_create_llm, \
             patch('src.execution.legacy_bridge.TaskExecutor') as mock_task_executor_class, \
             patch('src.execution.task_executor.Agent') as mock_agent_class:
            
            # Setup browser manager mock
            mock_browser_manager = Mock()
            mock_browser_manager.initialize = AsyncMock()
            mock_browser_manager.create_browser = AsyncMock(return_value=Mock())
            mock_browser_manager_class.return_value = mock_browser_manager
            
            # Setup LLM provider mock
            mock_llm_provider = Mock()
            mock_create_llm.return_value = mock_llm_provider
            
            # Setup agent mock
            mock_agent = Mock()
            mock_history = Mock()
            mock_history.final_result = Mock(return_value="Workflow task completed")
            mock_agent.run = AsyncMock(return_value=mock_history)
            mock_agent_class.return_value = mock_agent
            
            # Setup task executor mock
            mock_task_executor = Mock()
            mock_task_executor.execute_task = AsyncMock()
            
            # Create execution results for workflow tasks
            task_results = [
                ExecutionResult(
                    status=TaskStatus.COMPLETED,
                    result="Task 1 completed",
                    execution_time=3.0,
                    metadata={"task": "task1"}
                ),
                ExecutionResult(
                    status=TaskStatus.COMPLETED,
                    result="Task 2 completed", 
                    execution_time=4.0,
                    metadata={"task": "task2"}
                )
            ]
            mock_task_executor.execute_task.side_effect = task_results
            mock_task_executor_class.return_value = mock_task_executor
            
            # Create and initialize bridge
            bridge = LegacyTaskBridge(
                use_new_execution=True,
                fallback_to_legacy=False,
                config={"test": "workflow"}
            )
            await bridge.initialize()
            
            # Simulate workflow execution
            flow_sequence = ["task1", "task2"]
            task_templates = {
                "auth": "Login to the system",
                "task1": "Complete first task",
                "task2": "Complete second task"
            }
            
            results = await bridge.run_workflow(
                flow_sequence,
                task_templates,
                Mock(),
                "integration_workflow_123"
            )
            
            # Verify workflow results
            assert len(results) == 2
            assert results["task1"]["status"] == "completed"
            assert results["task2"]["status"] == "completed"
            assert "Task 1 completed" in results["task1"]["result"]
            assert "Task 2 completed" in results["task2"]["result"]
            
            # Verify component interactions
            mock_browser_manager.initialize.assert_called_once()
            assert mock_task_executor.execute_task.call_count == 2
            
            # Verify bridge statistics
            stats = bridge.get_statistics()
            assert stats["total_executions"] == 2
            assert stats["new_execution_count"] == 2
            assert stats["legacy_execution_count"] == 0
    
    @pytest.mark.asyncio
    async def test_error_handling_and_fallback(self):
        """Test error handling and fallback mechanisms."""
        # Setup feature flags with fallback enabled
        flag_manager = FeatureFlagManager()
        flag_manager.enable_flag(FeatureFlag.USE_NEW_EXECUTION_LAYER, "Error test")
        flag_manager.enable_flag(FeatureFlag.FALLBACK_TO_LEGACY, "Error test")
        
        # Mock components with failures
        with patch('src.execution.legacy_bridge.BrowserManager') as mock_browser_manager_class, \
             patch('src.execution.legacy_bridge.create_llm_provider') as mock_create_llm, \
             patch('src.execution.legacy_bridge.TaskExecutor') as mock_task_executor_class, \
             patch('utils.task_runner.run_task') as mock_legacy_run:
            
            # Setup failing new execution
            mock_browser_manager_class.side_effect = Exception("Browser manager failed")
            
            # Setup successful legacy execution
            mock_legacy_run.return_value = "Legacy fallback successful"
            
            # Create bridge
            bridge = LegacyTaskBridge(
                use_new_execution=True,
                fallback_to_legacy=True,
                config={}
            )
            
            # Attempt to initialize (should fail but not raise)
            await bridge.initialize()
            
            # Execute task (should fallback to legacy)
            result = await bridge.run_task(
                "Test error handling",
                Mock(),
                "error_test_logs"
            )
            
            assert result == "Legacy fallback successful"
            assert bridge.fallback_count == 1
            
            # Verify legacy was called
            mock_legacy_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_monitoring_integration(self):
        """Test health monitoring across all components."""
        # Create components with health check capabilities
        flag_manager = FeatureFlagManager()
        flag_manager.enable_migration_phase(2)
        
        # Mock healthy components
        with patch('src.execution.legacy_bridge.BrowserManager') as mock_browser_manager_class, \
             patch('src.execution.legacy_bridge.create_llm_provider') as mock_create_llm, \
             patch('src.execution.legacy_bridge.TaskExecutor') as mock_task_executor_class:
            
            # Setup healthy mocks
            mock_browser_manager = Mock()
            mock_browser_manager.initialize = AsyncMock()
            mock_browser_manager.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_browser_manager_class.return_value = mock_browser_manager
            
            mock_llm_provider = Mock()
            mock_llm_provider.health_check = AsyncMock(return_value=True)
            mock_create_llm.return_value = mock_llm_provider
            
            mock_task_executor = Mock()
            mock_task_executor.health_check = AsyncMock(return_value={"status": "healthy"})
            mock_task_executor_class.return_value = mock_task_executor
            
            # Create and initialize bridge
            bridge = LegacyTaskBridge(
                use_new_execution=True,
                config={"health_test": True}
            )
            await bridge.initialize()
            
            # Perform comprehensive health check
            health = await bridge.health_check()
            
            # Verify health status
            assert health["bridge_status"] == "healthy"
            assert health["task_executor"]["status"] == "healthy"
            assert health["browser_manager"]["status"] == "healthy"
            assert health["llm_provider"] is True
            
            # Verify statistics are included
            assert "statistics" in health
            assert health["statistics"]["use_new_execution"] is True
