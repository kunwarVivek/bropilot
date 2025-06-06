"""
Workflow controller with pause/resume functionality.

This module provides comprehensive workflow control including pause, resume,
cancel operations with proper state management and recovery.
"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime
import uuid

from core.interfaces import IWorkflowEngine, TaskStatus, WorkflowStatus
from core.exceptions import WorkflowExecutionError, StateManagementError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from .state_machine import ExecutionState, ExecutionContext
from .state_manager import StateManager


class WorkflowController:
    """Controller for workflow execution with pause/resume capabilities."""
    
    def __init__(self, state_manager: StateManager):
        """Initialize workflow controller.
        
        Args:
            state_manager: State manager instance for checkpoint/restore
        """
        self.logger = StructuredLogger("workflow_controller")
        self.state_manager = state_manager
        
        # Active workflow executions
        self.active_workflows: Dict[str, WorkflowExecution] = {}
        
        # Pause/resume control
        self.pause_events: Dict[str, asyncio.Event] = {}
        self.cancel_events: Dict[str, asyncio.Event] = {}
        
        # Execution locks for thread safety
        self.execution_locks: Dict[str, asyncio.Lock] = {}
    
    async def start_workflow(
        self,
        workflow_id: str,
        workflow_definition: Dict[str, Any],
        context: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> str:
        """Start a new workflow execution."""
        
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        self.logger.info(
            "Starting workflow execution",
            workflow_id=workflow_id,
            correlation_id=correlation_id
        )
        
        try:
            # Create execution context
            execution_context = await self.state_manager.start_execution_tracking(
                workflow_id, correlation_id, ExecutionState.PENDING
            )
            
            # Create workflow execution
            workflow_execution = WorkflowExecution(
                workflow_id=workflow_id,
                definition=workflow_definition,
                context=context,
                execution_context=execution_context
            )
            
            # Initialize control events
            self.pause_events[workflow_id] = asyncio.Event()
            self.pause_events[workflow_id].set()  # Start in running state
            
            self.cancel_events[workflow_id] = asyncio.Event()
            self.execution_locks[workflow_id] = asyncio.Lock()
            
            # Store active workflow
            self.active_workflows[workflow_id] = workflow_execution
            
            # Transition to initializing state
            await self.state_manager.transition_state(
                workflow_id,
                ExecutionState.INITIALIZING,
                reason="Workflow started",
                triggered_by="workflow_controller"
            )
            
            self.logger.info(
                "Workflow execution started successfully",
                workflow_id=workflow_id,
                correlation_id=correlation_id
            )
            
            return workflow_id
            
        except Exception as e:
            self.logger.error(
                "Failed to start workflow execution",
                workflow_id=workflow_id,
                correlation_id=correlation_id,
                error=str(e)
            )
            raise WorkflowExecutionError(f"Failed to start workflow: {e}") from e
    
    async def pause_workflow(self, workflow_id: str, reason: Optional[str] = None) -> bool:
        """Pause a running workflow."""
        
        self.logger.info(
            "Pausing workflow execution",
            workflow_id=workflow_id,
            reason=reason
        )
        
        try:
            async with self.execution_locks.get(workflow_id, asyncio.Lock()):
                workflow = self.active_workflows.get(workflow_id)
                if not workflow:
                    raise WorkflowExecutionError(f"Workflow {workflow_id} not found")
                
                current_state = workflow.execution_context.current_state
                
                # Check if workflow can be paused
                if current_state not in [ExecutionState.RUNNING]:
                    raise WorkflowExecutionError(
                        f"Cannot pause workflow in state {current_state}"
                    )
                
                # Transition to paused state
                await self.state_manager.transition_state(
                    workflow_id,
                    ExecutionState.PAUSED,
                    reason=reason or "Manual pause",
                    triggered_by="workflow_controller"
                )
                
                # Clear the pause event to block execution
                self.pause_events[workflow_id].clear()
                
                # Create checkpoint
                await self.state_manager.create_checkpoint(
                    workflow_id,
                    f"pause_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "pause",
                    f"Checkpoint created during pause: {reason}"
                )
                
                self.logger.info(
                    "Workflow execution paused successfully",
                    workflow_id=workflow_id
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to pause workflow execution",
                workflow_id=workflow_id,
                error=str(e)
            )
            raise WorkflowExecutionError(f"Failed to pause workflow: {e}") from e
    
    async def resume_workflow(self, workflow_id: str, reason: Optional[str] = None) -> bool:
        """Resume a paused workflow."""
        
        self.logger.info(
            "Resuming workflow execution",
            workflow_id=workflow_id,
            reason=reason
        )
        
        try:
            async with self.execution_locks.get(workflow_id, asyncio.Lock()):
                workflow = self.active_workflows.get(workflow_id)
                if not workflow:
                    raise WorkflowExecutionError(f"Workflow {workflow_id} not found")
                
                current_state = workflow.execution_context.current_state
                
                # Check if workflow can be resumed
                if current_state not in [ExecutionState.PAUSED]:
                    raise WorkflowExecutionError(
                        f"Cannot resume workflow in state {current_state}"
                    )
                
                # Transition to resuming state
                await self.state_manager.transition_state(
                    workflow_id,
                    ExecutionState.RESUMING,
                    reason=reason or "Manual resume",
                    triggered_by="workflow_controller"
                )
                
                # Set the pause event to allow execution
                self.pause_events[workflow_id].set()
                
                # Transition to running state
                await self.state_manager.transition_state(
                    workflow_id,
                    ExecutionState.RUNNING,
                    reason="Resume completed",
                    triggered_by="workflow_controller"
                )
                
                self.logger.info(
                    "Workflow execution resumed successfully",
                    workflow_id=workflow_id
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to resume workflow execution",
                workflow_id=workflow_id,
                error=str(e)
            )
            raise WorkflowExecutionError(f"Failed to resume workflow: {e}") from e
    
    async def cancel_workflow(self, workflow_id: str, reason: Optional[str] = None) -> bool:
        """Cancel a workflow execution."""
        
        self.logger.info(
            "Cancelling workflow execution",
            workflow_id=workflow_id,
            reason=reason
        )
        
        try:
            async with self.execution_locks.get(workflow_id, asyncio.Lock()):
                workflow = self.active_workflows.get(workflow_id)
                if not workflow:
                    raise WorkflowExecutionError(f"Workflow {workflow_id} not found")
                
                current_state = workflow.execution_context.current_state
                
                # Check if workflow can be cancelled
                if current_state in [ExecutionState.COMPLETED, ExecutionState.FAILED, ExecutionState.CANCELLED]:
                    self.logger.warning(
                        "Workflow already in terminal state",
                        workflow_id=workflow_id,
                        current_state=current_state.value
                    )
                    return True
                
                # Transition to cancelling state
                await self.state_manager.transition_state(
                    workflow_id,
                    ExecutionState.CANCELLING,
                    reason=reason or "Manual cancellation",
                    triggered_by="workflow_controller"
                )
                
                # Set the cancel event
                self.cancel_events[workflow_id].set()
                
                # Create final checkpoint
                await self.state_manager.create_checkpoint(
                    workflow_id,
                    f"cancel_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    "cancel",
                    f"Checkpoint created during cancellation: {reason}"
                )
                
                # Transition to cancelled state
                await self.state_manager.transition_state(
                    workflow_id,
                    ExecutionState.CANCELLED,
                    reason="Cancellation completed",
                    triggered_by="workflow_controller"
                )
                
                # Cleanup
                await self._cleanup_workflow(workflow_id)
                
                self.logger.info(
                    "Workflow execution cancelled successfully",
                    workflow_id=workflow_id
                )
                
                return True
                
        except Exception as e:
            self.logger.error(
                "Failed to cancel workflow execution",
                workflow_id=workflow_id,
                error=str(e)
            )
            raise WorkflowExecutionError(f"Failed to cancel workflow: {e}") from e
    
    async def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get the current status of a workflow."""
        
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            # Try to load from state manager
            context = await self.state_manager.load_state(workflow_id)
            if context:
                return {
                    "workflow_id": workflow_id,
                    "status": context.get("current_state", "unknown"),
                    "active": False,
                    "last_updated": context.get("updated_at"),
                    "variables": context.get("variables", {}),
                    "metadata": context.get("metadata", {})
                }
            else:
                raise WorkflowExecutionError(f"Workflow {workflow_id} not found")
        
        return {
            "workflow_id": workflow_id,
            "status": workflow.execution_context.current_state.value,
            "active": True,
            "created_at": workflow.execution_context.created_at.isoformat(),
            "updated_at": workflow.execution_context.updated_at.isoformat(),
            "variables": workflow.execution_context.variables,
            "metadata": workflow.execution_context.metadata,
            "transition_history": [
                {
                    "from_state": t.from_state.value,
                    "to_state": t.to_state.value,
                    "timestamp": t.timestamp.isoformat(),
                    "reason": t.reason,
                    "triggered_by": t.triggered_by
                }
                for t in workflow.execution_context.transition_history
            ]
        }
    
    async def wait_for_pause_or_cancel(self, workflow_id: str) -> str:
        """Wait for pause or cancel signal during execution."""
        
        pause_event = self.pause_events.get(workflow_id)
        cancel_event = self.cancel_events.get(workflow_id)
        
        if not pause_event or not cancel_event:
            return "continue"
        
        # Wait for either pause to be cleared or cancel to be set
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(pause_event.wait()),
                asyncio.create_task(cancel_event.wait())
            ],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel pending tasks
        for task in pending:
            task.cancel()
        
        # Check which event was triggered
        if cancel_event.is_set():
            return "cancel"
        elif not pause_event.is_set():
            return "pause"
        else:
            return "continue"
    
    async def _cleanup_workflow(self, workflow_id: str) -> None:
        """Clean up workflow resources."""
        
        # Remove from active workflows
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
        
        # Clean up events
        if workflow_id in self.pause_events:
            del self.pause_events[workflow_id]
        
        if workflow_id in self.cancel_events:
            del self.cancel_events[workflow_id]
        
        if workflow_id in self.execution_locks:
            del self.execution_locks[workflow_id]
        
        # Stop state tracking
        await self.state_manager.stop_execution_tracking(workflow_id)
    
    def get_active_workflows(self) -> List[str]:
        """Get list of active workflow IDs."""
        return list(self.active_workflows.keys())
    
    async def restore_workflow(
        self, 
        workflow_id: str, 
        checkpoint_name: Optional[str] = None
    ) -> bool:
        """Restore a workflow from a checkpoint."""
        
        self.logger.info(
            "Restoring workflow from checkpoint",
            workflow_id=workflow_id,
            checkpoint_name=checkpoint_name
        )
        
        try:
            # Restore execution context
            context = await self.state_manager.restore_from_checkpoint(
                workflow_id, checkpoint_name
            )
            
            if not context:
                raise WorkflowExecutionError(f"No checkpoint found for workflow {workflow_id}")
            
            # Recreate workflow execution (simplified - would need full definition)
            workflow_execution = WorkflowExecution(
                workflow_id=workflow_id,
                definition={},  # Would need to be restored from checkpoint
                context=context.variables,
                execution_context=context
            )
            
            # Initialize control events
            self.pause_events[workflow_id] = asyncio.Event()
            self.cancel_events[workflow_id] = asyncio.Event()
            self.execution_locks[workflow_id] = asyncio.Lock()
            
            # Set appropriate event state based on current state
            if context.current_state == ExecutionState.PAUSED:
                self.pause_events[workflow_id].clear()
            else:
                self.pause_events[workflow_id].set()
            
            # Store active workflow
            self.active_workflows[workflow_id] = workflow_execution
            
            self.logger.info(
                "Workflow restored successfully",
                workflow_id=workflow_id,
                restored_state=context.current_state.value
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to restore workflow",
                workflow_id=workflow_id,
                error=str(e)
            )
            raise WorkflowExecutionError(f"Failed to restore workflow: {e}") from e


class WorkflowExecution:
    """Represents an active workflow execution."""
    
    def __init__(
        self,
        workflow_id: str,
        definition: Dict[str, Any],
        context: Dict[str, Any],
        execution_context: ExecutionContext
    ):
        self.workflow_id = workflow_id
        self.definition = definition
        self.context = context
        self.execution_context = execution_context
        self.created_at = datetime.utcnow()
        self.current_task_index = 0
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
