"""
Execution state machine for workflow and task management.

This module provides a comprehensive state machine implementation for managing
the lifecycle of workflow and task executions with proper state transitions
and validation.
"""

from enum import Enum
from typing import Dict, Set, Optional, Any, Callable, List
from datetime import datetime
import uuid
import asyncio
from dataclasses import dataclass, field

from core.interfaces import TaskStatus, WorkflowStatus, IStateManager
from core.exceptions import StateManagementError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class ExecutionState(str, Enum):
    """Execution state enumeration."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    RESUMING = "resuming"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILING = "failing"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


@dataclass
class StateTransition:
    """Represents a state transition with metadata."""
    from_state: ExecutionState
    to_state: ExecutionState
    timestamp: datetime
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    triggered_by: Optional[str] = None


@dataclass
class ExecutionContext:
    """Execution context containing state and metadata."""
    execution_id: str
    correlation_id: str
    current_state: ExecutionState
    previous_state: Optional[ExecutionState] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    variables: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    transition_history: List[StateTransition] = field(default_factory=list)
    
    def update_state(
        self, 
        new_state: ExecutionState, 
        reason: Optional[str] = None,
        triggered_by: Optional[str] = None,
        **metadata
    ) -> None:
        """Update the execution state with transition tracking."""
        transition = StateTransition(
            from_state=self.current_state,
            to_state=new_state,
            timestamp=datetime.utcnow(),
            reason=reason,
            metadata=metadata,
            triggered_by=triggered_by
        )
        
        self.transition_history.append(transition)
        self.previous_state = self.current_state
        self.current_state = new_state
        self.updated_at = datetime.utcnow()


class StateMachine:
    """State machine for managing execution state transitions."""
    
    def __init__(self):
        """Initialize state machine with valid transitions."""
        self.logger = StructuredLogger("state_machine")
        
        # Define valid state transitions
        self.valid_transitions: Dict[ExecutionState, Set[ExecutionState]] = {
            ExecutionState.PENDING: {
                ExecutionState.INITIALIZING,
                ExecutionState.CANCELLED,
                ExecutionState.FAILED
            },
            ExecutionState.INITIALIZING: {
                ExecutionState.RUNNING,
                ExecutionState.FAILED,
                ExecutionState.CANCELLED
            },
            ExecutionState.RUNNING: {
                ExecutionState.PAUSED,
                ExecutionState.COMPLETING,
                ExecutionState.FAILING,
                ExecutionState.CANCELLING,
                ExecutionState.TIMEOUT
            },
            ExecutionState.PAUSED: {
                ExecutionState.RESUMING,
                ExecutionState.CANCELLING,
                ExecutionState.FAILED
            },
            ExecutionState.RESUMING: {
                ExecutionState.RUNNING,
                ExecutionState.FAILED,
                ExecutionState.CANCELLING
            },
            ExecutionState.COMPLETING: {
                ExecutionState.COMPLETED,
                ExecutionState.FAILED
            },
            ExecutionState.FAILING: {
                ExecutionState.FAILED
            },
            ExecutionState.CANCELLING: {
                ExecutionState.CANCELLED
            },
            # Terminal states have no outgoing transitions
            ExecutionState.COMPLETED: set(),
            ExecutionState.FAILED: set(),
            ExecutionState.CANCELLED: set(),
            ExecutionState.TIMEOUT: set()
        }
        
        # State transition hooks
        self.pre_transition_hooks: Dict[ExecutionState, List[Callable]] = {}
        self.post_transition_hooks: Dict[ExecutionState, List[Callable]] = {}
        
        # State entry/exit hooks
        self.state_entry_hooks: Dict[ExecutionState, List[Callable]] = {}
        self.state_exit_hooks: Dict[ExecutionState, List[Callable]] = {}
    
    def is_valid_transition(
        self, 
        from_state: ExecutionState, 
        to_state: ExecutionState
    ) -> bool:
        """Check if a state transition is valid."""
        return to_state in self.valid_transitions.get(from_state, set())
    
    def get_valid_transitions(self, from_state: ExecutionState) -> Set[ExecutionState]:
        """Get all valid transitions from a given state."""
        return self.valid_transitions.get(from_state, set()).copy()
    
    def is_terminal_state(self, state: ExecutionState) -> bool:
        """Check if a state is terminal (no outgoing transitions)."""
        return len(self.valid_transitions.get(state, set())) == 0
    
    async def transition(
        self,
        context: ExecutionContext,
        to_state: ExecutionState,
        reason: Optional[str] = None,
        triggered_by: Optional[str] = None,
        **metadata
    ) -> bool:
        """Perform a state transition with validation and hooks."""
        from_state = context.current_state
        
        # Validate transition
        if not self.is_valid_transition(from_state, to_state):
            raise StateManagementError(
                f"Invalid state transition from {from_state} to {to_state}",
                context={
                    "execution_id": context.execution_id,
                    "from_state": from_state.value,
                    "to_state": to_state.value,
                    "valid_transitions": [s.value for s in self.get_valid_transitions(from_state)]
                }
            )
        
        self.logger.info(
            f"State transition: {from_state} -> {to_state}",
            correlation_id=context.correlation_id,
            execution_id=context.execution_id,
            from_state=from_state.value,
            to_state=to_state.value,
            reason=reason,
            triggered_by=triggered_by
        )
        
        try:
            # Execute pre-transition hooks
            await self._execute_hooks(
                self.pre_transition_hooks.get(to_state, []),
                context, from_state, to_state
            )
            
            # Execute state exit hooks
            await self._execute_hooks(
                self.state_exit_hooks.get(from_state, []),
                context, from_state, to_state
            )
            
            # Update the context state
            context.update_state(to_state, reason, triggered_by, **metadata)
            
            # Execute state entry hooks
            await self._execute_hooks(
                self.state_entry_hooks.get(to_state, []),
                context, from_state, to_state
            )
            
            # Execute post-transition hooks
            await self._execute_hooks(
                self.post_transition_hooks.get(to_state, []),
                context, from_state, to_state
            )
            
            self.logger.info(
                f"State transition completed: {from_state} -> {to_state}",
                correlation_id=context.correlation_id,
                execution_id=context.execution_id
            )
            
            return True
            
        except Exception as e:
            self.logger.error(
                f"State transition failed: {from_state} -> {to_state}",
                correlation_id=context.correlation_id,
                execution_id=context.execution_id,
                error=str(e)
            )
            raise StateManagementError(
                f"State transition failed: {e}",
                context={
                    "execution_id": context.execution_id,
                    "from_state": from_state.value,
                    "to_state": to_state.value,
                    "error": str(e)
                }
            ) from e
    
    async def _execute_hooks(
        self,
        hooks: List[Callable],
        context: ExecutionContext,
        from_state: ExecutionState,
        to_state: ExecutionState
    ) -> None:
        """Execute a list of hooks."""
        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(context, from_state, to_state)
                else:
                    hook(context, from_state, to_state)
            except Exception as e:
                self.logger.error(
                    f"Hook execution failed: {hook.__name__}",
                    correlation_id=context.correlation_id,
                    execution_id=context.execution_id,
                    error=str(e)
                )
                raise
    
    def add_pre_transition_hook(
        self, 
        state: ExecutionState, 
        hook: Callable
    ) -> None:
        """Add a pre-transition hook for a specific state."""
        if state not in self.pre_transition_hooks:
            self.pre_transition_hooks[state] = []
        self.pre_transition_hooks[state].append(hook)
    
    def add_post_transition_hook(
        self, 
        state: ExecutionState, 
        hook: Callable
    ) -> None:
        """Add a post-transition hook for a specific state."""
        if state not in self.post_transition_hooks:
            self.post_transition_hooks[state] = []
        self.post_transition_hooks[state].append(hook)
    
    def add_state_entry_hook(
        self, 
        state: ExecutionState, 
        hook: Callable
    ) -> None:
        """Add a state entry hook."""
        if state not in self.state_entry_hooks:
            self.state_entry_hooks[state] = []
        self.state_entry_hooks[state].append(hook)
    
    def add_state_exit_hook(
        self, 
        state: ExecutionState, 
        hook: Callable
    ) -> None:
        """Add a state exit hook."""
        if state not in self.state_exit_hooks:
            self.state_exit_hooks[state] = []
        self.state_exit_hooks[state].append(hook)
    
    def get_transition_path(
        self, 
        from_state: ExecutionState, 
        to_state: ExecutionState
    ) -> Optional[List[ExecutionState]]:
        """Find a valid transition path between two states using BFS."""
        if from_state == to_state:
            return [from_state]
        
        queue = [(from_state, [from_state])]
        visited = {from_state}
        
        while queue:
            current_state, path = queue.pop(0)
            
            for next_state in self.valid_transitions.get(current_state, set()):
                if next_state == to_state:
                    return path + [next_state]
                
                if next_state not in visited:
                    visited.add(next_state)
                    queue.append((next_state, path + [next_state]))
        
        return None  # No valid path found
    
    def can_reach_state(
        self, 
        from_state: ExecutionState, 
        to_state: ExecutionState
    ) -> bool:
        """Check if a target state is reachable from the current state."""
        return self.get_transition_path(from_state, to_state) is not None
    
    def get_state_info(self, state: ExecutionState) -> Dict[str, Any]:
        """Get information about a specific state."""
        return {
            "state": state.value,
            "is_terminal": self.is_terminal_state(state),
            "valid_transitions": [s.value for s in self.get_valid_transitions(state)],
            "has_entry_hooks": len(self.state_entry_hooks.get(state, [])) > 0,
            "has_exit_hooks": len(self.state_exit_hooks.get(state, [])) > 0,
            "has_pre_transition_hooks": len(self.pre_transition_hooks.get(state, [])) > 0,
            "has_post_transition_hooks": len(self.post_transition_hooks.get(state, [])) > 0
        }
    
    def get_all_states_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all states."""
        return {
            state.value: self.get_state_info(state)
            for state in ExecutionState
        }
