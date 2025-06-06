"""
State manager with checkpoint and restore functionality.

This module provides comprehensive state management for workflow executions
including checkpoint creation, state persistence, and recovery mechanisms.
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
from pathlib import Path

from core.interfaces import IStateManager
from core.exceptions import StateManagementError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.infrastructure.storage.database import get_db_session
from src.infrastructure.storage.repositories import (
    WorkflowExecutionRepository, TaskExecutionRepository, ExecutionCheckpointRepository
)
from .state_machine import ExecutionContext, ExecutionState, StateMachine


class StateManager(IStateManager):
    """State manager with checkpoint and restore functionality."""
    
    def __init__(self, checkpoint_interval: int = 60):
        """Initialize state manager.
        
        Args:
            checkpoint_interval: Automatic checkpoint interval in seconds
        """
        self.logger = StructuredLogger("state_manager")
        self.checkpoint_interval = checkpoint_interval
        self.state_machine = StateMachine()
        
        # In-memory state cache for active executions
        self.active_contexts: Dict[str, ExecutionContext] = {}
        
        # Checkpoint storage
        self.checkpoint_storage: Dict[str, Dict[str, Any]] = {}
        
        # Auto-checkpoint tasks
        self.checkpoint_tasks: Dict[str, asyncio.Task] = {}
    
    async def save_state(
        self, 
        execution_id: str, 
        state: Dict[str, Any]
    ) -> bool:
        """Save execution state for later restoration."""
        try:
            self.logger.info(
                "Saving execution state",
                execution_id=execution_id,
                state_keys=list(state.keys())
            )
            
            # Validate state data
            self._validate_state_data(state)
            
            # Store in memory cache
            self.checkpoint_storage[execution_id] = {
                "state": state,
                "timestamp": datetime.utcnow().isoformat(),
                "version": state.get("version", "1.0.0")
            }
            
            # Persist to database
            async with get_db_session() as session:
                checkpoint_repo = ExecutionCheckpointRepository(session)
                
                await checkpoint_repo.create(
                    workflow_execution_id=uuid.UUID(execution_id),
                    checkpoint_name=f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                    checkpoint_type="automatic",
                    execution_state=state,
                    description="Automatic state checkpoint"
                )
                
                await session.commit()
            
            self.logger.info(
                "Execution state saved successfully",
                execution_id=execution_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to save execution state",
                execution_id=execution_id,
                error=str(e)
            )
            raise StateManagementError(f"Failed to save state: {e}") from e
    
    async def load_state(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Load previously saved execution state."""
        try:
            self.logger.info(
                "Loading execution state",
                execution_id=execution_id
            )
            
            # Try memory cache first
            if execution_id in self.checkpoint_storage:
                cached_state = self.checkpoint_storage[execution_id]
                self.logger.info(
                    "State loaded from memory cache",
                    execution_id=execution_id
                )
                return cached_state["state"]
            
            # Load from database
            async with get_db_session() as session:
                checkpoint_repo = ExecutionCheckpointRepository(session)
                
                checkpoint = await checkpoint_repo.get_latest(
                    workflow_execution_id=uuid.UUID(execution_id)
                )
                
                if checkpoint:
                    state = checkpoint.execution_state
                    
                    # Cache in memory
                    self.checkpoint_storage[execution_id] = {
                        "state": state,
                        "timestamp": checkpoint.created_at.isoformat(),
                        "version": state.get("version", "1.0.0")
                    }
                    
                    self.logger.info(
                        "State loaded from database",
                        execution_id=execution_id,
                        checkpoint_name=checkpoint.checkpoint_name
                    )
                    
                    return state
            
            self.logger.warning(
                "No saved state found",
                execution_id=execution_id
            )
            
            return None
            
        except Exception as e:
            self.logger.error(
                "Failed to load execution state",
                execution_id=execution_id,
                error=str(e)
            )
            raise StateManagementError(f"Failed to load state: {e}") from e
    
    async def delete_state(self, execution_id: str) -> bool:
        """Delete saved execution state."""
        try:
            self.logger.info(
                "Deleting execution state",
                execution_id=execution_id
            )
            
            # Remove from memory cache
            if execution_id in self.checkpoint_storage:
                del self.checkpoint_storage[execution_id]
            
            # Remove from active contexts
            if execution_id in self.active_contexts:
                del self.active_contexts[execution_id]
            
            # Cancel auto-checkpoint task
            if execution_id in self.checkpoint_tasks:
                self.checkpoint_tasks[execution_id].cancel()
                del self.checkpoint_tasks[execution_id]
            
            # Note: We don't delete from database to maintain audit trail
            # Database checkpoints are kept for historical purposes
            
            self.logger.info(
                "Execution state deleted successfully",
                execution_id=execution_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to delete execution state",
                execution_id=execution_id,
                error=str(e)
            )
            return False
    
    async def create_checkpoint(
        self, 
        execution_id: str, 
        checkpoint_name: str,
        checkpoint_type: str = "manual",
        description: Optional[str] = None
    ) -> bool:
        """Create a named checkpoint for the execution state."""
        try:
            self.logger.info(
                "Creating checkpoint",
                execution_id=execution_id,
                checkpoint_name=checkpoint_name,
                checkpoint_type=checkpoint_type
            )
            
            # Get current state
            context = self.active_contexts.get(execution_id)
            if not context:
                raise StateManagementError(f"No active context for execution {execution_id}")
            
            # Prepare checkpoint data
            checkpoint_data = {
                "execution_id": execution_id,
                "correlation_id": context.correlation_id,
                "current_state": context.current_state.value,
                "previous_state": context.previous_state.value if context.previous_state else None,
                "variables": context.variables,
                "metadata": context.metadata,
                "transition_history": [
                    {
                        "from_state": t.from_state.value,
                        "to_state": t.to_state.value,
                        "timestamp": t.timestamp.isoformat(),
                        "reason": t.reason,
                        "metadata": t.metadata,
                        "triggered_by": t.triggered_by
                    }
                    for t in context.transition_history
                ],
                "created_at": context.created_at.isoformat(),
                "updated_at": context.updated_at.isoformat(),
                "checkpoint_created_at": datetime.utcnow().isoformat(),
                "version": "1.0.0"
            }
            
            # Save to database
            async with get_db_session() as session:
                checkpoint_repo = ExecutionCheckpointRepository(session)
                
                await checkpoint_repo.create(
                    workflow_execution_id=uuid.UUID(execution_id),
                    checkpoint_name=checkpoint_name,
                    checkpoint_type=checkpoint_type,
                    execution_state=checkpoint_data,
                    description=description
                )
                
                await session.commit()
            
            self.logger.info(
                "Checkpoint created successfully",
                execution_id=execution_id,
                checkpoint_name=checkpoint_name
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                "Failed to create checkpoint",
                execution_id=execution_id,
                checkpoint_name=checkpoint_name,
                error=str(e)
            )
            raise StateManagementError(f"Failed to create checkpoint: {e}") from e
    
    async def restore_from_checkpoint(
        self, 
        execution_id: str, 
        checkpoint_name: Optional[str] = None
    ) -> Optional[ExecutionContext]:
        """Restore execution context from a checkpoint."""
        try:
            self.logger.info(
                "Restoring from checkpoint",
                execution_id=execution_id,
                checkpoint_name=checkpoint_name
            )
            
            async with get_db_session() as session:
                checkpoint_repo = ExecutionCheckpointRepository(session)
                
                if checkpoint_name:
                    checkpoint = await checkpoint_repo.get_by_name(
                        workflow_execution_id=uuid.UUID(execution_id),
                        checkpoint_name=checkpoint_name
                    )
                else:
                    checkpoint = await checkpoint_repo.get_latest(
                        workflow_execution_id=uuid.UUID(execution_id)
                    )
                
                if not checkpoint:
                    self.logger.warning(
                        "No checkpoint found for restoration",
                        execution_id=execution_id,
                        checkpoint_name=checkpoint_name
                    )
                    return None
                
                # Restore execution context
                checkpoint_data = checkpoint.execution_state
                
                context = ExecutionContext(
                    execution_id=checkpoint_data["execution_id"],
                    correlation_id=checkpoint_data["correlation_id"],
                    current_state=ExecutionState(checkpoint_data["current_state"]),
                    previous_state=ExecutionState(checkpoint_data["previous_state"]) if checkpoint_data.get("previous_state") else None,
                    created_at=datetime.fromisoformat(checkpoint_data["created_at"]),
                    updated_at=datetime.fromisoformat(checkpoint_data["updated_at"]),
                    variables=checkpoint_data.get("variables", {}),
                    metadata=checkpoint_data.get("metadata", {})
                )
                
                # Restore transition history
                for transition_data in checkpoint_data.get("transition_history", []):
                    from .state_machine import StateTransition
                    transition = StateTransition(
                        from_state=ExecutionState(transition_data["from_state"]),
                        to_state=ExecutionState(transition_data["to_state"]),
                        timestamp=datetime.fromisoformat(transition_data["timestamp"]),
                        reason=transition_data.get("reason"),
                        metadata=transition_data.get("metadata", {}),
                        triggered_by=transition_data.get("triggered_by")
                    )
                    context.transition_history.append(transition)
                
                # Add to active contexts
                self.active_contexts[execution_id] = context
                
                self.logger.info(
                    "Successfully restored from checkpoint",
                    execution_id=execution_id,
                    checkpoint_name=checkpoint.checkpoint_name,
                    restored_state=context.current_state.value
                )
                
                return context
                
        except Exception as e:
            self.logger.error(
                "Failed to restore from checkpoint",
                execution_id=execution_id,
                checkpoint_name=checkpoint_name,
                error=str(e)
            )
            raise StateManagementError(f"Failed to restore from checkpoint: {e}") from e
    
    async def start_execution_tracking(
        self, 
        execution_id: str, 
        correlation_id: str,
        initial_state: ExecutionState = ExecutionState.PENDING
    ) -> ExecutionContext:
        """Start tracking a new execution."""
        context = ExecutionContext(
            execution_id=execution_id,
            correlation_id=correlation_id,
            current_state=initial_state
        )
        
        self.active_contexts[execution_id] = context
        
        # Start auto-checkpoint task
        if self.checkpoint_interval > 0:
            task = asyncio.create_task(
                self._auto_checkpoint_task(execution_id)
            )
            self.checkpoint_tasks[execution_id] = task
        
        self.logger.info(
            "Started execution tracking",
            execution_id=execution_id,
            correlation_id=correlation_id,
            initial_state=initial_state.value
        )
        
        return context
    
    async def stop_execution_tracking(self, execution_id: str) -> None:
        """Stop tracking an execution."""
        # Cancel auto-checkpoint task
        if execution_id in self.checkpoint_tasks:
            self.checkpoint_tasks[execution_id].cancel()
            del self.checkpoint_tasks[execution_id]
        
        # Create final checkpoint
        if execution_id in self.active_contexts:
            await self.create_checkpoint(
                execution_id, 
                "final", 
                "automatic", 
                "Final checkpoint before stopping tracking"
            )
        
        self.logger.info(
            "Stopped execution tracking",
            execution_id=execution_id
        )
    
    async def _auto_checkpoint_task(self, execution_id: str) -> None:
        """Automatic checkpoint creation task."""
        try:
            while execution_id in self.active_contexts:
                await asyncio.sleep(self.checkpoint_interval)
                
                if execution_id in self.active_contexts:
                    await self.create_checkpoint(
                        execution_id,
                        f"auto_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                        "automatic",
                        f"Automatic checkpoint (interval: {self.checkpoint_interval}s)"
                    )
        
        except asyncio.CancelledError:
            self.logger.debug(
                "Auto-checkpoint task cancelled",
                execution_id=execution_id
            )
        except Exception as e:
            self.logger.error(
                "Auto-checkpoint task failed",
                execution_id=execution_id,
                error=str(e)
            )
    
    def _validate_state_data(self, state: Dict[str, Any]) -> None:
        """Validate state data structure."""
        required_fields = ["execution_id", "current_state"]
        
        for field in required_fields:
            if field not in state:
                raise ValidationError(f"Missing required field in state data: {field}")
        
        # Validate state value
        try:
            ExecutionState(state["current_state"])
        except ValueError as e:
            raise ValidationError(f"Invalid state value: {state['current_state']}") from e
    
    def get_active_executions(self) -> List[str]:
        """Get list of active execution IDs."""
        return list(self.active_contexts.keys())
    
    def get_execution_context(self, execution_id: str) -> Optional[ExecutionContext]:
        """Get execution context for an active execution."""
        return self.active_contexts.get(execution_id)
    
    async def transition_state(
        self,
        execution_id: str,
        to_state: ExecutionState,
        reason: Optional[str] = None,
        triggered_by: Optional[str] = None,
        **metadata
    ) -> bool:
        """Transition execution state using the state machine."""
        context = self.active_contexts.get(execution_id)
        if not context:
            raise StateManagementError(f"No active context for execution {execution_id}")
        
        return await self.state_machine.transition(
            context, to_state, reason, triggered_by, **metadata
        )
