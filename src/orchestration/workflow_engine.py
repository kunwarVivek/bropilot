"""
Core workflow execution engine.

This module provides the main workflow engine that orchestrates task execution,
manages workflow lifecycle, and integrates with all orchestration components.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from enum import Enum

from core.interfaces import (
    IWorkflowEngine, ITaskExecutor, TaskDefinition, WorkflowDefinition,
    ExecutionResult, TaskStatus, WorkflowStatus
)
from core.exceptions import (
    WorkflowExecutionError, ValidationError, TaskExecutionError,
    StateManagementError, OrchestrationError
)
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.orchestration.state_manager import StateManager
from src.orchestration.dependency_graph import DependencyGraph, TaskNode, TaskPriority
from src.orchestration.parallel_executor import ParallelExecutor, ExecutionConfig
from src.orchestration.workflow_controller import WorkflowController


class WorkflowExecutionMode(str, Enum):
    """Workflow execution modes."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEPENDENCY_BASED = "dependency_based"
    HYBRID = "hybrid"


class WorkflowEngine(IWorkflowEngine):
    """
    Core workflow execution engine.
    
    This engine provides comprehensive workflow orchestration capabilities including:
    - Sequential and parallel task execution
    - Dependency-based execution planning
    - State management and recovery
    - Pause/resume functionality
    - Error handling and retry logic
    """
    
    def __init__(
        self,
        task_executor: ITaskExecutor,
        state_manager: Optional[StateManager] = None,
        parallel_executor: Optional[ParallelExecutor] = None,
        workflow_controller: Optional[WorkflowController] = None,
        default_execution_mode: WorkflowExecutionMode = WorkflowExecutionMode.DEPENDENCY_BASED,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the workflow engine.
        
        Args:
            task_executor: Task executor for individual task execution
            state_manager: State manager for persistence and recovery
            parallel_executor: Parallel executor for concurrent task execution
            workflow_controller: Controller for workflow lifecycle management
            default_execution_mode: Default execution mode for workflows
            config: Additional configuration options
        """
        self.task_executor = task_executor
        self.state_manager = state_manager or StateManager()
        self.parallel_executor = parallel_executor or ParallelExecutor()
        self.workflow_controller = workflow_controller or WorkflowController(self.state_manager)
        self.default_execution_mode = default_execution_mode
        self.config = config or {}
        
        # Active workflows tracking
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        self.workflow_results: Dict[str, Dict[str, ExecutionResult]] = {}
        
        # Statistics
        self.total_workflows = 0
        self.successful_workflows = 0
        self.failed_workflows = 0
        
        # Initialize logger
        self.logger = StructuredLogger("workflow_engine")
        
        self.logger.info(
            "Workflow engine initialized",
            execution_mode=default_execution_mode.value,
            config_keys=list(self.config.keys())
        )
    
    async def initialize(self) -> None:
        """Initialize the workflow engine and its components."""
        try:
            # Initialize state manager
            await self.state_manager.initialize()
            
            # Initialize parallel executor
            await self.parallel_executor.initialize()
            
            self.logger.info("Workflow engine initialization completed")
            
        except Exception as e:
            self.logger.error("Failed to initialize workflow engine", error=str(e))
            raise OrchestrationError(f"Workflow engine initialization failed: {e}") from e
    
    @with_correlation_id
    async def execute_workflow(
        self,
        workflow_definition: WorkflowDefinition,
        context: Dict[str, Any]
    ) -> Dict[str, ExecutionResult]:
        """
        Execute a complete workflow.
        
        Args:
            workflow_definition: Definition of the workflow to execute
            context: Execution context with variables and metadata
            
        Returns:
            Dictionary mapping task names to their execution results
            
        Raises:
            WorkflowExecutionError: If workflow execution fails
            ValidationError: If workflow definition is invalid
        """
        workflow_id = context.get("workflow_id", str(uuid.uuid4()))
        correlation_id = context.get("correlation_id", str(uuid.uuid4()))
        
        self.logger.info(
            "Starting workflow execution",
            workflow_id=workflow_id,
            workflow_name=workflow_definition.name,
            task_count=len(workflow_definition.tasks),
            correlation_id=correlation_id
        )
        
        start_time = datetime.now(timezone.utc)
        self.total_workflows += 1
        
        try:
            # Validate workflow definition
            await self._validate_workflow(workflow_definition)
            
            # Create workflow execution context
            execution_context = await self._create_execution_context(
                workflow_definition, context, workflow_id, correlation_id
            )
            
            # Register active workflow
            self.active_workflows[workflow_id] = execution_context
            
            # Determine execution mode
            execution_mode = WorkflowExecutionMode(
                context.get("execution_mode", self.default_execution_mode.value)
            )
            
            # Execute workflow based on mode
            if execution_mode == WorkflowExecutionMode.SEQUENTIAL:
                results = await self._execute_sequential(workflow_definition, execution_context)
            elif execution_mode == WorkflowExecutionMode.PARALLEL:
                results = await self._execute_parallel(workflow_definition, execution_context)
            elif execution_mode == WorkflowExecutionMode.DEPENDENCY_BASED:
                results = await self._execute_dependency_based(workflow_definition, execution_context)
            elif execution_mode == WorkflowExecutionMode.HYBRID:
                results = await self._execute_hybrid(workflow_definition, execution_context)
            else:
                raise ValidationError(f"Unsupported execution mode: {execution_mode}")
            
            # Calculate execution time
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Update statistics
            if all(result.status == TaskStatus.COMPLETED for result in results.values()):
                self.successful_workflows += 1
                workflow_status = WorkflowStatus.COMPLETED
            else:
                self.failed_workflows += 1
                workflow_status = WorkflowStatus.FAILED
            
            # Store results
            self.workflow_results[workflow_id] = results
            
            # Update workflow context
            execution_context.update({
                "status": workflow_status,
                "end_time": datetime.now(timezone.utc),
                "execution_time": execution_time,
                "results": results
            })
            
            self.logger.info(
                "Workflow execution completed",
                workflow_id=workflow_id,
                status=workflow_status.value,
                execution_time=execution_time,
                successful_tasks=sum(1 for r in results.values() if r.status == TaskStatus.COMPLETED),
                total_tasks=len(results),
                correlation_id=correlation_id
            )
            
            return results
            
        except Exception as e:
            self.failed_workflows += 1
            execution_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            self.logger.error(
                "Workflow execution failed",
                workflow_id=workflow_id,
                error=str(e),
                execution_time=execution_time,
                correlation_id=correlation_id
            )
            
            # Create error result for all tasks
            error_results = {}
            for task_name in workflow_definition.tasks:
                error_results[task_name] = ExecutionResult(
                    status=TaskStatus.FAILED,
                    error_message=f"Workflow execution failed: {str(e)}",
                    execution_time=execution_time,
                    metadata={"workflow_error": True}
                )
            
            raise WorkflowExecutionError(f"Workflow execution failed: {e}") from e
            
        finally:
            # Cleanup active workflow
            if workflow_id in self.active_workflows:
                del self.active_workflows[workflow_id]
    
    async def pause_workflow(self, workflow_id: str) -> bool:
        """
        Pause a running workflow.
        
        Args:
            workflow_id: ID of the workflow to pause
            
        Returns:
            True if workflow was paused successfully
        """
        try:
            return await self.workflow_controller.pause_workflow(workflow_id)
        except Exception as e:
            self.logger.error(
                "Failed to pause workflow",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    async def resume_workflow(self, workflow_id: str) -> bool:
        """
        Resume a paused workflow.
        
        Args:
            workflow_id: ID of the workflow to resume
            
        Returns:
            True if workflow was resumed successfully
        """
        try:
            return await self.workflow_controller.resume_workflow(workflow_id)
        except Exception as e:
            self.logger.error(
                "Failed to resume workflow",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    async def cancel_workflow(self, workflow_id: str) -> bool:
        """
        Cancel a running workflow.
        
        Args:
            workflow_id: ID of the workflow to cancel
            
        Returns:
            True if workflow was cancelled successfully
        """
        try:
            return await self.workflow_controller.cancel_workflow(workflow_id)
        except Exception as e:
            self.logger.error(
                "Failed to cancel workflow",
                workflow_id=workflow_id,
                error=str(e)
            )
            return False
    
    async def get_workflow_status(self, workflow_id: str) -> WorkflowStatus:
        """
        Get the current status of a workflow.
        
        Args:
            workflow_id: ID of the workflow
            
        Returns:
            Current workflow status
        """
        try:
            return await self.workflow_controller.get_workflow_status(workflow_id)
        except Exception as e:
            self.logger.error(
                "Failed to get workflow status",
                workflow_id=workflow_id,
                error=str(e)
            )
            return WorkflowStatus.FAILED
    
    def get_active_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active workflows."""
        return {
            workflow_id: {
                "workflow_name": info.get("workflow_name"),
                "start_time": info.get("start_time").isoformat() if info.get("start_time") else None,
                "task_count": info.get("task_count"),
                "execution_mode": info.get("execution_mode"),
                "status": info.get("status", "running")
            }
            for workflow_id, info in self.active_workflows.items()
        }
    
    def get_workflow_results(self, workflow_id: str) -> Optional[Dict[str, ExecutionResult]]:
        """Get the results of a completed workflow."""
        return self.workflow_results.get(workflow_id)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get workflow engine statistics."""
        return {
            "total_workflows": self.total_workflows,
            "successful_workflows": self.successful_workflows,
            "failed_workflows": self.failed_workflows,
            "success_rate": self.successful_workflows / max(1, self.total_workflows),
            "active_workflows": len(self.active_workflows),
            "default_execution_mode": self.default_execution_mode.value,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of the workflow engine."""
        try:
            # Check state manager
            state_manager_health = await self.state_manager.health_check() if hasattr(self.state_manager, 'health_check') else {"status": "unknown"}
            
            # Check parallel executor
            parallel_executor_health = await self.parallel_executor.health_check() if hasattr(self.parallel_executor, 'health_check') else {"status": "unknown"}
            
            return {
                "status": "healthy",
                "engine": "workflow_engine",
                "active_workflows": len(self.active_workflows),
                "statistics": self.get_statistics(),
                "state_manager": state_manager_health,
                "parallel_executor": parallel_executor_health,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "engine": "workflow_engine",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def shutdown(self) -> None:
        """Shutdown the workflow engine and clean up resources."""
        self.logger.info("Shutting down workflow engine")
        
        try:
            # Cancel all active workflows
            for workflow_id in list(self.active_workflows.keys()):
                await self.cancel_workflow(workflow_id)
            
            # Shutdown components
            if hasattr(self.parallel_executor, 'shutdown'):
                await self.parallel_executor.shutdown()
            
            if hasattr(self.state_manager, 'shutdown'):
                await self.state_manager.shutdown()
            
        except Exception as e:
            self.logger.error("Error during workflow engine shutdown", error=str(e))
        
        self.logger.info("Workflow engine shutdown complete")

    # Private helper methods

    async def _validate_workflow(self, workflow_definition: WorkflowDefinition) -> None:
        """Validate workflow definition."""
        if not workflow_definition.name:
            raise ValidationError("Workflow name is required")

        if not workflow_definition.tasks:
            raise ValidationError("Workflow must contain at least one task")

        # Check for duplicate task names
        if len(workflow_definition.tasks) != len(set(workflow_definition.tasks)):
            raise ValidationError("Workflow contains duplicate task names")

    async def _create_execution_context(
        self,
        workflow_definition: WorkflowDefinition,
        context: Dict[str, Any],
        workflow_id: str,
        correlation_id: str
    ) -> Dict[str, Any]:
        """Create execution context for the workflow."""
        return {
            "workflow_id": workflow_id,
            "correlation_id": correlation_id,
            "workflow_name": workflow_definition.name,
            "workflow_description": workflow_definition.description,
            "task_count": len(workflow_definition.tasks),
            "start_time": datetime.now(timezone.utc),
            "execution_mode": context.get("execution_mode", self.default_execution_mode.value),
            "context": context,
            "metadata": workflow_definition.metadata or {}
        }

    async def _execute_sequential(
        self,
        workflow_definition: WorkflowDefinition,
        execution_context: Dict[str, Any]
    ) -> Dict[str, ExecutionResult]:
        """Execute workflow tasks sequentially."""
        results = {}

        for task_name in workflow_definition.tasks:
            # Create task definition
            task_definition = TaskDefinition(
                name=task_name,
                description=f"Task {task_name} from workflow {workflow_definition.name}",
                prompt_template=execution_context["context"].get(f"{task_name}_prompt", f"Execute task: {task_name}"),
                timeout=execution_context["context"].get(f"{task_name}_timeout", 300),
                retry_count=execution_context["context"].get(f"{task_name}_retry_count", 3),
                metadata={"workflow_id": execution_context["workflow_id"], "task_name": task_name}
            )

            # Execute task
            try:
                task_context = execution_context["context"].copy()
                task_context.update({
                    "task_name": task_name,
                    "workflow_id": execution_context["workflow_id"],
                    "correlation_id": execution_context["correlation_id"]
                })

                result = await self.task_executor.execute_task(task_definition, task_context)
                results[task_name] = result

                # Stop on failure if configured
                if result.status == TaskStatus.FAILED and not execution_context["context"].get("continue_on_failure", False):
                    break

            except Exception as e:
                results[task_name] = ExecutionResult(
                    status=TaskStatus.FAILED,
                    error_message=str(e),
                    metadata={"task_name": task_name, "execution_mode": "sequential"}
                )

                # Stop on failure if configured
                if not execution_context["context"].get("continue_on_failure", False):
                    break

        return results

    async def _execute_parallel(
        self,
        workflow_definition: WorkflowDefinition,
        execution_context: Dict[str, Any]
    ) -> Dict[str, ExecutionResult]:
        """Execute workflow tasks in parallel."""
        # Create task nodes for parallel execution
        task_nodes = []

        for task_name in workflow_definition.tasks:
            task_definition = TaskDefinition(
                name=task_name,
                description=f"Task {task_name} from workflow {workflow_definition.name}",
                prompt_template=execution_context["context"].get(f"{task_name}_prompt", f"Execute task: {task_name}"),
                timeout=execution_context["context"].get(f"{task_name}_timeout", 300),
                retry_count=execution_context["context"].get(f"{task_name}_retry_count", 3),
                metadata={"workflow_id": execution_context["workflow_id"], "task_name": task_name}
            )

            task_node = TaskNode(
                task_name=task_name,
                task_definition=task_definition,
                priority=TaskPriority.MEDIUM,
                dependencies=set(),  # No dependencies for parallel execution
                timeout=task_definition.timeout,
                max_retries=task_definition.retry_count
            )

            task_nodes.append(task_node)

        # Execute tasks in parallel
        execution_config = ExecutionConfig(
            max_concurrent_tasks=execution_context["context"].get("max_concurrent_tasks", 5),
            task_timeout=execution_context["context"].get("default_task_timeout", 300),
            continue_on_failure=execution_context["context"].get("continue_on_failure", True)
        )

        parallel_results = await self.parallel_executor.execute_tasks(
            task_nodes,
            self.task_executor,
            execution_config
        )

        # Convert parallel results to workflow results format
        results = {}
        for task_name, result in parallel_results.items():
            results[task_name] = result

        return results

    async def _execute_dependency_based(
        self,
        workflow_definition: WorkflowDefinition,
        execution_context: Dict[str, Any]
    ) -> Dict[str, ExecutionResult]:
        """Execute workflow tasks based on dependencies."""
        # Create dependency graph
        dependency_graph = DependencyGraph()

        # Add tasks to dependency graph
        for task_name in workflow_definition.tasks:
            task_definition = TaskDefinition(
                name=task_name,
                description=f"Task {task_name} from workflow {workflow_definition.name}",
                prompt_template=execution_context["context"].get(f"{task_name}_prompt", f"Execute task: {task_name}"),
                timeout=execution_context["context"].get(f"{task_name}_timeout", 300),
                retry_count=execution_context["context"].get(f"{task_name}_retry_count", 3),
                metadata={"workflow_id": execution_context["workflow_id"], "task_name": task_name}
            )

            # Get dependencies from context
            dependencies = set(execution_context["context"].get(f"{task_name}_dependencies", []))

            task_node = TaskNode(
                task_name=task_name,
                task_definition=task_definition,
                priority=TaskPriority.MEDIUM,
                dependencies=dependencies,
                timeout=task_definition.timeout,
                max_retries=task_definition.retry_count
            )

            dependency_graph.add_task(task_node)

        # Execute tasks based on dependency order
        execution_config = ExecutionConfig(
            max_concurrent_tasks=execution_context["context"].get("max_concurrent_tasks", 3),
            task_timeout=execution_context["context"].get("default_task_timeout", 300),
            continue_on_failure=execution_context["context"].get("continue_on_failure", False)
        )

        dependency_results = await self.parallel_executor.execute_dependency_graph(
            dependency_graph,
            self.task_executor,
            execution_config
        )

        # Convert dependency results to workflow results format
        results = {}
        for task_name, result in dependency_results.items():
            results[task_name] = result

        return results

    async def _execute_hybrid(
        self,
        workflow_definition: WorkflowDefinition,
        execution_context: Dict[str, Any]
    ) -> Dict[str, ExecutionResult]:
        """Execute workflow using hybrid approach (dependency-based with parallel optimization)."""
        # For now, use dependency-based execution
        # Future enhancement: Optimize parallel execution within dependency levels
        return await self._execute_dependency_based(workflow_definition, execution_context)
