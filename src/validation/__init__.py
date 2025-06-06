"""
Validation Framework for Browser Use Automation

This module provides comprehensive task validation and execution assurance
across multiple phases and validation strategies.
"""

from .core.validation_engine import ValidationEngine
from .core.validation_config import ValidationConfig, ValidationLevel, ValidationPhase, get_validation_config
from .core.validation_result import ValidationResult, ValidationStatus
from .core.evidence_collector import EvidenceCollector
from .validators.outcome_validator import OutcomeValidator
from .validators.data_quality_validator import DataQualityValidator
from .validators.step_validator import StepValidator
from .validators.checkpoint_validator import CheckpointValidator

__all__ = [
    "ValidationEngine",
    "ValidationConfig",
    "ValidationLevel",
    "ValidationPhase",
    "get_validation_config",
    "ValidationResult",
    "ValidationStatus",
    "EvidenceCollector",
    "OutcomeValidator",
    "DataQualityValidator",
    "StepValidator",
    "CheckpointValidator"
]
