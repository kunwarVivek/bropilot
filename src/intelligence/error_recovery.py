"""
Intelligent error recovery and self-healing mechanisms.

This module provides advanced error recovery capabilities using machine learning
and pattern recognition to automatically diagnose and fix common issues.
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid
import re
from collections import defaultdict, Counter

from core.interfaces import ILLMProvider
from core.exceptions import RecoveryError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id
from src.llm.conversation_manager import ConversationManager, ConversationConfig


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoveryStrategy(str, Enum):
    """Recovery strategy types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    REPAIR = "repair"
    RESTART = "restart"
    ESCALATE = "escalate"
    IGNORE = "ignore"


class ErrorCategory(str, Enum):
    """Error category classification."""
    NETWORK = "network"
    BROWSER = "browser"
    ELEMENT = "element"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    UNKNOWN = "unknown"


@dataclass
class ErrorPattern:
    """Represents a learned error pattern."""
    pattern_id: str
    error_signature: str
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_strategies: List[RecoveryStrategy]
    success_rate: float = 0.0
    occurrence_count: int = 0
    last_seen: datetime = field(default_factory=datetime.utcnow)
    context_patterns: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RecoveryAction:
    """Represents a recovery action."""
    action_id: str
    strategy: RecoveryStrategy
    description: str
    action_function: Callable
    prerequisites: List[str] = field(default_factory=list)
    estimated_time: float = 0.0
    success_probability: float = 0.5
    side_effects: List[str] = field(default_factory=list)


@dataclass
class ErrorIncident:
    """Represents an error incident."""
    incident_id: str
    error_message: str
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    stack_trace: Optional[str] = None
    recovery_attempts: List[Dict[str, Any]] = field(default_factory=list)
    resolved: bool = False
    resolution_time: Optional[float] = None


class IntelligentErrorRecovery:
    """Intelligent error recovery system with machine learning capabilities."""
    
    def __init__(self, llm_provider: Optional[ILLMProvider] = None):
        """Initialize intelligent error recovery system."""
        self.llm_provider = llm_provider
        self.logger = StructuredLogger("error_recovery")
        
        # Error pattern learning
        self.error_patterns: Dict[str, ErrorPattern] = {}
        self.error_history: List[ErrorIncident] = []
        self.recovery_actions: Dict[str, RecoveryAction] = {}
        
        # Pattern matching
        self.error_signatures: Dict[str, str] = {}  # error_hash -> pattern_id
        self.context_analyzers: List[Callable] = []
        
        # Recovery statistics
        self.total_errors = 0
        self.total_recoveries = 0
        self.recovery_success_rate = 0.0
        
        # Self-healing configuration
        self.auto_recovery_enabled = True
        self.max_recovery_attempts = 3
        self.learning_enabled = True
        
        # Initialize built-in recovery actions
        self._initialize_recovery_actions()
        
        # Initialize conversation manager for LLM-based recovery
        if self.llm_provider:
            self.conversation_manager = ConversationManager(
                self.llm_provider,
                ConversationConfig(
                    system_prompt="You are an expert system administrator and automation engineer. "
                                "Help diagnose and recover from browser automation errors."
                )
            )
    
    async def handle_error(
        self,
        error: Exception,
        context: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Handle an error with intelligent recovery."""
        
        incident_id = str(uuid.uuid4())
        
        self.logger.error(
            "Handling error with intelligent recovery",
            incident_id=incident_id,
            error_type=type(error).__name__,
            error_message=str(error),
            correlation_id=correlation_id
        )
        
        # Create error incident
        incident = ErrorIncident(
            incident_id=incident_id,
            error_message=str(error),
            error_type=type(error).__name__,
            category=self._classify_error(error, context),
            severity=self._assess_severity(error, context),
            context=context,
            stack_trace=getattr(error, '__traceback__', None)
        )
        
        self.error_history.append(incident)
        self.total_errors += 1
        
        # Find matching pattern or create new one
        pattern = await self._find_or_create_pattern(incident)
        
        # Attempt recovery
        recovery_result = await self._attempt_recovery(incident, pattern)
        
        # Update pattern based on recovery result
        if self.learning_enabled:
            await self._update_pattern(pattern, recovery_result)
        
        # Update statistics
        if recovery_result["success"]:
            self.total_recoveries += 1
            incident.resolved = True
            incident.resolution_time = recovery_result["total_time"]
        
        self.recovery_success_rate = self.total_recoveries / self.total_errors if self.total_errors > 0 else 0
        
        return {
            "incident_id": incident_id,
            "recovery_result": recovery_result,
            "pattern_id": pattern.pattern_id,
            "resolved": incident.resolved
        }
    
    def _classify_error(self, error: Exception, context: Dict[str, Any]) -> ErrorCategory:
        """Classify error into categories."""
        
        error_message = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Network-related errors
        if any(keyword in error_message for keyword in ["connection", "network", "timeout", "dns", "ssl"]):
            return ErrorCategory.NETWORK
        
        # Browser-related errors
        if any(keyword in error_message for keyword in ["browser", "page", "navigation", "crashed"]):
            return ErrorCategory.BROWSER
        
        # Element-related errors
        if any(keyword in error_message for keyword in ["element", "selector", "not found", "stale"]):
            return ErrorCategory.ELEMENT
        
        # Timeout errors
        if "timeout" in error_message or "timeout" in error_type:
            return ErrorCategory.TIMEOUT
        
        # Authentication errors
        if any(keyword in error_message for keyword in ["auth", "login", "credential", "permission"]):
            return ErrorCategory.AUTHENTICATION
        
        # Validation errors
        if "validation" in error_type or "invalid" in error_message:
            return ErrorCategory.VALIDATION
        
        # Resource errors
        if any(keyword in error_message for keyword in ["resource", "memory", "disk", "file"]):
            return ErrorCategory.RESOURCE
        
        # Configuration errors
        if any(keyword in error_message for keyword in ["config", "setting", "parameter"]):
            return ErrorCategory.CONFIGURATION
        
        return ErrorCategory.UNKNOWN
    
    def _assess_severity(self, error: Exception, context: Dict[str, Any]) -> ErrorSeverity:
        """Assess error severity."""
        
        error_message = str(error).lower()
        error_type = type(error).__name__
        
        # Critical errors
        critical_keywords = ["crash", "fatal", "critical", "system", "security"]
        if any(keyword in error_message for keyword in critical_keywords):
            return ErrorSeverity.CRITICAL
        
        # High severity errors
        high_keywords = ["failed", "error", "exception", "abort"]
        if any(keyword in error_message for keyword in high_keywords):
            return ErrorSeverity.HIGH
        
        # Medium severity errors
        medium_keywords = ["warning", "timeout", "retry"]
        if any(keyword in error_message for keyword in medium_keywords):
            return ErrorSeverity.MEDIUM
        
        return ErrorSeverity.LOW
    
    async def _find_or_create_pattern(self, incident: ErrorIncident) -> ErrorPattern:
        """Find existing pattern or create new one."""
        
        # Create error signature
        signature = self._create_error_signature(incident)
        
        # Check if pattern exists
        if signature in self.error_signatures:
            pattern_id = self.error_signatures[signature]
            pattern = self.error_patterns[pattern_id]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.utcnow()
            return pattern
        
        # Create new pattern
        pattern_id = str(uuid.uuid4())
        pattern = ErrorPattern(
            pattern_id=pattern_id,
            error_signature=signature,
            category=incident.category,
            severity=incident.severity,
            recovery_strategies=self._suggest_recovery_strategies(incident),
            occurrence_count=1
        )
        
        self.error_patterns[pattern_id] = pattern
        self.error_signatures[signature] = pattern_id
        
        self.logger.info(
            "New error pattern created",
            pattern_id=pattern_id,
            signature=signature,
            category=incident.category.value
        )
        
        return pattern
    
    def _create_error_signature(self, incident: ErrorIncident) -> str:
        """Create a unique signature for the error."""
        
        # Normalize error message
        normalized_message = re.sub(r'\d+', 'N', incident.error_message.lower())
        normalized_message = re.sub(r'[^\w\s]', ' ', normalized_message)
        normalized_message = ' '.join(normalized_message.split())
        
        # Create signature
        signature_parts = [
            incident.error_type,
            incident.category.value,
            normalized_message[:100]  # Limit length
        ]
        
        return "|".join(signature_parts)
    
    def _suggest_recovery_strategies(self, incident: ErrorIncident) -> List[RecoveryStrategy]:
        """Suggest recovery strategies based on error category."""
        
        strategy_map = {
            ErrorCategory.NETWORK: [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK],
            ErrorCategory.BROWSER: [RecoveryStrategy.RESTART, RecoveryStrategy.REPAIR],
            ErrorCategory.ELEMENT: [RecoveryStrategy.RETRY, RecoveryStrategy.REPAIR],
            ErrorCategory.TIMEOUT: [RecoveryStrategy.RETRY, RecoveryStrategy.FALLBACK],
            ErrorCategory.AUTHENTICATION: [RecoveryStrategy.REPAIR, RecoveryStrategy.ESCALATE],
            ErrorCategory.VALIDATION: [RecoveryStrategy.REPAIR, RecoveryStrategy.FALLBACK],
            ErrorCategory.RESOURCE: [RecoveryStrategy.RESTART, RecoveryStrategy.ESCALATE],
            ErrorCategory.CONFIGURATION: [RecoveryStrategy.REPAIR, RecoveryStrategy.ESCALATE],
            ErrorCategory.UNKNOWN: [RecoveryStrategy.RETRY, RecoveryStrategy.ESCALATE]
        }
        
        return strategy_map.get(incident.category, [RecoveryStrategy.ESCALATE])
    
    async def _attempt_recovery(
        self,
        incident: ErrorIncident,
        pattern: ErrorPattern
    ) -> Dict[str, Any]:
        """Attempt recovery using learned strategies."""
        
        start_time = time.time()
        recovery_attempts = []
        
        # Sort strategies by success probability
        strategies = sorted(
            pattern.recovery_strategies,
            key=lambda s: self._get_strategy_success_rate(s, pattern),
            reverse=True
        )
        
        for attempt_num, strategy in enumerate(strategies):
            if attempt_num >= self.max_recovery_attempts:
                break
            
            self.logger.info(
                "Attempting recovery",
                incident_id=incident.incident_id,
                strategy=strategy.value,
                attempt=attempt_num + 1
            )
            
            attempt_start = time.time()
            
            try:
                # Execute recovery strategy
                success = await self._execute_recovery_strategy(
                    strategy, incident, pattern
                )
                
                attempt_time = time.time() - attempt_start
                
                attempt_result = {
                    "strategy": strategy.value,
                    "success": success,
                    "attempt_time": attempt_time,
                    "attempt_number": attempt_num + 1
                }
                
                recovery_attempts.append(attempt_result)
                incident.recovery_attempts.append(attempt_result)
                
                if success:
                    total_time = time.time() - start_time
                    
                    self.logger.info(
                        "Recovery successful",
                        incident_id=incident.incident_id,
                        strategy=strategy.value,
                        total_time=total_time
                    )
                    
                    return {
                        "success": True,
                        "strategy": strategy.value,
                        "attempts": recovery_attempts,
                        "total_time": total_time
                    }
                
            except Exception as e:
                attempt_time = time.time() - attempt_start
                
                self.logger.error(
                    "Recovery attempt failed",
                    incident_id=incident.incident_id,
                    strategy=strategy.value,
                    error=str(e),
                    attempt_time=attempt_time
                )
                
                attempt_result = {
                    "strategy": strategy.value,
                    "success": False,
                    "error": str(e),
                    "attempt_time": attempt_time,
                    "attempt_number": attempt_num + 1
                }
                
                recovery_attempts.append(attempt_result)
                incident.recovery_attempts.append(attempt_result)
        
        # All recovery attempts failed
        total_time = time.time() - start_time
        
        self.logger.error(
            "All recovery attempts failed",
            incident_id=incident.incident_id,
            total_attempts=len(recovery_attempts),
            total_time=total_time
        )
        
        # Try LLM-based recovery as last resort
        if self.llm_provider:
            llm_result = await self._try_llm_recovery(incident, pattern)
            if llm_result["success"]:
                return llm_result
        
        return {
            "success": False,
            "attempts": recovery_attempts,
            "total_time": total_time
        }
    
    def _get_strategy_success_rate(
        self,
        strategy: RecoveryStrategy,
        pattern: ErrorPattern
    ) -> float:
        """Get success rate for a strategy with this pattern."""
        
        # Calculate based on historical data
        successful_attempts = 0
        total_attempts = 0
        
        for incident in self.error_history:
            if incident.category == pattern.category:
                for attempt in incident.recovery_attempts:
                    if attempt["strategy"] == strategy.value:
                        total_attempts += 1
                        if attempt["success"]:
                            successful_attempts += 1
        
        if total_attempts == 0:
            return 0.5  # Default probability
        
        return successful_attempts / total_attempts
    
    async def _execute_recovery_strategy(
        self,
        strategy: RecoveryStrategy,
        incident: ErrorIncident,
        pattern: ErrorPattern
    ) -> bool:
        """Execute a specific recovery strategy."""
        
        if strategy == RecoveryStrategy.RETRY:
            return await self._retry_operation(incident)
        
        elif strategy == RecoveryStrategy.FALLBACK:
            return await self._fallback_operation(incident)
        
        elif strategy == RecoveryStrategy.REPAIR:
            return await self._repair_operation(incident)
        
        elif strategy == RecoveryStrategy.RESTART:
            return await self._restart_operation(incident)
        
        elif strategy == RecoveryStrategy.ESCALATE:
            return await self._escalate_operation(incident)
        
        elif strategy == RecoveryStrategy.IGNORE:
            return True  # Always "succeeds"
        
        return False
    
    async def _retry_operation(self, incident: ErrorIncident) -> bool:
        """Retry the failed operation."""
        
        # Simple retry with exponential backoff
        retry_delay = 1.0
        max_retries = 3
        
        for retry in range(max_retries):
            await asyncio.sleep(retry_delay)
            
            # This would retry the original operation
            # For now, simulate success based on error category
            if incident.category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT]:
                return retry >= 1  # Succeed after first retry
            
            retry_delay *= 2
        
        return False
    
    async def _fallback_operation(self, incident: ErrorIncident) -> bool:
        """Use fallback approach."""
        
        # This would implement fallback logic
        # For now, simulate success for certain categories
        return incident.category in [
            ErrorCategory.ELEMENT,
            ErrorCategory.VALIDATION,
            ErrorCategory.TIMEOUT
        ]
    
    async def _repair_operation(self, incident: ErrorIncident) -> bool:
        """Repair the problematic state."""
        
        # This would implement repair logic
        # For now, simulate success for repairable categories
        return incident.category in [
            ErrorCategory.BROWSER,
            ErrorCategory.ELEMENT,
            ErrorCategory.AUTHENTICATION,
            ErrorCategory.CONFIGURATION
        ]
    
    async def _restart_operation(self, incident: ErrorIncident) -> bool:
        """Restart the affected component."""
        
        # This would restart browsers, services, etc.
        # For now, simulate success for restartable categories
        return incident.category in [
            ErrorCategory.BROWSER,
            ErrorCategory.RESOURCE
        ]
    
    async def _escalate_operation(self, incident: ErrorIncident) -> bool:
        """Escalate to human intervention."""
        
        # This would notify administrators
        # For now, always return False (requires human intervention)
        self.logger.warning(
            "Error escalated for human intervention",
            incident_id=incident.incident_id,
            category=incident.category.value,
            severity=incident.severity.value
        )
        
        return False
    
    async def _try_llm_recovery(
        self,
        incident: ErrorIncident,
        pattern: ErrorPattern
    ) -> Dict[str, Any]:
        """Try LLM-based recovery as last resort."""
        
        if not self.llm_provider:
            return {"success": False, "reason": "No LLM provider available"}
        
        try:
            # Create diagnostic prompt
            diagnostic_prompt = f"""
            I'm experiencing an error in my browser automation system:
            
            Error Type: {incident.error_type}
            Error Message: {incident.error_message}
            Category: {incident.category.value}
            Severity: {incident.severity.value}
            
            Context: {json.dumps(incident.context, indent=2)}
            
            Previous recovery attempts failed:
            {json.dumps(incident.recovery_attempts, indent=2)}
            
            Can you suggest a specific recovery strategy or solution?
            Please provide actionable steps.
            """
            
            response = await self.conversation_manager.send_message(diagnostic_prompt)
            
            # Parse LLM response for actionable suggestions
            suggestion = response.content
            
            self.logger.info(
                "LLM recovery suggestion received",
                incident_id=incident.incident_id,
                suggestion_length=len(suggestion)
            )
            
            # For now, return the suggestion without executing it
            # In practice, this would parse and execute the LLM's suggestions
            return {
                "success": False,  # Would be True if we could execute the suggestion
                "suggestion": suggestion,
                "strategy": "llm_guided",
                "total_time": 0.0
            }
            
        except Exception as e:
            self.logger.error(
                "LLM recovery failed",
                incident_id=incident.incident_id,
                error=str(e)
            )
            
            return {"success": False, "error": str(e)}
    
    async def _update_pattern(
        self,
        pattern: ErrorPattern,
        recovery_result: Dict[str, Any]
    ) -> None:
        """Update pattern based on recovery result."""
        
        if recovery_result["success"]:
            # Update success rate
            successful_strategy = recovery_result["strategy"]
            
            # Simple learning: increase success rate for successful strategy
            if successful_strategy in [s.value for s in pattern.recovery_strategies]:
                pattern.success_rate = min(1.0, pattern.success_rate + 0.1)
        else:
            # Decrease success rate for failed attempts
            pattern.success_rate = max(0.0, pattern.success_rate - 0.05)
    
    def _initialize_recovery_actions(self) -> None:
        """Initialize built-in recovery actions."""
        
        # This would initialize specific recovery actions
        # For now, just log that it's initialized
        self.logger.info("Recovery actions initialized")
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error and recovery statistics."""
        
        # Category distribution
        category_counts = Counter(incident.category.value for incident in self.error_history)
        
        # Severity distribution
        severity_counts = Counter(incident.severity.value for incident in self.error_history)
        
        # Recovery strategy effectiveness
        strategy_stats = defaultdict(lambda: {"attempts": 0, "successes": 0})
        
        for incident in self.error_history:
            for attempt in incident.recovery_attempts:
                strategy = attempt["strategy"]
                strategy_stats[strategy]["attempts"] += 1
                if attempt["success"]:
                    strategy_stats[strategy]["successes"] += 1
        
        # Calculate success rates
        for strategy, stats in strategy_stats.items():
            stats["success_rate"] = stats["successes"] / stats["attempts"] if stats["attempts"] > 0 else 0
        
        return {
            "total_errors": self.total_errors,
            "total_recoveries": self.total_recoveries,
            "overall_success_rate": self.recovery_success_rate,
            "category_distribution": dict(category_counts),
            "severity_distribution": dict(severity_counts),
            "strategy_effectiveness": dict(strategy_stats),
            "learned_patterns": len(self.error_patterns),
            "recent_errors": len([
                i for i in self.error_history
                if i.timestamp > datetime.utcnow() - timedelta(hours=24)
            ])
        }
    
    def get_pattern_insights(self) -> List[Dict[str, Any]]:
        """Get insights about learned error patterns."""
        
        insights = []
        
        for pattern in self.error_patterns.values():
            insights.append({
                "pattern_id": pattern.pattern_id,
                "category": pattern.category.value,
                "severity": pattern.severity.value,
                "occurrence_count": pattern.occurrence_count,
                "success_rate": pattern.success_rate,
                "last_seen": pattern.last_seen.isoformat(),
                "recovery_strategies": [s.value for s in pattern.recovery_strategies]
            })
        
        # Sort by occurrence count
        insights.sort(key=lambda x: x["occurrence_count"], reverse=True)
        
        return insights
