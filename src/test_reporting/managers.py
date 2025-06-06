"""
Test Reporting Managers

High-level managers for test reporting operations.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from .models import (
    TestReport, ReportType, ReportFormat, ReportSection, TestMetrics,
    TrendAnalysis, ReportConfiguration, SectionType
)
from src.infrastructure.logging.logger import StructuredLogger


class ReportManager:
    """Manager for test report operations."""
    
    def __init__(self, reports_path: str, execution_repository=None):
        self.reports_path = Path(reports_path)
        self.reports_path.mkdir(parents=True, exist_ok=True)
        self.execution_repository = execution_repository
        self.logger = StructuredLogger("report_manager")
        
        # In-memory storage for demo
        self.reports: Dict[str, TestReport] = {}
    
    async def generate_execution_report(
        self,
        execution_id: str,
        report_format: ReportFormat = ReportFormat.HTML,
        title: Optional[str] = None,
        **kwargs
    ) -> TestReport:
        """Generate a report for a test execution."""
        try:
            # Mock execution data for demo
            execution_data = await self._get_execution_data(execution_id)
            
            # Create report configuration
            config = ReportConfiguration(
                report_type=ReportType.EXECUTION_SUMMARY,
                format=report_format,
                title=title or f"Test Execution Report - {execution_id}",
                **kwargs
            )
            
            # Create report
            report = TestReport(
                title=config.title,
                report_type=config.report_type,
                format=config.format,
                execution_ids=[execution_id],
                configuration=config
            )
            
            # Add sections
            await self._add_summary_section(report, execution_data)
            
            if config.include_performance_metrics:
                await self._add_performance_section(report, execution_data)
            
            if config.include_failure_analysis:
                await self._add_failure_analysis_section(report, execution_data)
            
            # Generate report file
            file_path = await self._generate_report_file(report, execution_data)
            report.file_path = file_path
            
            # Store report
            self.reports[report.id] = report
            
            self.logger.info(
                "Execution report generated",
                report_id=report.id,
                execution_id=execution_id,
                format=report_format.value,
                file_path=file_path
            )
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Failed to generate execution report",
                error=str(e),
                execution_id=execution_id,
                format=report_format.value
            )
            raise
    
    async def generate_trend_report(
        self,
        days: int = 30,
        environment: Optional[str] = None,
        report_format: ReportFormat = ReportFormat.HTML,
        title: Optional[str] = None,
        **kwargs
    ) -> TestReport:
        """Generate a trend analysis report."""
        try:
            # Mock trend data for demo
            trend_data = await self._get_trend_data(days, environment)
            
            config = ReportConfiguration(
                report_type=ReportType.TREND_ANALYSIS,
                format=report_format,
                title=title or f"{days}-Day Trend Analysis",
                environment_filter=environment,
                **kwargs
            )
            
            report = TestReport(
                title=config.title,
                report_type=config.report_type,
                format=config.format,
                configuration=config,
                start_time=datetime.now(timezone.utc) - timedelta(days=days),
                end_time=datetime.now(timezone.utc)
            )
            
            # Add trend analysis sections
            await self._add_trend_summary_section(report, trend_data)
            await self._add_trend_charts_section(report, trend_data)
            
            # Generate report file
            file_path = await self._generate_report_file(report, trend_data)
            report.file_path = file_path
            
            self.reports[report.id] = report
            
            self.logger.info(
                "Trend report generated",
                report_id=report.id,
                days=days,
                environment=environment,
                format=report_format.value
            )
            
            return report
            
        except Exception as e:
            self.logger.error(
                "Failed to generate trend report",
                error=str(e),
                days=days,
                environment=environment
            )
            raise
    
    async def generate_dashboard(
        self,
        title: str = "Test Dashboard",
        environment: Optional[str] = None,
        auto_refresh: bool = False,
        refresh_interval: int = 30,
        **kwargs
    ) -> str:
        """Generate a test dashboard."""
        try:
            # Mock dashboard generation
            dashboard_data = await self._get_dashboard_data(environment)
            
            # Generate dashboard HTML
            dashboard_html = self._generate_dashboard_html(
                title, dashboard_data, auto_refresh, refresh_interval
            )
            
            # Save dashboard file
            dashboard_path = self.reports_path / "dashboard.html"
            with open(dashboard_path, 'w') as f:
                f.write(dashboard_html)
            
            dashboard_url = f"file://{dashboard_path.absolute()}"
            
            self.logger.info(
                "Dashboard generated",
                title=title,
                environment=environment,
                url=dashboard_url
            )
            
            return dashboard_url
            
        except Exception as e:
            self.logger.error(
                "Failed to generate dashboard",
                error=str(e),
                title=title,
                environment=environment
            )
            raise
    
    async def _get_execution_data(self, execution_id: str) -> Dict[str, Any]:
        """Get execution data (mock for demo)."""
        return {
            "execution_id": execution_id,
            "name": f"Test Execution {execution_id}",
            "status": "passed",
            "start_time": datetime.now(timezone.utc) - timedelta(minutes=30),
            "end_time": datetime.now(timezone.utc),
            "duration": 1800,  # 30 minutes
            "total_tests": 10,
            "passed_tests": 8,
            "failed_tests": 2,
            "skipped_tests": 0,
            "success_rate": 0.8,
            "environment": "staging",
            "test_results": [
                {
                    "test_case_id": f"tc_{i}",
                    "name": f"Test Case {i}",
                    "status": "passed" if i % 5 != 0 else "failed",
                    "duration": 180 + (i * 10),
                    "error_message": "Test failed" if i % 5 == 0 else None
                }
                for i in range(1, 11)
            ]
        }
    
    async def _get_trend_data(self, days: int, environment: Optional[str]) -> Dict[str, Any]:
        """Get trend data (mock for demo)."""
        import random
        
        data_points = []
        base_date = datetime.now(timezone.utc) - timedelta(days=days)
        
        for i in range(days):
            date = base_date + timedelta(days=i)
            success_rate = 0.7 + (random.random() * 0.3)  # 70-100%
            
            data_points.append({
                "date": date.isoformat(),
                "total_tests": random.randint(5, 20),
                "passed_tests": int(random.randint(5, 20) * success_rate),
                "failed_tests": random.randint(0, 3),
                "success_rate": success_rate,
                "avg_duration": random.uniform(120, 300)
            })
        
        return {
            "period_days": days,
            "environment": environment,
            "data_points": data_points,
            "overall_trend": "improving",
            "insights": [
                "Test success rate is trending upward",
                "Average execution time is stable",
                "No significant performance regressions detected"
            ]
        }
    
    async def _get_dashboard_data(self, environment: Optional[str]) -> Dict[str, Any]:
        """Get dashboard data (mock for demo)."""
        return {
            "environment": environment or "all",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "total_test_cases": 150,
                "active_test_suites": 12,
                "recent_executions": 25,
                "success_rate_7d": 0.85
            },
            "recent_executions": [
                {
                    "id": f"exec_{i}",
                    "name": f"Execution {i}",
                    "status": "passed" if i % 3 != 0 else "failed",
                    "timestamp": (datetime.now(timezone.utc) - timedelta(hours=i)).isoformat(),
                    "success_rate": 0.8 + (i * 0.02)
                }
                for i in range(1, 6)
            ]
        }
    
    async def _add_summary_section(self, report: TestReport, execution_data: Dict[str, Any]) -> None:
        """Add summary section to report."""
        metrics = TestMetrics(
            total_tests=execution_data["total_tests"],
            passed_tests=execution_data["passed_tests"],
            failed_tests=execution_data["failed_tests"],
            skipped_tests=execution_data["skipped_tests"],
            total_duration=execution_data["duration"],
            success_rate=execution_data["success_rate"]
        )
        metrics.calculate_derived_metrics()
        
        report.metrics = metrics
        
        summary_section = ReportSection(
            title="Execution Summary",
            section_type=SectionType.SUMMARY,
            content={
                "execution_name": execution_data["name"],
                "status": execution_data["status"],
                "environment": execution_data["environment"],
                "duration": execution_data["duration"],
                "metrics": metrics.to_dict()
            }
        )
        
        report.add_section(summary_section)
    
    async def _add_performance_section(self, report: TestReport, execution_data: Dict[str, Any]) -> None:
        """Add performance metrics section."""
        performance_section = ReportSection(
            title="Performance Metrics",
            section_type=SectionType.PERFORMANCE_METRICS,
            content={
                "total_duration": execution_data["duration"],
                "average_test_duration": execution_data["duration"] / execution_data["total_tests"],
                "throughput": execution_data["total_tests"] / (execution_data["duration"] / 60),
                "performance_trend": "stable"
            }
        )
        
        report.add_section(performance_section)
    
    async def _add_failure_analysis_section(self, report: TestReport, execution_data: Dict[str, Any]) -> None:
        """Add failure analysis section."""
        failed_tests = [
            test for test in execution_data["test_results"]
            if test["status"] == "failed"
        ]
        
        failure_section = ReportSection(
            title="Failure Analysis",
            section_type=SectionType.FAILURE_DETAILS,
            content={
                "failed_test_count": len(failed_tests),
                "failed_tests": failed_tests,
                "common_failure_patterns": ["timeout", "element_not_found"],
                "recommendations": [
                    "Review timeout configurations",
                    "Update element selectors"
                ]
            }
        )
        
        report.add_section(failure_section)
    
    async def _add_trend_summary_section(self, report: TestReport, trend_data: Dict[str, Any]) -> None:
        """Add trend summary section."""
        trend_section = ReportSection(
            title="Trend Summary",
            section_type=SectionType.SUMMARY,
            content={
                "period_days": trend_data["period_days"],
                "overall_trend": trend_data["overall_trend"],
                "insights": trend_data["insights"],
                "data_points_count": len(trend_data["data_points"])
            }
        )
        
        report.add_section(trend_section)
    
    async def _add_trend_charts_section(self, report: TestReport, trend_data: Dict[str, Any]) -> None:
        """Add trend charts section."""
        charts_section = ReportSection(
            title="Trend Charts",
            section_type=SectionType.TREND_CHARTS,
            content={
                "success_rate_chart": {
                    "type": "line",
                    "data": [
                        {"date": dp["date"], "value": dp["success_rate"]}
                        for dp in trend_data["data_points"]
                    ]
                },
                "execution_time_chart": {
                    "type": "line",
                    "data": [
                        {"date": dp["date"], "value": dp["avg_duration"]}
                        for dp in trend_data["data_points"]
                    ]
                }
            }
        )
        
        report.add_section(charts_section)
    
    async def _generate_report_file(self, report: TestReport, data: Dict[str, Any]) -> str:
        """Generate report file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if report.format == ReportFormat.HTML:
            filename = f"report_{report.id}_{timestamp}.html"
            file_path = self.reports_path / filename
            
            html_content = self._generate_html_report(report, data)
            with open(file_path, 'w') as f:
                f.write(html_content)
                
        elif report.format == ReportFormat.JSON:
            filename = f"report_{report.id}_{timestamp}.json"
            file_path = self.reports_path / filename
            
            import json
            with open(file_path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
                
        elif report.format == ReportFormat.JUNIT:
            filename = f"report_{report.id}_{timestamp}.xml"
            file_path = self.reports_path / filename
            
            junit_content = self._generate_junit_report(report, data)
            with open(file_path, 'w') as f:
                f.write(junit_content)
                
        else:
            # Default to JSON
            filename = f"report_{report.id}_{timestamp}.json"
            file_path = self.reports_path / filename
            
            import json
            with open(file_path, 'w') as f:
                json.dump(report.to_dict(), f, indent=2, default=str)
        
        return str(file_path)
    
    def _generate_html_report(self, report: TestReport, data: Dict[str, Any]) -> str:
        """Generate HTML report content."""
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{report.title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background: #f5f5f5; padding: 20px; border-radius: 5px; }}
        .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
        .metrics {{ display: flex; gap: 20px; }}
        .metric {{ text-align: center; padding: 10px; background: #e9f4ff; border-radius: 5px; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{report.title}</h1>
        <p>Generated: {report.generation_time}</p>
        <p>Report ID: {report.id}</p>
    </div>
"""
        
        for section in report.sections:
            html += f"""
    <div class="section">
        <h2>{section.title}</h2>
"""
            
            if section.section_type == SectionType.SUMMARY:
                metrics = section.content.get("metrics", {})
                html += f"""
        <div class="metrics">
            <div class="metric">
                <h3>Total Tests</h3>
                <p>{metrics.get('total_tests', 0)}</p>
            </div>
            <div class="metric">
                <h3 class="passed">Passed</h3>
                <p>{metrics.get('passed_tests', 0)}</p>
            </div>
            <div class="metric">
                <h3 class="failed">Failed</h3>
                <p>{metrics.get('failed_tests', 0)}</p>
            </div>
            <div class="metric">
                <h3>Success Rate</h3>
                <p>{metrics.get('success_rate', 0):.1%}</p>
            </div>
        </div>
"""
            else:
                html += f"<pre>{section.content}</pre>"
            
            html += "    </div>\n"
        
        html += """
</body>
</html>
"""
        return html
    
    def _generate_junit_report(self, report: TestReport, data: Dict[str, Any]) -> str:
        """Generate JUnit XML report."""
        metrics = report.metrics
        
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="{report.title}" 
           tests="{metrics.total_tests}" 
           failures="{metrics.failed_tests}" 
           errors="{metrics.error_tests}" 
           skipped="{metrics.skipped_tests}" 
           time="{metrics.total_duration}">
"""
        
        # Add test cases from data
        test_results = data.get("test_results", [])
        for test_result in test_results:
            xml += f"""
    <testcase name="{test_result['name']}" 
              classname="TestExecution" 
              time="{test_result['duration']}">
"""
            
            if test_result["status"] == "failed":
                xml += f"""
        <failure message="{test_result.get('error_message', 'Test failed')}">
            {test_result.get('error_message', 'Test failed')}
        </failure>
"""
            
            xml += "    </testcase>\n"
        
        xml += "</testsuite>"
        return xml
    
    def _generate_dashboard_html(
        self, 
        title: str, 
        data: Dict[str, Any], 
        auto_refresh: bool, 
        refresh_interval: int
    ) -> str:
        """Generate dashboard HTML."""
        refresh_meta = ""
        if auto_refresh:
            refresh_meta = f'<meta http-equiv="refresh" content="{refresh_interval}">'
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    {refresh_meta}
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .widget {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .metric {{ text-align: center; font-size: 2em; font-weight: bold; color: #2196F3; }}
        .status-passed {{ color: #4CAF50; }}
        .status-failed {{ color: #F44336; }}
        .execution-list {{ list-style: none; padding: 0; }}
        .execution-item {{ padding: 10px; margin: 5px 0; background: #f9f9f9; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Last Updated: {data['last_updated']}</p>
    
    <div class="dashboard">
        <div class="widget">
            <h3>Test Cases</h3>
            <div class="metric">{data['summary']['total_test_cases']}</div>
        </div>
        
        <div class="widget">
            <h3>Active Suites</h3>
            <div class="metric">{data['summary']['active_test_suites']}</div>
        </div>
        
        <div class="widget">
            <h3>7-Day Success Rate</h3>
            <div class="metric">{data['summary']['success_rate_7d']:.1%}</div>
        </div>
        
        <div class="widget">
            <h3>Recent Executions</h3>
            <ul class="execution-list">
"""
        
        for execution in data['recent_executions']:
            status_class = f"status-{execution['status']}"
            html += f"""
                <li class="execution-item">
                    <strong>{execution['name']}</strong>
                    <span class="{status_class}">{execution['status']}</span>
                    <br>
                    <small>{execution['timestamp']}</small>
                </li>
"""
        
        html += """
            </ul>
        </div>
    </div>
</body>
</html>
"""
        return html


class DashboardManager:
    """Manager for dashboard operations."""
    
    def __init__(self, report_manager: ReportManager):
        self.report_manager = report_manager
        self.logger = StructuredLogger("dashboard_manager")


class AnalyticsManager:
    """Manager for analytics operations."""
    
    def __init__(self, execution_repository=None):
        self.execution_repository = execution_repository
        self.logger = StructuredLogger("analytics_manager")
