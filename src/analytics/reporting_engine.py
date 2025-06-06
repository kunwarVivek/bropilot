"""
Advanced analytics and reporting system.

This module provides comprehensive analytics, metrics collection, and
reporting capabilities for browser automation workflows.
"""

import asyncio
import json
import statistics
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import uuid
from collections import defaultdict, Counter

from core.exceptions import AnalyticsError, ValidationError
from src.infrastructure.logging.logger import StructuredLogger, with_correlation_id


class MetricType(str, Enum):
    """Metric type enumeration."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    RATE = "rate"


class ReportType(str, Enum):
    """Report type enumeration."""
    EXECUTION_SUMMARY = "execution_summary"
    PERFORMANCE_ANALYSIS = "performance_analysis"
    ERROR_ANALYSIS = "error_analysis"
    RESOURCE_UTILIZATION = "resource_utilization"
    TREND_ANALYSIS = "trend_analysis"
    CUSTOM = "custom"


class AggregationType(str, Enum):
    """Aggregation type enumeration."""
    SUM = "sum"
    AVERAGE = "average"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    PERCENTILE = "percentile"
    RATE = "rate"


@dataclass
class Metric:
    """Represents a metric data point."""
    metric_id: str
    name: str
    metric_type: MetricType
    value: Union[int, float]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportConfig:
    """Configuration for report generation."""
    report_type: ReportType
    time_range: Tuple[datetime, datetime]
    filters: Dict[str, Any] = field(default_factory=dict)
    aggregations: List[AggregationType] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)
    include_charts: bool = True
    format: str = "json"  # json, html, pdf, csv


@dataclass
class AnalyticsInsight:
    """Represents an analytics insight."""
    insight_id: str
    title: str
    description: str
    insight_type: str
    confidence: float
    impact: str  # low, medium, high
    recommendations: List[str]
    supporting_data: Dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)


class MetricsCollector:
    """Collects and stores metrics from various sources."""
    
    def __init__(self):
        """Initialize metrics collector."""
        self.logger = StructuredLogger("metrics_collector")
        
        # Metric storage
        self.metrics: List[Metric] = []
        self.metric_index: Dict[str, List[int]] = defaultdict(list)  # name -> indices
        
        # Real-time aggregations
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        self.timers: Dict[str, List[float]] = defaultdict(list)
        
        # Configuration
        self.retention_period = timedelta(days=30)
        self.max_metrics = 1000000  # 1M metrics max
    
    def record_metric(
        self,
        name: str,
        value: Union[int, float],
        metric_type: MetricType,
        tags: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record a metric."""
        
        metric_id = str(uuid.uuid4())
        
        metric = Metric(
            metric_id=metric_id,
            name=name,
            metric_type=metric_type,
            value=value,
            tags=tags or {},
            metadata=metadata or {}
        )
        
        # Store metric
        index = len(self.metrics)
        self.metrics.append(metric)
        self.metric_index[name].append(index)
        
        # Update real-time aggregations
        self._update_aggregations(metric)
        
        # Cleanup old metrics if needed
        if len(self.metrics) > self.max_metrics:
            self._cleanup_old_metrics()
        
        self.logger.debug(
            "Metric recorded",
            metric_id=metric_id,
            name=name,
            value=value,
            metric_type=metric_type.value
        )
        
        return metric_id
    
    def _update_aggregations(self, metric: Metric) -> None:
        """Update real-time aggregations."""
        
        if metric.metric_type == MetricType.COUNTER:
            self.counters[metric.name] += metric.value
        
        elif metric.metric_type == MetricType.GAUGE:
            self.gauges[metric.name] = metric.value
        
        elif metric.metric_type == MetricType.HISTOGRAM:
            self.histograms[metric.name].append(metric.value)
            # Keep only recent values
            if len(self.histograms[metric.name]) > 1000:
                self.histograms[metric.name] = self.histograms[metric.name][-500:]
        
        elif metric.metric_type == MetricType.TIMER:
            self.timers[metric.name].append(metric.value)
            # Keep only recent values
            if len(self.timers[metric.name]) > 1000:
                self.timers[metric.name] = self.timers[metric.name][-500:]
    
    def _cleanup_old_metrics(self) -> None:
        """Clean up old metrics to maintain performance."""
        
        cutoff_time = datetime.utcnow() - self.retention_period
        
        # Find metrics to keep
        metrics_to_keep = []
        new_index = defaultdict(list)
        
        for i, metric in enumerate(self.metrics):
            if metric.timestamp >= cutoff_time:
                new_index[metric.name].append(len(metrics_to_keep))
                metrics_to_keep.append(metric)
        
        # Update storage
        removed_count = len(self.metrics) - len(metrics_to_keep)
        self.metrics = metrics_to_keep
        self.metric_index = new_index
        
        self.logger.info(
            "Cleaned up old metrics",
            removed_count=removed_count,
            remaining_count=len(self.metrics)
        )
    
    def get_metrics(
        self,
        name: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> List[Metric]:
        """Get metrics based on filters."""
        
        if name:
            # Use index for faster lookup
            indices = self.metric_index.get(name, [])
            metrics = [self.metrics[i] for i in indices if i < len(self.metrics)]
        else:
            metrics = self.metrics.copy()
        
        # Apply time range filter
        if time_range:
            start_time, end_time = time_range
            metrics = [
                m for m in metrics
                if start_time <= m.timestamp <= end_time
            ]
        
        # Apply tag filters
        if tags:
            metrics = [
                m for m in metrics
                if all(m.tags.get(k) == v for k, v in tags.items())
            ]
        
        return metrics
    
    def get_aggregated_value(
        self,
        name: str,
        aggregation: AggregationType,
        time_range: Optional[Tuple[datetime, datetime]] = None,
        percentile: float = 95.0
    ) -> Optional[float]:
        """Get aggregated metric value."""
        
        metrics = self.get_metrics(name, time_range)
        
        if not metrics:
            return None
        
        values = [m.value for m in metrics]
        
        if aggregation == AggregationType.SUM:
            return sum(values)
        elif aggregation == AggregationType.AVERAGE:
            return statistics.mean(values)
        elif aggregation == AggregationType.MIN:
            return min(values)
        elif aggregation == AggregationType.MAX:
            return max(values)
        elif aggregation == AggregationType.COUNT:
            return len(values)
        elif aggregation == AggregationType.PERCENTILE:
            return statistics.quantiles(values, n=100)[int(percentile) - 1] if len(values) > 1 else values[0]
        elif aggregation == AggregationType.RATE:
            if time_range:
                duration = (time_range[1] - time_range[0]).total_seconds()
                return len(values) / duration if duration > 0 else 0
            return 0
        
        return None


class ReportGenerator:
    """Generates comprehensive reports from collected metrics."""
    
    def __init__(self, metrics_collector: MetricsCollector):
        """Initialize report generator."""
        self.metrics_collector = metrics_collector
        self.logger = StructuredLogger("report_generator")
        
        # Report templates
        self.report_templates: Dict[ReportType, Dict[str, Any]] = {
            ReportType.EXECUTION_SUMMARY: {
                "metrics": ["workflow_executions", "task_executions", "success_rate", "failure_rate"],
                "aggregations": [AggregationType.COUNT, AggregationType.AVERAGE],
                "charts": ["execution_timeline", "success_rate_trend"]
            },
            ReportType.PERFORMANCE_ANALYSIS: {
                "metrics": ["execution_time", "response_time", "throughput"],
                "aggregations": [AggregationType.AVERAGE, AggregationType.PERCENTILE],
                "charts": ["performance_distribution", "response_time_trend"]
            },
            ReportType.ERROR_ANALYSIS: {
                "metrics": ["error_count", "error_rate", "recovery_success"],
                "aggregations": [AggregationType.COUNT, AggregationType.RATE],
                "charts": ["error_distribution", "error_trend"]
            },
            ReportType.RESOURCE_UTILIZATION: {
                "metrics": ["cpu_usage", "memory_usage", "browser_count"],
                "aggregations": [AggregationType.AVERAGE, AggregationType.MAX],
                "charts": ["resource_timeline", "utilization_distribution"]
            }
        }
    
    async def generate_report(self, config: ReportConfig) -> Dict[str, Any]:
        """Generate a comprehensive report."""
        
        self.logger.info(
            "Generating report",
            report_type=config.report_type.value,
            time_range=f"{config.time_range[0]} to {config.time_range[1]}",
            format=config.format
        )
        
        try:
            # Get report template
            template = self.report_templates.get(config.report_type, {})
            
            # Collect data
            report_data = await self._collect_report_data(config, template)
            
            # Generate insights
            insights = await self._generate_insights(report_data, config)
            
            # Create report structure
            report = {
                "report_id": str(uuid.uuid4()),
                "report_type": config.report_type.value,
                "generated_at": datetime.utcnow().isoformat(),
                "time_range": {
                    "start": config.time_range[0].isoformat(),
                    "end": config.time_range[1].isoformat()
                },
                "config": {
                    "filters": config.filters,
                    "aggregations": [a.value for a in config.aggregations],
                    "group_by": config.group_by
                },
                "data": report_data,
                "insights": [insight.__dict__ for insight in insights],
                "summary": self._generate_summary(report_data),
                "metadata": {
                    "total_metrics": len(self.metrics_collector.metrics),
                    "data_points_analyzed": sum(len(section.get("data", [])) for section in report_data.values())
                }
            }
            
            # Add charts if requested
            if config.include_charts:
                report["charts"] = await self._generate_charts(report_data, template)
            
            self.logger.info(
                "Report generated successfully",
                report_id=report["report_id"],
                insights_count=len(insights)
            )
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Report generation failed",
                report_type=config.report_type.value,
                error=str(e)
            )
            raise AnalyticsError(f"Report generation failed: {e}") from e
    
    async def _collect_report_data(
        self,
        config: ReportConfig,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Collect data for the report."""
        
        data = {}
        
        # Get metrics from template or config
        metrics_to_analyze = template.get("metrics", [])
        aggregations = config.aggregations or template.get("aggregations", [AggregationType.AVERAGE])
        
        for metric_name in metrics_to_analyze:
            metric_data = {
                "name": metric_name,
                "aggregations": {},
                "data": []
            }
            
            # Get raw metrics
            metrics = self.metrics_collector.get_metrics(
                name=metric_name,
                time_range=config.time_range
            )
            
            # Apply filters
            if config.filters:
                metrics = self._apply_filters(metrics, config.filters)
            
            # Calculate aggregations
            for agg_type in aggregations:
                value = self.metrics_collector.get_aggregated_value(
                    metric_name, agg_type, config.time_range
                )
                metric_data["aggregations"][agg_type.value] = value
            
            # Group data if requested
            if config.group_by:
                grouped_data = self._group_metrics(metrics, config.group_by)
                metric_data["grouped_data"] = grouped_data
            
            # Store raw data for charts
            metric_data["data"] = [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "value": m.value,
                    "tags": m.tags
                }
                for m in metrics[-1000:]  # Limit to recent 1000 points
            ]
            
            data[metric_name] = metric_data
        
        return data
    
    def _apply_filters(self, metrics: List[Metric], filters: Dict[str, Any]) -> List[Metric]:
        """Apply filters to metrics."""
        
        filtered_metrics = metrics
        
        for filter_key, filter_value in filters.items():
            if filter_key == "tags":
                filtered_metrics = [
                    m for m in filtered_metrics
                    if all(m.tags.get(k) == v for k, v in filter_value.items())
                ]
            elif filter_key == "min_value":
                filtered_metrics = [
                    m for m in filtered_metrics
                    if m.value >= filter_value
                ]
            elif filter_key == "max_value":
                filtered_metrics = [
                    m for m in filtered_metrics
                    if m.value <= filter_value
                ]
        
        return filtered_metrics
    
    def _group_metrics(self, metrics: List[Metric], group_by: List[str]) -> Dict[str, List[Metric]]:
        """Group metrics by specified fields."""
        
        grouped = defaultdict(list)
        
        for metric in metrics:
            # Create group key
            group_key_parts = []
            for field in group_by:
                if field in metric.tags:
                    group_key_parts.append(f"{field}:{metric.tags[field]}")
                elif field == "hour":
                    group_key_parts.append(f"hour:{metric.timestamp.hour}")
                elif field == "day":
                    group_key_parts.append(f"day:{metric.timestamp.date()}")
            
            group_key = "|".join(group_key_parts) if group_key_parts else "default"
            grouped[group_key].append(metric)
        
        return dict(grouped)
    
    async def _generate_insights(
        self,
        report_data: Dict[str, Any],
        config: ReportConfig
    ) -> List[AnalyticsInsight]:
        """Generate insights from report data."""
        
        insights = []
        
        # Performance insights
        if "execution_time" in report_data:
            execution_data = report_data["execution_time"]
            avg_time = execution_data["aggregations"].get("average", 0)
            
            if avg_time > 30:  # 30 seconds threshold
                insights.append(AnalyticsInsight(
                    insight_id=str(uuid.uuid4()),
                    title="High Average Execution Time",
                    description=f"Average execution time is {avg_time:.2f} seconds, which is above the recommended threshold.",
                    insight_type="performance",
                    confidence=0.9,
                    impact="high",
                    recommendations=[
                        "Optimize task execution logic",
                        "Review resource allocation",
                        "Consider parallel execution"
                    ],
                    supporting_data={"average_time": avg_time, "threshold": 30}
                ))
        
        # Error rate insights
        if "error_rate" in report_data:
            error_data = report_data["error_rate"]
            error_rate = error_data["aggregations"].get("average", 0)
            
            if error_rate > 0.05:  # 5% threshold
                insights.append(AnalyticsInsight(
                    insight_id=str(uuid.uuid4()),
                    title="High Error Rate",
                    description=f"Error rate is {error_rate*100:.1f}%, indicating potential stability issues.",
                    insight_type="reliability",
                    confidence=0.95,
                    impact="high",
                    recommendations=[
                        "Review error patterns",
                        "Improve error handling",
                        "Enhance retry mechanisms"
                    ],
                    supporting_data={"error_rate": error_rate, "threshold": 0.05}
                ))
        
        # Resource utilization insights
        if "cpu_usage" in report_data:
            cpu_data = report_data["cpu_usage"]
            max_cpu = cpu_data["aggregations"].get("max", 0)
            
            if max_cpu > 0.8:  # 80% threshold
                insights.append(AnalyticsInsight(
                    insight_id=str(uuid.uuid4()),
                    title="High CPU Utilization",
                    description=f"Maximum CPU utilization reached {max_cpu*100:.1f}%, indicating potential resource constraints.",
                    insight_type="resource",
                    confidence=0.85,
                    impact="medium",
                    recommendations=[
                        "Scale up resources",
                        "Optimize CPU-intensive operations",
                        "Implement load balancing"
                    ],
                    supporting_data={"max_cpu": max_cpu, "threshold": 0.8}
                ))
        
        return insights
    
    def _generate_summary(self, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report summary."""
        
        summary = {
            "metrics_analyzed": len(report_data),
            "key_findings": [],
            "recommendations": []
        }
        
        # Extract key findings
        for metric_name, metric_data in report_data.items():
            aggregations = metric_data.get("aggregations", {})
            
            if aggregations:
                summary["key_findings"].append({
                    "metric": metric_name,
                    "value": aggregations.get("average", aggregations.get("count", 0)),
                    "trend": "stable"  # Would calculate actual trend
                })
        
        return summary
    
    async def _generate_charts(
        self,
        report_data: Dict[str, Any],
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate chart configurations."""
        
        charts = {}
        
        # This would generate actual chart configurations
        # For now, return chart metadata
        
        chart_types = template.get("charts", [])
        
        for chart_type in chart_types:
            charts[chart_type] = {
                "type": chart_type,
                "data_source": "report_data",
                "config": {
                    "title": chart_type.replace("_", " ").title(),
                    "x_axis": "timestamp",
                    "y_axis": "value"
                }
            }
        
        return charts


class AnalyticsEngine:
    """Main analytics engine coordinating metrics collection and reporting."""
    
    def __init__(self):
        """Initialize analytics engine."""
        self.logger = StructuredLogger("analytics_engine")
        
        # Components
        self.metrics_collector = MetricsCollector()
        self.report_generator = ReportGenerator(self.metrics_collector)
        
        # Background tasks
        self.collection_task: Optional[asyncio.Task] = None
        self.is_running = False
    
    async def start(self) -> None:
        """Start the analytics engine."""
        if self.is_running:
            return
        
        self.is_running = True
        
        # Start background collection
        self.collection_task = asyncio.create_task(self._collection_loop())
        
        self.logger.info("Analytics engine started")
    
    async def stop(self) -> None:
        """Stop the analytics engine."""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # Stop background tasks
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                pass
        
        self.logger.info("Analytics engine stopped")
    
    async def _collection_loop(self) -> None:
        """Background metrics collection loop."""
        
        while self.is_running:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                # Sleep for collection interval
                await asyncio.sleep(60)  # Collect every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(
                    "Metrics collection error",
                    error=str(e)
                )
                await asyncio.sleep(60)
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        
        # This would collect actual system metrics
        # For now, record sample metrics
        
        import psutil
        
        # CPU usage
        cpu_usage = psutil.cpu_percent()
        self.metrics_collector.record_metric(
            "cpu_usage",
            cpu_usage / 100.0,  # Normalize to 0-1
            MetricType.GAUGE,
            tags={"source": "system"}
        )
        
        # Memory usage
        memory = psutil.virtual_memory()
        self.metrics_collector.record_metric(
            "memory_usage",
            memory.percent / 100.0,  # Normalize to 0-1
            MetricType.GAUGE,
            tags={"source": "system"}
        )
    
    def record_workflow_execution(
        self,
        workflow_id: str,
        execution_time: float,
        success: bool,
        task_count: int
    ) -> None:
        """Record workflow execution metrics."""
        
        # Execution time
        self.metrics_collector.record_metric(
            "workflow_execution_time",
            execution_time,
            MetricType.TIMER,
            tags={"workflow_id": workflow_id, "success": str(success)}
        )
        
        # Success/failure
        self.metrics_collector.record_metric(
            "workflow_executions",
            1,
            MetricType.COUNTER,
            tags={"workflow_id": workflow_id, "result": "success" if success else "failure"}
        )
        
        # Task count
        self.metrics_collector.record_metric(
            "workflow_task_count",
            task_count,
            MetricType.GAUGE,
            tags={"workflow_id": workflow_id}
        )
    
    def record_error(
        self,
        error_type: str,
        error_category: str,
        severity: str,
        recovered: bool
    ) -> None:
        """Record error metrics."""
        
        # Error count
        self.metrics_collector.record_metric(
            "error_count",
            1,
            MetricType.COUNTER,
            tags={
                "error_type": error_type,
                "category": error_category,
                "severity": severity,
                "recovered": str(recovered)
            }
        )
        
        # Recovery success
        if recovered:
            self.metrics_collector.record_metric(
                "recovery_success",
                1,
                MetricType.COUNTER,
                tags={"error_category": error_category}
            )
    
    async def generate_dashboard_data(self) -> Dict[str, Any]:
        """Generate real-time dashboard data."""
        
        now = datetime.utcnow()
        last_hour = now - timedelta(hours=1)
        
        # Get recent metrics
        recent_executions = self.metrics_collector.get_metrics(
            "workflow_executions",
            (last_hour, now)
        )
        
        recent_errors = self.metrics_collector.get_metrics(
            "error_count",
            (last_hour, now)
        )
        
        # Calculate dashboard metrics
        total_executions = len(recent_executions)
        total_errors = len(recent_errors)
        error_rate = total_errors / total_executions if total_executions > 0 else 0
        
        # Current resource usage
        current_cpu = self.metrics_collector.gauges.get("cpu_usage", 0)
        current_memory = self.metrics_collector.gauges.get("memory_usage", 0)
        
        return {
            "timestamp": now.isoformat(),
            "executions": {
                "total": total_executions,
                "rate": total_executions / 3600  # per second
            },
            "errors": {
                "total": total_errors,
                "rate": error_rate
            },
            "resources": {
                "cpu_usage": current_cpu,
                "memory_usage": current_memory
            },
            "health": {
                "status": "healthy" if error_rate < 0.05 else "degraded",
                "uptime": "99.9%"  # Would calculate actual uptime
            }
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analytics engine statistics."""
        
        return {
            "metrics_collected": len(self.metrics_collector.metrics),
            "unique_metric_names": len(self.metrics_collector.metric_index),
            "counters": len(self.metrics_collector.counters),
            "gauges": len(self.metrics_collector.gauges),
            "histograms": len(self.metrics_collector.histograms),
            "timers": len(self.metrics_collector.timers),
            "is_running": self.is_running
        }
