"""
Validation Engine

Central orchestrator for all validation activities across phases and strategies.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, Type
from datetime import datetime, timezone

from .validation_config import ValidationConfig, ValidationPhase, ValidationType
from .validation_result import ValidationResult, ValidationStatus, ValidationIssue, ValidationSeverity
from .evidence_collector import EvidenceCollector
from ..validators.base_validator import BaseValidator
from ..validators.outcome_validator import OutcomeValidator
from ..validators.data_quality_validator import DataQualityValidator
from ..validators.step_validator import StepValidator
from ..validators.checkpoint_validator import CheckpointValidator
from ..validators.performance_validator import PerformanceValidator
from ..validators.security_validator import SecurityValidator
from ..validators.llm_validator import LLMValidator

from src.infrastructure.logging.logger import StructuredLogger


class ValidationEngine:
    """Central validation engine orchestrating all validation activities."""
    
    def __init__(self, config: ValidationConfig = None):
        self.config = config or ValidationConfig()
        self.logger = StructuredLogger("validation_engine")
        
        # Validator registry
        self.validators: Dict[str, BaseValidator] = {}
        self.phase_validators: Dict[ValidationPhase, List[BaseValidator]] = {
            phase: [] for phase in ValidationPhase
        }
        
        # Evidence collector
        self.evidence_collector: Optional[EvidenceCollector] = None
        
        # Validation state
        self.current_validation: Optional[ValidationResult] = None
        self.validation_history: List[ValidationResult] = []
        
        # Initialize validators
        self._initialize_validators()
        
        self.logger.info("Validation engine initialized", 
                        validation_level=self.config.validation_level.value)
    
    def _initialize_validators(self) -> None:
        """Initialize and register validators based on configuration."""
        try:
            # Core validators (always available)
            self.validators["outcome"] = OutcomeValidator(self.config)
            self.validators["step"] = StepValidator(self.config)
            self.validators["checkpoint"] = CheckpointValidator(self.config)
            
            # Optional validators based on configuration
            if self.config.is_type_enabled(ValidationType.DATA_QUALITY):
                self.validators["data_quality"] = DataQualityValidator(self.config)
            
            if self.config.is_type_enabled(ValidationType.PERFORMANCE):
                self.validators["performance"] = PerformanceValidator(self.config)
            
            if self.config.is_type_enabled(ValidationType.SECURITY):
                self.validators["security"] = SecurityValidator(self.config)
            
            if self.config.enable_llm_validation:
                self.validators["llm"] = LLMValidator(self.config)
            
            # Assign validators to phases
            self._assign_validators_to_phases()
            
            self.logger.info("Validators initialized", 
                           validator_count=len(self.validators),
                           validators=list(self.validators.keys()))
            
        except Exception as e:
            self.logger.error("Failed to initialize validators", error=str(e))
            raise
    
    def _assign_validators_to_phases(self) -> None:
        """Assign validators to appropriate execution phases."""
        # Pre-execution validators
        self.phase_validators[ValidationPhase.PRE_EXECUTION] = [
            self.validators.get("security"),
            self.validators.get("llm")
        ]
        
        # During execution validators
        self.phase_validators[ValidationPhase.DURING_EXECUTION] = [
            self.validators.get("step"),
            self.validators.get("checkpoint"),
            self.validators.get("performance")
        ]
        
        # Post-execution validators
        self.phase_validators[ValidationPhase.POST_EXECUTION] = [
            self.validators.get("outcome"),
            self.validators.get("data_quality"),
            self.validators.get("llm")
        ]
        
        # Continuous validators
        self.phase_validators[ValidationPhase.CONTINUOUS] = [
            self.validators.get("performance"),
            self.validators.get("security")
        ]
        
        # Filter out None validators
        for phase in ValidationPhase:
            self.phase_validators[phase] = [
                v for v in self.phase_validators[phase] if v is not None
            ]
    
    async def start_validation(self, task_id: str, task_definition: Dict[str, Any]) -> ValidationResult:
        """Start validation for a task."""
        try:
            # Create validation result
            self.current_validation = ValidationResult(task_id, self.config.dict())
            
            # Initialize evidence collector if enabled
            if self.config.collect_evidence:
                self.evidence_collector = EvidenceCollector(
                    evidence_dir="evidence",
                    task_id=task_id
                )
                self.current_validation.add_evidence(
                    "evidence_dir", 
                    str(self.evidence_collector.task_evidence_dir)
                )
            
            self.logger.info("Validation started", 
                           task_id=task_id,
                           validation_id=self.current_validation.validation_id)
            
            return self.current_validation
            
        except Exception as e:
            self.logger.error("Failed to start validation", 
                            task_id=task_id, error=str(e))
            raise
    
    async def validate_phase(self, phase: ValidationPhase, 
                           context: Dict[str, Any]) -> None:
        """Execute validation for a specific phase."""
        if not self.current_validation:
            raise ValueError("No active validation session")
        
        try:
            phase_config = self.config.get_phase_config(phase)
            if not phase_config.enabled:
                self.logger.info("Phase validation disabled", phase=phase.value)
                return
            
            # Start phase
            phase_result = self.current_validation.start_phase(phase.value)
            
            self.logger.info("Starting phase validation", 
                           phase=phase.value,
                           validator_count=len(self.phase_validators[phase]))
            
            # Get validators for this phase
            validators = self.phase_validators[phase]
            
            if phase_config.parallel_execution:
                # Run validators in parallel
                await self._run_validators_parallel(validators, phase, context)
            else:
                # Run validators sequentially
                await self._run_validators_sequential(validators, phase, context, 
                                                   phase_config.fail_fast)
            
            # Complete phase
            self.current_validation.complete_phase(phase.value)
            
            self.logger.info("Phase validation completed", 
                           phase=phase.value,
                           status=phase_result.status.value)
            
        except Exception as e:
            self.logger.error("Phase validation failed", 
                            phase=phase.value, error=str(e))
            
            # Add error to validation result
            issue = ValidationIssue(
                message=f"Phase validation failed: {str(e)}",
                severity=ValidationSeverity.ERROR,
                rule_name="phase_execution",
                phase=phase.value
            )
            self.current_validation.add_issue(issue, phase.value)
            
            # Complete phase with error status
            self.current_validation.complete_phase(phase.value, ValidationStatus.ERROR)
    
    async def _run_validators_sequential(self, validators: List[BaseValidator], 
                                       phase: ValidationPhase, context: Dict[str, Any],
                                       fail_fast: bool = False) -> None:
        """Run validators sequentially."""
        for validator in validators:
            try:
                await validator.validate(context, self.evidence_collector)
                
                # Check for validation issues
                if validator.has_errors() and fail_fast:
                    self.logger.warning("Fail-fast triggered", 
                                      validator=validator.__class__.__name__)
                    break
                    
            except Exception as e:
                self.logger.error("Validator failed", 
                                validator=validator.__class__.__name__, 
                                error=str(e))
                
                # Add validator error to results
                issue = ValidationIssue(
                    message=f"Validator {validator.__class__.__name__} failed: {str(e)}",
                    severity=ValidationSeverity.ERROR,
                    rule_name=validator.__class__.__name__.lower(),
                    phase=phase.value
                )
                self.current_validation.add_issue(issue, phase.value)
                
                if fail_fast:
                    break
    
    async def _run_validators_parallel(self, validators: List[BaseValidator], 
                                     phase: ValidationPhase, context: Dict[str, Any]) -> None:
        """Run validators in parallel."""
        tasks = []
        for validator in validators:
            task = asyncio.create_task(
                self._run_single_validator(validator, context, phase)
            )
            tasks.append(task)
        
        # Wait for all validators to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_single_validator(self, validator: BaseValidator, 
                                  context: Dict[str, Any], 
                                  phase: ValidationPhase) -> None:
        """Run a single validator with error handling."""
        try:
            await validator.validate(context, self.evidence_collector)
            
        except Exception as e:
            self.logger.error("Validator failed", 
                            validator=validator.__class__.__name__, 
                            error=str(e))
            
            # Add validator error to results
            issue = ValidationIssue(
                message=f"Validator {validator.__class__.__name__} failed: {str(e)}",
                severity=ValidationSeverity.ERROR,
                rule_name=validator.__class__.__name__.lower(),
                phase=phase.value
            )
            self.current_validation.add_issue(issue, phase.value)
    
    async def complete_validation(self) -> ValidationResult:
        """Complete the current validation session."""
        if not self.current_validation:
            raise ValueError("No active validation session")
        
        try:
            # Save evidence if collector is available
            if self.evidence_collector:
                evidence_paths = self.evidence_collector.save_all_evidence()
                for evidence_type, path in evidence_paths.items():
                    self.current_validation.add_evidence(evidence_type, path)
            
            # Complete validation
            self.current_validation.complete_validation()
            
            # Add to history
            self.validation_history.append(self.current_validation)
            
            # Log completion
            self.logger.info("Validation completed", 
                           validation_id=self.current_validation.validation_id,
                           status=self.current_validation.overall_status.value,
                           duration=self.current_validation.duration,
                           success_rate=self.current_validation.metrics.success_rate)
            
            # Return result and clear current validation
            result = self.current_validation
            self.current_validation = None
            self.evidence_collector = None
            
            return result
            
        except Exception as e:
            self.logger.error("Failed to complete validation", error=str(e))
            raise
    
    def add_custom_validator(self, name: str, validator: BaseValidator, 
                           phases: List[ValidationPhase] = None) -> None:
        """Add a custom validator to the engine."""
        self.validators[name] = validator
        
        # Add to specified phases or all phases
        target_phases = phases or list(ValidationPhase)
        for phase in target_phases:
            if validator not in self.phase_validators[phase]:
                self.phase_validators[phase].append(validator)
        
        self.logger.info("Custom validator added", 
                        name=name, phases=[p.value for p in target_phases])
    
    def get_validation_history(self, limit: int = 10) -> List[ValidationResult]:
        """Get recent validation history."""
        return self.validation_history[-limit:]
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if not self.validation_history:
            return {"total_validations": 0}
        
        total_validations = len(self.validation_history)
        successful_validations = sum(
            1 for v in self.validation_history if v.is_successful
        )
        
        return {
            "total_validations": total_validations,
            "successful_validations": successful_validations,
            "success_rate": successful_validations / total_validations,
            "average_duration": sum(v.duration for v in self.validation_history) / total_validations,
            "total_issues": sum(len(v.get_all_issues()) for v in self.validation_history),
            "average_issues_per_validation": sum(len(v.get_all_issues()) for v in self.validation_history) / total_validations
        }
