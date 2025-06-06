"""
Advanced Test Reporting System

Comprehensive test reporting and analytics for LLM-powered browser automation testing.
Provides detailed reports, dashboards, trend analysis, and integration capabilities.
"""

from .models import (
    TestReport,
    ReportType,
    ReportFormat,
    ReportSection,
    TestMetrics,
    TrendAnalysis,
    ReportConfiguration
)

# TODO: Implement these modules
# from .generators import (
#     HTMLReportGenerator,
#     PDFReportGenerator,
#     JSONReportGenerator,
#     JUnitReportGenerator,
#     AllureReportGenerator,
#     DashboardGenerator
# )

# from .analyzers import (
#     TestTrendAnalyzer,
#     FailureAnalyzer,
#     PerformanceAnalyzer,
#     QualityAnalyzer
# )

from .managers import (
    ReportManager,
    DashboardManager,
    AnalyticsManager
)

# from .exporters import (
#     ReportExporter,
#     TestRailExporter,
#     JiraExporter,
#     SlackNotifier,
#     EmailNotifier
# )

# from .templates import (
#     ReportTemplate,
#     DashboardTemplate,
#     EmailTemplate
# )

__all__ = [
    # Models
    "TestReport",
    "ReportType",
    "ReportFormat",
    "ReportSection",
    "TestMetrics",
    "TrendAnalysis",
    "ReportConfiguration",

    # Managers
    "ReportManager",
    "DashboardManager",
    "AnalyticsManager",

    # TODO: Add when implemented
    # "HTMLReportGenerator",
    # "PDFReportGenerator",
    # "JSONReportGenerator",
    # "JUnitReportGenerator",
    # "AllureReportGenerator",
    # "DashboardGenerator",
    # "TestTrendAnalyzer",
    # "FailureAnalyzer",
    # "PerformanceAnalyzer",
    # "QualityAnalyzer",
    # "ReportExporter",
    # "TestRailExporter",
    # "JiraExporter",
    # "SlackNotifier",
    # "EmailNotifier",
    # "ReportTemplate",
    # "DashboardTemplate",
    # "EmailTemplate"
]
