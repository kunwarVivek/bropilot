"""
Step Validator

Validates individual execution steps during task execution.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timezone

from .base_validator import BaseValidator
from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationSeverity
from ..core.evidence_collector import EvidenceCollector


class StepValidator(BaseValidator):
    """Validates individual execution steps during task execution."""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.step_history: List[Dict[str, Any]] = []
        self.current_step: Optional[Dict[str, Any]] = None
    
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Validate execution step."""
        # Validate required context
        required_keys = ["step_info"]
        if not self.validate_required_context(context, required_keys):
            return
        
        step_info = context["step_info"]
        
        # Validate step structure
        await self._validate_step_structure(step_info, evidence_collector)
        
        # Validate step execution
        await self._validate_step_execution(step_info, context, evidence_collector)
        
        # Validate step timing
        await self._validate_step_timing(step_info, evidence_collector)
        
        # Validate step dependencies
        await self._validate_step_dependencies(step_info, context, evidence_collector)
        
        # Store step for history
        self._record_step(step_info)
    
    async def _validate_step_structure(self, step_info: Dict[str, Any], 
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate step structure and required fields."""
        required_fields = ["step_id", "action", "status"]
        missing_fields = [field for field in required_fields if field not in step_info]
        
        if missing_fields:
            self.add_error(
                f"Step missing required fields: {', '.join(missing_fields)}",
                "step_structure",
                {"missing_fields": missing_fields, "step_info": step_info},
                "Ensure all execution steps include required metadata"
            )
            return
        
        # Validate step ID format
        step_id = step_info.get("step_id")
        if not isinstance(step_id, str) or not step_id.strip():
            self.add_error(
                "Invalid step ID format",
                "step_id_format",
                {"step_id": step_id},
                "Step ID must be a non-empty string"
            )
        
        # Validate action field
        action = step_info.get("action")
        if not isinstance(action, str) or not action.strip():
            self.add_error(
                "Invalid action format",
                "action_format",
                {"action": action},
                "Action must be a non-empty string describing the step"
            )
        
        # Validate status
        valid_statuses = ["pending", "running", "completed", "failed", "skipped"]
        status = step_info.get("status")
        if status not in valid_statuses:
            self.add_error(
                f"Invalid step status: {status}",
                "step_status",
                {"status": status, "valid_statuses": valid_statuses},
                f"Status must be one of: {', '.join(valid_statuses)}"
            )
        
        self.add_info(
            f"Step structure validated: {step_id}",
            "step_structure",
            {"step_id": step_id, "action": action, "status": status}
        )
    
    async def _validate_step_execution(self, step_info: Dict[str, Any], 
                                     context: Dict[str, Any],
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate step execution results."""
        status = step_info.get("status")
        step_id = step_info.get("step_id", "unknown")
        
        if status == "completed":
            await self._validate_successful_execution(step_info, context, evidence_collector)
        elif status == "failed":
            await self._validate_failed_execution(step_info, context, evidence_collector)
        elif status == "running":
            await self._validate_running_execution(step_info, context, evidence_collector)
        
        # Validate execution results
        result = step_info.get("result")
        if status == "completed" and result is None:
            self.add_warning(
                f"Completed step {step_id} has no result",
                "missing_result",
                {"step_id": step_id, "status": status},
                "Consider capturing step execution results for better traceability"
            )
        
        # Validate error information for failed steps
        if status == "failed":
            error_info = step_info.get("error")
            if not error_info:
                self.add_warning(
                    f"Failed step {step_id} has no error information",
                    "missing_error_info",
                    {"step_id": step_id},
                    "Include error details for failed steps to aid debugging"
                )
    
    async def _validate_successful_execution(self, step_info: Dict[str, Any], 
                                           context: Dict[str, Any],
                                           evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate successful step execution."""
        step_id = step_info.get("step_id")
        result = step_info.get("result")
        
        # Check if result meets expectations
        expected_result = step_info.get("expected_result")
        if expected_result and result != expected_result:
            self.add_warning(
                f"Step {step_id} result differs from expected",
                "result_mismatch",
                {
                    "step_id": step_id,
                    "expected": expected_result,
                    "actual": result
                },
                "Review step logic to ensure expected outcomes"
            )
        
        # Validate execution time
        execution_time = step_info.get("execution_time", 0)
        max_execution_time = step_info.get("max_execution_time")
        
        if max_execution_time and execution_time > max_execution_time:
            self.add_warning(
                f"Step {step_id} execution time exceeded limit: {execution_time}s > {max_execution_time}s",
                "execution_time_exceeded",
                {
                    "step_id": step_id,
                    "execution_time": execution_time,
                    "max_execution_time": max_execution_time
                },
                "Consider optimizing step execution or adjusting time limits"
            )
        
        self.add_info(
            f"Step {step_id} executed successfully",
            "step_success",
            {"step_id": step_id, "execution_time": execution_time}
        )
        
        # Collect success evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "step_success",
                {
                    "step_id": step_id,
                    "result": result,
                    "execution_time": execution_time,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                f"step_success_{step_id}.json"
            )
    
    async def _validate_failed_execution(self, step_info: Dict[str, Any], 
                                       context: Dict[str, Any],
                                       evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate failed step execution."""
        step_id = step_info.get("step_id")
        error_info = step_info.get("error", {})
        
        # Analyze error information
        error_type = error_info.get("type", "unknown")
        error_message = error_info.get("message", "No error message")
        
        # Categorize error severity
        critical_errors = ["timeout", "system_error", "security_error"]
        if error_type in critical_errors:
            self.add_error(
                f"Critical error in step {step_id}: {error_message}",
                "critical_step_error",
                {
                    "step_id": step_id,
                    "error_type": error_type,
                    "error_message": error_message
                },
                "Investigate and resolve critical error before proceeding"
            )
        else:
            self.add_warning(
                f"Step {step_id} failed: {error_message}",
                "step_failure",
                {
                    "step_id": step_id,
                    "error_type": error_type,
                    "error_message": error_message
                },
                "Review step execution logic and error handling"
            )
        
        # Check retry information
        retry_count = step_info.get("retry_count", 0)
        max_retries = step_info.get("max_retries", 0)
        
        if retry_count >= max_retries:
            self.add_error(
                f"Step {step_id} exhausted all retries ({retry_count}/{max_retries})",
                "retries_exhausted",
                {
                    "step_id": step_id,
                    "retry_count": retry_count,
                    "max_retries": max_retries
                },
                "Consider increasing retry limits or fixing underlying issues"
            )
        
        # Collect failure evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "step_failure",
                {
                    "step_id": step_id,
                    "error_info": error_info,
                    "retry_count": retry_count,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                f"step_failure_{step_id}.json"
            )
    
    async def _validate_running_execution(self, step_info: Dict[str, Any], 
                                        context: Dict[str, Any],
                                        evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate currently running step execution."""
        step_id = step_info.get("step_id")
        start_time = step_info.get("start_time")
        
        if start_time:
            # Check if step has been running too long
            current_time = datetime.now(timezone.utc)
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            
            running_time = (current_time - start_time).total_seconds()
            max_execution_time = step_info.get("max_execution_time", 300)  # 5 minutes default
            
            if running_time > max_execution_time:
                self.add_warning(
                    f"Step {step_id} has been running for {running_time:.1f}s (limit: {max_execution_time}s)",
                    "long_running_step",
                    {
                        "step_id": step_id,
                        "running_time": running_time,
                        "max_execution_time": max_execution_time
                    },
                    "Consider checking if step is stuck or needs more time"
                )
        
        self.add_info(
            f"Step {step_id} is currently running",
            "step_running",
            {"step_id": step_id}
        )
    
    async def _validate_step_timing(self, step_info: Dict[str, Any], 
                                  evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate step timing and performance."""
        step_id = step_info.get("step_id")
        start_time = step_info.get("start_time")
        end_time = step_info.get("end_time")
        execution_time = step_info.get("execution_time")
        
        # Validate timing consistency
        if start_time and end_time and execution_time:
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            calculated_time = (end_time - start_time).total_seconds()
            time_diff = abs(calculated_time - execution_time)
            
            if time_diff > 1.0:  # Allow 1 second tolerance
                self.add_warning(
                    f"Step {step_id} timing inconsistency: calculated {calculated_time:.2f}s vs reported {execution_time:.2f}s",
                    "timing_inconsistency",
                    {
                        "step_id": step_id,
                        "calculated_time": calculated_time,
                        "reported_time": execution_time,
                        "difference": time_diff
                    },
                    "Check timing calculation logic"
                )
        
        # Performance analysis
        if execution_time:
            # Categorize performance
            if execution_time < 1.0:
                performance_category = "fast"
            elif execution_time < 10.0:
                performance_category = "normal"
            elif execution_time < 60.0:
                performance_category = "slow"
            else:
                performance_category = "very_slow"
            
            if performance_category in ["slow", "very_slow"]:
                self.add_info(
                    f"Step {step_id} performance: {performance_category} ({execution_time:.2f}s)",
                    "step_performance",
                    {
                        "step_id": step_id,
                        "execution_time": execution_time,
                        "performance_category": performance_category
                    }
                )
    
    async def _validate_step_dependencies(self, step_info: Dict[str, Any], 
                                        context: Dict[str, Any],
                                        evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate step dependencies."""
        step_id = step_info.get("step_id")
        dependencies = step_info.get("dependencies", [])
        
        if not dependencies:
            return
        
        # Check if dependencies were completed
        completed_steps = {step["step_id"] for step in self.step_history if step.get("status") == "completed"}
        
        missing_dependencies = [dep for dep in dependencies if dep not in completed_steps]
        
        if missing_dependencies:
            self.add_error(
                f"Step {step_id} has unmet dependencies: {', '.join(missing_dependencies)}",
                "unmet_dependencies",
                {
                    "step_id": step_id,
                    "missing_dependencies": missing_dependencies,
                    "completed_steps": list(completed_steps)
                },
                "Ensure dependent steps complete before executing this step"
            )
        else:
            self.add_info(
                f"Step {step_id} dependencies satisfied",
                "dependencies_satisfied",
                {"step_id": step_id, "dependencies": dependencies}
            )
    
    def _record_step(self, step_info: Dict[str, Any]) -> None:
        """Record step in history."""
        step_record = {
            **step_info,
            "validation_timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.step_history.append(step_record)
        self.current_step = step_record
    
    def get_step_history(self) -> List[Dict[str, Any]]:
        """Get step execution history."""
        return self.step_history.copy()
    
    def get_current_step(self) -> Optional[Dict[str, Any]]:
        """Get current step information."""
        return self.current_step
    
    def get_step_statistics(self) -> Dict[str, Any]:
        """Get step execution statistics."""
        if not self.step_history:
            return {"total_steps": 0}
        
        total_steps = len(self.step_history)
        completed_steps = sum(1 for step in self.step_history if step.get("status") == "completed")
        failed_steps = sum(1 for step in self.step_history if step.get("status") == "failed")
        
        execution_times = [
            step.get("execution_time", 0) 
            for step in self.step_history 
            if step.get("execution_time") is not None
        ]
        
        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "failed_steps": failed_steps,
            "success_rate": completed_steps / total_steps if total_steps > 0 else 0,
            "average_execution_time": sum(execution_times) / len(execution_times) if execution_times else 0,
            "total_execution_time": sum(execution_times)
        }
    
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        return [
            "step_structure",
            "step_id_format",
            "action_format",
            "step_status",
            "missing_result",
            "missing_error_info",
            "result_mismatch",
            "execution_time_exceeded",
            "critical_step_error",
            "step_failure",
            "retries_exhausted",
            "long_running_step",
            "timing_inconsistency",
            "step_performance",
            "unmet_dependencies",
            "dependencies_satisfied"
        ]
