"""
Validation Result System

Provides comprehensive validation result tracking and reporting.
"""

from enum import Enum
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import json


class ValidationStatus(Enum):
    """Validation result status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


class ValidationSeverity(Enum):
    """Validation issue severity."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ValidationIssue:
    """Individual validation issue."""
    message: str
    severity: ValidationSeverity
    rule_name: str
    phase: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: Optional[str] = None
    evidence_path: Optional[str] = None


@dataclass
class ValidationMetrics:
    """Validation performance metrics."""
    total_validations: int = 0
    passed_validations: int = 0
    failed_validations: int = 0
    warning_validations: int = 0
    skipped_validations: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate validation success rate."""
        if self.total_validations == 0:
            return 0.0
        return self.passed_validations / self.total_validations
    
    @property
    def failure_rate(self) -> float:
        """Calculate validation failure rate."""
        if self.total_validations == 0:
            return 0.0
        return self.failed_validations / self.total_validations


@dataclass
class PhaseResult:
    """Validation result for a specific phase."""
    phase: str
    status: ValidationStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    execution_time: float = 0.0
    issues: List[ValidationIssue] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration(self) -> float:
        """Get phase execution duration."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return self.execution_time
    
    def add_issue(self, issue: ValidationIssue) -> None:
        """Add validation issue to phase result."""
        self.issues.append(issue)
        
        # Update status based on issue severity
        if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.status = ValidationStatus.FAILED
        elif issue.severity == ValidationSeverity.WARNING and self.status == ValidationStatus.PASSED:
            self.status = ValidationStatus.WARNING


class ValidationResult:
    """Comprehensive validation result."""
    
    def __init__(self, task_id: str, validation_config: Dict[str, Any]):
        self.validation_id = str(uuid.uuid4())
        self.task_id = task_id
        self.validation_config = validation_config
        self.start_time = datetime.now(timezone.utc)
        self.end_time: Optional[datetime] = None
        self.overall_status = ValidationStatus.PENDING
        self.phase_results: Dict[str, PhaseResult] = {}
        self.global_issues: List[ValidationIssue] = []
        self.evidence_paths: Dict[str, str] = {}
        self.metadata: Dict[str, Any] = {}
        self.metrics = ValidationMetrics()
    
    def start_phase(self, phase: str) -> PhaseResult:
        """Start validation for a specific phase."""
        phase_result = PhaseResult(
            phase=phase,
            status=ValidationStatus.RUNNING,
            start_time=datetime.now(timezone.utc)
        )
        self.phase_results[phase] = phase_result
        return phase_result
    
    def complete_phase(self, phase: str, status: ValidationStatus = ValidationStatus.PASSED) -> None:
        """Complete validation for a specific phase."""
        if phase in self.phase_results:
            phase_result = self.phase_results[phase]
            phase_result.end_time = datetime.now(timezone.utc)
            phase_result.execution_time = phase_result.duration
            
            # Set status if not already set by issues
            if phase_result.status == ValidationStatus.RUNNING:
                phase_result.status = status
    
    def add_issue(self, issue: ValidationIssue, phase: Optional[str] = None) -> None:
        """Add validation issue."""
        if phase and phase in self.phase_results:
            self.phase_results[phase].add_issue(issue)
        else:
            self.global_issues.append(issue)
        
        # Update overall status
        self._update_overall_status(issue.severity)
    
    def add_evidence(self, evidence_type: str, evidence_path: str, phase: Optional[str] = None) -> None:
        """Add evidence file path."""
        if phase and phase in self.phase_results:
            self.phase_results[phase].evidence[evidence_type] = evidence_path
        else:
            self.evidence_paths[evidence_type] = evidence_path
    
    def complete_validation(self) -> None:
        """Complete the overall validation."""
        self.end_time = datetime.now(timezone.utc)
        self._calculate_metrics()
        self._determine_final_status()
    
    def _update_overall_status(self, severity: ValidationSeverity) -> None:
        """Update overall status based on issue severity."""
        if severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]:
            self.overall_status = ValidationStatus.FAILED
        elif severity == ValidationSeverity.WARNING and self.overall_status == ValidationStatus.PENDING:
            self.overall_status = ValidationStatus.WARNING
    
    def _calculate_metrics(self) -> None:
        """Calculate validation metrics."""
        total_validations = 0
        passed_validations = 0
        failed_validations = 0
        warning_validations = 0
        skipped_validations = 0
        total_execution_time = 0.0
        
        for phase_result in self.phase_results.values():
            total_validations += 1
            total_execution_time += phase_result.execution_time
            
            if phase_result.status == ValidationStatus.PASSED:
                passed_validations += 1
            elif phase_result.status == ValidationStatus.FAILED:
                failed_validations += 1
            elif phase_result.status == ValidationStatus.WARNING:
                warning_validations += 1
            elif phase_result.status == ValidationStatus.SKIPPED:
                skipped_validations += 1
        
        self.metrics = ValidationMetrics(
            total_validations=total_validations,
            passed_validations=passed_validations,
            failed_validations=failed_validations,
            warning_validations=warning_validations,
            skipped_validations=skipped_validations,
            total_execution_time=total_execution_time,
            average_execution_time=total_execution_time / max(total_validations, 1)
        )
    
    def _determine_final_status(self) -> None:
        """Determine final validation status."""
        if self.overall_status == ValidationStatus.PENDING:
            # No issues found, check if all phases passed
            all_passed = all(
                result.status == ValidationStatus.PASSED 
                for result in self.phase_results.values()
            )
            self.overall_status = ValidationStatus.PASSED if all_passed else ValidationStatus.WARNING
    
    @property
    def duration(self) -> float:
        """Get total validation duration."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def is_successful(self) -> bool:
        """Check if validation was successful."""
        return self.overall_status in [ValidationStatus.PASSED, ValidationStatus.WARNING]
    
    @property
    def has_errors(self) -> bool:
        """Check if validation has errors."""
        return self.overall_status in [ValidationStatus.FAILED, ValidationStatus.ERROR]
    
    def get_all_issues(self) -> List[ValidationIssue]:
        """Get all validation issues across all phases."""
        all_issues = list(self.global_issues)
        for phase_result in self.phase_results.values():
            all_issues.extend(phase_result.issues)
        return all_issues
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues by severity level."""
        return [issue for issue in self.get_all_issues() if issue.severity == severity]
    
    def get_summary(self) -> Dict[str, Any]:
        """Get validation result summary."""
        return {
            "validation_id": self.validation_id,
            "task_id": self.task_id,
            "overall_status": self.overall_status.value,
            "duration": self.duration,
            "success_rate": self.metrics.success_rate,
            "total_issues": len(self.get_all_issues()),
            "error_count": len(self.get_issues_by_severity(ValidationSeverity.ERROR)),
            "warning_count": len(self.get_issues_by_severity(ValidationSeverity.WARNING)),
            "phases_completed": len(self.phase_results),
            "evidence_collected": len(self.evidence_paths)
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert validation result to dictionary."""
        return {
            "validation_id": self.validation_id,
            "task_id": self.task_id,
            "validation_config": self.validation_config,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "overall_status": self.overall_status.value,
            "duration": self.duration,
            "phase_results": {
                phase: {
                    "phase": result.phase,
                    "status": result.status.value,
                    "start_time": result.start_time.isoformat(),
                    "end_time": result.end_time.isoformat() if result.end_time else None,
                    "execution_time": result.execution_time,
                    "issues": [
                        {
                            "message": issue.message,
                            "severity": issue.severity.value,
                            "rule_name": issue.rule_name,
                            "phase": issue.phase,
                            "timestamp": issue.timestamp.isoformat(),
                            "details": issue.details,
                            "suggestion": issue.suggestion,
                            "evidence_path": issue.evidence_path
                        }
                        for issue in result.issues
                    ],
                    "evidence": result.evidence,
                    "metrics": result.metrics
                }
                for phase, result in self.phase_results.items()
            },
            "global_issues": [
                {
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "rule_name": issue.rule_name,
                    "phase": issue.phase,
                    "timestamp": issue.timestamp.isoformat(),
                    "details": issue.details,
                    "suggestion": issue.suggestion,
                    "evidence_path": issue.evidence_path
                }
                for issue in self.global_issues
            ],
            "evidence_paths": self.evidence_paths,
            "metadata": self.metadata,
            "metrics": {
                "total_validations": self.metrics.total_validations,
                "passed_validations": self.metrics.passed_validations,
                "failed_validations": self.metrics.failed_validations,
                "warning_validations": self.metrics.warning_validations,
                "skipped_validations": self.metrics.skipped_validations,
                "total_execution_time": self.metrics.total_execution_time,
                "average_execution_time": self.metrics.average_execution_time,
                "success_rate": self.metrics.success_rate,
                "failure_rate": self.metrics.failure_rate
            }
        }
    
    def to_json(self) -> str:
        """Convert validation result to JSON string."""
        return json.dumps(self.to_dict(), indent=2, default=str)
