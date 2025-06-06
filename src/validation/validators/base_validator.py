"""
Base Validator

Abstract base class for all validation implementations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationIssue, ValidationSeverity
from ..core.evidence_collector import EvidenceCollector
from src.infrastructure.logging.logger import StructuredLogger


class BaseValidator(ABC):
    """Abstract base class for all validators."""
    
    def __init__(self, config: ValidationConfig):
        self.config = config
        self.logger = StructuredLogger(f"validator_{self.__class__.__name__.lower()}")
        self.issues: List[ValidationIssue] = []
        self.validation_start_time: Optional[datetime] = None
        self.validation_end_time: Optional[datetime] = None
        
    @abstractmethod
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """
        Perform validation with the given context.
        
        Args:
            context: Validation context containing task data, execution state, etc.
            evidence_collector: Optional evidence collector for gathering validation evidence
        """
        pass
    
    @abstractmethod
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        pass
    
    def start_validation(self) -> None:
        """Mark the start of validation."""
        self.validation_start_time = datetime.now(timezone.utc)
        self.issues.clear()
        self.logger.info("Validation started", validator=self.__class__.__name__)
    
    def complete_validation(self) -> None:
        """Mark the completion of validation."""
        self.validation_end_time = datetime.now(timezone.utc)
        duration = self.get_validation_duration()
        
        self.logger.info("Validation completed", 
                        validator=self.__class__.__name__,
                        duration=duration,
                        issues_count=len(self.issues),
                        has_errors=self.has_errors())
    
    def add_issue(self, message: str, severity: ValidationSeverity, 
                  rule_name: str, details: Dict[str, Any] = None,
                  suggestion: str = None, evidence_path: str = None) -> None:
        """Add a validation issue."""
        issue = ValidationIssue(
            message=message,
            severity=severity,
            rule_name=rule_name,
            phase=self.__class__.__name__.lower(),
            details=details or {},
            suggestion=suggestion,
            evidence_path=evidence_path
        )
        
        self.issues.append(issue)
        
        self.logger.log(
            level="error" if severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL] else "warning",
            message=f"Validation issue: {message}",
            rule_name=rule_name,
            severity=severity.value,
            details=details
        )
    
    def add_info(self, message: str, rule_name: str, 
                 details: Dict[str, Any] = None) -> None:
        """Add an informational validation result."""
        self.add_issue(message, ValidationSeverity.INFO, rule_name, details)
    
    def add_warning(self, message: str, rule_name: str, 
                   details: Dict[str, Any] = None, suggestion: str = None) -> None:
        """Add a validation warning."""
        self.add_issue(message, ValidationSeverity.WARNING, rule_name, details, suggestion)
    
    def add_error(self, message: str, rule_name: str, 
                  details: Dict[str, Any] = None, suggestion: str = None) -> None:
        """Add a validation error."""
        self.add_issue(message, ValidationSeverity.ERROR, rule_name, details, suggestion)
    
    def add_critical(self, message: str, rule_name: str, 
                    details: Dict[str, Any] = None, suggestion: str = None) -> None:
        """Add a critical validation error."""
        self.add_issue(message, ValidationSeverity.CRITICAL, rule_name, details, suggestion)
    
    def has_issues(self) -> bool:
        """Check if validator has any issues."""
        return len(self.issues) > 0
    
    def has_errors(self) -> bool:
        """Check if validator has errors or critical issues."""
        return any(
            issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
            for issue in self.issues
        )
    
    def has_warnings(self) -> bool:
        """Check if validator has warnings."""
        return any(
            issue.severity == ValidationSeverity.WARNING
            for issue in self.issues
        )
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get issues by severity level."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def get_error_count(self) -> int:
        """Get count of errors and critical issues."""
        return len([
            issue for issue in self.issues 
            if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL]
        ])
    
    def get_warning_count(self) -> int:
        """Get count of warnings."""
        return len(self.get_issues_by_severity(ValidationSeverity.WARNING))
    
    def get_validation_duration(self) -> float:
        """Get validation duration in seconds."""
        if self.validation_start_time and self.validation_end_time:
            return (self.validation_end_time - self.validation_start_time).total_seconds()
        return 0.0
    
    def get_validation_summary(self) -> Dict[str, Any]:
        """Get validation summary."""
        return {
            "validator": self.__class__.__name__,
            "duration": self.get_validation_duration(),
            "total_issues": len(self.issues),
            "error_count": self.get_error_count(),
            "warning_count": self.get_warning_count(),
            "has_errors": self.has_errors(),
            "validation_rules": self.get_validation_rules(),
            "issues": [
                {
                    "message": issue.message,
                    "severity": issue.severity.value,
                    "rule_name": issue.rule_name,
                    "timestamp": issue.timestamp.isoformat(),
                    "details": issue.details
                }
                for issue in self.issues
            ]
        }
    
    def reset(self) -> None:
        """Reset validator state."""
        self.issues.clear()
        self.validation_start_time = None
        self.validation_end_time = None
    
    async def collect_evidence(self, evidence_collector: EvidenceCollector,
                             evidence_type: str, data: Any, 
                             filename: str = None) -> str:
        """Helper method to collect evidence."""
        if evidence_collector:
            return evidence_collector.collect_custom_evidence(
                evidence_type, data, filename
            )
        return ""
    
    def validate_required_context(self, context: Dict[str, Any], 
                                required_keys: List[str]) -> bool:
        """Validate that required context keys are present."""
        missing_keys = [key for key in required_keys if key not in context]
        
        if missing_keys:
            self.add_error(
                f"Missing required context keys: {', '.join(missing_keys)}",
                "context_validation",
                {"missing_keys": missing_keys}
            )
            return False
        
        return True
    
    def validate_context_type(self, context: Dict[str, Any], 
                            key: str, expected_type: type) -> bool:
        """Validate context value type."""
        if key not in context:
            return True  # Let validate_required_context handle missing keys
        
        value = context[key]
        if not isinstance(value, expected_type):
            self.add_error(
                f"Context key '{key}' has invalid type. Expected {expected_type.__name__}, got {type(value).__name__}",
                "context_type_validation",
                {
                    "key": key,
                    "expected_type": expected_type.__name__,
                    "actual_type": type(value).__name__
                }
            )
            return False
        
        return True
    
    async def safe_validate(self, context: Dict[str, Any], 
                          evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Safely execute validation with error handling."""
        try:
            self.start_validation()
            await self.validate(context, evidence_collector)
            self.complete_validation()
            
        except Exception as e:
            self.add_critical(
                f"Validator execution failed: {str(e)}",
                "validator_execution",
                {"error": str(e), "error_type": type(e).__name__}
            )
            self.complete_validation()
            
            # Re-raise for higher-level handling
            raise
