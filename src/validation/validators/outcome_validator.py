"""
Outcome Validator

Validates task outcomes against expected results and success criteria.
"""

import json
import re
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .base_validator import BaseValidator
from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationSeverity
from ..core.evidence_collector import EvidenceCollector


class OutcomeValidator(BaseValidator):
    """Validates task execution outcomes against expected results."""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.success_criteria: Dict[str, Any] = {}
        self.expected_outcomes: Dict[str, Any] = {}
    
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Validate task outcomes."""
        # Validate required context
        required_keys = ["task_result", "task_definition"]
        if not self.validate_required_context(context, required_keys):
            return
        
        task_result = context["task_result"]
        task_definition = context["task_definition"]
        
        # Extract success criteria and expected outcomes
        self._extract_success_criteria(task_definition)
        
        # Perform outcome validations
        await self._validate_task_completion(task_result, evidence_collector)
        await self._validate_expected_outcomes(task_result, evidence_collector)
        await self._validate_data_extraction(task_result, context, evidence_collector)
        await self._validate_side_effects(task_result, context, evidence_collector)
        await self._validate_business_rules(task_result, context, evidence_collector)
    
    def _extract_success_criteria(self, task_definition: Dict[str, Any]) -> None:
        """Extract success criteria from task definition."""
        self.success_criteria = task_definition.get("success_criteria", {})
        self.expected_outcomes = task_definition.get("expected_outcomes", {})
        
        # Default success criteria if not specified
        if not self.success_criteria:
            self.success_criteria = {
                "completion_required": True,
                "error_tolerance": 0,
                "min_data_quality": 0.8
            }
    
    async def _validate_task_completion(self, task_result: Dict[str, Any], 
                                      evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate that the task completed successfully."""
        completion_status = task_result.get("status", "unknown")
        completion_required = self.success_criteria.get("completion_required", True)
        
        if completion_required and completion_status != "completed":
            self.add_error(
                f"Task did not complete successfully. Status: {completion_status}",
                "task_completion",
                {
                    "expected_status": "completed",
                    "actual_status": completion_status,
                    "completion_required": completion_required
                },
                "Check task execution logs for errors and retry if necessary"
            )
        elif completion_status == "completed":
            self.add_info(
                "Task completed successfully",
                "task_completion",
                {"status": completion_status}
            )
        
        # Validate execution time if specified
        max_execution_time = self.success_criteria.get("max_execution_time")
        if max_execution_time:
            actual_time = task_result.get("execution_time", 0)
            if actual_time > max_execution_time:
                self.add_warning(
                    f"Task execution time exceeded limit: {actual_time}s > {max_execution_time}s",
                    "execution_time",
                    {
                        "max_execution_time": max_execution_time,
                        "actual_execution_time": actual_time
                    },
                    "Consider optimizing task execution or increasing time limit"
                )
        
        # Collect completion evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "task_completion",
                {
                    "status": completion_status,
                    "execution_time": task_result.get("execution_time"),
                    "completion_timestamp": datetime.now().isoformat(),
                    "success_criteria": self.success_criteria
                },
                "task_completion_validation.json"
            )
    
    async def _validate_expected_outcomes(self, task_result: Dict[str, Any], 
                                        evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate actual outcomes against expected outcomes."""
        if not self.expected_outcomes:
            self.add_info(
                "No expected outcomes specified for validation",
                "expected_outcomes"
            )
            return
        
        actual_outcomes = task_result.get("outcomes", {})
        validation_results = {}
        
        for outcome_key, expected_value in self.expected_outcomes.items():
            actual_value = actual_outcomes.get(outcome_key)
            
            if actual_value is None:
                self.add_error(
                    f"Expected outcome '{outcome_key}' not found in results",
                    "missing_outcome",
                    {
                        "outcome_key": outcome_key,
                        "expected_value": expected_value
                    },
                    f"Ensure task execution produces '{outcome_key}' outcome"
                )
                validation_results[outcome_key] = {"status": "missing"}
                continue
            
            # Compare outcomes based on type
            match_result = self._compare_outcomes(expected_value, actual_value)
            validation_results[outcome_key] = match_result
            
            if not match_result["matches"]:
                self.add_error(
                    f"Outcome '{outcome_key}' does not match expected value",
                    "outcome_mismatch",
                    {
                        "outcome_key": outcome_key,
                        "expected_value": expected_value,
                        "actual_value": actual_value,
                        "comparison_details": match_result
                    },
                    f"Review task logic for '{outcome_key}' generation"
                )
            else:
                self.add_info(
                    f"Outcome '{outcome_key}' matches expected value",
                    "outcome_match",
                    {"outcome_key": outcome_key}
                )
        
        # Collect outcome validation evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "outcome_validation",
                {
                    "expected_outcomes": self.expected_outcomes,
                    "actual_outcomes": actual_outcomes,
                    "validation_results": validation_results,
                    "validation_timestamp": datetime.now().isoformat()
                },
                "outcome_validation.json"
            )
    
    def _compare_outcomes(self, expected: Any, actual: Any) -> Dict[str, Any]:
        """Compare expected and actual outcomes."""
        comparison_result = {
            "matches": False,
            "expected_type": type(expected).__name__,
            "actual_type": type(actual).__name__,
            "comparison_method": "exact"
        }
        
        # Exact match
        if expected == actual:
            comparison_result["matches"] = True
            return comparison_result
        
        # Type-specific comparisons
        if isinstance(expected, str) and isinstance(actual, str):
            return self._compare_strings(expected, actual)
        elif isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
            return self._compare_numbers(expected, actual)
        elif isinstance(expected, list) and isinstance(actual, list):
            return self._compare_lists(expected, actual)
        elif isinstance(expected, dict) and isinstance(actual, dict):
            return self._compare_dicts(expected, actual)
        
        return comparison_result
    
    def _compare_strings(self, expected: str, actual: str) -> Dict[str, Any]:
        """Compare string outcomes with fuzzy matching."""
        result = {
            "matches": False,
            "expected_type": "str",
            "actual_type": "str",
            "comparison_method": "string"
        }
        
        # Exact match
        if expected == actual:
            result["matches"] = True
            result["comparison_method"] = "exact"
            return result
        
        # Case-insensitive match
        if expected.lower() == actual.lower():
            result["matches"] = True
            result["comparison_method"] = "case_insensitive"
            return result
        
        # Substring match
        if expected.lower() in actual.lower() or actual.lower() in expected.lower():
            result["matches"] = True
            result["comparison_method"] = "substring"
            return result
        
        # Regex match (if expected looks like a regex)
        if expected.startswith("^") or expected.endswith("$") or "*" in expected:
            try:
                if re.search(expected, actual, re.IGNORECASE):
                    result["matches"] = True
                    result["comparison_method"] = "regex"
                    return result
            except re.error:
                pass
        
        # Calculate similarity score
        similarity = self._calculate_string_similarity(expected, actual)
        result["similarity_score"] = similarity
        
        # Consider match if similarity is high enough
        similarity_threshold = self.success_criteria.get("string_similarity_threshold", 0.8)
        if similarity >= similarity_threshold:
            result["matches"] = True
            result["comparison_method"] = "similarity"
        
        return result
    
    def _compare_numbers(self, expected: Union[int, float], 
                        actual: Union[int, float]) -> Dict[str, Any]:
        """Compare numeric outcomes with tolerance."""
        result = {
            "matches": False,
            "expected_type": type(expected).__name__,
            "actual_type": type(actual).__name__,
            "comparison_method": "numeric"
        }
        
        # Exact match
        if expected == actual:
            result["matches"] = True
            result["comparison_method"] = "exact"
            return result
        
        # Tolerance-based match
        tolerance = self.success_criteria.get("numeric_tolerance", 0.01)
        if isinstance(tolerance, float) and tolerance < 1.0:
            # Relative tolerance
            relative_diff = abs(expected - actual) / max(abs(expected), abs(actual), 1e-10)
            if relative_diff <= tolerance:
                result["matches"] = True
                result["comparison_method"] = "relative_tolerance"
                result["relative_difference"] = relative_diff
        else:
            # Absolute tolerance
            absolute_diff = abs(expected - actual)
            if absolute_diff <= tolerance:
                result["matches"] = True
                result["comparison_method"] = "absolute_tolerance"
                result["absolute_difference"] = absolute_diff
        
        return result
    
    def _compare_lists(self, expected: List, actual: List) -> Dict[str, Any]:
        """Compare list outcomes."""
        result = {
            "matches": False,
            "expected_type": "list",
            "actual_type": "list",
            "comparison_method": "list",
            "expected_length": len(expected),
            "actual_length": len(actual)
        }
        
        # Exact match
        if expected == actual:
            result["matches"] = True
            result["comparison_method"] = "exact"
            return result
        
        # Length comparison
        if len(expected) != len(actual):
            length_tolerance = self.success_criteria.get("list_length_tolerance", 0)
            if abs(len(expected) - len(actual)) > length_tolerance:
                return result
        
        # Element-wise comparison
        matching_elements = 0
        for i, exp_item in enumerate(expected):
            if i < len(actual):
                item_comparison = self._compare_outcomes(exp_item, actual[i])
                if item_comparison["matches"]:
                    matching_elements += 1
        
        # Calculate match percentage
        match_percentage = matching_elements / max(len(expected), len(actual), 1)
        result["match_percentage"] = match_percentage
        
        # Consider match if percentage is high enough
        list_match_threshold = self.success_criteria.get("list_match_threshold", 0.8)
        if match_percentage >= list_match_threshold:
            result["matches"] = True
            result["comparison_method"] = "partial_match"
        
        return result
    
    def _compare_dicts(self, expected: Dict, actual: Dict) -> Dict[str, Any]:
        """Compare dictionary outcomes."""
        result = {
            "matches": False,
            "expected_type": "dict",
            "actual_type": "dict",
            "comparison_method": "dict",
            "expected_keys": len(expected),
            "actual_keys": len(actual)
        }
        
        # Exact match
        if expected == actual:
            result["matches"] = True
            result["comparison_method"] = "exact"
            return result
        
        # Key-wise comparison
        matching_keys = 0
        total_keys = set(expected.keys()) | set(actual.keys())
        
        for key in total_keys:
            if key in expected and key in actual:
                key_comparison = self._compare_outcomes(expected[key], actual[key])
                if key_comparison["matches"]:
                    matching_keys += 1
        
        # Calculate match percentage
        match_percentage = matching_keys / max(len(total_keys), 1)
        result["match_percentage"] = match_percentage
        
        # Consider match if percentage is high enough
        dict_match_threshold = self.success_criteria.get("dict_match_threshold", 0.8)
        if match_percentage >= dict_match_threshold:
            result["matches"] = True
            result["comparison_method"] = "partial_match"
        
        return result
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity using simple algorithm."""
        # Simple Levenshtein-like similarity
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
        
        # Convert to lowercase for comparison
        s1, s2 = str1.lower(), str2.lower()
        
        # Calculate character overlap
        common_chars = set(s1) & set(s2)
        total_chars = set(s1) | set(s2)
        
        if not total_chars:
            return 1.0
        
        return len(common_chars) / len(total_chars)
    
    async def _validate_data_extraction(self, task_result: Dict[str, Any], 
                                      context: Dict[str, Any],
                                      evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate extracted data quality and completeness."""
        extracted_data = task_result.get("extracted_data")
        if not extracted_data:
            return
        
        # Validate data completeness
        min_data_quality = self.success_criteria.get("min_data_quality", 0.8)
        
        if isinstance(extracted_data, list):
            # Check for empty or null items
            valid_items = [item for item in extracted_data if item is not None and item != ""]
            completeness = len(valid_items) / len(extracted_data) if extracted_data else 0
            
            if completeness < min_data_quality:
                self.add_warning(
                    f"Data completeness below threshold: {completeness:.2%} < {min_data_quality:.2%}",
                    "data_completeness",
                    {
                        "completeness": completeness,
                        "threshold": min_data_quality,
                        "total_items": len(extracted_data),
                        "valid_items": len(valid_items)
                    },
                    "Review data extraction logic for missing or null values"
                )
        
        # Collect data validation evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "data_extraction_validation",
                {
                    "extracted_data_summary": {
                        "type": type(extracted_data).__name__,
                        "length": len(extracted_data) if hasattr(extracted_data, "__len__") else "unknown",
                        "sample": str(extracted_data)[:500] if extracted_data else None
                    },
                    "validation_timestamp": datetime.now().isoformat()
                },
                "data_extraction_validation.json"
            )
    
    async def _validate_side_effects(self, task_result: Dict[str, Any], 
                                   context: Dict[str, Any],
                                   evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate for unintended side effects."""
        # Check for unexpected changes
        before_state = context.get("before_state", {})
        after_state = context.get("after_state", {})
        
        if before_state and after_state:
            unexpected_changes = self._detect_unexpected_changes(before_state, after_state)
            
            if unexpected_changes:
                self.add_warning(
                    f"Detected {len(unexpected_changes)} unexpected changes",
                    "side_effects",
                    {"unexpected_changes": unexpected_changes},
                    "Review task execution for unintended side effects"
                )
    
    def _detect_unexpected_changes(self, before: Dict[str, Any], 
                                 after: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect unexpected changes between states."""
        changes = []
        
        # Simple change detection (can be enhanced)
        all_keys = set(before.keys()) | set(after.keys())
        
        for key in all_keys:
            before_value = before.get(key)
            after_value = after.get(key)
            
            if before_value != after_value:
                changes.append({
                    "key": key,
                    "before": before_value,
                    "after": after_value,
                    "change_type": "modified" if key in before else "added" if key in after else "removed"
                })
        
        return changes
    
    async def _validate_business_rules(self, task_result: Dict[str, Any], 
                                     context: Dict[str, Any],
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate business-specific rules."""
        business_rules = self.success_criteria.get("business_rules", [])
        
        for rule in business_rules:
            rule_name = rule.get("name", "unknown_rule")
            rule_condition = rule.get("condition")
            rule_message = rule.get("message", f"Business rule '{rule_name}' violated")
            
            try:
                # Simple rule evaluation (can be enhanced with proper rule engine)
                if not self._evaluate_business_rule(rule_condition, task_result, context):
                    self.add_error(
                        rule_message,
                        f"business_rule_{rule_name}",
                        {"rule": rule, "task_result": task_result}
                    )
            except Exception as e:
                self.add_warning(
                    f"Failed to evaluate business rule '{rule_name}': {str(e)}",
                    f"business_rule_evaluation_{rule_name}",
                    {"rule": rule, "error": str(e)}
                )
    
    def _evaluate_business_rule(self, condition: str, task_result: Dict[str, Any], 
                              context: Dict[str, Any]) -> bool:
        """Evaluate a business rule condition."""
        # Simple condition evaluation (enhance as needed)
        # This is a basic implementation - in production, use a proper rule engine
        
        if not condition:
            return True
        
        # Create evaluation context
        eval_context = {
            "task_result": task_result,
            "context": context,
            "result": task_result  # Alias for convenience
        }
        
        try:
            # WARNING: eval() is dangerous in production - use a proper rule engine
            return bool(eval(condition, {"__builtins__": {}}, eval_context))
        except Exception:
            return False
    
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        return [
            "task_completion",
            "expected_outcomes",
            "outcome_mismatch",
            "execution_time",
            "data_completeness",
            "side_effects",
            "business_rules"
        ]
