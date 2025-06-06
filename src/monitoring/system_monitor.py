"""
Comprehensive system monitoring for browser automation platform.

This module provides real-time monitoring of all system components including
browser resources, LLM usage, costs, and performance metrics.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from src.infrastructure.logging.logger import StructuredLogger
from src.execution.browser_manager import EnhancedBrowserManager
from src.execution.llm_provider import TaskLLMProvider
from src.infrastructure.cost_management import CostManager
from src.execution.enhanced_error_recovery import EnhancedErrorRecovery


class HealthStatus(str, Enum):
    """System health status levels."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DOWN = "down"


@dataclass
class SystemMetrics:
    """System-wide metrics snapshot."""
    timestamp: datetime
    overall_health: HealthStatus
    browser_metrics: Dict[str, Any]
    llm_metrics: Dict[str, Any]
    cost_metrics: Dict[str, Any]
    error_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]


class SystemMonitor:
    """
    Comprehensive system monitor for the browser automation platform.
    
    Provides real-time monitoring, alerting, and health checks for all
    system components with performance optimization recommendations.
    """
    
    def __init__(
        self,
        browser_manager: Optional[EnhancedBrowserManager] = None,
        llm_provider: Optional[TaskLLMProvider] = None,
        cost_manager: Optional[CostManager] = None,
        error_recovery: Optional[EnhancedErrorRecovery] = None,
        monitoring_interval: int = 30,  # seconds
        alert_thresholds: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the system monitor.
        
        Args:
            browser_manager: Browser manager instance to monitor
            llm_provider: LLM provider instance to monitor
            cost_manager: Cost manager instance to monitor
            error_recovery: Error recovery system to monitor
            monitoring_interval: How often to collect metrics (seconds)
            alert_thresholds: Custom alert thresholds
        """
        self.browser_manager = browser_manager
        self.llm_provider = llm_provider
        self.cost_manager = cost_manager
        self.error_recovery = error_recovery
        self.monitoring_interval = monitoring_interval
        
        # Alert thresholds
        self.alert_thresholds = alert_thresholds or {
            "memory_usage": 0.85,      # 85% memory usage
            "error_rate": 0.1,         # 10% error rate
            "response_time": 10.0,     # 10 seconds response time
            "cost_budget": 0.9,        # 90% of budget used
            "browser_sessions": 50     # Maximum browser sessions
        }
        
        # Monitoring state
        self.monitoring_task: Optional[asyncio.Task] = None
        self.is_monitoring = False
        self.metrics_history: List[SystemMetrics] = []
        self.alert_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
        
        # Performance tracking
        self.performance_baseline: Dict[str, float] = {}
        self.performance_trends: Dict[str, List[float]] = {}
        
        self.logger = StructuredLogger("system_monitor")
    
    async def start_monitoring(self) -> None:
        """Start continuous system monitoring."""
        if self.is_monitoring:
            self.logger.warning("Monitoring already started")
            return
        
        self.is_monitoring = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        self.logger.info(
            "System monitoring started",
            interval=self.monitoring_interval,
            thresholds=self.alert_thresholds
        )
    
    async def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        self.is_monitoring = False
        
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("System monitoring stopped")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Collect metrics
                metrics = await self.collect_metrics()
                
                # Store metrics
                self.metrics_history.append(metrics)
                
                # Keep only recent metrics (last 24 hours)
                cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m.timestamp > cutoff
                ]
                
                # Check for alerts
                await self._check_alerts(metrics)
                
                # Update performance trends
                self._update_performance_trends(metrics)
                
                # Log summary
                self.logger.info(
                    "System metrics collected",
                    overall_health=metrics.overall_health.value,
                    active_browsers=metrics.browser_metrics.get("active_sessions", 0),
                    llm_requests=metrics.llm_metrics.get("request_count", 0),
                    total_cost=metrics.cost_metrics.get("total_cost", 0.0)
                )
                
                await asyncio.sleep(self.monitoring_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitoring loop error: {e}")
                await asyncio.sleep(self.monitoring_interval)
    
    async def collect_metrics(self) -> SystemMetrics:
        """Collect comprehensive system metrics."""
        timestamp = datetime.now(timezone.utc)
        
        # Collect browser metrics
        browser_metrics = {}
        if self.browser_manager:
            try:
                browser_metrics = self.browser_manager.get_resource_stats()
            except Exception as e:
                browser_metrics = {"error": str(e)}
        
        # Collect LLM metrics
        llm_metrics = {}
        if self.llm_provider:
            try:
                llm_metrics = self.llm_provider.get_statistics()
            except Exception as e:
                llm_metrics = {"error": str(e)}
        
        # Collect cost metrics
        cost_metrics = {}
        if self.cost_manager:
            try:
                cost_metrics = {
                    "daily": self.cost_manager.get_usage_summary("daily"),
                    "monthly": self.cost_manager.get_usage_summary("monthly"),
                    "alerts": len(self.cost_manager.alerts)
                }
            except Exception as e:
                cost_metrics = {"error": str(e)}
        
        # Collect error metrics
        error_metrics = {}
        if self.error_recovery:
            try:
                error_metrics = self.error_recovery.get_recovery_statistics()
            except Exception as e:
                error_metrics = {"error": str(e)}
        
        # Collect performance metrics
        performance_metrics = await self._collect_performance_metrics()
        
        # Determine overall health
        overall_health = self._assess_overall_health(
            browser_metrics, llm_metrics, cost_metrics, error_metrics, performance_metrics
        )
        
        return SystemMetrics(
            timestamp=timestamp,
            overall_health=overall_health,
            browser_metrics=browser_metrics,
            llm_metrics=llm_metrics,
            cost_metrics=cost_metrics,
            error_metrics=error_metrics,
            performance_metrics=performance_metrics
        )
    
    async def _collect_performance_metrics(self) -> Dict[str, Any]:
        """Collect system performance metrics."""
        try:
            import psutil
            
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Network I/O
            network = psutil.net_io_counters()
            
            # Process count
            process_count = len(psutil.pids())
            
            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_percent": disk.percent,
                "disk_free_gb": disk.free / (1024**3),
                "network_bytes_sent": network.bytes_sent,
                "network_bytes_recv": network.bytes_recv,
                "process_count": process_count,
                "timestamp": time.time()
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _assess_overall_health(
        self,
        browser_metrics: Dict[str, Any],
        llm_metrics: Dict[str, Any],
        cost_metrics: Dict[str, Any],
        error_metrics: Dict[str, Any],
        performance_metrics: Dict[str, Any]
    ) -> HealthStatus:
        """Assess overall system health based on all metrics."""
        
        # Check for critical issues
        if performance_metrics.get("memory_percent", 0) > 95:
            return HealthStatus.CRITICAL
        
        if browser_metrics.get("error") or llm_metrics.get("error"):
            return HealthStatus.CRITICAL
        
        # Check for warnings
        warning_conditions = [
            performance_metrics.get("memory_percent", 0) > self.alert_thresholds["memory_usage"] * 100,
            llm_metrics.get("basic_stats", {}).get("error_rate", 0) > self.alert_thresholds["error_rate"],
            browser_metrics.get("sessions", {}).get("active_count", 0) > self.alert_thresholds["browser_sessions"]
        ]
        
        if any(warning_conditions):
            return HealthStatus.WARNING
        
        return HealthStatus.HEALTHY
    
    async def _check_alerts(self, metrics: SystemMetrics) -> None:
        """Check metrics against alert thresholds."""
        alerts = []
        
        # Memory usage alert
        memory_percent = metrics.performance_metrics.get("memory_percent", 0) / 100
        if memory_percent > self.alert_thresholds["memory_usage"]:
            alerts.append({
                "type": "memory_usage",
                "severity": "critical" if memory_percent > 0.95 else "warning",
                "message": f"High memory usage: {memory_percent:.1%}",
                "current_value": memory_percent,
                "threshold": self.alert_thresholds["memory_usage"]
            })
        
        # Error rate alert
        error_rate = metrics.llm_metrics.get("basic_stats", {}).get("error_rate", 0)
        if error_rate > self.alert_thresholds["error_rate"]:
            alerts.append({
                "type": "error_rate",
                "severity": "warning",
                "message": f"High error rate: {error_rate:.1%}",
                "current_value": error_rate,
                "threshold": self.alert_thresholds["error_rate"]
            })
        
        # Browser sessions alert
        active_sessions = metrics.browser_metrics.get("sessions", {}).get("active_count", 0)
        if active_sessions > self.alert_thresholds["browser_sessions"]:
            alerts.append({
                "type": "browser_sessions",
                "severity": "warning",
                "message": f"High number of browser sessions: {active_sessions}",
                "current_value": active_sessions,
                "threshold": self.alert_thresholds["browser_sessions"]
            })
        
        # Send alerts
        for alert in alerts:
            await self._send_alert(alert["type"], alert)
    
    async def _send_alert(self, alert_type: str, alert_data: Dict[str, Any]) -> None:
        """Send alert to registered callbacks."""
        for callback in self.alert_callbacks:
            try:
                callback(alert_type, alert_data)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")
        
        # Log alert
        self.logger.warning(
            "System alert triggered",
            alert_type=alert_type,
            severity=alert_data.get("severity"),
            message=alert_data.get("message")
        )
    
    def _update_performance_trends(self, metrics: SystemMetrics) -> None:
        """Update performance trend tracking."""
        trends = {
            "memory_percent": metrics.performance_metrics.get("memory_percent", 0),
            "cpu_percent": metrics.performance_metrics.get("cpu_percent", 0),
            "error_rate": metrics.llm_metrics.get("basic_stats", {}).get("error_rate", 0),
            "response_time": metrics.llm_metrics.get("basic_stats", {}).get("average_response_time", 0)
        }
        
        for metric, value in trends.items():
            if metric not in self.performance_trends:
                self.performance_trends[metric] = []
            
            self.performance_trends[metric].append(value)
            
            # Keep only recent values (last 100 measurements)
            if len(self.performance_trends[metric]) > 100:
                self.performance_trends[metric] = self.performance_trends[metric][-100:]
    
    def add_alert_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add a callback for system alerts."""
        self.alert_callbacks.append(callback)
    
    def get_health_summary(self) -> Dict[str, Any]:
        """Get current system health summary."""
        if not self.metrics_history:
            return {"status": "no_data"}
        
        latest_metrics = self.metrics_history[-1]
        
        return {
            "overall_health": latest_metrics.overall_health.value,
            "timestamp": latest_metrics.timestamp.isoformat(),
            "components": {
                "browser_manager": "healthy" if not latest_metrics.browser_metrics.get("error") else "error",
                "llm_provider": "healthy" if not latest_metrics.llm_metrics.get("error") else "error",
                "cost_manager": "healthy" if not latest_metrics.cost_metrics.get("error") else "error"
            },
            "key_metrics": {
                "memory_usage": f"{latest_metrics.performance_metrics.get('memory_percent', 0):.1f}%",
                "active_browsers": latest_metrics.browser_metrics.get("sessions", {}).get("active_count", 0),
                "error_rate": f"{latest_metrics.llm_metrics.get('basic_stats', {}).get('error_rate', 0):.1%}",
                "daily_cost": latest_metrics.cost_metrics.get("daily", {}).get("total_cost", 0.0)
            }
        }
    
    def get_performance_trends(self) -> Dict[str, Any]:
        """Get performance trend analysis."""
        if not self.performance_trends:
            return {"status": "no_data"}
        
        trends = {}
        for metric, values in self.performance_trends.items():
            if len(values) < 2:
                continue
            
            # Calculate trend (simple linear regression slope)
            n = len(values)
            x_sum = sum(range(n))
            y_sum = sum(values)
            xy_sum = sum(i * values[i] for i in range(n))
            x2_sum = sum(i * i for i in range(n))
            
            slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
            
            trends[metric] = {
                "current": values[-1],
                "average": sum(values) / len(values),
                "trend": "increasing" if slope > 0.01 else "decreasing" if slope < -0.01 else "stable",
                "slope": slope
            }
        
        return trends
