"""
Performance Validator

Validates system performance, resource usage, and execution efficiency.
"""

import psutil
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .base_validator import BaseValidator
from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationSeverity
from ..core.evidence_collector import EvidenceCollector


class PerformanceValidator(BaseValidator):
    """Validates performance metrics and resource usage."""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.performance_thresholds = {
            "cpu_usage": config.memory_threshold * 100,  # Convert to percentage
            "memory_usage": config.memory_threshold,
            "response_time": config.max_execution_time or 30.0,
            "throughput": 1.0,  # requests per second
            "error_rate": 0.05  # 5% error rate threshold
        }
        self.baseline_metrics: Optional[Dict[str, Any]] = None
    
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Validate performance metrics."""
        if not self.config.performance_monitoring:
            self.add_info("Performance monitoring disabled", "config_check")
            return
        
        # Collect current performance metrics
        current_metrics = await self._collect_performance_metrics(context)
        
        # Validate system resources
        await self._validate_system_resources(current_metrics, evidence_collector)
        
        # Validate execution performance
        await self._validate_execution_performance(context, current_metrics, evidence_collector)
        
        # Validate response times
        await self._validate_response_times(context, current_metrics, evidence_collector)
        
        # Validate throughput
        await self._validate_throughput(context, current_metrics, evidence_collector)
        
        # Validate against baseline if available
        if self.baseline_metrics:
            await self._validate_against_baseline(current_metrics, evidence_collector)
        
        # Store metrics as new baseline if none exists
        if not self.baseline_metrics:
            self.baseline_metrics = current_metrics
            self.add_info("Performance baseline established", "baseline_set")
    
    async def _collect_performance_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect comprehensive performance metrics."""
        metrics = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "system": await self._collect_system_metrics(),
            "process": await self._collect_process_metrics(),
            "task": await self._collect_task_metrics(context),
            "browser": await self._collect_browser_metrics(context)
        }
        
        return metrics
    
    async def _collect_system_metrics(self) -> Dict[str, Any]:
        """Collect system-level performance metrics."""
        try:
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_count": psutil.cpu_count(),
                "memory": {
                    "total": psutil.virtual_memory().total,
                    "available": psutil.virtual_memory().available,
                    "percent": psutil.virtual_memory().percent,
                    "used": psutil.virtual_memory().used
                },
                "disk": {
                    "total": psutil.disk_usage('/').total,
                    "used": psutil.disk_usage('/').used,
                    "free": psutil.disk_usage('/').free,
                    "percent": psutil.disk_usage('/').percent
                },
                "network": {
                    "bytes_sent": psutil.net_io_counters().bytes_sent,
                    "bytes_recv": psutil.net_io_counters().bytes_recv,
                    "packets_sent": psutil.net_io_counters().packets_sent,
                    "packets_recv": psutil.net_io_counters().packets_recv
                },
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            self.add_warning(
                f"Failed to collect system metrics: {str(e)}",
                "system_metrics_failed",
                {"error": str(e)}
            )
            return {}
    
    async def _collect_process_metrics(self) -> Dict[str, Any]:
        """Collect current process performance metrics."""
        try:
            process = psutil.Process()
            return {
                "pid": process.pid,
                "cpu_percent": process.cpu_percent(),
                "memory_info": {
                    "rss": process.memory_info().rss,
                    "vms": process.memory_info().vms,
                    "percent": process.memory_percent()
                },
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None,
                "create_time": process.create_time(),
                "status": process.status()
            }
        except Exception as e:
            self.add_warning(
                f"Failed to collect process metrics: {str(e)}",
                "process_metrics_failed",
                {"error": str(e)}
            )
            return {}
    
    async def _collect_task_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect task-specific performance metrics."""
        task_result = context.get("task_result", {})
        
        return {
            "execution_time": task_result.get("execution_time", 0),
            "step_count": len(task_result.get("steps", [])),
            "error_count": len(task_result.get("errors", [])),
            "retry_count": task_result.get("retry_count", 0),
            "data_size": len(str(task_result.get("extracted_data", "")))
        }
    
    async def _collect_browser_metrics(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Collect browser-specific performance metrics."""
        browser_state = context.get("browser_state", {})
        
        return {
            "active_sessions": browser_state.get("active_sessions", 0),
            "total_requests": browser_state.get("total_requests", 0),
            "failed_requests": browser_state.get("failed_requests", 0),
            "average_response_time": browser_state.get("average_response_time", 0),
            "memory_usage": browser_state.get("memory_usage", 0),
            "page_load_time": browser_state.get("page_load_time", 0)
        }
    
    async def _validate_system_resources(self, metrics: Dict[str, Any], 
                                       evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate system resource usage."""
        system_metrics = metrics.get("system", {})
        
        # Validate CPU usage
        cpu_percent = system_metrics.get("cpu_percent", 0)
        cpu_threshold = self.performance_thresholds["cpu_usage"]
        
        if cpu_percent > cpu_threshold:
            self.add_warning(
                f"High CPU usage: {cpu_percent:.1f}% > {cpu_threshold:.1f}%",
                "high_cpu_usage",
                {"cpu_percent": cpu_percent, "threshold": cpu_threshold},
                "Consider optimizing CPU-intensive operations"
            )
        
        # Validate memory usage
        memory_info = system_metrics.get("memory", {})
        memory_percent = memory_info.get("percent", 0)
        memory_threshold = self.performance_thresholds["memory_usage"] * 100
        
        if memory_percent > memory_threshold:
            self.add_error(
                f"High memory usage: {memory_percent:.1f}% > {memory_threshold:.1f}%",
                "high_memory_usage",
                {
                    "memory_percent": memory_percent,
                    "threshold": memory_threshold,
                    "available_gb": memory_info.get("available", 0) / (1024**3)
                },
                "Free up memory or increase system resources"
            )
        
        # Validate disk usage
        disk_info = system_metrics.get("disk", {})
        disk_percent = disk_info.get("percent", 0)
        
        if disk_percent > 90:
            self.add_error(
                f"High disk usage: {disk_percent:.1f}% > 90%",
                "high_disk_usage",
                {
                    "disk_percent": disk_percent,
                    "free_gb": disk_info.get("free", 0) / (1024**3)
                },
                "Free up disk space to prevent system issues"
            )
        elif disk_percent > 80:
            self.add_warning(
                f"Moderate disk usage: {disk_percent:.1f}% > 80%",
                "moderate_disk_usage",
                {"disk_percent": disk_percent},
                "Monitor disk usage and plan for cleanup"
            )
        
        # Collect resource evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "system_resources",
                system_metrics,
                "system_resources.json"
            )
    
    async def _validate_execution_performance(self, context: Dict[str, Any], 
                                            metrics: Dict[str, Any],
                                            evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate task execution performance."""
        task_metrics = metrics.get("task", {})
        execution_time = task_metrics.get("execution_time", 0)
        
        # Validate execution time
        max_execution_time = self.performance_thresholds["response_time"]
        
        if execution_time > max_execution_time:
            self.add_warning(
                f"Slow execution time: {execution_time:.2f}s > {max_execution_time:.2f}s",
                "slow_execution",
                {
                    "execution_time": execution_time,
                    "threshold": max_execution_time,
                    "step_count": task_metrics.get("step_count", 0)
                },
                "Optimize task execution or increase time limits"
            )
        
        # Validate error rate
        step_count = task_metrics.get("step_count", 1)
        error_count = task_metrics.get("error_count", 0)
        error_rate = error_count / step_count if step_count > 0 else 0
        error_threshold = self.performance_thresholds["error_rate"]
        
        if error_rate > error_threshold:
            self.add_error(
                f"High error rate: {error_rate:.2%} > {error_threshold:.2%}",
                "high_error_rate",
                {
                    "error_rate": error_rate,
                    "error_count": error_count,
                    "step_count": step_count,
                    "threshold": error_threshold
                },
                "Investigate and fix sources of errors"
            )
        
        # Validate retry efficiency
        retry_count = task_metrics.get("retry_count", 0)
        if retry_count > step_count:
            self.add_warning(
                f"Excessive retries: {retry_count} retries for {step_count} steps",
                "excessive_retries",
                {"retry_count": retry_count, "step_count": step_count},
                "Review retry logic and error handling"
            )
    
    async def _validate_response_times(self, context: Dict[str, Any], 
                                     metrics: Dict[str, Any],
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate response times and latency."""
        browser_metrics = metrics.get("browser", {})
        
        # Validate average response time
        avg_response_time = browser_metrics.get("average_response_time", 0)
        if avg_response_time > 5.0:  # 5 second threshold
            self.add_warning(
                f"Slow average response time: {avg_response_time:.2f}s > 5.0s",
                "slow_response_time",
                {"average_response_time": avg_response_time},
                "Check network connectivity and server performance"
            )
        
        # Validate page load time
        page_load_time = browser_metrics.get("page_load_time", 0)
        if page_load_time > 10.0:  # 10 second threshold
            self.add_warning(
                f"Slow page load time: {page_load_time:.2f}s > 10.0s",
                "slow_page_load",
                {"page_load_time": page_load_time},
                "Optimize page loading or check network conditions"
            )
    
    async def _validate_throughput(self, context: Dict[str, Any], 
                                 metrics: Dict[str, Any],
                                 evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate system throughput."""
        task_metrics = metrics.get("task", {})
        execution_time = task_metrics.get("execution_time", 1)
        step_count = task_metrics.get("step_count", 0)
        
        # Calculate throughput (steps per second)
        throughput = step_count / execution_time if execution_time > 0 else 0
        min_throughput = self.performance_thresholds["throughput"]
        
        if throughput < min_throughput and step_count > 0:
            self.add_warning(
                f"Low throughput: {throughput:.2f} steps/sec < {min_throughput:.2f} steps/sec",
                "low_throughput",
                {
                    "throughput": throughput,
                    "threshold": min_throughput,
                    "step_count": step_count,
                    "execution_time": execution_time
                },
                "Optimize step execution for better throughput"
            )
        elif throughput > 0:
            self.add_info(
                f"Throughput acceptable: {throughput:.2f} steps/sec",
                "throughput_ok",
                {"throughput": throughput}
            )
    
    async def _validate_against_baseline(self, current_metrics: Dict[str, Any], 
                                       evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate current metrics against baseline."""
        if not self.baseline_metrics:
            return
        
        # Compare execution time
        current_exec_time = current_metrics.get("task", {}).get("execution_time", 0)
        baseline_exec_time = self.baseline_metrics.get("task", {}).get("execution_time", 0)
        
        if baseline_exec_time > 0:
            time_ratio = current_exec_time / baseline_exec_time
            
            if time_ratio > 2.0:  # 100% slower
                self.add_warning(
                    f"Execution time degraded: {time_ratio:.1f}x slower than baseline",
                    "performance_degradation",
                    {
                        "current_time": current_exec_time,
                        "baseline_time": baseline_exec_time,
                        "ratio": time_ratio
                    },
                    "Investigate performance regression"
                )
            elif time_ratio < 0.5:  # 50% faster
                self.add_info(
                    f"Execution time improved: {1/time_ratio:.1f}x faster than baseline",
                    "performance_improvement",
                    {
                        "current_time": current_exec_time,
                        "baseline_time": baseline_exec_time,
                        "ratio": time_ratio
                    }
                )
        
        # Compare memory usage
        current_memory = current_metrics.get("system", {}).get("memory", {}).get("percent", 0)
        baseline_memory = self.baseline_metrics.get("system", {}).get("memory", {}).get("percent", 0)
        
        if baseline_memory > 0:
            memory_diff = current_memory - baseline_memory
            
            if memory_diff > 20:  # 20% increase
                self.add_warning(
                    f"Memory usage increased: +{memory_diff:.1f}% from baseline",
                    "memory_increase",
                    {
                        "current_memory": current_memory,
                        "baseline_memory": baseline_memory,
                        "difference": memory_diff
                    },
                    "Monitor for memory leaks"
                )
        
        # Collect baseline comparison evidence
        if evidence_collector:
            comparison_data = {
                "current_metrics": current_metrics,
                "baseline_metrics": self.baseline_metrics,
                "comparison_timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            await self.collect_evidence(
                evidence_collector,
                "baseline_comparison",
                comparison_data,
                "baseline_comparison.json"
            )
    
    def update_baseline(self, metrics: Dict[str, Any]) -> None:
        """Update performance baseline with new metrics."""
        self.baseline_metrics = metrics
        self.add_info("Performance baseline updated", "baseline_updated")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance validation summary."""
        return {
            "thresholds": self.performance_thresholds,
            "has_baseline": self.baseline_metrics is not None,
            "validation_rules": self.get_validation_rules()
        }
    
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        return [
            "high_cpu_usage",
            "high_memory_usage",
            "high_disk_usage",
            "moderate_disk_usage",
            "slow_execution",
            "high_error_rate",
            "excessive_retries",
            "slow_response_time",
            "slow_page_load",
            "low_throughput",
            "throughput_ok",
            "performance_degradation",
            "performance_improvement",
            "memory_increase",
            "baseline_set",
            "baseline_updated",
            "system_metrics_failed",
            "process_metrics_failed"
        ]
