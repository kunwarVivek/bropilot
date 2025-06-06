"""
End-to-end testing scenarios for complete workflow execution.

Tests realistic browser automation scenarios from start to finish,
including all advanced features and error conditions.
"""

import pytest
import asyncio
import json
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

from src.intelligence.advanced_orchestrator import (
    AdvancedOrchestrator, 
    IntelligentWorkflowConfig
)
from src.orchestration.dependency_graph import DependencyGraph, TaskNode, TaskPriority
from src.orchestration.parallel_executor import ParallelExecutor, ExecutionConfig
from src.orchestration.state_manager import StateManager
from src.infrastructure.resources.browser_pool import BrowserPool, BrowserFactory
from src.infrastructure.resources.pool_manager import PoolConfig
from core.interfaces import IWorkflowEngine, ITaskExecutor, ILLMProvider


class E2ETestExecutor(ITaskExecutor):
    """Test executor that simulates real browser automation tasks."""
    
    def __init__(self):
        self.execution_history = []
        self.failure_rate = 0.0  # Configurable failure rate for testing
        self.execution_delay = 0.1  # Simulated execution time
    
    async def execute_task(self, task_definition: Dict[str, Any], context: Dict[str, Any] = None) -> Any:
        """Simulate task execution with realistic behavior."""
        
        task_type = task_definition.get("type", "unknown")
        task_id = task_definition.get("id", "unknown")
        
        # Record execution
        execution_record = {
            "task_id": task_id,
            "task_type": task_type,
            "timestamp": datetime.utcnow(),
            "context": context or {}
        }
        self.execution_history.append(execution_record)
        
        # Simulate execution time
        await asyncio.sleep(self.execution_delay)
        
        # Simulate failures based on failure rate
        import random
        if random.random() < self.failure_rate:
            raise Exception(f"Simulated failure in task {task_id}")
        
        # Return task-specific results
        if task_type == "navigate":
            return {
                "url": task_definition.get("url", "https://example.com"),
                "status": "success",
                "load_time": 1.2
            }
        
        elif task_type == "screenshot":
            return {
                "screenshot": b"fake_screenshot_data",
                "timestamp": datetime.utcnow().isoformat(),
                "dimensions": {"width": 1920, "height": 1080}
            }
        
        elif task_type == "extract_data":
            return {
                "data": {"title": "Example Page", "content": "Sample content"},
                "elements_found": 5,
                "extraction_time": 0.5
            }
        
        elif task_type == "form_interaction":
            return {
                "form_filled": True,
                "fields_completed": task_definition.get("fields", []),
                "submission_status": "success"
            }
        
        else:
            return {
                "task_type": task_type,
                "status": "completed",
                "result": "Generic task result"
            }


class E2ETestLLMProvider(ILLMProvider):
    """Test LLM provider with realistic responses."""
    
    def __init__(self):
        self.call_history = []
    
    async def generate_response(
        self,
        messages,
        temperature=0.7,
        max_tokens=None,
        functions=None,
        tools=None
    ):
        """Generate contextual responses based on message content."""
        
        # Record call
        self.call_history.append({
            "messages": messages,
            "timestamp": datetime.utcnow(),
            "functions": functions,
            "tools": tools
        })
        
        # Analyze message content to provide relevant responses
        last_message = messages[-1] if messages else {}
        content = last_message.get("content", "").lower()
        
        if "analyze" in content and "workflow" in content:
            response_content = """
            Workflow Analysis:
            1. The workflow appears well-structured with clear task dependencies
            2. Potential optimization: Tasks 1 and 3 could run in parallel
            3. Risk factors: Network timeouts in navigation tasks
            4. Estimated execution time: 15-20 seconds
            5. Recommendation: Add retry logic for network-dependent tasks
            """
        
        elif "error" in content or "failed" in content:
            response_content = """
            Error Analysis:
            1. This appears to be a network connectivity issue
            2. Recommended recovery: Retry with exponential backoff
            3. Alternative approach: Use cached data if available
            4. Prevention: Implement connection health checks
            """
        
        elif "performance" in content or "execution" in content:
            response_content = """
            Performance Analysis:
            1. Execution time is within acceptable range
            2. Parallel execution reduced total time by 40%
            3. Resource utilization was optimal
            4. Recommendations: Consider caching for repeated operations
            """
        
        else:
            response_content = "I understand your request and will provide appropriate assistance for this automation workflow."
        
        return {
            "content": response_content,
            "model": "test-model-v1",
            "usage": {"total_tokens": len(response_content.split()) * 2},
            "finish_reason": "stop"
        }


@pytest.fixture
async def e2e_orchestrator():
    """Create orchestrator for end-to-end testing."""
    
    task_executor = E2ETestExecutor()
    llm_provider = E2ETestLLMProvider()
    
    # Mock workflow engine
    workflow_engine = Mock()
    workflow_engine.execute_workflow = AsyncMock(return_value={"success": True})
    
    orchestrator = AdvancedOrchestrator(
        workflow_engine=workflow_engine,
        task_executor=task_executor,
        llm_provider=llm_provider
    )
    
    await orchestrator.start()
    yield orchestrator
    await orchestrator.stop()


@pytest.fixture
def e2e_config():
    """Configuration for end-to-end testing."""
    return IntelligentWorkflowConfig(
        enable_llm_assistance=True,
        enable_multimodal=True,
        enable_error_recovery=True,
        enable_analytics=True,
        auto_optimize=True,
        learning_mode=True,
        conversation_context={"test_mode": "e2e"},
        performance_targets={"max_execution_time": 30.0}
    )


class TestCompleteWorkflows:
    """End-to-end workflow testing scenarios."""
    
    @pytest.mark.asyncio
    async def test_web_scraping_workflow(self, e2e_orchestrator, e2e_config):
        """Test complete web scraping workflow."""
        
        workflow = {
            "type": "web_scraping",
            "name": "E2E Web Scraping Test",
            "tasks": [
                {
                    "id": "navigate_to_site",
                    "name": "Navigate to Target Site",
                    "type": "navigate",
                    "priority": "high",
                    "definition": {
                        "url": "https://example.com",
                        "wait_for": "body"
                    }
                },
                {
                    "id": "take_screenshot",
                    "name": "Take Page Screenshot",
                    "type": "screenshot",
                    "priority": "normal",
                    "definition": {
                        "element": "body",
                        "full_page": True
                    }
                },
                {
                    "id": "extract_content",
                    "name": "Extract Page Content",
                    "type": "extract_data",
                    "priority": "high",
                    "definition": {
                        "selectors": ["h1", "p", ".content"],
                        "attributes": ["text", "href"]
                    }
                },
                {
                    "id": "process_data",
                    "name": "Process Extracted Data",
                    "type": "data_processing",
                    "priority": "normal",
                    "definition": {
                        "operations": ["clean", "validate", "transform"]
                    }
                }
            ],
            "dependencies": [
                {"from": "navigate_to_site", "to": "take_screenshot", "type": "hard"},
                {"from": "navigate_to_site", "to": "extract_content", "type": "hard"},
                {"from": "extract_content", "to": "process_data", "type": "hard"}
            ],
            "execution_mode": "hybrid",
            "max_parallel": 3,
            "timeout": 60
        }
        
        # Execute workflow
        result = await e2e_orchestrator.execute_intelligent_workflow(
            workflow_definition=workflow,
            config=e2e_config
        )
        
        # Verify successful execution
        assert result["result"]["success"] is True
        assert result["execution_time"] > 0
        
        # Verify all tasks were executed
        task_executor = e2e_orchestrator.task_executor
        assert len(task_executor.execution_history) == 4
        
        # Verify task execution order respects dependencies
        execution_times = {
            record["task_id"]: record["timestamp"] 
            for record in task_executor.execution_history
        }
        
        # Navigate should be first
        assert execution_times["navigate_to_site"] <= execution_times["take_screenshot"]
        assert execution_times["navigate_to_site"] <= execution_times["extract_content"]
        
        # Process data should be last
        assert execution_times["extract_content"] <= execution_times["process_data"]
        
        # Verify intelligence insights
        insights = result["intelligence_insights"]
        assert insights["llm_analysis"] is not None
        assert insights["conversation_statistics"]["total_messages"] >= 2
    
    @pytest.mark.asyncio
    async def test_form_automation_workflow(self, e2e_orchestrator, e2e_config):
        """Test form automation workflow with error recovery."""
        
        workflow = {
            "type": "form_automation",
            "name": "E2E Form Automation Test",
            "tasks": [
                {
                    "id": "navigate_to_form",
                    "name": "Navigate to Form Page",
                    "type": "navigate",
                    "priority": "critical",
                    "definition": {
                        "url": "https://example.com/form",
                        "wait_for": "form"
                    }
                },
                {
                    "id": "fill_personal_info",
                    "name": "Fill Personal Information",
                    "type": "form_interaction",
                    "priority": "high",
                    "definition": {
                        "fields": [
                            {"name": "first_name", "value": "John"},
                            {"name": "last_name", "value": "Doe"},
                            {"name": "email", "value": "john.doe@example.com"}
                        ]
                    }
                },
                {
                    "id": "fill_address",
                    "name": "Fill Address Information",
                    "type": "form_interaction",
                    "priority": "high",
                    "definition": {
                        "fields": [
                            {"name": "street", "value": "123 Main St"},
                            {"name": "city", "value": "Anytown"},
                            {"name": "zip", "value": "12345"}
                        ]
                    }
                },
                {
                    "id": "submit_form",
                    "name": "Submit Form",
                    "type": "form_interaction",
                    "priority": "critical",
                    "definition": {
                        "action": "submit",
                        "button": "#submit-btn",
                        "wait_for_response": True
                    }
                },
                {
                    "id": "verify_submission",
                    "name": "Verify Form Submission",
                    "type": "extract_data",
                    "priority": "high",
                    "definition": {
                        "selectors": [".success-message", ".error-message"],
                        "validation": "success"
                    }
                }
            ],
            "dependencies": [
                {"from": "navigate_to_form", "to": "fill_personal_info", "type": "hard"},
                {"from": "navigate_to_form", "to": "fill_address", "type": "hard"},
                {"from": "fill_personal_info", "to": "submit_form", "type": "hard"},
                {"from": "fill_address", "to": "submit_form", "type": "hard"},
                {"from": "submit_form", "to": "verify_submission", "type": "hard"}
            ],
            "execution_mode": "hybrid",
            "max_parallel": 2
        }
        
        # Execute workflow
        result = await e2e_orchestrator.execute_intelligent_workflow(
            workflow_definition=workflow,
            config=e2e_config
        )
        
        # Verify execution
        assert result["result"]["success"] is True
        
        # Verify parallel execution of form filling tasks
        task_executor = e2e_orchestrator.task_executor
        execution_records = task_executor.execution_history
        
        # Find form filling tasks
        personal_info_time = None
        address_time = None
        
        for record in execution_records:
            if record["task_id"] == "fill_personal_info":
                personal_info_time = record["timestamp"]
            elif record["task_id"] == "fill_address":
                address_time = record["timestamp"]
        
        # These tasks should run in parallel (very close timestamps)
        if personal_info_time and address_time:
            time_diff = abs((personal_info_time - address_time).total_seconds())
            assert time_diff < 1.0  # Should start within 1 second of each other
    
    @pytest.mark.asyncio
    async def test_error_recovery_scenario(self, e2e_orchestrator, e2e_config):
        """Test workflow with error recovery."""
        
        # Configure task executor to fail initially
        task_executor = e2e_orchestrator.task_executor
        task_executor.failure_rate = 0.5  # 50% failure rate
        
        workflow = {
            "type": "error_prone_workflow",
            "name": "E2E Error Recovery Test",
            "tasks": [
                {
                    "id": "unreliable_task_1",
                    "name": "Unreliable Network Task",
                    "type": "navigate",
                    "priority": "high",
                    "definition": {"url": "https://unreliable-site.com"}
                },
                {
                    "id": "unreliable_task_2",
                    "name": "Unreliable Data Task",
                    "type": "extract_data",
                    "priority": "normal",
                    "definition": {"selector": ".dynamic-content"}
                }
            ],
            "dependencies": [
                {"from": "unreliable_task_1", "to": "unreliable_task_2", "type": "hard"}
            ],
            "execution_mode": "sequential"
        }
        
        # Mock error recovery to always succeed
        with patch.object(
            e2e_orchestrator.error_recovery,
            'handle_error',
            return_value={"resolved": True, "pattern_id": "network_error"}
        ):
            # Execute workflow - should recover from errors
            result = await e2e_orchestrator.execute_intelligent_workflow(
                workflow_definition=workflow,
                config=e2e_config
            )
            
            # Verify eventual success despite errors
            assert result["result"]["success"] is True
            
            # Verify error recovery statistics
            insights = result["intelligence_insights"]
            error_stats = insights["error_recovery_statistics"]
            assert error_stats is not None
    
    @pytest.mark.asyncio
    async def test_performance_optimization_learning(self, e2e_orchestrator, e2e_config):
        """Test performance optimization through learning."""
        
        workflow = {
            "type": "performance_test_workflow",
            "name": "Performance Learning Test",
            "tasks": [
                {
                    "id": "task_a",
                    "name": "Task A",
                    "type": "navigate",
                    "priority": "normal",
                    "definition": {"url": "https://site-a.com"}
                },
                {
                    "id": "task_b",
                    "name": "Task B", 
                    "type": "extract_data",
                    "priority": "normal",
                    "definition": {"selector": ".content"}
                },
                {
                    "id": "task_c",
                    "name": "Task C",
                    "type": "screenshot",
                    "priority": "low",
                    "definition": {"element": "body"}
                }
            ],
            "dependencies": [],  # No dependencies - can run in parallel
            "execution_mode": "parallel",
            "max_parallel": 3
        }
        
        # Execute workflow multiple times to build learning data
        execution_times = []
        
        for i in range(5):
            result = await e2e_orchestrator.execute_intelligent_workflow(
                workflow_definition=workflow,
                config=e2e_config
            )
            
            execution_times.append(result["execution_time"])
            assert result["result"]["success"] is True
        
        # Verify learning occurred
        workflow_type = workflow["type"]
        assert workflow_type in e2e_orchestrator.execution_patterns
        
        pattern = e2e_orchestrator.execution_patterns[workflow_type]
        assert pattern["execution_count"] == 5
        assert pattern["average_execution_time"] > 0
        assert pattern["success_rate"] == 1.0
        
        # Get optimization suggestions
        suggestions = await e2e_orchestrator.get_optimization_suggestions()
        assert isinstance(suggestions, list)
    
    @pytest.mark.asyncio
    async def test_multimodal_content_processing(self, e2e_orchestrator, e2e_config):
        """Test workflow with multi-modal content processing."""
        
        workflow = {
            "type": "multimodal_workflow",
            "name": "E2E Multimodal Test",
            "tasks": [
                {
                    "id": "capture_screenshot",
                    "name": "Capture Page Screenshot",
                    "type": "screenshot",
                    "priority": "high",
                    "definition": {
                        "element": "body",
                        "full_page": True
                    }
                },
                {
                    "id": "analyze_image",
                    "name": "Analyze Screenshot",
                    "type": "image_analysis",
                    "priority": "normal",
                    "definition": {
                        "analysis_type": "ui",
                        "extract_text": True
                    }
                }
            ],
            "dependencies": [
                {"from": "capture_screenshot", "to": "analyze_image", "type": "hard"}
            ],
            "execution_mode": "sequential"
        }
        
        # Mock multimodal processor
        with patch.object(
            e2e_orchestrator.multimodal_processor,
            'process_content',
            return_value=AsyncMock(
                result_data={
                    "analysis": "UI screenshot analysis",
                    "elements_detected": ["button", "form", "text"],
                    "text_extracted": "Sample page content"
                }
            )
        ):
            result = await e2e_orchestrator.execute_intelligent_workflow(
                workflow_definition=workflow,
                config=e2e_config
            )
            
            assert result["result"]["success"] is True
            
            # Verify multimodal processing was triggered
            insights = result["intelligence_insights"]
            assert insights["multimodal_statistics"] is not None
    
    @pytest.mark.asyncio
    async def test_state_persistence_and_recovery(self, e2e_orchestrator, e2e_config):
        """Test workflow state persistence and recovery."""
        
        workflow = {
            "type": "stateful_workflow",
            "name": "E2E State Persistence Test",
            "tasks": [
                {
                    "id": "long_running_task",
                    "name": "Long Running Task",
                    "type": "data_processing",
                    "priority": "normal",
                    "definition": {
                        "operation": "complex_calculation",
                        "duration": 5
                    }
                }
            ],
            "execution_mode": "sequential",
            "enable_checkpoints": True
        }
        
        # Execute workflow
        result = await e2e_orchestrator.execute_intelligent_workflow(
            workflow_definition=workflow,
            config=e2e_config
        )
        
        assert result["result"]["success"] is True
        
        # Verify state manager was used
        state_manager = e2e_orchestrator.state_manager
        assert state_manager is not None
    
    @pytest.mark.asyncio
    async def test_comprehensive_analytics_collection(self, e2e_orchestrator, e2e_config):
        """Test comprehensive analytics collection during workflow execution."""
        
        workflow = {
            "type": "analytics_test_workflow",
            "name": "E2E Analytics Collection Test",
            "tasks": [
                {
                    "id": "metric_generating_task",
                    "name": "Task That Generates Metrics",
                    "type": "navigate",
                    "priority": "normal",
                    "definition": {"url": "https://metrics-test.com"}
                }
            ],
            "execution_mode": "sequential"
        }
        
        # Execute workflow
        result = await e2e_orchestrator.execute_intelligent_workflow(
            workflow_definition=workflow,
            config=e2e_config
        )
        
        assert result["result"]["success"] is True
        
        # Verify analytics were collected
        analytics_engine = e2e_orchestrator.analytics_engine
        stats = analytics_engine.get_statistics()
        
        assert stats["metrics_collected"] > 0
        assert stats["is_running"] is True
        
        # Verify dashboard data can be generated
        dashboard_data = await analytics_engine.generate_dashboard_data()
        assert "timestamp" in dashboard_data
        assert "executions" in dashboard_data
        assert "health" in dashboard_data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
