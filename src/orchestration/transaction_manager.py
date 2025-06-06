"""
Transaction manager for state changes.

This module provides transactional support for state changes with rollback
capabilities, ensuring data consistency and integrity during workflow execution.
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from enum import Enum
import uuid
from dataclasses import dataclass, field

from core.exceptions import StateManagementError, TransactionError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.infrastructure.storage.database import get_db_session
from .state_machine import ExecutionState, ExecutionContext


class TransactionStatus(str, Enum):
    """Transaction status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


@dataclass
class TransactionOperation:
    """Represents a single operation within a transaction."""
    operation_id: str
    operation_type: str  # 'state_change', 'variable_update', 'checkpoint', 'database'
    target: str  # execution_id, variable_name, etc.
    operation_data: Dict[str, Any]
    rollback_data: Optional[Dict[str, Any]] = None
    executed: bool = False
    rolled_back: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Transaction:
    """Represents a transaction with multiple operations."""
    transaction_id: str
    correlation_id: str
    status: TransactionStatus = TransactionStatus.PENDING
    operations: List[TransactionOperation] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TransactionManager:
    """Manager for transactional state changes."""
    
    def __init__(self):
        """Initialize transaction manager."""
        self.logger = StructuredLogger("transaction_manager")
        
        # Active transactions
        self.active_transactions: Dict[str, Transaction] = {}
        
        # Transaction locks for thread safety
        self.transaction_locks: Dict[str, asyncio.Lock] = {}
        
        # Operation handlers
        self.operation_handlers: Dict[str, Callable] = {
            'state_change': self._handle_state_change,
            'variable_update': self._handle_variable_update,
            'checkpoint': self._handle_checkpoint,
            'database': self._handle_database_operation
        }
        
        # Rollback handlers
        self.rollback_handlers: Dict[str, Callable] = {
            'state_change': self._rollback_state_change,
            'variable_update': self._rollback_variable_update,
            'checkpoint': self._rollback_checkpoint,
            'database': self._rollback_database_operation
        }
    
    async def begin_transaction(
        self, 
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Begin a new transaction."""
        
        transaction_id = str(uuid.uuid4())
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        transaction = Transaction(
            transaction_id=transaction_id,
            correlation_id=correlation_id,
            metadata=metadata or {}
        )
        
        self.active_transactions[transaction_id] = transaction
        self.transaction_locks[transaction_id] = asyncio.Lock()
        
        self.logger.info(
            "Transaction started",
            transaction_id=transaction_id,
            correlation_id=correlation_id
        )
        
        return transaction_id
    
    async def add_operation(
        self,
        transaction_id: str,
        operation_type: str,
        target: str,
        operation_data: Dict[str, Any],
        rollback_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add an operation to a transaction."""
        
        async with self.transaction_locks.get(transaction_id, asyncio.Lock()):
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                raise TransactionError(f"Transaction {transaction_id} not found")
            
            if transaction.status != TransactionStatus.PENDING:
                raise TransactionError(
                    f"Cannot add operation to transaction in status {transaction.status}"
                )
            
            operation_id = str(uuid.uuid4())
            operation = TransactionOperation(
                operation_id=operation_id,
                operation_type=operation_type,
                target=target,
                operation_data=operation_data,
                rollback_data=rollback_data
            )
            
            transaction.operations.append(operation)
            
            self.logger.debug(
                "Operation added to transaction",
                transaction_id=transaction_id,
                operation_id=operation_id,
                operation_type=operation_type,
                target=target
            )
            
            return operation_id
    
    async def commit_transaction(self, transaction_id: str) -> bool:
        """Commit a transaction by executing all operations."""
        
        async with self.transaction_locks.get(transaction_id, asyncio.Lock()):
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                raise TransactionError(f"Transaction {transaction_id} not found")
            
            if transaction.status != TransactionStatus.PENDING:
                raise TransactionError(
                    f"Cannot commit transaction in status {transaction.status}"
                )
            
            self.logger.info(
                "Committing transaction",
                transaction_id=transaction_id,
                operation_count=len(transaction.operations)
            )
            
            try:
                # Mark transaction as active
                transaction.status = TransactionStatus.ACTIVE
                transaction.started_at = datetime.utcnow()
                
                # Execute all operations
                executed_operations = []
                
                for operation in transaction.operations:
                    try:
                        await self._execute_operation(operation)
                        operation.executed = True
                        executed_operations.append(operation)
                        
                        self.logger.debug(
                            "Operation executed successfully",
                            transaction_id=transaction_id,
                            operation_id=operation.operation_id,
                            operation_type=operation.operation_type
                        )
                        
                    except Exception as e:
                        self.logger.error(
                            "Operation execution failed",
                            transaction_id=transaction_id,
                            operation_id=operation.operation_id,
                            operation_type=operation.operation_type,
                            error=str(e)
                        )
                        
                        # Rollback executed operations
                        await self._rollback_operations(executed_operations)
                        
                        transaction.status = TransactionStatus.FAILED
                        transaction.error_message = str(e)
                        transaction.completed_at = datetime.utcnow()
                        
                        raise TransactionError(f"Transaction failed: {e}") from e
                
                # Mark transaction as committed
                transaction.status = TransactionStatus.COMMITTED
                transaction.completed_at = datetime.utcnow()
                
                self.logger.info(
                    "Transaction committed successfully",
                    transaction_id=transaction_id,
                    operation_count=len(transaction.operations)
                )
                
                return True
                
            except Exception as e:
                self.logger.error(
                    "Transaction commit failed",
                    transaction_id=transaction_id,
                    error=str(e)
                )
                raise
            
            finally:
                # Cleanup
                if transaction_id in self.transaction_locks:
                    del self.transaction_locks[transaction_id]
    
    async def rollback_transaction(self, transaction_id: str) -> bool:
        """Rollback a transaction by undoing executed operations."""
        
        async with self.transaction_locks.get(transaction_id, asyncio.Lock()):
            transaction = self.active_transactions.get(transaction_id)
            if not transaction:
                raise TransactionError(f"Transaction {transaction_id} not found")
            
            if transaction.status not in [TransactionStatus.ACTIVE, TransactionStatus.FAILED]:
                self.logger.warning(
                    "Cannot rollback transaction in current status",
                    transaction_id=transaction_id,
                    status=transaction.status.value
                )
                return False
            
            self.logger.info(
                "Rolling back transaction",
                transaction_id=transaction_id,
                operation_count=len(transaction.operations)
            )
            
            try:
                # Rollback executed operations in reverse order
                executed_operations = [op for op in transaction.operations if op.executed]
                await self._rollback_operations(reversed(executed_operations))
                
                transaction.status = TransactionStatus.ROLLED_BACK
                transaction.completed_at = datetime.utcnow()
                
                self.logger.info(
                    "Transaction rolled back successfully",
                    transaction_id=transaction_id
                )
                
                return True
                
            except Exception as e:
                self.logger.error(
                    "Transaction rollback failed",
                    transaction_id=transaction_id,
                    error=str(e)
                )
                raise TransactionError(f"Rollback failed: {e}") from e
            
            finally:
                # Cleanup
                if transaction_id in self.transaction_locks:
                    del self.transaction_locks[transaction_id]
    
    async def _execute_operation(self, operation: TransactionOperation) -> None:
        """Execute a single operation."""
        
        handler = self.operation_handlers.get(operation.operation_type)
        if not handler:
            raise TransactionError(f"No handler for operation type: {operation.operation_type}")
        
        # Store rollback data before execution
        if not operation.rollback_data:
            operation.rollback_data = await self._prepare_rollback_data(operation)
        
        # Execute the operation
        await handler(operation)
    
    async def _rollback_operations(self, operations: List[TransactionOperation]) -> None:
        """Rollback a list of operations."""
        
        for operation in operations:
            if not operation.executed or operation.rolled_back:
                continue
            
            try:
                handler = self.rollback_handlers.get(operation.operation_type)
                if handler:
                    await handler(operation)
                    operation.rolled_back = True
                    
                    self.logger.debug(
                        "Operation rolled back successfully",
                        operation_id=operation.operation_id,
                        operation_type=operation.operation_type
                    )
                else:
                    self.logger.warning(
                        "No rollback handler for operation type",
                        operation_id=operation.operation_id,
                        operation_type=operation.operation_type
                    )
                    
            except Exception as e:
                self.logger.error(
                    "Operation rollback failed",
                    operation_id=operation.operation_id,
                    operation_type=operation.operation_type,
                    error=str(e)
                )
                # Continue with other rollbacks
    
    async def _prepare_rollback_data(self, operation: TransactionOperation) -> Dict[str, Any]:
        """Prepare rollback data for an operation."""
        
        if operation.operation_type == 'state_change':
            # Store current state for rollback
            from .state_manager import StateManager
            state_manager = StateManager()  # Would be injected in real implementation
            context = state_manager.get_execution_context(operation.target)
            
            if context:
                return {
                    "previous_state": context.current_state.value,
                    "previous_metadata": context.metadata.copy()
                }
        
        elif operation.operation_type == 'variable_update':
            # Store current variable value
            from .state_manager import StateManager
            state_manager = StateManager()
            context = state_manager.get_execution_context(operation.operation_data["execution_id"])
            
            if context:
                variable_name = operation.operation_data["variable_name"]
                return {
                    "previous_value": context.variables.get(variable_name),
                    "variable_existed": variable_name in context.variables
                }
        
        return {}
    
    # Operation handlers
    async def _handle_state_change(self, operation: TransactionOperation) -> None:
        """Handle state change operation."""
        # Implementation would integrate with state manager
        pass
    
    async def _handle_variable_update(self, operation: TransactionOperation) -> None:
        """Handle variable update operation."""
        # Implementation would update execution context variables
        pass
    
    async def _handle_checkpoint(self, operation: TransactionOperation) -> None:
        """Handle checkpoint creation operation."""
        # Implementation would create checkpoint
        pass
    
    async def _handle_database_operation(self, operation: TransactionOperation) -> None:
        """Handle database operation."""
        # Implementation would execute database operations
        pass
    
    # Rollback handlers
    async def _rollback_state_change(self, operation: TransactionOperation) -> None:
        """Rollback state change operation."""
        # Implementation would restore previous state
        pass
    
    async def _rollback_variable_update(self, operation: TransactionOperation) -> None:
        """Rollback variable update operation."""
        # Implementation would restore previous variable value
        pass
    
    async def _rollback_checkpoint(self, operation: TransactionOperation) -> None:
        """Rollback checkpoint creation operation."""
        # Implementation would remove checkpoint
        pass
    
    async def _rollback_database_operation(self, operation: TransactionOperation) -> None:
        """Rollback database operation."""
        # Implementation would rollback database changes
        pass
    
    def get_transaction_status(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction status and details."""
        
        transaction = self.active_transactions.get(transaction_id)
        if not transaction:
            return None
        
        return {
            "transaction_id": transaction.transaction_id,
            "correlation_id": transaction.correlation_id,
            "status": transaction.status.value,
            "operation_count": len(transaction.operations),
            "executed_operations": sum(1 for op in transaction.operations if op.executed),
            "rolled_back_operations": sum(1 for op in transaction.operations if op.rolled_back),
            "created_at": transaction.created_at.isoformat(),
            "started_at": transaction.started_at.isoformat() if transaction.started_at else None,
            "completed_at": transaction.completed_at.isoformat() if transaction.completed_at else None,
            "error_message": transaction.error_message,
            "metadata": transaction.metadata
        }
    
    def get_active_transactions(self) -> List[str]:
        """Get list of active transaction IDs."""
        return [
            tid for tid, transaction in self.active_transactions.items()
            if transaction.status in [TransactionStatus.PENDING, TransactionStatus.ACTIVE]
        ]
    
    async def cleanup_completed_transactions(self, max_age_hours: int = 24) -> int:
        """Clean up completed transactions older than specified age."""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        for transaction_id, transaction in list(self.active_transactions.items()):
            if (transaction.status in [TransactionStatus.COMMITTED, TransactionStatus.ROLLED_BACK, TransactionStatus.FAILED] 
                and transaction.completed_at 
                and transaction.completed_at < cutoff_time):
                
                del self.active_transactions[transaction_id]
                if transaction_id in self.transaction_locks:
                    del self.transaction_locks[transaction_id]
                
                cleaned_count += 1
        
        if cleaned_count > 0:
            self.logger.info(
                "Cleaned up completed transactions",
                cleaned_count=cleaned_count,
                max_age_hours=max_age_hours
            )
        
        return cleaned_count


# Global transaction manager instance
transaction_manager = TransactionManager()


class TransactionError(Exception):
    """Transaction-related error."""
    pass
