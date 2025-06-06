"""
Comprehensive cost management and budget controls for LLM usage.

This module provides advanced cost tracking, budget enforcement, and
usage optimization for LLM API consumption.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid

from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class CostPeriod(str, Enum):
    """Cost tracking periods."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class AlertLevel(str, Enum):
    """Cost alert levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class CostBudget:
    """Budget configuration for cost control."""
    period: CostPeriod
    limit: float  # Dollar amount
    warning_threshold: float = 0.8  # 80% of limit
    critical_threshold: float = 0.95  # 95% of limit
    auto_suspend: bool = True  # Auto-suspend when limit reached
    rollover_unused: bool = False  # Rollover unused budget


@dataclass
class UsageRecord:
    """Record of LLM usage for cost tracking."""
    timestamp: datetime
    provider: str
    model: str
    operation: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    actual_cost: Optional[float] = None
    correlation_id: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None


@dataclass
class CostAlert:
    """Cost alert notification."""
    alert_id: str
    level: AlertLevel
    message: str
    current_usage: float
    budget_limit: float
    period: CostPeriod
    timestamp: datetime
    recommendations: List[str] = field(default_factory=list)


class AdvancedRateLimiter:
    """
    Advanced rate limiter with dynamic adjustment and cost awareness.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 60,
        tokens_per_minute: int = 90000,
        cost_per_minute: float = 10.0,
        adaptive: bool = True
    ):
        self.base_requests_per_minute = requests_per_minute
        self.base_tokens_per_minute = tokens_per_minute
        self.base_cost_per_minute = cost_per_minute
        self.adaptive = adaptive
        
        # Current limits (may be adjusted dynamically)
        self.current_requests_per_minute = requests_per_minute
        self.current_tokens_per_minute = tokens_per_minute
        self.current_cost_per_minute = cost_per_minute
        
        # Tracking windows
        self.request_times: List[float] = []
        self.token_usage: List[tuple[float, int]] = []
        self.cost_usage: List[tuple[float, float]] = []
        
        # Performance metrics
        self.success_rate = 1.0
        self.average_response_time = 1.0
        self.error_rate = 0.0
        
        self.logger = StructuredLogger("advanced_rate_limiter")
        self._lock = asyncio.Lock()
    
    async def acquire(
        self,
        estimated_tokens: int = 1000,
        estimated_cost: float = 0.01,
        priority: str = "normal"
    ) -> bool:
        """
        Acquire permission with advanced rate limiting.
        
        Args:
            estimated_tokens: Estimated tokens for the request
            estimated_cost: Estimated cost for the request
            priority: Request priority (low, normal, high, critical)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        async with self._lock:
            now = time.time()
            
            # Clean old entries
            self._cleanup_old_entries(now)
            
            # Adjust limits based on performance if adaptive
            if self.adaptive:
                self._adjust_limits_based_on_performance()
            
            # Check all rate limits
            if not self._check_request_limit():
                return False
            
            if not self._check_token_limit(estimated_tokens):
                return False
            
            if not self._check_cost_limit(estimated_cost):
                return False
            
            # Apply priority-based adjustments
            if priority == "critical":
                # Critical requests always pass if any capacity exists
                pass
            elif priority == "high":
                # High priority gets 2x weight
                if not self._check_priority_capacity(2.0):
                    return False
            elif priority == "low":
                # Low priority only if plenty of capacity
                if not self._check_priority_capacity(0.5):
                    return False
            
            # Record the request
            self.request_times.append(now)
            self.token_usage.append((now, estimated_tokens))
            self.cost_usage.append((now, estimated_cost))
            
            return True
    
    def _cleanup_old_entries(self, now: float) -> None:
        """Remove entries older than 1 minute."""
        cutoff = now - 60
        
        self.request_times = [t for t in self.request_times if t > cutoff]
        self.token_usage = [(t, tokens) for t, tokens in self.token_usage if t > cutoff]
        self.cost_usage = [(t, cost) for t, cost in self.cost_usage if t > cutoff]
    
    def _check_request_limit(self) -> bool:
        """Check request rate limit."""
        return len(self.request_times) < self.current_requests_per_minute
    
    def _check_token_limit(self, estimated_tokens: int) -> bool:
        """Check token rate limit."""
        current_tokens = sum(tokens for _, tokens in self.token_usage)
        return current_tokens + estimated_tokens <= self.current_tokens_per_minute
    
    def _check_cost_limit(self, estimated_cost: float) -> bool:
        """Check cost rate limit."""
        current_cost = sum(cost for _, cost in self.cost_usage)
        return current_cost + estimated_cost <= self.current_cost_per_minute
    
    def _check_priority_capacity(self, weight: float) -> bool:
        """Check if there's capacity for the given priority weight."""
        current_usage = len(self.request_times) / self.current_requests_per_minute
        required_capacity = weight * 0.1  # 10% capacity per weight unit
        
        return current_usage + required_capacity <= 1.0
    
    def _adjust_limits_based_on_performance(self) -> None:
        """Dynamically adjust limits based on performance metrics."""
        
        # Increase limits if performance is good
        if self.success_rate > 0.95 and self.error_rate < 0.05:
            adjustment_factor = 1.1
        # Decrease limits if performance is poor
        elif self.success_rate < 0.8 or self.error_rate > 0.2:
            adjustment_factor = 0.9
        else:
            adjustment_factor = 1.0
        
        # Apply adjustments with bounds
        self.current_requests_per_minute = min(
            self.base_requests_per_minute * 2,
            max(
                self.base_requests_per_minute * 0.5,
                int(self.current_requests_per_minute * adjustment_factor)
            )
        )
        
        self.current_tokens_per_minute = min(
            self.base_tokens_per_minute * 2,
            max(
                self.base_tokens_per_minute * 0.5,
                int(self.current_tokens_per_minute * adjustment_factor)
            )
        )
    
    def update_performance_metrics(
        self,
        success: bool,
        response_time: float,
        error_occurred: bool
    ) -> None:
        """Update performance metrics for adaptive adjustment."""
        
        # Update success rate (exponential moving average)
        self.success_rate = 0.9 * self.success_rate + 0.1 * (1.0 if success else 0.0)
        
        # Update response time (exponential moving average)
        self.average_response_time = 0.9 * self.average_response_time + 0.1 * response_time
        
        # Update error rate (exponential moving average)
        self.error_rate = 0.9 * self.error_rate + 0.1 * (1.0 if error_occurred else 0.0)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current rate limiter status."""
        now = time.time()
        self._cleanup_old_entries(now)
        
        current_tokens = sum(tokens for _, tokens in self.token_usage)
        current_cost = sum(cost for _, cost in self.cost_usage)
        
        return {
            "requests_this_minute": len(self.request_times),
            "requests_limit": self.current_requests_per_minute,
            "tokens_this_minute": current_tokens,
            "tokens_limit": self.current_tokens_per_minute,
            "cost_this_minute": current_cost,
            "cost_limit": self.current_cost_per_minute,
            "performance_metrics": {
                "success_rate": self.success_rate,
                "average_response_time": self.average_response_time,
                "error_rate": self.error_rate
            },
            "adaptive_enabled": self.adaptive
        }


class CostManager:
    """
    Comprehensive cost management system for LLM usage.
    """
    
    def __init__(self):
        self.logger = StructuredLogger("cost_manager")
        
        # Budget configuration
        self.budgets: Dict[str, CostBudget] = {}
        
        # Usage tracking
        self.usage_records: List[UsageRecord] = []
        self.current_usage: Dict[str, Dict[str, float]] = {}  # period -> {provider: cost}
        
        # Cost alerts
        self.alerts: List[CostAlert] = []
        self.alert_callbacks: List[Callable[[CostAlert], None]] = []
        
        # Provider pricing (per 1K tokens)
        self.provider_pricing = {
            "openai": {
                "gpt-4": {"input": 0.03, "output": 0.06},
                "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
            },
            "anthropic": {
                "claude-3-opus": {"input": 0.015, "output": 0.075},
                "claude-3-sonnet": {"input": 0.003, "output": 0.015}
            },
            "gemini": {
                "gemini-pro": {"input": 0.0005, "output": 0.0015},
                "gemini-pro-vision": {"input": 0.00025, "output": 0.00025}
            }
        }
        
        # Suspended providers due to budget limits
        self.suspended_providers: Dict[str, datetime] = {}
    
    def set_budget(self, budget_id: str, budget: CostBudget) -> None:
        """Set a cost budget."""
        self.budgets[budget_id] = budget
        
        self.logger.info(
            "Budget configured",
            budget_id=budget_id,
            period=budget.period.value,
            limit=budget.limit,
            auto_suspend=budget.auto_suspend
        )
    
    async def record_usage(
        self,
        provider: str,
        model: str,
        operation: str,
        prompt_tokens: int,
        completion_tokens: int,
        correlation_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> UsageRecord:
        """Record LLM usage for cost tracking."""
        
        # Calculate estimated cost
        estimated_cost = self._calculate_cost(provider, model, prompt_tokens, completion_tokens)
        
        # Create usage record
        record = UsageRecord(
            timestamp=datetime.now(timezone.utc),
            provider=provider,
            model=model,
            operation=operation,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            estimated_cost=estimated_cost,
            correlation_id=correlation_id,
            user_id=user_id,
            project_id=project_id
        )
        
        # Store record
        self.usage_records.append(record)
        
        # Update current usage
        await self._update_current_usage(record)
        
        # Check budgets
        await self._check_budgets(provider)
        
        self.logger.info(
            "Usage recorded",
            provider=provider,
            model=model,
            total_tokens=record.total_tokens,
            estimated_cost=estimated_cost,
            correlation_id=correlation_id
        )
        
        return record
    
    def _calculate_cost(
        self,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> float:
        """Calculate estimated cost for usage."""
        
        if provider not in self.provider_pricing:
            # Default pricing if provider not configured
            return (prompt_tokens + completion_tokens) * 0.001 / 1000
        
        provider_models = self.provider_pricing[provider]
        
        # Find matching model or use default
        model_pricing = None
        for model_name, pricing in provider_models.items():
            if model_name in model.lower():
                model_pricing = pricing
                break
        
        if not model_pricing:
            # Use first available model pricing as default
            model_pricing = next(iter(provider_models.values()))
        
        # Calculate cost
        input_cost = (prompt_tokens / 1000) * model_pricing["input"]
        output_cost = (completion_tokens / 1000) * model_pricing["output"]
        
        return input_cost + output_cost
    
    async def _update_current_usage(self, record: UsageRecord) -> None:
        """Update current usage tracking."""
        
        for period in CostPeriod:
            period_key = self._get_period_key(record.timestamp, period)
            
            if period_key not in self.current_usage:
                self.current_usage[period_key] = {}
            
            if record.provider not in self.current_usage[period_key]:
                self.current_usage[period_key][record.provider] = 0.0
            
            self.current_usage[period_key][record.provider] += record.estimated_cost
    
    def _get_period_key(self, timestamp: datetime, period: CostPeriod) -> str:
        """Get period key for usage tracking."""
        
        if period == CostPeriod.HOURLY:
            return f"{timestamp.strftime('%Y-%m-%d-%H')}-hourly"
        elif period == CostPeriod.DAILY:
            return f"{timestamp.strftime('%Y-%m-%d')}-daily"
        elif period == CostPeriod.WEEKLY:
            # Get week start (Monday)
            week_start = timestamp - timedelta(days=timestamp.weekday())
            return f"{week_start.strftime('%Y-%m-%d')}-weekly"
        elif period == CostPeriod.MONTHLY:
            return f"{timestamp.strftime('%Y-%m')}-monthly"
        
        return f"{timestamp.isoformat()}-unknown"
    
    async def _check_budgets(self, provider: str) -> None:
        """Check if any budgets are exceeded."""
        
        for budget_id, budget in self.budgets.items():
            current_period_key = self._get_period_key(datetime.now(timezone.utc), budget.period)
            
            if current_period_key not in self.current_usage:
                continue
            
            current_cost = self.current_usage[current_period_key].get(provider, 0.0)
            usage_percentage = current_cost / budget.limit
            
            # Check thresholds
            if usage_percentage >= 1.0:
                # Budget exceeded
                if budget.auto_suspend:
                    self.suspended_providers[provider] = datetime.now(timezone.utc)
                
                await self._create_alert(
                    AlertLevel.EMERGENCY,
                    f"Budget exceeded for {provider}",
                    current_cost,
                    budget.limit,
                    budget.period,
                    [
                        "Provider suspended due to budget limit",
                        "Review usage patterns",
                        "Consider increasing budget or optimizing usage"
                    ]
                )
            
            elif usage_percentage >= budget.critical_threshold:
                await self._create_alert(
                    AlertLevel.CRITICAL,
                    f"Critical budget threshold reached for {provider}",
                    current_cost,
                    budget.limit,
                    budget.period,
                    [
                        "Approaching budget limit",
                        "Monitor usage closely",
                        "Consider rate limiting"
                    ]
                )
            
            elif usage_percentage >= budget.warning_threshold:
                await self._create_alert(
                    AlertLevel.WARNING,
                    f"Budget warning threshold reached for {provider}",
                    current_cost,
                    budget.limit,
                    budget.period,
                    [
                        "Monitor usage",
                        "Review cost optimization opportunities"
                    ]
                )
    
    async def _create_alert(
        self,
        level: AlertLevel,
        message: str,
        current_usage: float,
        budget_limit: float,
        period: CostPeriod,
        recommendations: List[str]
    ) -> None:
        """Create and process a cost alert."""
        
        alert = CostAlert(
            alert_id=str(uuid.uuid4()),
            level=level,
            message=message,
            current_usage=current_usage,
            budget_limit=budget_limit,
            period=period,
            timestamp=datetime.now(timezone.utc),
            recommendations=recommendations
        )
        
        self.alerts.append(alert)
        
        # Log alert
        self.logger.warning(
            "Cost alert generated",
            alert_id=alert.alert_id,
            level=level.value,
            message=message,
            usage_percentage=current_usage / budget_limit * 100
        )
        
        # Notify callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
    
    def is_provider_suspended(self, provider: str) -> bool:
        """Check if a provider is suspended due to budget limits."""
        return provider in self.suspended_providers
    
    def get_usage_summary(self, period: CostPeriod) -> Dict[str, Any]:
        """Get usage summary for a period."""
        current_period_key = self._get_period_key(datetime.now(timezone.utc), period)
        
        usage = self.current_usage.get(current_period_key, {})
        total_cost = sum(usage.values())
        
        return {
            "period": period.value,
            "total_cost": total_cost,
            "provider_breakdown": usage,
            "suspended_providers": list(self.suspended_providers.keys())
        }
    
    def add_alert_callback(self, callback: Callable[[CostAlert], None]) -> None:
        """Add a callback for cost alerts."""
        self.alert_callbacks.append(callback)
