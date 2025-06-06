"""
Enhanced error recovery system for the unified execution layer.

This module provides comprehensive error handling that addresses root causes
rather than masking issues with fallbacks.
"""

import asyncio
import uuid
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass
import traceback

from core.exceptions import (
    TaskExecutionError, BrowserError, LLMError, ResourceError,
    ConfigurationError, TimeoutError, RetryExhaustedError
)
from core.interfaces import TaskStatus
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    CRITICAL = "critical"      # System-breaking errors
    HIGH = "high"             # Service-affecting errors
    MEDIUM = "medium"         # Feature-affecting errors
    LOW = "low"              # Minor issues
    INFO = "info"            # Informational


class RecoveryAction(str, Enum):
    """Available recovery actions."""
    RETRY = "retry"
    RESTART_COMPONENT = "restart_component"
    FALLBACK = "fallback"
    ESCALATE = "escalate"
    ABORT = "abort"
    INVESTIGATE = "investigate"


@dataclass
class ErrorContext:
    """Enhanced error context with diagnostic information."""
    error_id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    component: str
    operation: str
    timestamp: datetime
    correlation_id: Optional[str] = None
    stack_trace: Optional[str] = None
    system_state: Optional[Dict[str, Any]] = None
    previous_errors: Optional[List[str]] = None
    recovery_attempts: int = 0
    max_recovery_attempts: int = 3


@dataclass
class RecoveryPlan:
    """Recovery plan with specific actions and conditions."""
    actions: List[RecoveryAction]
    conditions: Dict[str, Any]
    timeout: float
    success_criteria: Callable[[Any], bool]
    rollback_plan: Optional[List[RecoveryAction]] = None


class EnhancedErrorRecovery:
    """
    Enhanced error recovery system that focuses on root cause resolution.
    
    This system provides intelligent error analysis, targeted recovery actions,
    and comprehensive monitoring to prevent error masking.
    """
    
    def __init__(self):
        self.logger = StructuredLogger("enhanced_error_recovery")
        
        # Error tracking
        self.error_history: List[ErrorContext] = []
        self.error_patterns: Dict[str, List[ErrorContext]] = {}
        self.recovery_statistics: Dict[str, Dict[str, int]] = {}
        
        # Component health tracking
        self.component_health: Dict[str, Dict[str, Any]] = {}
        self.last_health_check: Dict[str, datetime] = {}
        
        # Recovery strategies
        self.recovery_strategies: Dict[str, RecoveryPlan] = {}
        self._initialize_recovery_strategies()
    
    def _initialize_recovery_strategies(self) -> None:
        """Initialize default recovery strategies."""
        
        # Browser-related errors
        self.recovery_strategies["browser_crash"] = RecoveryPlan(
            actions=[RecoveryAction.RESTART_COMPONENT, RecoveryAction.RETRY],
            conditions={"max_retries": 2, "restart_delay": 5.0},
            timeout=30.0,
            success_criteria=lambda result: result is not None
        )
        
        # LLM provider errors
        self.recovery_strategies["llm_rate_limit"] = RecoveryPlan(
            actions=[RecoveryAction.FALLBACK, RecoveryAction.RETRY],
            conditions={"backoff_multiplier": 2.0, "max_backoff": 60.0},
            timeout=120.0,
            success_criteria=lambda result: isinstance(result, str) and len(result) > 0
        )
        
        # Resource exhaustion
        self.recovery_strategies["resource_exhaustion"] = RecoveryPlan(
            actions=[RecoveryAction.INVESTIGATE, RecoveryAction.RESTART_COMPONENT],
            conditions={"cleanup_threshold": 0.8, "restart_delay": 10.0},
            timeout=60.0,
            success_criteria=lambda result: True  # Success is cleanup completion
        )
        
        # Configuration errors
        self.recovery_strategies["configuration_error"] = RecoveryPlan(
            actions=[RecoveryAction.INVESTIGATE, RecoveryAction.ESCALATE],
            conditions={"validation_required": True},
            timeout=0.0,  # No automatic retry for config errors
            success_criteria=lambda result: False  # Always escalate config errors
        )
    
    @with_correlation_id
    async def handle_error(
        self,
        error: Exception,
        component: str,
        operation: str,
        context: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle an error with enhanced recovery logic.
        
        Args:
            error: The exception that occurred
            component: Component where error occurred
            operation: Operation that failed
            context: Additional context information
            correlation_id: Request correlation ID
            
        Returns:
            Recovery result with detailed information
        """
        correlation_id = correlation_id or str(uuid.uuid4())
        context = context or {}
        
        # Create error context
        error_context = ErrorContext(
            error_id=str(uuid.uuid4()),
            error_type=type(error).__name__,
            error_message=str(error),
            severity=self._assess_severity(error, component),
            component=component,
            operation=operation,
            timestamp=datetime.now(timezone.utc),
            correlation_id=correlation_id,
            stack_trace=traceback.format_exc(),
            system_state=await self._capture_system_state(component),
            previous_errors=self._get_recent_errors(component, operation)
        )
        
        # Log error with full context
        self.logger.error(
            "Error occurred in component",
            error_id=error_context.error_id,
            error_type=error_context.error_type,
            error_message=error_context.error_message,
            severity=error_context.severity.value,
            component=component,
            operation=operation,
            correlation_id=correlation_id,
            previous_errors_count=len(error_context.previous_errors or [])
        )
        
        # Store error for pattern analysis
        self._store_error(error_context)
        
        # Analyze error patterns
        pattern_analysis = await self._analyze_error_patterns(error_context)
        
        # Determine recovery strategy
        recovery_strategy = self._determine_recovery_strategy(error_context, pattern_analysis)
        
        # Execute recovery if appropriate
        if recovery_strategy and error_context.severity != ErrorSeverity.CRITICAL:
            recovery_result = await self._execute_recovery(error_context, recovery_strategy)
        else:
            # Critical errors or no strategy - escalate immediately
            recovery_result = {
                "success": False,
                "action": "escalated",
                "reason": "Critical error or no recovery strategy available"
            }
        
        # Update statistics
        self._update_recovery_statistics(error_context, recovery_result)
        
        return {
            "error_id": error_context.error_id,
            "severity": error_context.severity.value,
            "recovery_attempted": recovery_strategy is not None,
            "recovery_result": recovery_result,
            "pattern_analysis": pattern_analysis,
            "correlation_id": correlation_id
        }
    
    def _assess_severity(self, error: Exception, component: str) -> ErrorSeverity:
        """Assess error severity based on error type and component."""
        
        # Critical errors that break the system
        if isinstance(error, (SystemExit, KeyboardInterrupt, MemoryError)):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        if isinstance(error, (ConfigurationError, ResourceError)):
            return ErrorSeverity.HIGH
        
        # Component-specific severity assessment
        if component == "browser_manager":
            if isinstance(error, BrowserError):
                return ErrorSeverity.MEDIUM
        elif component == "llm_provider":
            if isinstance(error, LLMError):
                # Rate limiting is medium, other LLM errors are high
                if "rate limit" in str(error).lower():
                    return ErrorSeverity.MEDIUM
                return ErrorSeverity.HIGH
        
        # Default to medium for execution errors
        if isinstance(error, TaskExecutionError):
            return ErrorSeverity.MEDIUM
        
        # Low severity for timeouts and retryable errors
        if isinstance(error, (TimeoutError, RetryExhaustedError)):
            return ErrorSeverity.LOW
        
        return ErrorSeverity.MEDIUM
    
    async def _capture_system_state(self, component: str) -> Dict[str, Any]:
        """Capture current system state for diagnostics."""
        try:
            import psutil
            
            state = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "component": component,
                "system": {
                    "cpu_percent": psutil.cpu_percent(interval=0.1),
                    "memory_percent": psutil.virtual_memory().percent,
                    "disk_percent": psutil.disk_usage('/').percent,
                    "process_count": len(psutil.pids())
                }
            }
            
            # Component-specific state
            if component == "browser_manager":
                state["browser_processes"] = len([
                    p for p in psutil.process_iter(['name']) 
                    if 'chrome' in p.info['name'].lower() or 'firefox' in p.info['name'].lower()
                ])
            
            return state
            
        except Exception as e:
            self.logger.warning(f"Failed to capture system state: {e}")
            return {"error": str(e)}
    
    def _get_recent_errors(self, component: str, operation: str, hours: int = 1) -> List[str]:
        """Get recent errors for the same component/operation."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        recent_errors = [
            error.error_id for error in self.error_history
            if (error.component == component and 
                error.operation == operation and 
                error.timestamp > cutoff)
        ]
        
        return recent_errors[-10:]  # Last 10 errors
    
    def _store_error(self, error_context: ErrorContext) -> None:
        """Store error for pattern analysis."""
        self.error_history.append(error_context)
        
        # Keep only recent errors (last 1000)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Store in pattern tracking
        pattern_key = f"{error_context.component}:{error_context.error_type}"
        if pattern_key not in self.error_patterns:
            self.error_patterns[pattern_key] = []
        
        self.error_patterns[pattern_key].append(error_context)
        
        # Keep only recent patterns
        if len(self.error_patterns[pattern_key]) > 50:
            self.error_patterns[pattern_key] = self.error_patterns[pattern_key][-50:]
    
    async def _analyze_error_patterns(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Analyze error patterns to identify systemic issues."""
        pattern_key = f"{error_context.component}:{error_context.error_type}"
        
        if pattern_key not in self.error_patterns:
            return {"pattern_detected": False}
        
        recent_errors = self.error_patterns[pattern_key]
        
        # Check for error frequency patterns
        now = datetime.now(timezone.utc)
        last_hour_errors = [
            e for e in recent_errors 
            if (now - e.timestamp).total_seconds() < 3600
        ]
        
        last_day_errors = [
            e for e in recent_errors 
            if (now - e.timestamp).total_seconds() < 86400
        ]
        
        analysis = {
            "pattern_detected": len(last_hour_errors) > 5,  # More than 5 errors in last hour
            "error_frequency": {
                "last_hour": len(last_hour_errors),
                "last_day": len(last_day_errors),
                "total": len(recent_errors)
            },
            "trend": "increasing" if len(last_hour_errors) > len(last_day_errors) / 24 else "stable"
        }
        
        # Check for cascading failures
        if len(error_context.previous_errors or []) > 3:
            analysis["cascading_failure"] = True
            analysis["recommendation"] = "Investigate root cause - multiple related failures detected"
        
        return analysis
    
    def _determine_recovery_strategy(
        self, 
        error_context: ErrorContext, 
        pattern_analysis: Dict[str, Any]
    ) -> Optional[RecoveryPlan]:
        """Determine appropriate recovery strategy."""
        
        # Don't attempt recovery for critical errors
        if error_context.severity == ErrorSeverity.CRITICAL:
            return None
        
        # Don't attempt recovery if too many attempts already made
        if error_context.recovery_attempts >= error_context.max_recovery_attempts:
            return None
        
        # Check for cascading failures - escalate instead of retry
        if pattern_analysis.get("cascading_failure"):
            return None
        
        # Map error types to strategies
        error_type_lower = error_context.error_type.lower()
        
        if "browser" in error_type_lower or "chrome" in error_type_lower:
            return self.recovery_strategies.get("browser_crash")
        elif "rate" in error_type_lower and "limit" in error_type_lower:
            return self.recovery_strategies.get("llm_rate_limit")
        elif "resource" in error_type_lower or "memory" in error_type_lower:
            return self.recovery_strategies.get("resource_exhaustion")
        elif "configuration" in error_type_lower:
            return self.recovery_strategies.get("configuration_error")
        
        # Default strategy for unknown errors
        return RecoveryPlan(
            actions=[RecoveryAction.RETRY],
            conditions={"max_retries": 1},
            timeout=30.0,
            success_criteria=lambda result: result is not None
        )
    
    async def _execute_recovery(
        self, 
        error_context: ErrorContext, 
        recovery_plan: RecoveryPlan
    ) -> Dict[str, Any]:
        """Execute recovery plan."""
        
        self.logger.info(
            "Executing recovery plan",
            error_id=error_context.error_id,
            actions=recovery_plan.actions,
            correlation_id=error_context.correlation_id
        )
        
        for action in recovery_plan.actions:
            try:
                if action == RecoveryAction.INVESTIGATE:
                    # Perform investigation
                    investigation_result = await self._investigate_error(error_context)
                    if investigation_result.get("root_cause_identified"):
                        return {
                            "success": True,
                            "action": action.value,
                            "details": investigation_result
                        }
                
                elif action == RecoveryAction.ESCALATE:
                    # Escalate to human intervention
                    await self._escalate_error(error_context)
                    return {
                        "success": False,
                        "action": action.value,
                        "reason": "Escalated for human intervention"
                    }
                
                # Other actions would be implemented based on specific needs
                
            except Exception as recovery_error:
                self.logger.error(
                    "Recovery action failed",
                    error_id=error_context.error_id,
                    action=action.value,
                    recovery_error=str(recovery_error)
                )
                continue
        
        return {
            "success": False,
            "action": "all_actions_failed",
            "reason": "All recovery actions were attempted but failed"
        }
    
    async def _investigate_error(self, error_context: ErrorContext) -> Dict[str, Any]:
        """Investigate error to identify root cause."""
        
        investigation = {
            "root_cause_identified": False,
            "recommendations": [],
            "system_health": await self._capture_system_state(error_context.component)
        }
        
        # Check for common root causes
        if error_context.component == "browser_manager":
            if "memory" in error_context.error_message.lower():
                investigation["root_cause_identified"] = True
                investigation["root_cause"] = "Memory exhaustion"
                investigation["recommendations"].append("Implement browser instance cleanup")
                investigation["recommendations"].append("Reduce concurrent browser sessions")
        
        elif error_context.component == "llm_provider":
            if "quota" in error_context.error_message.lower():
                investigation["root_cause_identified"] = True
                investigation["root_cause"] = "API quota exceeded"
                investigation["recommendations"].append("Implement usage monitoring")
                investigation["recommendations"].append("Add cost controls")
        
        return investigation
    
    async def _escalate_error(self, error_context: ErrorContext) -> None:
        """Escalate error for human intervention."""
        
        self.logger.critical(
            "Error escalated for human intervention",
            error_id=error_context.error_id,
            error_type=error_context.error_type,
            component=error_context.component,
            severity=error_context.severity.value,
            correlation_id=error_context.correlation_id
        )
        
        # In a real system, this would trigger alerts, notifications, etc.
    
    def _update_recovery_statistics(
        self, 
        error_context: ErrorContext, 
        recovery_result: Dict[str, Any]
    ) -> None:
        """Update recovery statistics for monitoring."""
        
        component = error_context.component
        if component not in self.recovery_statistics:
            self.recovery_statistics[component] = {
                "total_errors": 0,
                "recovery_attempts": 0,
                "successful_recoveries": 0,
                "escalations": 0
            }
        
        stats = self.recovery_statistics[component]
        stats["total_errors"] += 1
        
        if recovery_result.get("action") != "escalated":
            stats["recovery_attempts"] += 1
            
            if recovery_result.get("success"):
                stats["successful_recoveries"] += 1
        else:
            stats["escalations"] += 1
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get recovery statistics for monitoring."""
        return {
            "component_statistics": self.recovery_statistics,
            "total_errors": len(self.error_history),
            "error_patterns": {
                pattern: len(errors) 
                for pattern, errors in self.error_patterns.items()
            }
        }
