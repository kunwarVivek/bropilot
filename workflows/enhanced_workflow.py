"""
Enhanced workflow implementation using the new execution layer.

This module provides an improved workflow system that uses the new execution layer
while maintaining compatibility with existing task definitions and APIs.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any
from fastapi import HTTPException
from tenacity import RetryError
from dotenv import dotenv_values, load_dotenv

from src.execution.legacy_bridge import get_legacy_bridge, initialize_bridge
from tasks.definitions import get_task_templates

load_dotenv()


class EnhancedWorkflowEngine:
    """
    Enhanced workflow engine using the new execution layer.
    
    This engine provides improved error handling, monitoring, and execution
    capabilities while maintaining backward compatibility.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the enhanced workflow engine.
        
        Args:
            config: Configuration for the workflow engine
        """
        self.config = config or {}
        self.bridge = None
        self.llm = None
        
        # Workflow tracking
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_history: List[Dict[str, Any]] = []
    
    async def initialize(self) -> None:
        """Initialize the workflow engine and its dependencies."""
        # Initialize the legacy bridge with new execution layer
        bridge_config = {
            "use_new_execution": self.config.get("use_new_execution", True),
            "fallback_to_legacy": self.config.get("fallback_to_legacy", True),
            "llm_provider": self.config.get("llm_provider", "gemini"),
            "llm_config": self.config.get("llm_config", {}),
            "browser_config": self.config.get("browser_config", {}),
            "enable_browser_pooling": self.config.get("enable_browser_pooling", False),
            "default_timeout": self.config.get("default_timeout", 300),
            "save_logs": self.config.get("save_logs", True),
            "logs_base_path": self.config.get("logs_base_path", "logs")
        }
        
        self.bridge = await initialize_bridge(bridge_config)
        
        # Initialize LLM
        self.llm = get_llm()
        
        # Test LLM connectivity
        try:
            response = self.llm.invoke("What is the capital of France?")
            print(f"LLM test successful: {response}")
        except RetryError:
            raise HTTPException(
                status_code=503, 
                detail="The AI model is currently overloaded. Please try again shortly."
            )
    
    async def run_workflow(
        self,
        flow_sequence: List[str],
        workflow_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a workflow with enhanced monitoring and error handling.
        
        Args:
            flow_sequence: List of task names to execute
            workflow_id: Optional workflow identifier
            **kwargs: Additional parameters
            
        Returns:
            Workflow execution results with metadata
        """
        # Generate workflow ID if not provided
        workflow_id = workflow_id or str(uuid.uuid4())
        
        # Load task templates
        env_vars = dotenv_values(".env")
        task_templates = get_task_templates(env_vars)
        
        # Validate tasks
        invalid_tasks = [task for task in flow_sequence if task not in task_templates]
        if invalid_tasks:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid tasks: {', '.join(invalid_tasks)}"
            )
        
        # Initialize workflow tracking
        workflow_start_time = time.time()
        workflow_metadata = {
            "workflow_id": workflow_id,
            "flow_sequence": flow_sequence,
            "start_time": workflow_start_time,
            "status": "running",
            "task_count": len(flow_sequence),
            "use_new_execution": self.bridge.use_new_execution if self.bridge else False
        }
        
        self.active_workflows[workflow_id] = workflow_metadata
        
        print(f"Starting enhanced workflow {workflow_id} with tasks: {flow_sequence}")
        
        try:
            # Execute workflow using the bridge
            results = await self.bridge.run_workflow(
                flow_sequence=flow_sequence,
                task_templates=task_templates,
                llm=self.llm,
                workflow_id=workflow_id,
                **kwargs
            )
            
            # Calculate workflow statistics
            workflow_end_time = time.time()
            total_execution_time = workflow_end_time - workflow_start_time
            
            # Count task statuses
            completed_tasks = sum(1 for r in results.values() if r["status"] == "completed")
            failed_tasks = sum(1 for r in results.values() if r["status"] == "error")
            timeout_tasks = sum(1 for r in results.values() if r["status"] == "timeout")
            
            # Update workflow metadata
            workflow_metadata.update({
                "status": "completed",
                "end_time": workflow_end_time,
                "total_execution_time": total_execution_time,
                "completed_tasks": completed_tasks,
                "failed_tasks": failed_tasks,
                "timeout_tasks": timeout_tasks,
                "success_rate": completed_tasks / len(flow_sequence) if flow_sequence else 0
            })
            
            # Create enhanced result
            enhanced_result = {
                "workflow_id": workflow_id,
                "status": "completed",
                "metadata": workflow_metadata,
                "task_results": results,
                "statistics": {
                    "total_tasks": len(flow_sequence),
                    "completed_tasks": completed_tasks,
                    "failed_tasks": failed_tasks,
                    "timeout_tasks": timeout_tasks,
                    "success_rate": completed_tasks / len(flow_sequence) if flow_sequence else 0,
                    "total_execution_time": total_execution_time
                },
                "bridge_statistics": self.bridge.get_statistics() if self.bridge else {}
            }
            
            # Move to history
            self.workflow_history.append(workflow_metadata.copy())
            del self.active_workflows[workflow_id]
            
            print(f"Enhanced workflow {workflow_id} completed in {total_execution_time:.2f} seconds")
            print(f"Success rate: {completed_tasks}/{len(flow_sequence)} ({enhanced_result['statistics']['success_rate']:.1%})")
            
            return enhanced_result
            
        except Exception as e:
            # Handle workflow failure
            workflow_metadata.update({
                "status": "failed",
                "error": str(e),
                "end_time": time.time()
            })
            
            self.workflow_history.append(workflow_metadata.copy())
            del self.active_workflows[workflow_id]
            
            print(f"Enhanced workflow {workflow_id} failed: {str(e)}")
            
            return {
                "workflow_id": workflow_id,
                "status": "failed",
                "error": str(e),
                "metadata": workflow_metadata
            }
    
    def get_available_tasks(self) -> Dict[str, List[str]]:
        """Get available tasks with enhanced metadata."""
        env_vars = dotenv_values(".env")
        task_templates = get_task_templates(env_vars)
        
        return {
            "tasks": list(task_templates.keys()),
            "task_count": len(task_templates),
            "engine_type": "enhanced",
            "new_execution_available": self.bridge.use_new_execution if self.bridge else False
        }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a specific workflow."""
        if workflow_id in self.active_workflows:
            return self.active_workflows[workflow_id].copy()
        
        # Check history
        for workflow in self.workflow_history:
            if workflow["workflow_id"] == workflow_id:
                return workflow.copy()
        
        return None
    
    def get_active_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active workflows."""
        return self.active_workflows.copy()
    
    def get_workflow_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent workflow history."""
        return self.workflow_history[-limit:] if limit > 0 else self.workflow_history.copy()
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the workflow engine."""
        health_status = {
            "engine_status": "healthy",
            "active_workflows": len(self.active_workflows),
            "total_workflows_executed": len(self.workflow_history),
            "llm_available": self.llm is not None
        }
        
        # Check bridge health
        if self.bridge:
            bridge_health = await self.bridge.health_check()
            health_status["bridge_health"] = bridge_health
        
        return health_status
    
    async def shutdown(self) -> None:
        """Shutdown the workflow engine and clean up resources."""
        if self.bridge:
            await self.bridge.shutdown()


# Legacy compatibility functions
def get_llm():
    """Get LLM instance (legacy compatibility)."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    import os
    from langchain_core.rate_limiters import InMemoryRateLimiter

    rate_limiter = InMemoryRateLimiter(
        requests_per_second=1,
        check_every_n_seconds=0.1,
        max_bucket_size=10
    )
    return ChatGoogleGenerativeAI(
        model="models/gemini-2.5-flash-preview-04-17",
        google_api_key=os.environ["GEMINI_API_KEY"],
        rate_limiter=rate_limiter
    )


async def run_workflow(flow_sequence: List[str], **kwargs) -> Dict[str, Any]:
    """
    Legacy-compatible workflow execution function.
    
    This function maintains the same API as the original run_workflow
    but uses the enhanced workflow engine internally.
    """
    # Create and initialize enhanced engine
    config = kwargs.get("config", {})
    engine = EnhancedWorkflowEngine(config)
    await engine.initialize()
    
    # Execute workflow
    result = await engine.run_workflow(flow_sequence, **kwargs)
    
    # Return in legacy format for backward compatibility
    if "task_results" in result:
        return result["task_results"]
    else:
        return {"error": result.get("error", "Unknown error")}


def get_available_tasks() -> Dict[str, List[str]]:
    """Legacy-compatible function to get available tasks."""
    env_vars = dotenv_values(".env")
    task_templates = get_task_templates(env_vars)
    return {"tasks": list(task_templates.keys())}


# Global engine instance for advanced usage
_global_engine: Optional[EnhancedWorkflowEngine] = None


async def get_workflow_engine(config: Optional[Dict[str, Any]] = None) -> EnhancedWorkflowEngine:
    """
    Get the global workflow engine instance.
    
    Args:
        config: Configuration for the engine (only used on first call)
        
    Returns:
        Initialized EnhancedWorkflowEngine instance
    """
    global _global_engine
    
    if _global_engine is None:
        _global_engine = EnhancedWorkflowEngine(config)
        await _global_engine.initialize()
    
    return _global_engine
