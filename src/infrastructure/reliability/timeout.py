"""
Timeout handling for long-running operations.

This module provides comprehensive timeout management with cancellation,
progress tracking, and graceful degradation for long-running operations.
"""

import asyncio
import time
import signal
from typing import Any, Callable, Optional, Dict, Union, Awaitable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import functools
import threading

from core.exceptions import TimeoutError, OperationCancelledError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class TimeoutStrategy(str, Enum):
    """Timeout strategy enumeration."""
    HARD = "hard"          # Immediate cancellation
    SOFT = "soft"          # Graceful shutdown with warning
    PROGRESSIVE = "progressive"  # Multiple warning levels
    ADAPTIVE = "adaptive"  # Adjust timeout based on operation history


@dataclass
class TimeoutConfig:
    """Configuration for timeout behavior."""
    timeout_seconds: float
    strategy: TimeoutStrategy = TimeoutStrategy.HARD
    warning_threshold: float = 0.8  # Warn at 80% of timeout
    grace_period: float = 5.0  # Grace period for soft timeout
    max_extensions: int = 2  # Maximum timeout extensions
    extension_factor: float = 1.5  # Factor to extend timeout
    progress_callback: Optional[Callable[[float], None]] = None
    cancellation_callback: Optional[Callable[[], None]] = None


@dataclass
class TimeoutResult:
    """Result of a timeout operation."""
    success: bool
    result: Any = None
    exception: Optional[Exception] = None
    execution_time: float = 0.0
    timeout_occurred: bool = False
    warnings_issued: int = 0
    extensions_used: int = 0
    cancelled_by_user: bool = False


class OperationTimeoutManager:
    """Manager for operation timeouts with various strategies."""
    
    def __init__(self):
        """Initialize timeout manager."""
        self.logger = StructuredLogger("timeout_manager")
        self.active_operations: Dict[str, asyncio.Task] = {}
        self.operation_history: Dict[str, List[float]] = {}
        self.cancellation_tokens: Dict[str, asyncio.Event] = {}
    
    async def execute_with_timeout(
        self,
        operation: Callable,
        config: TimeoutConfig,
        operation_id: Optional[str] = None,
        *args,
        **kwargs
    ) -> TimeoutResult:
        """Execute an operation with timeout handling."""
        
        if not operation_id:
            operation_id = f"op_{int(time.time() * 1000)}"
        
        start_time = time.time()
        warnings_issued = 0
        extensions_used = 0
        timeout_seconds = config.timeout_seconds
        
        # Adjust timeout if using adaptive strategy
        if config.strategy == TimeoutStrategy.ADAPTIVE:
            timeout_seconds = self._calculate_adaptive_timeout(operation, config)
        
        self.logger.info(
            "Starting operation with timeout",
            operation_id=operation_id,
            timeout_seconds=timeout_seconds,
            strategy=config.strategy.value
        )
        
        # Create cancellation token
        cancellation_token = asyncio.Event()
        self.cancellation_tokens[operation_id] = cancellation_token
        
        try:
            # Create the operation task
            if asyncio.iscoroutinefunction(operation):
                operation_task = asyncio.create_task(operation(*args, **kwargs))
            else:
                operation_task = asyncio.create_task(
                    asyncio.to_thread(operation, *args, **kwargs)
                )
            
            self.active_operations[operation_id] = operation_task
            
            # Handle different timeout strategies
            if config.strategy == TimeoutStrategy.HARD:
                result = await self._handle_hard_timeout(
                    operation_task, timeout_seconds, operation_id
                )
            
            elif config.strategy == TimeoutStrategy.SOFT:
                result = await self._handle_soft_timeout(
                    operation_task, config, operation_id
                )
            
            elif config.strategy == TimeoutStrategy.PROGRESSIVE:
                result = await self._handle_progressive_timeout(
                    operation_task, config, operation_id
                )
            
            elif config.strategy == TimeoutStrategy.ADAPTIVE:
                result = await self._handle_adaptive_timeout(
                    operation_task, config, operation_id
                )
            
            else:
                result = await self._handle_hard_timeout(
                    operation_task, timeout_seconds, operation_id
                )
            
            execution_time = time.time() - start_time
            
            # Record operation history for adaptive timeout
            operation_name = getattr(operation, '__name__', str(operation))
            if operation_name not in self.operation_history:
                self.operation_history[operation_name] = []
            self.operation_history[operation_name].append(execution_time)
            
            # Keep only recent history
            if len(self.operation_history[operation_name]) > 10:
                self.operation_history[operation_name] = self.operation_history[operation_name][-10:]
            
            self.logger.info(
                "Operation completed",
                operation_id=operation_id,
                execution_time=execution_time,
                success=not isinstance(result, Exception)
            )
            
            if isinstance(result, Exception):
                return TimeoutResult(
                    success=False,
                    exception=result,
                    execution_time=execution_time,
                    timeout_occurred=isinstance(result, TimeoutError),
                    warnings_issued=warnings_issued,
                    extensions_used=extensions_used
                )
            else:
                return TimeoutResult(
                    success=True,
                    result=result,
                    execution_time=execution_time,
                    warnings_issued=warnings_issued,
                    extensions_used=extensions_used
                )
        
        finally:
            # Cleanup
            if operation_id in self.active_operations:
                del self.active_operations[operation_id]
            if operation_id in self.cancellation_tokens:
                del self.cancellation_tokens[operation_id]
    
    async def _handle_hard_timeout(
        self,
        operation_task: asyncio.Task,
        timeout_seconds: float,
        operation_id: str
    ) -> Any:
        """Handle hard timeout - immediate cancellation."""
        
        try:
            result = await asyncio.wait_for(operation_task, timeout=timeout_seconds)
            return result
        
        except asyncio.TimeoutError:
            operation_task.cancel()
            
            self.logger.warning(
                "Operation timed out (hard timeout)",
                operation_id=operation_id,
                timeout_seconds=timeout_seconds
            )
            
            raise TimeoutError(
                f"Operation {operation_id} timed out after {timeout_seconds}s",
                context={
                    "operation_id": operation_id,
                    "timeout_seconds": timeout_seconds,
                    "strategy": "hard"
                }
            )
    
    async def _handle_soft_timeout(
        self,
        operation_task: asyncio.Task,
        config: TimeoutConfig,
        operation_id: str
    ) -> Any:
        """Handle soft timeout - graceful shutdown with warning."""
        
        warning_time = config.timeout_seconds * config.warning_threshold
        
        try:
            # Wait for warning threshold
            result = await asyncio.wait_for(operation_task, timeout=warning_time)
            return result
        
        except asyncio.TimeoutError:
            # Issue warning
            self.logger.warning(
                "Operation approaching timeout",
                operation_id=operation_id,
                elapsed_time=warning_time,
                remaining_time=config.timeout_seconds - warning_time
            )
            
            if config.progress_callback:
                config.progress_callback(config.warning_threshold)
            
            # Wait for remaining time + grace period
            remaining_time = config.timeout_seconds - warning_time + config.grace_period
            
            try:
                result = await asyncio.wait_for(operation_task, timeout=remaining_time)
                return result
            
            except asyncio.TimeoutError:
                # Graceful cancellation
                if config.cancellation_callback:
                    config.cancellation_callback()
                
                operation_task.cancel()
                
                self.logger.error(
                    "Operation timed out (soft timeout)",
                    operation_id=operation_id,
                    total_timeout=config.timeout_seconds + config.grace_period
                )
                
                raise TimeoutError(
                    f"Operation {operation_id} timed out after {config.timeout_seconds + config.grace_period}s",
                    context={
                        "operation_id": operation_id,
                        "timeout_seconds": config.timeout_seconds,
                        "grace_period": config.grace_period,
                        "strategy": "soft"
                    }
                )
    
    async def _handle_progressive_timeout(
        self,
        operation_task: asyncio.Task,
        config: TimeoutConfig,
        operation_id: str
    ) -> Any:
        """Handle progressive timeout - multiple warning levels."""
        
        warning_intervals = [0.5, 0.7, 0.8, 0.9]  # Warning at 50%, 70%, 80%, 90%
        last_warning_time = 0.0
        warnings_issued = 0
        
        for warning_threshold in warning_intervals:
            warning_time = config.timeout_seconds * warning_threshold
            wait_time = warning_time - last_warning_time
            
            try:
                result = await asyncio.wait_for(operation_task, timeout=wait_time)
                return result
            
            except asyncio.TimeoutError:
                warnings_issued += 1
                elapsed_time = warning_time
                remaining_time = config.timeout_seconds - elapsed_time
                
                self.logger.warning(
                    f"Operation timeout warning {warnings_issued}",
                    operation_id=operation_id,
                    elapsed_time=elapsed_time,
                    remaining_time=remaining_time,
                    progress_percent=warning_threshold * 100
                )
                
                if config.progress_callback:
                    config.progress_callback(warning_threshold)
                
                last_warning_time = warning_time
        
        # Final timeout
        final_wait_time = config.timeout_seconds - last_warning_time
        
        try:
            result = await asyncio.wait_for(operation_task, timeout=final_wait_time)
            return result
        
        except asyncio.TimeoutError:
            operation_task.cancel()
            
            self.logger.error(
                "Operation timed out (progressive timeout)",
                operation_id=operation_id,
                timeout_seconds=config.timeout_seconds,
                warnings_issued=warnings_issued
            )
            
            raise TimeoutError(
                f"Operation {operation_id} timed out after {config.timeout_seconds}s",
                context={
                    "operation_id": operation_id,
                    "timeout_seconds": config.timeout_seconds,
                    "warnings_issued": warnings_issued,
                    "strategy": "progressive"
                }
            )
    
    async def _handle_adaptive_timeout(
        self,
        operation_task: asyncio.Task,
        config: TimeoutConfig,
        operation_id: str
    ) -> Any:
        """Handle adaptive timeout - adjust based on history."""
        
        adaptive_timeout = self._calculate_adaptive_timeout(
            operation_task.get_coro().cr_code.co_name if hasattr(operation_task.get_coro(), 'cr_code') else 'unknown',
            config
        )
        
        extensions_used = 0
        current_timeout = adaptive_timeout
        
        while extensions_used <= config.max_extensions:
            try:
                result = await asyncio.wait_for(operation_task, timeout=current_timeout)
                return result
            
            except asyncio.TimeoutError:
                if extensions_used < config.max_extensions:
                    extensions_used += 1
                    extension_time = current_timeout * (config.extension_factor - 1)
                    current_timeout *= config.extension_factor
                    
                    self.logger.warning(
                        "Operation timeout extended",
                        operation_id=operation_id,
                        extension_number=extensions_used,
                        extension_time=extension_time,
                        new_timeout=current_timeout
                    )
                else:
                    operation_task.cancel()
                    
                    self.logger.error(
                        "Operation timed out (adaptive timeout)",
                        operation_id=operation_id,
                        final_timeout=current_timeout,
                        extensions_used=extensions_used
                    )
                    
                    raise TimeoutError(
                        f"Operation {operation_id} timed out after {current_timeout}s",
                        context={
                            "operation_id": operation_id,
                            "timeout_seconds": current_timeout,
                            "extensions_used": extensions_used,
                            "strategy": "adaptive"
                        }
                    )
    
    def _calculate_adaptive_timeout(self, operation_name: str, config: TimeoutConfig) -> float:
        """Calculate adaptive timeout based on operation history."""
        
        if operation_name not in self.operation_history:
            return config.timeout_seconds
        
        history = self.operation_history[operation_name]
        if not history:
            return config.timeout_seconds
        
        # Calculate percentile-based timeout (95th percentile + buffer)
        sorted_times = sorted(history)
        percentile_95 = sorted_times[int(len(sorted_times) * 0.95)]
        
        # Add 50% buffer and ensure it's not less than base timeout
        adaptive_timeout = max(percentile_95 * 1.5, config.timeout_seconds)
        
        self.logger.debug(
            "Calculated adaptive timeout",
            operation_name=operation_name,
            history_count=len(history),
            percentile_95=percentile_95,
            adaptive_timeout=adaptive_timeout,
            base_timeout=config.timeout_seconds
        )
        
        return adaptive_timeout
    
    async def cancel_operation(self, operation_id: str) -> bool:
        """Cancel a running operation."""
        
        if operation_id in self.active_operations:
            task = self.active_operations[operation_id]
            task.cancel()
            
            if operation_id in self.cancellation_tokens:
                self.cancellation_tokens[operation_id].set()
            
            self.logger.info(
                "Operation cancelled",
                operation_id=operation_id
            )
            
            return True
        
        return False
    
    def get_active_operations(self) -> Dict[str, Dict[str, Any]]:
        """Get information about active operations."""
        
        result = {}
        for operation_id, task in self.active_operations.items():
            result[operation_id] = {
                "operation_id": operation_id,
                "done": task.done(),
                "cancelled": task.cancelled(),
                "exception": str(task.exception()) if task.done() and task.exception() else None
            }
        
        return result


def timeout(
    timeout_seconds: float,
    strategy: TimeoutStrategy = TimeoutStrategy.HARD,
    warning_threshold: float = 0.8,
    grace_period: float = 5.0,
    max_extensions: int = 2,
    extension_factor: float = 1.5,
    progress_callback: Optional[Callable[[float], None]] = None,
    cancellation_callback: Optional[Callable[[], None]] = None
):
    """Decorator for adding timeout functionality to functions."""
    
    def decorator(func: Callable) -> Callable:
        config = TimeoutConfig(
            timeout_seconds=timeout_seconds,
            strategy=strategy,
            warning_threshold=warning_threshold,
            grace_period=grace_period,
            max_extensions=max_extensions,
            extension_factor=extension_factor,
            progress_callback=progress_callback,
            cancellation_callback=cancellation_callback
        )
        
        timeout_manager = OperationTimeoutManager()
        
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            result = await timeout_manager.execute_with_timeout(func, config, None, *args, **kwargs)
            
            if result.success:
                return result.result
            else:
                raise result.exception
        
        return wrapper
    
    return decorator


# Global timeout manager instance
timeout_manager = OperationTimeoutManager()
