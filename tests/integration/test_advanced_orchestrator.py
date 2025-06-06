"""
Integration tests for the Advanced Orchestrator.

Tests the complete integration of all advanced features including LLM integration,
multi-modal processing, error recovery, and analytics.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any

from src.intelligence.advanced_orchestrator import (
    AdvancedOrchestrator, 
    IntelligentWorkflowConfig,
    ExecutionContext
)
from src.llm.conversation_manager import ConversationManager, MessageRole
from src.llm.multimodal_processor import MultiModalProcessor, MediaType, ProcessingMode
from src.intelligence.error_recovery import IntelligentErrorRecovery
from src.analytics.reporting_engine import AnalyticsEngine
from core.interfaces import IWorkflowEngine, ITaskExecutor, ILLMProvider
from core.exceptions import OrchestrationError


class MockLLMProvider(ILLMProvider):
    """Mock LLM provider for testing."""
    
    async def generate_response(
        self,
        messages,
        temperature=0.7,
        max_tokens=None,
        functions=None,
        tools=None
    ):
        """Mock LLM response."""
        return {
            "content": "This is a mock LLM response for testing purposes.",
            "model": "mock-model",
            "usage": {"total_tokens": 100},
            "finish_reason": "stop"
        }


class MockWorkflowEngine(IWorkflowEngine):
    """Mock workflow engine for testing."""
    
    async def execute_workflow(self, workflow_definition, context=None):
        """Mock workflow execution."""
        return {
            "success": True,
            "results": {"task_1": "completed", "task_2": "completed"},
            "execution_time": 5.0
        }


class MockTaskExecutor(ITaskExecutor):
    """Mock task executor for testing."""
    
    async def execute_task(self, task_definition, context=None):
        """Mock task execution."""
        return {
            "success": True,
            "result": "Task completed successfully",
            "execution_time": 1.0
        }


@pytest.fixture
async def mock_llm_provider():
    """Create mock LLM provider."""
    return MockLLMProvider()


@pytest.fixture
async def mock_workflow_engine():
    """Create mock workflow engine."""
    return MockWorkflowEngine()


@pytest.fixture
async def mock_task_executor():
    """Create mock task executor."""
    return MockTaskExecutor()


@pytest.fixture
async def advanced_orchestrator(mock_workflow_engine, mock_task_executor, mock_llm_provider):
    """Create advanced orchestrator with mocks."""
    orchestrator = AdvancedOrchestrator(
        workflow_engine=mock_workflow_engine,
        task_executor=mock_task_executor,
        llm_provider=mock_llm_provider
    )
    await orchestrator.start()
    yield orchestrator
    await orchestrator.stop()


@pytest.fixture
def intelligent_config():
    """Create intelligent workflow configuration."""
    return IntelligentWorkflowConfig(
        enable_llm_assistance=True,
        enable_multimodal=True,
        enable_error_recovery=True,
        enable_analytics=True,
        auto_optimize=True,
        learning_mode=True,
        conversation_context={"test_mode": True},
        performance_targets={"max_execution_time": 30.0}
    )


@pytest.fixture
def sample_workflow():
    """Create sample workflow definition."""
    return {
        "type": "test_workflow",
        "name": "Integration Test Workflow",
        "tasks": [
            {
                "id": "task_1",
                "name": "First Task",
                "type": "browser_action",
                "priority": "high",
                "definition": {"action": "navigate", "url": "https://example.com"}
            },
            {
                "id": "task_2", 
                "name": "Second Task",
                "type": "data_extraction",
                "priority": "normal",
                "definition": {"selector": "h1", "action": "get_text"}
            }
        ],
        "dependencies": [
            {"from": "task_1", "to": "task_2", "type": "hard"}
        ],
        "execution_mode": "hybrid",
        "max_parallel": 3
    }


class TestAdvancedOrchestrator:
    """Test suite for Advanced Orchestrator integration."""
    
    @pytest.mark.asyncio
    async def test_intelligent_workflow_execution(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test complete intelligent workflow execution."""
        
        # Execute workflow with intelligence
        result = await advanced_orchestrator.execute_intelligent_workflow(
            workflow_definition=sample_workflow,
            config=intelligent_config,
            context={"test_execution": True}
        )
        
        # Verify result structure
        assert "workflow_id" in result
        assert "correlation_id" in result
        assert "result" in result
        assert "execution_time" in result
        assert "intelligence_insights" in result
        assert "performance_metrics" in result
        
        # Verify execution success
        assert result["result"]["success"] is True
        assert result["execution_time"] > 0
        
        # Verify intelligence insights are present
        insights = result["intelligence_insights"]
        assert "llm_analysis" in insights
        assert "conversation_statistics" in insights
        assert "multimodal_statistics" in insights
        assert "error_recovery_statistics" in insights
    
    @pytest.mark.asyncio
    async def test_llm_workflow_analysis(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test LLM-based workflow analysis."""
        
        # Execute workflow with LLM assistance enabled
        result = await advanced_orchestrator.execute_intelligent_workflow(
            workflow_definition=sample_workflow,
            config=intelligent_config
        )
        
        # Verify LLM analysis was performed
        insights = result["intelligence_insights"]
        assert insights["llm_analysis"] is not None
        assert "analysis" in insights["llm_analysis"]
        assert "timestamp" in insights["llm_analysis"]
        
        # Verify conversation statistics
        conv_stats = insights["conversation_statistics"]
        assert conv_stats is not None
        assert conv_stats["total_messages"] > 0
    
    @pytest.mark.asyncio
    async def test_error_recovery_integration(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test error recovery integration."""
        
        # Mock an error in task execution
        with patch.object(
            advanced_orchestrator.task_executor, 
            'execute_task', 
            side_effect=Exception("Test error")
        ):
            # Mock successful recovery
            with patch.object(
                advanced_orchestrator.error_recovery,
                'handle_error',
                return_value={"resolved": True, "pattern_id": "test_pattern"}
            ):
                # Execute workflow - should recover from error
                result = await advanced_orchestrator.execute_intelligent_workflow(
                    workflow_definition=sample_workflow,
                    config=intelligent_config
                )
                
                # Verify error recovery was triggered
                insights = result["intelligence_insights"]
                assert insights["error_recovery_statistics"] is not None
    
    @pytest.mark.asyncio
    async def test_analytics_integration(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test analytics integration."""
        
        # Execute workflow
        result = await advanced_orchestrator.execute_intelligent_workflow(
            workflow_definition=sample_workflow,
            config=intelligent_config
        )
        
        # Verify analytics were recorded
        analytics_stats = advanced_orchestrator.analytics_engine.get_statistics()
        assert analytics_stats["metrics_collected"] > 0
        
        # Verify performance metrics
        perf_metrics = result["performance_metrics"]
        assert isinstance(perf_metrics, dict)
    
    @pytest.mark.asyncio
    async def test_workflow_optimization(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test workflow optimization based on patterns."""
        
        # Execute workflow multiple times to build patterns
        for i in range(3):
            await advanced_orchestrator.execute_intelligent_workflow(
                workflow_definition=sample_workflow,
                config=intelligent_config
            )
        
        # Get optimization suggestions
        suggestions = await advanced_orchestrator.get_optimization_suggestions()
        
        # Verify suggestions are generated
        assert isinstance(suggestions, list)
        
        # Verify orchestrator statistics
        stats = advanced_orchestrator.get_statistics()
        assert stats["learned_patterns"] > 0
    
    @pytest.mark.asyncio
    async def test_multimodal_processing_integration(
        self, 
        advanced_orchestrator, 
        intelligent_config
    ):
        """Test multi-modal processing integration."""
        
        # Create workflow with screenshot task
        workflow_with_screenshot = {
            "type": "screenshot_workflow",
            "tasks": [
                {
                    "id": "screenshot_task",
                    "name": "Take Screenshot",
                    "type": "screenshot",
                    "definition": {"action": "screenshot", "element": "body"}
                }
            ]
        }
        
        # Mock task executor to return screenshot data
        mock_screenshot_data = b"fake_screenshot_data"
        with patch.object(
            advanced_orchestrator.task_executor,
            'execute_task',
            return_value=AsyncMock(
                success=True,
                result={"screenshot": mock_screenshot_data}
            )
        ):
            # Mock multimodal processor
            with patch.object(
                advanced_orchestrator.multimodal_processor,
                'process_content',
                return_value=AsyncMock(
                    result_data={"analysis": "Screenshot analysis result"}
                )
            ):
                result = await advanced_orchestrator.execute_intelligent_workflow(
                    workflow_definition=workflow_with_screenshot,
                    config=intelligent_config
                )
                
                # Verify multimodal processing was triggered
                insights = result["intelligence_insights"]
                assert insights["multimodal_statistics"] is not None
    
    @pytest.mark.asyncio
    async def test_conversation_management(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test conversation management integration."""
        
        # Execute workflow
        result = await advanced_orchestrator.execute_intelligent_workflow(
            workflow_definition=sample_workflow,
            config=intelligent_config
        )
        
        # Verify conversation was created and managed
        insights = result["intelligence_insights"]
        conv_stats = insights["conversation_statistics"]
        
        assert conv_stats is not None
        assert conv_stats["conversation_id"] is not None
        assert conv_stats["total_messages"] >= 2  # Analysis + post-execution
        assert conv_stats["state"] in ["active", "completed"]
    
    @pytest.mark.asyncio
    async def test_execution_context_management(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test execution context management."""
        
        # Start workflow execution
        execution_task = asyncio.create_task(
            advanced_orchestrator.execute_intelligent_workflow(
                workflow_definition=sample_workflow,
                config=intelligent_config
            )
        )
        
        # Give it a moment to start
        await asyncio.sleep(0.1)
        
        # Verify active execution is tracked
        assert len(advanced_orchestrator.active_executions) > 0
        
        # Wait for completion
        result = await execution_task
        
        # Verify execution was cleaned up
        assert len(advanced_orchestrator.active_executions) == 0
        assert result["result"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_performance_learning(
        self, 
        advanced_orchestrator, 
        intelligent_config, 
        sample_workflow
    ):
        """Test performance learning and pattern recognition."""
        
        # Execute same workflow type multiple times
        workflow_type = sample_workflow["type"]
        
        for i in range(5):
            await advanced_orchestrator.execute_intelligent_workflow(
                workflow_definition=sample_workflow,
                config=intelligent_config
            )
        
        # Verify patterns were learned
        assert workflow_type in advanced_orchestrator.execution_patterns
        
        pattern = advanced_orchestrator.execution_patterns[workflow_type]
        assert pattern["execution_count"] == 5
        assert pattern["average_execution_time"] > 0
        assert pattern["success_rate"] > 0
    
    @pytest.mark.asyncio
    async def test_configuration_variations(
        self, 
        advanced_orchestrator, 
        sample_workflow
    ):
        """Test different configuration variations."""
        
        # Test with minimal configuration
        minimal_config = IntelligentWorkflowConfig(
            enable_llm_assistance=False,
            enable_multimodal=False,
            enable_error_recovery=False,
            enable_analytics=False
        )
        
        result = await advanced_orchestrator.execute_intelligent_workflow(
            workflow_definition=sample_workflow,
            config=minimal_config
        )
        
        assert result["result"]["success"] is True
        
        # Test with full configuration
        full_config = IntelligentWorkflowConfig(
            enable_llm_assistance=True,
            enable_multimodal=True,
            enable_error_recovery=True,
            enable_analytics=True,
            auto_optimize=True,
            learning_mode=True
        )
        
        result = await advanced_orchestrator.execute_intelligent_workflow(
            workflow_definition=sample_workflow,
            config=full_config
        )
        
        assert result["result"]["success"] is True
        
        # Verify full configuration provides more insights
        insights = result["intelligence_insights"]
        assert insights["llm_analysis"] is not None
        assert insights["conversation_statistics"] is not None


@pytest.mark.asyncio
async def test_orchestrator_lifecycle():
    """Test orchestrator startup and shutdown."""
    
    mock_workflow_engine = MockWorkflowEngine()
    mock_task_executor = MockTaskExecutor()
    mock_llm_provider = MockLLMProvider()
    
    orchestrator = AdvancedOrchestrator(
        workflow_engine=mock_workflow_engine,
        task_executor=mock_task_executor,
        llm_provider=mock_llm_provider
    )
    
    # Test startup
    await orchestrator.start()
    assert orchestrator.analytics_engine.is_running is True
    
    # Test shutdown
    await orchestrator.stop()
    assert orchestrator.analytics_engine.is_running is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
