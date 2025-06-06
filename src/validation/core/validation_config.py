"""
Validation Configuration System

Provides configurable validation options across all phases and strategies.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel


class ValidationLevel(Enum):
    """Validation levels from basic to comprehensive."""
    DISABLED = "disabled"
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    PARANOID = "paranoid"


class ValidationType(Enum):
    """Types of validation to perform."""
    FUNCTIONAL = "functional"
    DATA_QUALITY = "data_quality"
    PERFORMANCE = "performance"
    SECURITY = "security"
    BUSINESS_LOGIC = "business_logic"


class ValidationPhase(Enum):
    """Validation phases during task execution."""
    PRE_EXECUTION = "pre_execution"
    DURING_EXECUTION = "during_execution"
    POST_EXECUTION = "post_execution"
    CONTINUOUS = "continuous"


@dataclass
class ValidationRule:
    """Individual validation rule configuration."""
    name: str
    description: str
    rule_type: ValidationType
    phase: ValidationPhase
    enabled: bool = True
    severity: str = "error"  # error, warning, info
    timeout: Optional[float] = None
    retry_count: int = 0
    custom_params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseConfig:
    """Configuration for a specific validation phase."""
    enabled: bool = True
    timeout: Optional[float] = None
    parallel_execution: bool = False
    fail_fast: bool = False
    rules: List[ValidationRule] = field(default_factory=list)


class ValidationConfig(BaseModel):
    """Comprehensive validation configuration."""
    
    # Global settings
    validation_level: ValidationLevel = ValidationLevel.STANDARD
    enabled_types: List[ValidationType] = field(default_factory=lambda: [
        ValidationType.FUNCTIONAL,
        ValidationType.DATA_QUALITY
    ])
    
    # Phase configurations
    pre_execution: PhaseConfig = field(default_factory=PhaseConfig)
    during_execution: PhaseConfig = field(default_factory=PhaseConfig)
    post_execution: PhaseConfig = field(default_factory=PhaseConfig)
    continuous: PhaseConfig = field(default_factory=PhaseConfig)
    
    # Evidence collection
    collect_evidence: bool = True
    evidence_types: List[str] = field(default_factory=lambda: [
        "screenshots", "network_logs", "dom_snapshots", "execution_logs"
    ])
    
    # LLM validation settings
    enable_llm_validation: bool = True
    llm_self_validation: bool = False
    llm_cross_validation: bool = False
    
    # Data validation settings
    data_quality_checks: bool = True
    data_completeness_threshold: float = 0.95
    data_accuracy_threshold: float = 0.90
    
    # Performance validation
    performance_monitoring: bool = True
    max_execution_time: Optional[float] = None
    memory_threshold: float = 0.85
    
    # Security validation
    security_checks: bool = False
    privacy_compliance: bool = True
    
    # Advanced features
    predictive_validation: bool = False
    auto_rule_generation: bool = False
    validation_learning: bool = False
    
    # Reporting and storage
    store_validation_results: bool = True
    generate_reports: bool = True
    alert_on_failures: bool = True
    
    class Config:
        use_enum_values = True

    @classmethod
    def create_basic_config(cls) -> "ValidationConfig":
        """Create basic validation configuration."""
        return cls(
            validation_level=ValidationLevel.BASIC,
            enabled_types=[ValidationType.FUNCTIONAL],
            collect_evidence=False,
            enable_llm_validation=False,
            data_quality_checks=False,
            performance_monitoring=False,
            security_checks=False
        )
    
    @classmethod
    def create_standard_config(cls) -> "ValidationConfig":
        """Create standard validation configuration."""
        return cls(
            validation_level=ValidationLevel.STANDARD,
            enabled_types=[
                ValidationType.FUNCTIONAL,
                ValidationType.DATA_QUALITY
            ],
            collect_evidence=True,
            enable_llm_validation=True,
            data_quality_checks=True,
            performance_monitoring=True
        )
    
    @classmethod
    def create_comprehensive_config(cls) -> "ValidationConfig":
        """Create comprehensive validation configuration."""
        return cls(
            validation_level=ValidationLevel.COMPREHENSIVE,
            enabled_types=[
                ValidationType.FUNCTIONAL,
                ValidationType.DATA_QUALITY,
                ValidationType.PERFORMANCE,
                ValidationType.SECURITY
            ],
            collect_evidence=True,
            evidence_types=[
                "screenshots", "network_logs", "dom_snapshots", 
                "execution_logs", "video_recording", "performance_metrics"
            ],
            enable_llm_validation=True,
            llm_self_validation=True,
            llm_cross_validation=True,
            data_quality_checks=True,
            performance_monitoring=True,
            security_checks=True,
            predictive_validation=True
        )
    
    @classmethod
    def create_paranoid_config(cls) -> "ValidationConfig":
        """Create paranoid validation configuration (maximum validation)."""
        return cls(
            validation_level=ValidationLevel.PARANOID,
            enabled_types=list(ValidationType),
            collect_evidence=True,
            evidence_types=[
                "screenshots", "network_logs", "dom_snapshots", 
                "execution_logs", "video_recording", "performance_metrics",
                "memory_snapshots", "security_audit", "compliance_check"
            ],
            enable_llm_validation=True,
            llm_self_validation=True,
            llm_cross_validation=True,
            data_quality_checks=True,
            data_completeness_threshold=0.99,
            data_accuracy_threshold=0.95,
            performance_monitoring=True,
            security_checks=True,
            privacy_compliance=True,
            predictive_validation=True,
            auto_rule_generation=True,
            validation_learning=True
        )
    
    def get_phase_config(self, phase: ValidationPhase) -> PhaseConfig:
        """Get configuration for a specific phase."""
        phase_configs = {
            ValidationPhase.PRE_EXECUTION: self.pre_execution,
            ValidationPhase.DURING_EXECUTION: self.during_execution,
            ValidationPhase.POST_EXECUTION: self.post_execution,
            ValidationPhase.CONTINUOUS: self.continuous
        }
        return phase_configs.get(phase, PhaseConfig())
    
    def is_type_enabled(self, validation_type: ValidationType) -> bool:
        """Check if a validation type is enabled."""
        return validation_type in self.enabled_types
    
    def should_collect_evidence(self, evidence_type: str) -> bool:
        """Check if specific evidence type should be collected."""
        return self.collect_evidence and evidence_type in self.evidence_types


# Predefined configurations for common use cases
VALIDATION_CONFIGS = {
    "disabled": ValidationConfig(validation_level=ValidationLevel.DISABLED),
    "basic": ValidationConfig.create_basic_config(),
    "standard": ValidationConfig.create_standard_config(),
    "comprehensive": ValidationConfig.create_comprehensive_config(),
    "paranoid": ValidationConfig.create_paranoid_config()
}


def get_validation_config(level: str = "standard") -> ValidationConfig:
    """Get predefined validation configuration by level."""
    return VALIDATION_CONFIGS.get(level, ValidationConfig.create_standard_config())
