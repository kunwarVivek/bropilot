"""
Test Reporting Models

Core data models for advanced test reporting system.
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from enum import Enum
from dataclasses import dataclass, field


class ReportType(str, Enum):
    """Report type enumeration."""
    EXECUTION_SUMMARY = "execution_summary"
    DETAILED_RESULTS = "detailed_results"
    TREND_ANALYSIS = "trend_analysis"
    FAILURE_ANALYSIS = "failure_analysis"
    PERFORMANCE_REPORT = "performance_report"
    QUALITY_METRICS = "quality_metrics"
    DASHBOARD = "dashboard"
    CUSTOM = "custom"


class ReportFormat(str, Enum):
    """Report format enumeration."""
    HTML = "html"
    PDF = "pdf"
    JSON = "json"
    XML = "xml"
    CSV = "csv"
    JUNIT = "junit"
    ALLURE = "allure"
    DASHBOARD = "dashboard"


class SectionType(str, Enum):
    """Report section type."""
    SUMMARY = "summary"
    STATISTICS = "statistics"
    TEST_RESULTS = "test_results"
    FAILURE_DETAILS = "failure_details"
    PERFORMANCE_METRICS = "performance_metrics"
    TREND_CHARTS = "trend_charts"
    SCREENSHOTS = "screenshots"
    LOGS = "logs"
    RECOMMENDATIONS = "recommendations"
    CUSTOM = "custom"


@dataclass
class TestMetrics:
    """Test execution metrics."""
    
    # Basic counts
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    blocked_tests: int = 0
    
    # Timing metrics
    total_duration: float = 0.0
    average_duration: float = 0.0
    min_duration: float = 0.0
    max_duration: float = 0.0
    
    # Success metrics
    success_rate: float = 0.0
    failure_rate: float = 0.0
    
    # Performance metrics
    average_response_time: float = 0.0
    throughput: float = 0.0  # tests per minute
    
    # Quality metrics
    test_coverage: float = 0.0
    code_coverage: float = 0.0
    defect_density: float = 0.0
    
    # Resource metrics
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    browser_sessions: int = 0
    
    def calculate_derived_metrics(self) -> None:
        """Calculate derived metrics from basic counts."""
        if self.total_tests > 0:
            self.success_rate = self.passed_tests / self.total_tests
            self.failure_rate = (self.failed_tests + self.error_tests) / self.total_tests
            
            if self.total_duration > 0:
                self.average_duration = self.total_duration / self.total_tests
                self.throughput = self.total_tests / (self.total_duration / 60)  # per minute
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "error_tests": self.error_tests,
            "blocked_tests": self.blocked_tests,
            "total_duration": self.total_duration,
            "average_duration": self.average_duration,
            "min_duration": self.min_duration,
            "max_duration": self.max_duration,
            "success_rate": self.success_rate,
            "failure_rate": self.failure_rate,
            "average_response_time": self.average_response_time,
            "throughput": self.throughput,
            "test_coverage": self.test_coverage,
            "code_coverage": self.code_coverage,
            "defect_density": self.defect_density,
            "cpu_usage": self.cpu_usage,
            "memory_usage": self.memory_usage,
            "browser_sessions": self.browser_sessions
        }


@dataclass
class TrendData:
    """Trend analysis data point."""
    timestamp: datetime
    metrics: TestMetrics
    execution_id: str
    environment: str = "default"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "metrics": self.metrics.to_dict(),
            "execution_id": self.execution_id,
            "environment": self.environment
        }


@dataclass
class TrendAnalysis:
    """Trend analysis results."""
    
    # Time period
    start_date: datetime
    end_date: datetime
    period_days: int
    
    # Trend data
    data_points: List[TrendData] = field(default_factory=list)
    
    # Trend metrics
    success_rate_trend: float = 0.0  # Positive = improving, Negative = degrading
    performance_trend: float = 0.0
    failure_trend: float = 0.0
    
    # Statistical analysis
    average_success_rate: float = 0.0
    success_rate_variance: float = 0.0
    performance_regression: bool = False
    quality_improvement: bool = False
    
    # Insights
    insights: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    
    def add_data_point(self, data_point: TrendData) -> None:
        """Add a trend data point."""
        self.data_points.append(data_point)
        self.data_points.sort(key=lambda x: x.timestamp)
    
    def calculate_trends(self) -> None:
        """Calculate trend metrics from data points."""
        if len(self.data_points) < 2:
            return
        
        # Calculate success rate trend
        success_rates = [dp.metrics.success_rate for dp in self.data_points]
        if len(success_rates) >= 2:
            self.success_rate_trend = success_rates[-1] - success_rates[0]
            self.average_success_rate = sum(success_rates) / len(success_rates)
            
            # Calculate variance
            mean = self.average_success_rate
            self.success_rate_variance = sum((x - mean) ** 2 for x in success_rates) / len(success_rates)
        
        # Calculate performance trend
        durations = [dp.metrics.average_duration for dp in self.data_points if dp.metrics.average_duration > 0]
        if len(durations) >= 2:
            self.performance_trend = durations[0] - durations[-1]  # Positive = faster
            self.performance_regression = durations[-1] > durations[0] * 1.1  # 10% slower
        
        # Generate insights
        self._generate_insights()
    
    def _generate_insights(self) -> None:
        """Generate insights from trend analysis."""
        self.insights.clear()
        self.recommendations.clear()
        
        # Success rate insights
        if self.success_rate_trend > 0.05:
            self.insights.append("Test success rate is improving")
            self.quality_improvement = True
        elif self.success_rate_trend < -0.05:
            self.insights.append("Test success rate is declining")
            self.recommendations.append("Review recent test failures and fix flaky tests")
        
        # Performance insights
        if self.performance_regression:
            self.insights.append("Performance regression detected")
            self.recommendations.append("Investigate performance bottlenecks")
        elif self.performance_trend > 0:
            self.insights.append("Test execution performance is improving")
        
        # Variance insights
        if self.success_rate_variance > 0.1:
            self.insights.append("High variability in test results")
            self.recommendations.append("Stabilize test environment and fix flaky tests")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "period_days": self.period_days,
            "data_points": [dp.to_dict() for dp in self.data_points],
            "success_rate_trend": self.success_rate_trend,
            "performance_trend": self.performance_trend,
            "failure_trend": self.failure_trend,
            "average_success_rate": self.average_success_rate,
            "success_rate_variance": self.success_rate_variance,
            "performance_regression": self.performance_regression,
            "quality_improvement": self.quality_improvement,
            "insights": self.insights,
            "recommendations": self.recommendations
        }


@dataclass
class ReportSection:
    """Individual report section."""
    
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    section_type: SectionType = SectionType.CUSTOM
    content: Dict[str, Any] = field(default_factory=dict)
    order: int = 0
    visible: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "section_type": self.section_type.value,
            "content": self.content,
            "order": self.order,
            "visible": self.visible
        }


@dataclass
class ReportConfiguration:
    """Report generation configuration."""
    
    # Report settings
    report_type: ReportType = ReportType.EXECUTION_SUMMARY
    format: ReportFormat = ReportFormat.HTML
    title: str = "Test Execution Report"
    description: str = ""
    
    # Content settings
    include_screenshots: bool = True
    include_logs: bool = True
    include_performance_metrics: bool = True
    include_trend_analysis: bool = False
    include_failure_analysis: bool = True
    
    # Filtering
    environment_filter: Optional[str] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    test_type_filter: Optional[List[str]] = None
    tag_filter: Optional[List[str]] = None
    
    # Styling and branding
    theme: str = "default"
    logo_url: Optional[str] = None
    company_name: Optional[str] = None
    custom_css: Optional[str] = None
    
    # Output settings
    output_path: str = "reports"
    filename_template: str = "test_report_{timestamp}"
    auto_open: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_type": self.report_type.value,
            "format": self.format.value,
            "title": self.title,
            "description": self.description,
            "include_screenshots": self.include_screenshots,
            "include_logs": self.include_logs,
            "include_performance_metrics": self.include_performance_metrics,
            "include_trend_analysis": self.include_trend_analysis,
            "include_failure_analysis": self.include_failure_analysis,
            "environment_filter": self.environment_filter,
            "date_range_start": self.date_range_start.isoformat() if self.date_range_start else None,
            "date_range_end": self.date_range_end.isoformat() if self.date_range_end else None,
            "test_type_filter": self.test_type_filter,
            "tag_filter": self.tag_filter,
            "theme": self.theme,
            "logo_url": self.logo_url,
            "company_name": self.company_name,
            "custom_css": self.custom_css,
            "output_path": self.output_path,
            "filename_template": self.filename_template,
            "auto_open": self.auto_open
        }


@dataclass
class TestReport:
    """Comprehensive test report."""
    
    # Report identification
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    report_type: ReportType = ReportType.EXECUTION_SUMMARY
    format: ReportFormat = ReportFormat.HTML
    
    # Report content
    sections: List[ReportSection] = field(default_factory=list)
    metrics: TestMetrics = field(default_factory=TestMetrics)
    trend_analysis: Optional[TrendAnalysis] = None
    
    # Execution context
    execution_ids: List[str] = field(default_factory=list)
    test_suite_ids: List[str] = field(default_factory=list)
    environment: str = "default"
    
    # Time period
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    generation_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Report metadata
    configuration: ReportConfiguration = field(default_factory=ReportConfiguration)
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    
    # Audit fields
    generated_by: str = "system"
    version: str = "1.0"
    
    def add_section(self, section: ReportSection) -> None:
        """Add a section to the report."""
        section.order = len(self.sections)
        self.sections.append(section)
    
    def get_section(self, section_type: SectionType) -> Optional[ReportSection]:
        """Get a section by type."""
        return next(
            (section for section in self.sections if section.section_type == section_type),
            None
        )
    
    def remove_section(self, section_id: str) -> bool:
        """Remove a section from the report."""
        for i, section in enumerate(self.sections):
            if section.id == section_id:
                self.sections.pop(i)
                # Reorder remaining sections
                for j, remaining_section in enumerate(self.sections[i:], i):
                    remaining_section.order = j
                return True
        return False
    
    def get_duration(self) -> float:
        """Get report time period duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "report_type": self.report_type.value,
            "format": self.format.value,
            "sections": [section.to_dict() for section in self.sections],
            "metrics": self.metrics.to_dict(),
            "trend_analysis": self.trend_analysis.to_dict() if self.trend_analysis else None,
            "execution_ids": self.execution_ids,
            "test_suite_ids": self.test_suite_ids,
            "environment": self.environment,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "generation_time": self.generation_time.isoformat(),
            "duration": self.get_duration(),
            "configuration": self.configuration.to_dict(),
            "file_path": self.file_path,
            "file_size": self.file_size,
            "generated_by": self.generated_by,
            "version": self.version
        }
