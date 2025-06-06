"""
Unit tests for legacy system integration.

This module tests the integration between the new execution layer and the
legacy system, including the bridge, feature flags, and migration functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timezone

from core.interfaces import TaskDefinition, ExecutionResult, TaskStatus
from core.exceptions import TaskExecutionError, ConfigurationError
from src.execution.legacy_bridge import LegacyTaskBridge, get_legacy_bridge
from src.execution.feature_flags import FeatureFlagManager, FeatureFlag


@pytest.fixture
def mock_task_executor():
    """Create a mock task executor."""
    executor = Mock()
    executor.execute_task = AsyncMock()
    executor.health_check = AsyncMock(return_value={"status": "healthy"})
    return executor


@pytest.fixture
def mock_browser_manager():
    """Create a mock browser manager."""
    manager = Mock()
    manager.initialize = AsyncMock()
    manager.health_check = AsyncMock(return_value={"status": "healthy"})
    manager.shutdown = AsyncMock()
    return manager


@pytest.fixture
def mock_llm_provider():
    """Create a mock LLM provider."""
    provider = Mock()
    provider.health_check = AsyncMock(return_value=True)
    return provider


@pytest.fixture
def bridge_config():
    """Create a sample bridge configuration."""
    return {
        "use_new_execution": True,
        "fallback_to_legacy": True,
        "llm_provider": "gemini",
        "llm_config": {"api_key": "test_key"},
        "browser_config": {"headless": True},
        "default_timeout": 300,
        "save_logs": True,
        "logs_base_path": "test_logs"
    }


class TestLegacyTaskBridge:
    """Test cases for LegacyTaskBridge."""
    
    def test_init(self, bridge_config):
        """Test LegacyTaskBridge initialization."""
        bridge = LegacyTaskBridge(
            use_new_execution=True,
            fallback_to_legacy=True,
            config=bridge_config
        )
        
        assert bridge.use_new_execution is True
        assert bridge.fallback_to_legacy is True
        assert bridge.config == bridge_config
        assert bridge.new_execution_count == 0
        assert bridge.legacy_execution_count == 0
        assert bridge.fallback_count == 0
    
    @pytest.mark.asyncio
    async def test_initialize_success(
        self, 
        bridge_config, 
        mock_task_executor, 
        mock_browser_manager, 
        mock_llm_provider
    ):
        """Test successful bridge initialization."""
        with patch('src.execution.legacy_bridge.BrowserManager', return_value=mock_browser_manager), \
             patch('src.execution.legacy_bridge.create_llm_provider', return_value=mock_llm_provider), \
             patch('src.execution.legacy_bridge.TaskExecutor', return_value=mock_task_executor):
            
            bridge = LegacyTaskBridge(config=bridge_config)
            await bridge.initialize()
            
            assert bridge.browser_manager == mock_browser_manager
            assert bridge.llm_provider == mock_llm_provider
            assert bridge.task_executor == mock_task_executor
            
            mock_browser_manager.initialize.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialize_failure_no_fallback(self, bridge_config):
        """Test bridge initialization failure without fallback."""
        with patch('src.execution.legacy_bridge.BrowserManager') as mock_manager_class:
            mock_manager_class.side_effect = Exception("Initialization failed")
            
            bridge = LegacyTaskBridge(
                use_new_execution=True,
                fallback_to_legacy=False,
                config=bridge_config
            )
            
            with pytest.raises(ConfigurationError, match="Failed to initialize execution layer"):
                await bridge.initialize()
    
    @pytest.mark.asyncio
    async def test_run_task_new_execution_success(
        self, 
        bridge_config, 
        mock_task_executor
    ):
        """Test successful task execution with new execution layer."""
        # Mock successful execution result
        mock_result = ExecutionResult(
            status=TaskStatus.COMPLETED,
            result="Task completed successfully",
            execution_time=10.5,
            metadata={"test": True}
        )
        mock_task_executor.execute_task.return_value = mock_result
        
        bridge = LegacyTaskBridge(config=bridge_config)
        bridge.task_executor = mock_task_executor
        
        result = await bridge.run_task(
            "Test task",
            Mock(),
            "test_logs"
        )
        
        assert result == "Task completed successfully"
        assert bridge.new_execution_count == 1
        assert bridge.legacy_execution_count == 0
        assert bridge.fallback_count == 0
        
        mock_task_executor.execute_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_task_new_execution_failure_with_fallback(
        self, 
        bridge_config, 
        mock_task_executor
    ):
        """Test task execution failure with fallback to legacy."""
        # Mock failed execution
        mock_task_executor.execute_task.side_effect = Exception("Execution failed")
        
        with patch('src.execution.legacy_bridge.run_task') as mock_legacy_run:
            mock_legacy_run.return_value = "Legacy execution result"
            
            bridge = LegacyTaskBridge(config=bridge_config)
            bridge.task_executor = mock_task_executor
            
            result = await bridge.run_task(
                "Test task",
                Mock(),
                "test_logs"
            )
            
            assert result == "Legacy execution result"
            assert bridge.new_execution_count == 0
            assert bridge.legacy_execution_count == 0
            assert bridge.fallback_count == 1
            
            mock_legacy_run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_run_task_legacy_only(self, bridge_config):
        """Test task execution using legacy system only."""
        with patch('src.execution.legacy_bridge.run_task') as mock_legacy_run:
            mock_legacy_run.return_value = "Legacy execution result"
            
            bridge = LegacyTaskBridge(
                use_new_execution=False,
                config=bridge_config
            )
            
            result = await bridge.run_task(
                "Test task",
                Mock(),
                "test_logs"
            )
            
            assert result == "Legacy execution result"
            assert bridge.new_execution_count == 0
            assert bridge.legacy_execution_count == 1
            assert bridge.fallback_count == 0
    
    @pytest.mark.asyncio
    async def test_run_workflow_success(self, bridge_config):
        """Test successful workflow execution."""
        flow_sequence = ["task1", "task2"]
        task_templates = {
            "auth": "Login task",
            "task1": "First task",
            "task2": "Second task"
        }
        
        with patch.object(LegacyTaskBridge, 'run_task') as mock_run_task:
            mock_run_task.side_effect = ["Result 1", "Result 2"]
            
            bridge = LegacyTaskBridge(config=bridge_config)
            
            results = await bridge.run_workflow(
                flow_sequence,
                task_templates,
                Mock(),
                "test_workflow_123"
            )
            
            assert len(results) == 2
            assert results["task1"]["status"] == "completed"
            assert results["task1"]["result"] == "Result 1"
            assert results["task2"]["status"] == "completed"
            assert results["task2"]["result"] == "Result 2"
            
            assert mock_run_task.call_count == 2
    
    @pytest.mark.asyncio
    async def test_run_workflow_with_timeout(self, bridge_config):
        """Test workflow execution with task timeout."""
        flow_sequence = ["task1"]
        task_templates = {
            "auth": "Login task",
            "task1": "First task"
        }
        
        with patch.object(LegacyTaskBridge, 'run_task') as mock_run_task:
            mock_run_task.side_effect = asyncio.TimeoutError()
            
            bridge = LegacyTaskBridge(config=bridge_config)
            
            results = await bridge.run_workflow(
                flow_sequence,
                task_templates,
                Mock(),
                "test_workflow_123",
                task_timeout=1
            )
            
            assert results["task1"]["status"] == "timeout"
            assert "timed out" in results["task1"]["result"]
    
    @pytest.mark.asyncio
    async def test_run_workflow_with_error(self, bridge_config):
        """Test workflow execution with task error."""
        flow_sequence = ["task1"]
        task_templates = {
            "auth": "Login task",
            "task1": "First task"
        }
        
        with patch.object(LegacyTaskBridge, 'run_task') as mock_run_task:
            mock_run_task.side_effect = Exception("Task execution failed")
            
            bridge = LegacyTaskBridge(config=bridge_config)
            
            results = await bridge.run_workflow(
                flow_sequence,
                task_templates,
                Mock(),
                "test_workflow_123"
            )
            
            assert results["task1"]["status"] == "error"
            assert "Task execution failed" in results["task1"]["result"]
    
    def test_get_statistics(self, bridge_config):
        """Test statistics retrieval."""
        bridge = LegacyTaskBridge(config=bridge_config)
        
        # Simulate some activity
        bridge.new_execution_count = 10
        bridge.legacy_execution_count = 5
        bridge.fallback_count = 2
        
        stats = bridge.get_statistics()
        
        assert stats["total_executions"] == 15
        assert stats["new_execution_count"] == 10
        assert stats["legacy_execution_count"] == 5
        assert stats["fallback_count"] == 2
        assert stats["new_execution_rate"] == 10/15
        assert stats["fallback_rate"] == 2/15
        assert stats["use_new_execution"] is True
        assert stats["fallback_to_legacy"] is True
    
    @pytest.mark.asyncio
    async def test_health_check(
        self, 
        bridge_config, 
        mock_task_executor, 
        mock_browser_manager, 
        mock_llm_provider
    ):
        """Test health check functionality."""
        bridge = LegacyTaskBridge(config=bridge_config)
        bridge.task_executor = mock_task_executor
        bridge.browser_manager = mock_browser_manager
        bridge.llm_provider = mock_llm_provider
        
        health = await bridge.health_check()
        
        assert health["bridge_status"] == "healthy"
        assert health["use_new_execution"] is True
        assert health["fallback_to_legacy"] is True
        assert "statistics" in health
        assert "task_executor" in health
        assert "browser_manager" in health
        assert "llm_provider" in health
    
    @pytest.mark.asyncio
    async def test_shutdown(
        self, 
        bridge_config, 
        mock_browser_manager
    ):
        """Test bridge shutdown."""
        bridge = LegacyTaskBridge(config=bridge_config)
        bridge.browser_manager = mock_browser_manager
        
        await bridge.shutdown()
        
        mock_browser_manager.shutdown.assert_called_once()


class TestFeatureFlagManager:
    """Test cases for FeatureFlagManager."""
    
    def test_init(self):
        """Test FeatureFlagManager initialization."""
        manager = FeatureFlagManager()
        
        assert len(manager.flags) > 0
        assert len(manager.default_flags) > 0
        assert manager.env_prefix == "EXECUTION_"
    
    def test_is_enabled_default(self):
        """Test checking if a flag is enabled with default values."""
        manager = FeatureFlagManager()
        
        # Test default values
        assert manager.is_enabled(FeatureFlag.FALLBACK_TO_LEGACY) is True
        assert manager.is_enabled(FeatureFlag.USE_NEW_EXECUTION_LAYER) is False
    
    def test_enable_flag(self):
        """Test enabling a feature flag."""
        manager = FeatureFlagManager()
        
        # Initially disabled
        assert manager.is_enabled(FeatureFlag.USE_NEW_EXECUTION_LAYER) is False
        
        # Enable flag
        manager.enable_flag(FeatureFlag.USE_NEW_EXECUTION_LAYER, "Test enable")
        
        # Should now be enabled
        assert manager.is_enabled(FeatureFlag.USE_NEW_EXECUTION_LAYER) is True
        
        # Check metadata
        metadata = manager.get_flag_metadata(FeatureFlag.USE_NEW_EXECUTION_LAYER)
        assert metadata is not None
        assert metadata["reason"] == "Test enable"
        assert "enabled_at" in metadata
    
    def test_disable_flag(self):
        """Test disabling a feature flag."""
        manager = FeatureFlagManager()
        
        # Enable first
        manager.enable_flag(FeatureFlag.FALLBACK_TO_LEGACY, "Test enable")
        assert manager.is_enabled(FeatureFlag.FALLBACK_TO_LEGACY) is True
        
        # Disable flag
        manager.disable_flag(FeatureFlag.FALLBACK_TO_LEGACY, "Test disable")
        
        # Should now be disabled
        assert manager.is_enabled(FeatureFlag.FALLBACK_TO_LEGACY) is False
    
    def test_get_migration_status(self):
        """Test migration status calculation."""
        manager = FeatureFlagManager()
        
        status = manager.get_migration_status()
        
        assert "migration_progress" in status
        assert "core_migration" in status
        assert "workflow_migration" in status
        assert "adapter_migration" in status
        assert "total_flags" in status
        assert "enabled_flags" in status
        assert "fallback_enabled" in status
        assert "health_checks_enabled" in status
    
    def test_enable_migration_phase(self):
        """Test enabling migration phases."""
        manager = FeatureFlagManager()
        
        # Enable phase 1
        manager.enable_migration_phase(1)
        
        # Check that phase 1 flags are enabled
        assert manager.is_enabled(FeatureFlag.USE_BROWSER_USE_ADAPTER) is True
        assert manager.is_enabled(FeatureFlag.USE_GEMINI_ADAPTER) is True
        assert manager.is_enabled(FeatureFlag.FALLBACK_TO_LEGACY) is True
        
        # Enable phase 2
        manager.enable_migration_phase(2)
        
        # Check that phase 2 flags are enabled
        assert manager.is_enabled(FeatureFlag.USE_NEW_LLM_PROVIDER) is True
        assert manager.is_enabled(FeatureFlag.USE_NEW_BROWSER_MANAGER) is True
    
    def test_enable_migration_phase_invalid(self):
        """Test enabling invalid migration phase."""
        manager = FeatureFlagManager()
        
        with pytest.raises(ValueError, match="Invalid migration phase"):
            manager.enable_migration_phase(5)


class TestGlobalFunctions:
    """Test cases for global utility functions."""
    
    def test_get_legacy_bridge(self):
        """Test getting global legacy bridge instance."""
        # Clear any existing global instance
        import src.execution.legacy_bridge
        src.execution.legacy_bridge._global_bridge = None
        
        bridge1 = get_legacy_bridge()
        bridge2 = get_legacy_bridge()
        
        # Should return the same instance
        assert bridge1 is bridge2
    
    @pytest.mark.asyncio
    async def test_initialize_bridge(self):
        """Test initializing global legacy bridge."""
        with patch.object(LegacyTaskBridge, 'initialize') as mock_init:
            mock_init.return_value = None
            
            config = {"test": "config"}
            bridge = await src.execution.legacy_bridge.initialize_bridge(config)
            
            assert isinstance(bridge, LegacyTaskBridge)
            mock_init.assert_called_once()
