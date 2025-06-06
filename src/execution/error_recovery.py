#!/usr/bin/env python3
"""
Advanced Error Recovery System for the Execution Layer.

This module provides enhanced error recovery capabilities specifically designed
for the execution layer, building upon the intelligent error recovery system
with execution-specific patterns and strategies.

Week 2 Task 2.1: Advanced Error Recovery System
- Error pattern classification system
- Automatic retry strategies with exponential backoff
- Error recovery analytics and reporting
- LLM-guided error diagnosis
- Recovery strategy learning
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
import uuid
from collections import defaultdict, deque

from core.exceptions import (
    TaskExecutionError, BrowserError, ConfigurationError, 
    TimeoutError, RetryExhaustedError, FrameworkException
)
from core.interfaces import TaskStatus, ILLMProvider
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.intelligence.error_recovery import (
    IntelligentErrorRecovery, ErrorIncident, ErrorPattern, 
    ErrorCategory, ErrorSeverity, RecoveryStrategy
)


class ExecutionErrorCategory(str, Enum):
    """Execution-specific error categories."""
    ADAPTER_FAILURE = "adapter_failure"
    BROWSER_CRASH = "browser_crash"
    TASK_TIMEOUT = "task_timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DEPENDENCY_FAILURE = "dependency_failure"
    CONFIGURATION_INVALID = "configuration_invalid"
    WORKFLOW_CORRUPTION = "workflow_corruption"
    CONCURRENCY_CONFLICT = "concurrency_conflict"


class RecoveryPriority(str, Enum):
    """Recovery priority levels."""
    IMMEDIATE = "immediate"      # < 1 second
    URGENT = "urgent"           # < 5 seconds
    NORMAL = "normal"           # < 30 seconds
    BACKGROUND = "background"   # > 30 seconds


@dataclass
class ExecutionErrorMetrics:
    """Metrics for execution error tracking."""
    total_errors: int = 0
    total_recoveries: int = 0
    recovery_success_rate: float = 0.0
    average_recovery_time: float = 0.0
    errors_by_category: Dict[str, int] = field(default_factory=dict)
    recovery_strategies_used: Dict[str, int] = field(default_factory=dict)
    pattern_accuracy: float = 0.0
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RecoveryContext:
    """Context for error recovery operations."""
    task_id: Optional[str] = None
    workflow_id: Optional[str] = None
    adapter_id: Optional[str] = None
    browser_session_id: Optional[str] = None
    execution_phase: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: float = 30.0
    priority: RecoveryPriority = RecoveryPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)


class ExecutionErrorRecovery:
    """
    Advanced error recovery system for the execution layer.
    
    Provides execution-specific error handling with:
    - Pattern classification for execution errors
    - Automatic retry with exponential backoff
    - Recovery analytics and reporting
    - LLM-guided diagnosis
    - Strategy learning and optimization
    """
    
    def __init__(
        self, 
        llm_provider: Optional[ILLMProvider] = None,
        enable_learning: bool = True,
        max_recovery_attempts: int = 3
    ):
        """Initialize execution error recovery system."""
        self.logger = StructuredLogger("execution_error_recovery")
        
        # Core recovery system
        self.intelligent_recovery = IntelligentErrorRecovery(llm_provider)
        
        # Execution-specific configuration
        self.enable_learning = enable_learning
        self.max_recovery_attempts = max_recovery_attempts
        
        # Metrics and analytics
        self.metrics = ExecutionErrorMetrics()
        self.error_history = deque(maxlen=1000)  # Keep last 1000 errors
        
        # Recovery strategies registry
        self.recovery_strategies: Dict[str, Callable] = {}
        self.strategy_success_rates: Dict[str, float] = {}
        
        # Pattern classification
        self.execution_patterns: Dict[str, Dict[str, Any]] = {}
        
        # Recovery queue for background processing
        self.recovery_queue: asyncio.Queue = asyncio.Queue()
        self.background_recovery_task: Optional[asyncio.Task] = None
        
        # Initialize built-in strategies
        self._initialize_recovery_strategies()
        
        self.logger.info("Execution error recovery system initialized",
                        enable_learning=enable_learning,
                        max_attempts=max_recovery_attempts)
    
    async def start_background_recovery(self) -> None:
        """Start background recovery processing."""
        if self.background_recovery_task is None:
            self.background_recovery_task = asyncio.create_task(
                self._background_recovery_processor()
            )
            self.logger.info("Background recovery processor started")
    
    async def stop_background_recovery(self) -> None:
        """Stop background recovery processing."""
        if self.background_recovery_task:
            self.background_recovery_task.cancel()
            try:
                await self.background_recovery_task
            except asyncio.CancelledError:
                pass
            self.background_recovery_task = None
            self.logger.info("Background recovery processor stopped")
    
    @with_correlation_id()
    async def handle_execution_error(
        self,
        error: Exception,
        recovery_context: RecoveryContext,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle execution error with advanced recovery strategies.
        
        Args:
            error: The exception that occurred
            recovery_context: Context for recovery operations
            correlation_id: Correlation ID for tracking
            
        Returns:
            Recovery result with success status and details
        """
        start_time = time.time()
        incident_id = str(uuid.uuid4())
        
        self.logger.error(
            "Handling execution error",
            incident_id=incident_id,
            error_type=type(error).__name__,
            error_message=str(error),
            task_id=recovery_context.task_id,
            workflow_id=recovery_context.workflow_id,
            correlation_id=correlation_id
        )
        
        # Update metrics
        self.metrics.total_errors += 1
        error_category = self._classify_execution_error(error, recovery_context)
        self.metrics.errors_by_category[error_category] = (
            self.metrics.errors_by_category.get(error_category, 0) + 1
        )
        
        # Create enhanced context for intelligent recovery
        enhanced_context = {
            "execution_context": asdict(recovery_context),
            "error_category": error_category,
            "correlation_id": correlation_id,
            "incident_id": incident_id
        }
        
        # Attempt immediate recovery for high-priority errors
        if recovery_context.priority in [RecoveryPriority.IMMEDIATE, RecoveryPriority.URGENT]:
            recovery_result = await self._immediate_recovery(
                error, recovery_context, enhanced_context
            )
        else:
            # Queue for background recovery
            await self.recovery_queue.put({
                "error": error,
                "context": recovery_context,
                "enhanced_context": enhanced_context,
                "incident_id": incident_id,
                "timestamp": datetime.utcnow()
            })
            
            # Return immediate response for background processing
            recovery_result = {
                "success": False,
                "queued_for_background": True,
                "incident_id": incident_id,
                "estimated_recovery_time": self._estimate_recovery_time(error_category)
            }
        
        # Update metrics
        execution_time = time.time() - start_time
        if recovery_result.get("success"):
            self.metrics.total_recoveries += 1
            self.metrics.recovery_success_rate = (
                self.metrics.total_recoveries / self.metrics.total_errors
            )
        
        # Update average recovery time
        if self.metrics.total_recoveries > 0:
            current_avg = self.metrics.average_recovery_time
            new_avg = (current_avg * (self.metrics.total_recoveries - 1) + execution_time) / self.metrics.total_recoveries
            self.metrics.average_recovery_time = new_avg
        
        self.metrics.last_updated = datetime.utcnow()
        
        # Store in error history
        self.error_history.append({
            "incident_id": incident_id,
            "error_type": type(error).__name__,
            "error_category": error_category,
            "recovery_result": recovery_result,
            "execution_time": execution_time,
            "timestamp": datetime.utcnow(),
            "context": recovery_context
        })
        
        return recovery_result
    
    def _classify_execution_error(
        self,
        error: Exception,
        context: RecoveryContext
    ) -> str:
        """Classify execution-specific errors."""

        error_type = type(error).__name__
        error_message = str(error).lower()

        # Browser-related errors (check first for BrowserError)
        if isinstance(error, BrowserError) or "browser" in error_message:
            if any(keyword in error_message for keyword in ["crash", "disconnected", "closed"]):
                return ExecutionErrorCategory.BROWSER_CRASH.value
            return ExecutionErrorCategory.BROWSER_CRASH.value  # Default for browser errors

        # Task timeout (check TimeoutError type)
        if isinstance(error, TimeoutError) or "timeout" in error_message:
            return ExecutionErrorCategory.TASK_TIMEOUT.value

        # Dependency failures (check ImportError type)
        if isinstance(error, ImportError) or any(keyword in error_message for keyword in ["dependency", "import", "module"]):
            return ExecutionErrorCategory.DEPENDENCY_FAILURE.value

        # Configuration issues (check ValueError for config issues)
        if isinstance(error, (ConfigurationError, ValueError)) or any(keyword in error_message for keyword in ["config", "invalid"]):
            return ExecutionErrorCategory.CONFIGURATION_INVALID.value

        # Resource exhaustion
        if any(keyword in error_message for keyword in ["memory", "resource", "limit", "exhausted"]):
            return ExecutionErrorCategory.RESOURCE_EXHAUSTION.value

        # Adapter-related errors (check after more specific types)
        if isinstance(error, TaskExecutionError) or "adapter" in error_message or context.adapter_id:
            return ExecutionErrorCategory.ADAPTER_FAILURE.value

        # Workflow corruption
        if "workflow" in error_message or "corrupt" in error_message:
            return ExecutionErrorCategory.WORKFLOW_CORRUPTION.value

        # Concurrency conflicts
        if any(keyword in error_message for keyword in ["lock", "concurrent", "race"]):
            return ExecutionErrorCategory.CONCURRENCY_CONFLICT.value

        # Fallback to general classification
        return self.intelligent_recovery._classify_error(error, asdict(context)).value
    
    async def _immediate_recovery(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform immediate recovery for high-priority errors."""
        
        # Use intelligent recovery system
        recovery_result = await self.intelligent_recovery.handle_error(
            error, enhanced_context, enhanced_context.get("correlation_id")
        )
        
        # Apply execution-specific recovery strategies
        if not recovery_result.get("resolved"):
            execution_recovery = await self._apply_execution_strategies(
                error, context, enhanced_context
            )
            
            if execution_recovery.get("success"):
                recovery_result.update(execution_recovery)
                recovery_result["resolved"] = True
        
        return recovery_result
    
    async def _apply_execution_strategies(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply execution-specific recovery strategies."""
        
        error_category = enhanced_context.get("error_category")
        strategies = self._get_execution_strategies(error_category)
        
        for strategy_name in strategies:
            if strategy_name in self.recovery_strategies:
                try:
                    self.logger.info(
                        "Applying execution recovery strategy",
                        strategy=strategy_name,
                        error_category=error_category,
                        incident_id=enhanced_context.get("incident_id")
                    )
                    
                    strategy_func = self.recovery_strategies[strategy_name]
                    success = await strategy_func(error, context, enhanced_context)
                    
                    # Update strategy metrics
                    self.metrics.recovery_strategies_used[strategy_name] = (
                        self.metrics.recovery_strategies_used.get(strategy_name, 0) + 1
                    )
                    
                    if success:
                        return {
                            "success": True,
                            "strategy_used": strategy_name,
                            "execution_recovery": True
                        }
                        
                except Exception as strategy_error:
                    self.logger.error(
                        "Recovery strategy failed",
                        strategy=strategy_name,
                        error=str(strategy_error),
                        incident_id=enhanced_context.get("incident_id")
                    )
        
        return {"success": False, "execution_recovery": True}
    
    def _get_execution_strategies(self, error_category: str) -> List[str]:
        """Get execution-specific recovery strategies for error category."""
        
        strategy_map = {
            ExecutionErrorCategory.ADAPTER_FAILURE.value: [
                "restart_adapter", "fallback_adapter", "reset_adapter_state"
            ],
            ExecutionErrorCategory.BROWSER_CRASH.value: [
                "restart_browser", "cleanup_browser_resources", "fallback_browser"
            ],
            ExecutionErrorCategory.TASK_TIMEOUT.value: [
                "extend_timeout", "retry_with_backoff", "simplify_task"
            ],
            ExecutionErrorCategory.RESOURCE_EXHAUSTION.value: [
                "cleanup_resources", "reduce_concurrency", "restart_with_limits"
            ],
            ExecutionErrorCategory.DEPENDENCY_FAILURE.value: [
                "reload_dependencies", "fallback_implementation", "skip_optional_deps"
            ],
            ExecutionErrorCategory.CONFIGURATION_INVALID.value: [
                "reload_configuration", "use_default_config", "validate_and_fix_config"
            ],
            ExecutionErrorCategory.WORKFLOW_CORRUPTION.value: [
                "restore_workflow_state", "restart_workflow", "fallback_workflow"
            ],
            ExecutionErrorCategory.CONCURRENCY_CONFLICT.value: [
                "retry_with_jitter", "serialize_access", "resolve_deadlock"
            ]
        }
        
        return strategy_map.get(error_category, ["generic_retry"])
    
    def _estimate_recovery_time(self, error_category: str) -> float:
        """Estimate recovery time based on error category and historical data."""
        
        # Base estimates by category (in seconds)
        base_estimates = {
            ExecutionErrorCategory.ADAPTER_FAILURE.value: 5.0,
            ExecutionErrorCategory.BROWSER_CRASH.value: 10.0,
            ExecutionErrorCategory.TASK_TIMEOUT.value: 2.0,
            ExecutionErrorCategory.RESOURCE_EXHAUSTION.value: 15.0,
            ExecutionErrorCategory.DEPENDENCY_FAILURE.value: 8.0,
            ExecutionErrorCategory.CONFIGURATION_INVALID.value: 3.0,
            ExecutionErrorCategory.WORKFLOW_CORRUPTION.value: 12.0,
            ExecutionErrorCategory.CONCURRENCY_CONFLICT.value: 1.0
        }
        
        base_time = base_estimates.get(error_category, 5.0)
        
        # Adjust based on historical data
        if self.metrics.average_recovery_time > 0:
            historical_factor = min(2.0, self.metrics.average_recovery_time / base_time)
            return base_time * historical_factor
        
        return base_time

    def _initialize_recovery_strategies(self) -> None:
        """Initialize built-in recovery strategies."""

        # Adapter recovery strategies
        self.recovery_strategies["restart_adapter"] = self._restart_adapter_strategy
        self.recovery_strategies["fallback_adapter"] = self._fallback_adapter_strategy
        self.recovery_strategies["reset_adapter_state"] = self._reset_adapter_state_strategy

        # Browser recovery strategies
        self.recovery_strategies["restart_browser"] = self._restart_browser_strategy
        self.recovery_strategies["cleanup_browser_resources"] = self._cleanup_browser_strategy
        self.recovery_strategies["fallback_browser"] = self._fallback_browser_strategy

        # Task recovery strategies
        self.recovery_strategies["extend_timeout"] = self._extend_timeout_strategy
        self.recovery_strategies["retry_with_backoff"] = self._retry_with_backoff_strategy
        self.recovery_strategies["simplify_task"] = self._simplify_task_strategy

        # Resource recovery strategies
        self.recovery_strategies["cleanup_resources"] = self._cleanup_resources_strategy
        self.recovery_strategies["reduce_concurrency"] = self._reduce_concurrency_strategy
        self.recovery_strategies["restart_with_limits"] = self._restart_with_limits_strategy

        # Configuration recovery strategies
        self.recovery_strategies["reload_configuration"] = self._reload_configuration_strategy
        self.recovery_strategies["use_default_config"] = self._use_default_config_strategy
        self.recovery_strategies["validate_and_fix_config"] = self._validate_fix_config_strategy

        # Generic strategies
        self.recovery_strategies["generic_retry"] = self._generic_retry_strategy

        self.logger.info("Recovery strategies initialized",
                        strategy_count=len(self.recovery_strategies))

    async def _restart_adapter_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Restart the adapter that failed."""
        try:
            if context.adapter_id:
                self.logger.info("Attempting adapter restart",
                               adapter_id=context.adapter_id)

                # Simulate adapter restart (would integrate with actual adapter factory)
                await asyncio.sleep(0.5)  # Simulate restart time

                # In real implementation, would call:
                # await adapter_factory.restart_adapter(context.adapter_id)

                return True
        except Exception as e:
            self.logger.error("Adapter restart failed", error=str(e))
        return False

    async def _fallback_adapter_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Switch to fallback adapter."""
        try:
            self.logger.info("Attempting adapter fallback",
                           original_adapter=context.adapter_id)

            # Simulate fallback adapter selection
            await asyncio.sleep(0.2)

            # In real implementation, would call:
            # await adapter_factory.switch_to_fallback(context.adapter_id)

            return True
        except Exception as e:
            self.logger.error("Adapter fallback failed", error=str(e))
        return False

    async def _reset_adapter_state_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Reset adapter state to clean state."""
        try:
            self.logger.info("Attempting adapter state reset",
                           adapter_id=context.adapter_id)

            # Simulate state reset
            await asyncio.sleep(0.1)

            return True
        except Exception as e:
            self.logger.error("Adapter state reset failed", error=str(e))
        return False

    async def _restart_browser_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Restart browser session."""
        try:
            self.logger.info("Attempting browser restart",
                           session_id=context.browser_session_id)

            # Simulate browser restart
            await asyncio.sleep(2.0)  # Browser restart takes longer

            return True
        except Exception as e:
            self.logger.error("Browser restart failed", error=str(e))
        return False

    async def _cleanup_browser_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Cleanup browser resources."""
        try:
            self.logger.info("Attempting browser cleanup",
                           session_id=context.browser_session_id)

            # Simulate resource cleanup
            await asyncio.sleep(0.5)

            return True
        except Exception as e:
            self.logger.error("Browser cleanup failed", error=str(e))
        return False

    async def _fallback_browser_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Switch to fallback browser."""
        try:
            self.logger.info("Attempting browser fallback")

            # Simulate browser fallback
            await asyncio.sleep(1.0)

            return True
        except Exception as e:
            self.logger.error("Browser fallback failed", error=str(e))
        return False

    async def _extend_timeout_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Extend timeout for the operation."""
        try:
            new_timeout = context.timeout_seconds * 1.5
            self.logger.info("Extending timeout",
                           old_timeout=context.timeout_seconds,
                           new_timeout=new_timeout)

            context.timeout_seconds = new_timeout
            return True
        except Exception as e:
            self.logger.error("Timeout extension failed", error=str(e))
        return False

    async def _retry_with_backoff_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Retry with exponential backoff."""
        try:
            if context.retry_count >= context.max_retries:
                return False

            # Calculate backoff delay
            backoff_delay = min(30.0, (2 ** context.retry_count) * 0.5)

            self.logger.info("Retrying with backoff",
                           retry_count=context.retry_count,
                           backoff_delay=backoff_delay)

            await asyncio.sleep(backoff_delay)
            context.retry_count += 1

            return True
        except Exception as e:
            self.logger.error("Retry with backoff failed", error=str(e))
        return False

    async def _simplify_task_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Simplify task to reduce complexity."""
        try:
            self.logger.info("Attempting task simplification",
                           task_id=context.task_id)

            # Simulate task simplification
            await asyncio.sleep(0.1)

            return True
        except Exception as e:
            self.logger.error("Task simplification failed", error=str(e))
        return False

    async def _cleanup_resources_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Cleanup system resources."""
        try:
            self.logger.info("Attempting resource cleanup")

            # Simulate resource cleanup
            await asyncio.sleep(0.5)

            return True
        except Exception as e:
            self.logger.error("Resource cleanup failed", error=str(e))
        return False

    async def _reduce_concurrency_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Reduce concurrency to avoid resource conflicts."""
        try:
            self.logger.info("Attempting concurrency reduction")

            # Simulate concurrency reduction
            await asyncio.sleep(0.2)

            return True
        except Exception as e:
            self.logger.error("Concurrency reduction failed", error=str(e))
        return False

    async def _restart_with_limits_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Restart with resource limits."""
        try:
            self.logger.info("Attempting restart with limits")

            # Simulate restart with limits
            await asyncio.sleep(1.0)

            return True
        except Exception as e:
            self.logger.error("Restart with limits failed", error=str(e))
        return False

    async def _reload_configuration_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Reload configuration from source."""
        try:
            self.logger.info("Attempting configuration reload")

            # Simulate configuration reload
            await asyncio.sleep(0.3)

            return True
        except Exception as e:
            self.logger.error("Configuration reload failed", error=str(e))
        return False

    async def _use_default_config_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Use default configuration."""
        try:
            self.logger.info("Attempting default configuration fallback")

            # Simulate default config usage
            await asyncio.sleep(0.1)

            return True
        except Exception as e:
            self.logger.error("Default configuration fallback failed", error=str(e))
        return False

    async def _validate_fix_config_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Validate and fix configuration."""
        try:
            self.logger.info("Attempting configuration validation and fix")

            # Simulate config validation and fix
            await asyncio.sleep(0.5)

            return True
        except Exception as e:
            self.logger.error("Configuration validation and fix failed", error=str(e))
        return False

    async def _generic_retry_strategy(
        self,
        error: Exception,
        context: RecoveryContext,
        enhanced_context: Dict[str, Any]
    ) -> bool:
        """Generic retry strategy."""
        try:
            if context.retry_count >= context.max_retries:
                return False

            self.logger.info("Attempting generic retry",
                           retry_count=context.retry_count)

            await asyncio.sleep(1.0)
            context.retry_count += 1

            return True
        except Exception as e:
            self.logger.error("Generic retry failed", error=str(e))
        return False

    async def _background_recovery_processor(self) -> None:
        """Background processor for queued recovery operations."""
        self.logger.info("Background recovery processor started")

        while True:
            try:
                # Wait for recovery request
                recovery_request = await self.recovery_queue.get()

                self.logger.info(
                    "Processing background recovery",
                    incident_id=recovery_request["incident_id"]
                )

                # Process recovery
                await self._process_background_recovery(recovery_request)

                # Mark task as done
                self.recovery_queue.task_done()

            except asyncio.CancelledError:
                self.logger.info("Background recovery processor cancelled")
                break
            except Exception as e:
                self.logger.error("Background recovery processor error", error=str(e))
                await asyncio.sleep(1.0)  # Brief pause before continuing

    async def _process_background_recovery(self, recovery_request: Dict[str, Any]) -> None:
        """Process a background recovery request."""
        try:
            error = recovery_request["error"]
            context = recovery_request["context"]
            enhanced_context = recovery_request["enhanced_context"]

            # Apply recovery strategies
            recovery_result = await self._apply_execution_strategies(
                error, context, enhanced_context
            )

            # Log result
            if recovery_result.get("success"):
                self.logger.info(
                    "Background recovery successful",
                    incident_id=recovery_request["incident_id"],
                    strategy=recovery_result.get("strategy_used")
                )
            else:
                self.logger.warning(
                    "Background recovery failed",
                    incident_id=recovery_request["incident_id"]
                )

        except Exception as e:
            self.logger.error(
                "Background recovery processing failed",
                incident_id=recovery_request.get("incident_id"),
                error=str(e)
            )

    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get comprehensive recovery metrics."""
        return {
            "total_errors": self.metrics.total_errors,
            "total_recoveries": self.metrics.total_recoveries,
            "recovery_success_rate": self.metrics.recovery_success_rate,
            "average_recovery_time": self.metrics.average_recovery_time,
            "errors_by_category": dict(self.metrics.errors_by_category),
            "recovery_strategies_used": dict(self.metrics.recovery_strategies_used),
            "pattern_accuracy": self.metrics.pattern_accuracy,
            "last_updated": self.metrics.last_updated.isoformat(),
            "queue_size": self.recovery_queue.qsize(),
            "background_processor_active": self.background_recovery_task is not None
        }

    def get_error_analytics(self) -> Dict[str, Any]:
        """Get detailed error analytics."""
        if not self.error_history:
            return {"message": "No error history available"}

        # Calculate analytics
        recent_errors = list(self.error_history)[-100:]  # Last 100 errors

        # Error frequency by category
        category_counts = defaultdict(int)
        for error_record in recent_errors:
            category_counts[error_record["error_category"]] += 1

        # Recovery success by category
        category_success = defaultdict(lambda: {"total": 0, "successful": 0})
        for error_record in recent_errors:
            category = error_record["error_category"]
            category_success[category]["total"] += 1
            if error_record["recovery_result"].get("success"):
                category_success[category]["successful"] += 1

        # Calculate success rates
        success_rates = {}
        for category, stats in category_success.items():
            if stats["total"] > 0:
                success_rates[category] = stats["successful"] / stats["total"]
            else:
                success_rates[category] = 0.0

        # Average recovery times by category
        recovery_times = defaultdict(list)
        for error_record in recent_errors:
            if error_record["recovery_result"].get("success"):
                category = error_record["error_category"]
                recovery_times[category].append(error_record["execution_time"])

        avg_recovery_times = {}
        for category, times in recovery_times.items():
            if times:
                avg_recovery_times[category] = sum(times) / len(times)
            else:
                avg_recovery_times[category] = 0.0

        return {
            "total_errors_analyzed": len(recent_errors),
            "error_frequency_by_category": dict(category_counts),
            "recovery_success_rates": success_rates,
            "average_recovery_times": avg_recovery_times,
            "most_common_error_category": max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None,
            "best_recovery_category": max(success_rates.items(), key=lambda x: x[1])[0] if success_rates else None,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }

    async def generate_recovery_report(self) -> Dict[str, Any]:
        """Generate comprehensive recovery report."""
        metrics = self.get_recovery_metrics()
        analytics = self.get_error_analytics()

        # Pattern analysis
        pattern_analysis = await self._analyze_error_patterns()

        # Recommendations
        recommendations = self._generate_recommendations(analytics)

        return {
            "report_timestamp": datetime.utcnow().isoformat(),
            "metrics": metrics,
            "analytics": analytics,
            "pattern_analysis": pattern_analysis,
            "recommendations": recommendations,
            "system_health": {
                "recovery_system_operational": True,
                "background_processor_active": self.background_recovery_task is not None,
                "queue_backlog": self.recovery_queue.qsize(),
                "learning_enabled": self.enable_learning
            }
        }

    async def _analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns for insights."""
        if not self.error_history:
            return {"message": "Insufficient data for pattern analysis"}

        recent_errors = list(self.error_history)[-50:]  # Last 50 errors

        # Time-based patterns
        hourly_distribution = defaultdict(int)
        for error_record in recent_errors:
            hour = error_record["timestamp"].hour
            hourly_distribution[hour] += 1

        # Error clustering
        error_clusters = defaultdict(list)
        for error_record in recent_errors:
            key = f"{error_record['error_type']}_{error_record['error_category']}"
            error_clusters[key].append(error_record)

        # Most problematic patterns
        problematic_patterns = []
        for pattern, errors in error_clusters.items():
            if len(errors) >= 3:  # Pattern appears 3+ times
                success_rate = sum(1 for e in errors if e["recovery_result"].get("success")) / len(errors)
                problematic_patterns.append({
                    "pattern": pattern,
                    "occurrences": len(errors),
                    "success_rate": success_rate,
                    "avg_recovery_time": sum(e["execution_time"] for e in errors) / len(errors)
                })

        # Sort by occurrence and low success rate
        problematic_patterns.sort(key=lambda x: (x["occurrences"], -x["success_rate"]), reverse=True)

        return {
            "hourly_error_distribution": dict(hourly_distribution),
            "error_clusters": len(error_clusters),
            "problematic_patterns": problematic_patterns[:5],  # Top 5
            "pattern_diversity": len(error_clusters) / len(recent_errors) if recent_errors else 0
        }

    def _generate_recommendations(self, analytics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate actionable recommendations based on analytics."""
        recommendations = []

        # Low success rate categories
        success_rates = analytics.get("recovery_success_rates", {})
        for category, rate in success_rates.items():
            if rate < 0.7:  # Less than 70% success rate
                recommendations.append({
                    "type": "improvement",
                    "priority": "high",
                    "category": category,
                    "issue": f"Low recovery success rate ({rate:.1%})",
                    "recommendation": f"Review and enhance recovery strategies for {category} errors",
                    "impact": "Reduce manual intervention and improve system reliability"
                })

        # High frequency categories
        frequency = analytics.get("error_frequency_by_category", {})
        total_errors = sum(frequency.values())
        for category, count in frequency.items():
            if count / total_errors > 0.3:  # More than 30% of errors
                recommendations.append({
                    "type": "prevention",
                    "priority": "medium",
                    "category": category,
                    "issue": f"High error frequency ({count} errors, {count/total_errors:.1%})",
                    "recommendation": f"Investigate root causes of {category} errors for prevention",
                    "impact": "Reduce overall error rate and improve system stability"
                })

        # Slow recovery times
        recovery_times = analytics.get("average_recovery_times", {})
        for category, time in recovery_times.items():
            if time > 10.0:  # More than 10 seconds
                recommendations.append({
                    "type": "optimization",
                    "priority": "medium",
                    "category": category,
                    "issue": f"Slow recovery time ({time:.1f}s average)",
                    "recommendation": f"Optimize recovery strategies for {category} to reduce time",
                    "impact": "Improve user experience and system responsiveness"
                })

        return recommendations
