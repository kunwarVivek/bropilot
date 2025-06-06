"""
Data Quality Validator

Validates the quality, completeness, and accuracy of extracted or processed data.
"""

import re
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from collections import Counter

from .base_validator import BaseValidator
from ..core.validation_config import ValidationConfig
from ..core.validation_result import ValidationSeverity
from ..core.evidence_collector import EvidenceCollector


class DataQualityValidator(BaseValidator):
    """Validates data quality across multiple dimensions."""
    
    def __init__(self, config: ValidationConfig):
        super().__init__(config)
        self.quality_thresholds = {
            "completeness": config.data_completeness_threshold,
            "accuracy": config.data_accuracy_threshold,
            "consistency": 0.90,
            "validity": 0.85,
            "uniqueness": 0.95
        }
    
    async def validate(self, context: Dict[str, Any], 
                      evidence_collector: Optional[EvidenceCollector] = None) -> None:
        """Validate data quality."""
        # Check if data quality validation is enabled
        if not self.config.data_quality_checks:
            self.add_info("Data quality validation disabled", "config_check")
            return
        
        # Validate required context
        if not self.validate_required_context(context, ["task_result"]):
            return
        
        task_result = context["task_result"]
        extracted_data = task_result.get("extracted_data")
        
        if not extracted_data:
            self.add_info("No extracted data found for validation", "no_data")
            return
        
        # Perform data quality validations
        await self._validate_completeness(extracted_data, evidence_collector)
        await self._validate_accuracy(extracted_data, context, evidence_collector)
        await self._validate_consistency(extracted_data, evidence_collector)
        await self._validate_validity(extracted_data, context, evidence_collector)
        await self._validate_uniqueness(extracted_data, evidence_collector)
        await self._validate_format_compliance(extracted_data, context, evidence_collector)
        
        # Generate overall quality score
        await self._calculate_quality_score(extracted_data, evidence_collector)
    
    async def _validate_completeness(self, data: Any, 
                                   evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate data completeness."""
        completeness_score = self._calculate_completeness(data)
        threshold = self.quality_thresholds["completeness"]
        
        if completeness_score < threshold:
            self.add_error(
                f"Data completeness below threshold: {completeness_score:.2%} < {threshold:.2%}",
                "data_completeness",
                {
                    "completeness_score": completeness_score,
                    "threshold": threshold,
                    "data_type": type(data).__name__
                },
                "Review data extraction logic to ensure all required fields are captured"
            )
        else:
            self.add_info(
                f"Data completeness acceptable: {completeness_score:.2%}",
                "data_completeness",
                {"completeness_score": completeness_score}
            )
        
        # Collect evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "completeness_analysis",
                {
                    "completeness_score": completeness_score,
                    "threshold": threshold,
                    "analysis_details": self._analyze_completeness_details(data)
                },
                "completeness_analysis.json"
            )
    
    def _calculate_completeness(self, data: Any) -> float:
        """Calculate data completeness score."""
        if isinstance(data, list):
            if not data:
                return 0.0
            
            total_items = len(data)
            complete_items = 0
            
            for item in data:
                if self._is_item_complete(item):
                    complete_items += 1
            
            return complete_items / total_items
        
        elif isinstance(data, dict):
            return self._calculate_dict_completeness(data)
        
        elif isinstance(data, str):
            return 1.0 if data.strip() else 0.0
        
        else:
            return 1.0 if data is not None else 0.0
    
    def _is_item_complete(self, item: Any) -> bool:
        """Check if a data item is complete."""
        if item is None:
            return False
        
        if isinstance(item, str):
            return bool(item.strip())
        
        if isinstance(item, dict):
            # Consider dict complete if it has at least one non-empty value
            return any(
                value is not None and (not isinstance(value, str) or value.strip())
                for value in item.values()
            )
        
        if isinstance(item, list):
            return len(item) > 0
        
        return True
    
    def _calculate_dict_completeness(self, data: Dict[str, Any]) -> float:
        """Calculate completeness for dictionary data."""
        if not data:
            return 0.0
        
        total_fields = len(data)
        complete_fields = sum(1 for value in data.values() if self._is_item_complete(value))
        
        return complete_fields / total_fields
    
    def _analyze_completeness_details(self, data: Any) -> Dict[str, Any]:
        """Analyze completeness details for evidence."""
        details = {
            "data_type": type(data).__name__,
            "total_size": len(data) if hasattr(data, "__len__") else 1
        }
        
        if isinstance(data, list):
            empty_items = sum(1 for item in data if not self._is_item_complete(item))
            details.update({
                "empty_items": empty_items,
                "complete_items": len(data) - empty_items,
                "empty_percentage": empty_items / len(data) if data else 0
            })
        
        elif isinstance(data, dict):
            empty_fields = sum(1 for value in data.values() if not self._is_item_complete(value))
            details.update({
                "empty_fields": empty_fields,
                "complete_fields": len(data) - empty_fields,
                "field_names": list(data.keys())
            })
        
        return details
    
    async def _validate_accuracy(self, data: Any, context: Dict[str, Any],
                                evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate data accuracy against known patterns or references."""
        accuracy_score = await self._calculate_accuracy(data, context)
        threshold = self.quality_thresholds["accuracy"]
        
        if accuracy_score < threshold:
            self.add_warning(
                f"Data accuracy below threshold: {accuracy_score:.2%} < {threshold:.2%}",
                "data_accuracy",
                {
                    "accuracy_score": accuracy_score,
                    "threshold": threshold
                },
                "Review data extraction patterns and validation rules"
            )
        else:
            self.add_info(
                f"Data accuracy acceptable: {accuracy_score:.2%}",
                "data_accuracy",
                {"accuracy_score": accuracy_score}
            )
    
    async def _calculate_accuracy(self, data: Any, context: Dict[str, Any]) -> float:
        """Calculate data accuracy score."""
        # Get expected patterns or reference data
        expected_patterns = context.get("expected_patterns", {})
        reference_data = context.get("reference_data")
        
        if not expected_patterns and not reference_data:
            return 1.0  # No reference to validate against
        
        if isinstance(data, list):
            return self._validate_list_accuracy(data, expected_patterns, reference_data)
        elif isinstance(data, dict):
            return self._validate_dict_accuracy(data, expected_patterns, reference_data)
        else:
            return self._validate_item_accuracy(data, expected_patterns, reference_data)
    
    def _validate_list_accuracy(self, data: List[Any], patterns: Dict[str, Any], 
                               reference: Any) -> float:
        """Validate accuracy for list data."""
        if not data:
            return 1.0
        
        accurate_items = 0
        for item in data:
            if self._validate_item_accuracy(item, patterns, reference) > 0.8:
                accurate_items += 1
        
        return accurate_items / len(data)
    
    def _validate_dict_accuracy(self, data: Dict[str, Any], patterns: Dict[str, Any], 
                               reference: Any) -> float:
        """Validate accuracy for dictionary data."""
        if not data:
            return 1.0
        
        accurate_fields = 0
        for key, value in data.items():
            field_patterns = patterns.get(key, {})
            field_reference = reference.get(key) if isinstance(reference, dict) else None
            
            if self._validate_item_accuracy(value, field_patterns, field_reference) > 0.8:
                accurate_fields += 1
        
        return accurate_fields / len(data)
    
    def _validate_item_accuracy(self, item: Any, patterns: Dict[str, Any], 
                               reference: Any) -> float:
        """Validate accuracy for individual item."""
        if reference is not None:
            # Compare against reference data
            if item == reference:
                return 1.0
            elif isinstance(item, str) and isinstance(reference, str):
                return self._calculate_string_similarity(item, reference)
        
        if patterns:
            # Validate against patterns
            return self._validate_against_patterns(item, patterns)
        
        return 1.0  # No validation criteria
    
    def _validate_against_patterns(self, item: Any, patterns: Dict[str, Any]) -> float:
        """Validate item against expected patterns."""
        if not isinstance(item, str):
            return 1.0
        
        pattern_matches = 0
        total_patterns = 0
        
        for pattern_name, pattern in patterns.items():
            total_patterns += 1
            
            if pattern_name == "regex":
                if re.match(pattern, item):
                    pattern_matches += 1
            elif pattern_name == "format":
                if self._validate_format(item, pattern):
                    pattern_matches += 1
            elif pattern_name == "length":
                min_len, max_len = pattern.get("min", 0), pattern.get("max", float('inf'))
                if min_len <= len(item) <= max_len:
                    pattern_matches += 1
        
        return pattern_matches / total_patterns if total_patterns > 0 else 1.0
    
    def _validate_format(self, item: str, format_spec: str) -> bool:
        """Validate item format."""
        format_validators = {
            "email": lambda x: re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', x),
            "url": lambda x: re.match(r'^https?://[^\s/$.?#].[^\s]*$', x),
            "phone": lambda x: re.match(r'^\+?[\d\s\-\(\)]{10,}$', x),
            "date": lambda x: self._validate_date_format(x),
            "number": lambda x: x.replace('.', '').replace('-', '').isdigit()
        }
        
        validator = format_validators.get(format_spec)
        return bool(validator(item)) if validator else True
    
    def _validate_date_format(self, date_str: str) -> bool:
        """Validate date format."""
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{2}/\d{2}/\d{4}$',  # MM/DD/YYYY
            r'^\d{2}-\d{2}-\d{4}$',  # MM-DD-YYYY
        ]
        
        return any(re.match(pattern, date_str) for pattern in date_patterns)
    
    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """Calculate string similarity."""
        if not str1 and not str2:
            return 1.0
        if not str1 or not str2:
            return 0.0
        
        # Simple character-based similarity
        s1, s2 = str1.lower(), str2.lower()
        common_chars = set(s1) & set(s2)
        total_chars = set(s1) | set(s2)
        
        return len(common_chars) / len(total_chars) if total_chars else 1.0
    
    async def _validate_consistency(self, data: Any, 
                                  evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate data consistency."""
        consistency_score = self._calculate_consistency(data)
        threshold = self.quality_thresholds["consistency"]
        
        if consistency_score < threshold:
            self.add_warning(
                f"Data consistency below threshold: {consistency_score:.2%} < {threshold:.2%}",
                "data_consistency",
                {"consistency_score": consistency_score, "threshold": threshold},
                "Review data for inconsistent formats or values"
            )
        else:
            self.add_info(
                f"Data consistency acceptable: {consistency_score:.2%}",
                "data_consistency",
                {"consistency_score": consistency_score}
            )
    
    def _calculate_consistency(self, data: Any) -> float:
        """Calculate data consistency score."""
        if isinstance(data, list):
            return self._calculate_list_consistency(data)
        elif isinstance(data, dict):
            return self._calculate_dict_consistency(data)
        else:
            return 1.0  # Single item is always consistent
    
    def _calculate_list_consistency(self, data: List[Any]) -> float:
        """Calculate consistency for list data."""
        if len(data) <= 1:
            return 1.0
        
        # Check type consistency
        types = [type(item).__name__ for item in data]
        type_consistency = len(set(types)) / len(types)
        
        # Check format consistency for strings
        if all(isinstance(item, str) for item in data):
            format_consistency = self._calculate_format_consistency(data)
            return (type_consistency + format_consistency) / 2
        
        return type_consistency
    
    def _calculate_format_consistency(self, string_data: List[str]) -> float:
        """Calculate format consistency for string data."""
        if not string_data:
            return 1.0
        
        # Analyze patterns
        patterns = []
        for item in string_data:
            pattern = self._extract_pattern(item)
            patterns.append(pattern)
        
        # Calculate pattern consistency
        pattern_counts = Counter(patterns)
        most_common_count = pattern_counts.most_common(1)[0][1] if pattern_counts else 0
        
        return most_common_count / len(string_data)
    
    def _extract_pattern(self, text: str) -> str:
        """Extract pattern from text."""
        # Simple pattern extraction
        pattern = ""
        for char in text:
            if char.isdigit():
                pattern += "D"
            elif char.isalpha():
                pattern += "A"
            elif char.isspace():
                pattern += "S"
            else:
                pattern += "X"
        
        return pattern
    
    def _calculate_dict_consistency(self, data: Dict[str, Any]) -> float:
        """Calculate consistency for dictionary data."""
        if not data:
            return 1.0
        
        # Check if all values have consistent types
        value_types = [type(value).__name__ for value in data.values()]
        type_consistency = len(set(value_types)) / len(value_types) if value_types else 1.0
        
        return type_consistency
    
    async def _validate_validity(self, data: Any, context: Dict[str, Any],
                                evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate data validity against business rules."""
        validity_score = self._calculate_validity(data, context)
        threshold = self.quality_thresholds["validity"]
        
        if validity_score < threshold:
            self.add_warning(
                f"Data validity below threshold: {validity_score:.2%} < {threshold:.2%}",
                "data_validity",
                {"validity_score": validity_score, "threshold": threshold},
                "Review data against business rules and constraints"
            )
        else:
            self.add_info(
                f"Data validity acceptable: {validity_score:.2%}",
                "data_validity",
                {"validity_score": validity_score}
            )
    
    def _calculate_validity(self, data: Any, context: Dict[str, Any]) -> float:
        """Calculate data validity score."""
        validation_rules = context.get("validation_rules", [])
        
        if not validation_rules:
            return 1.0  # No rules to validate against
        
        if isinstance(data, list):
            valid_items = sum(
                1 for item in data 
                if self._validate_item_rules(item, validation_rules)
            )
            return valid_items / len(data) if data else 1.0
        else:
            return 1.0 if self._validate_item_rules(data, validation_rules) else 0.0
    
    def _validate_item_rules(self, item: Any, rules: List[Dict[str, Any]]) -> bool:
        """Validate item against rules."""
        for rule in rules:
            if not self._apply_validation_rule(item, rule):
                return False
        return True
    
    def _apply_validation_rule(self, item: Any, rule: Dict[str, Any]) -> bool:
        """Apply a single validation rule."""
        rule_type = rule.get("type")
        
        if rule_type == "not_empty":
            return bool(item and str(item).strip())
        elif rule_type == "min_length":
            return len(str(item)) >= rule.get("value", 0)
        elif rule_type == "max_length":
            return len(str(item)) <= rule.get("value", float('inf'))
        elif rule_type == "regex":
            return bool(re.match(rule.get("pattern", ""), str(item)))
        elif rule_type == "in_list":
            return item in rule.get("values", [])
        
        return True  # Unknown rule type passes
    
    async def _validate_uniqueness(self, data: Any, 
                                  evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate data uniqueness."""
        uniqueness_score = self._calculate_uniqueness(data)
        threshold = self.quality_thresholds["uniqueness"]
        
        if uniqueness_score < threshold:
            self.add_warning(
                f"Data uniqueness below threshold: {uniqueness_score:.2%} < {threshold:.2%}",
                "data_uniqueness",
                {"uniqueness_score": uniqueness_score, "threshold": threshold},
                "Review data for duplicate entries"
            )
        else:
            self.add_info(
                f"Data uniqueness acceptable: {uniqueness_score:.2%}",
                "data_uniqueness",
                {"uniqueness_score": uniqueness_score}
            )
    
    def _calculate_uniqueness(self, data: Any) -> float:
        """Calculate data uniqueness score."""
        if isinstance(data, list):
            if not data:
                return 1.0
            
            unique_items = len(set(str(item) for item in data))
            return unique_items / len(data)
        
        return 1.0  # Non-list data is considered unique
    
    async def _validate_format_compliance(self, data: Any, context: Dict[str, Any],
                                        evidence_collector: Optional[EvidenceCollector]) -> None:
        """Validate format compliance."""
        expected_format = context.get("expected_format")
        if not expected_format:
            return
        
        compliance_score = self._calculate_format_compliance(data, expected_format)
        
        if compliance_score < 0.9:  # High threshold for format compliance
            self.add_error(
                f"Format compliance below threshold: {compliance_score:.2%} < 90%",
                "format_compliance",
                {"compliance_score": compliance_score, "expected_format": expected_format},
                "Ensure data matches expected format specifications"
            )
        else:
            self.add_info(
                f"Format compliance acceptable: {compliance_score:.2%}",
                "format_compliance",
                {"compliance_score": compliance_score}
            )
    
    def _calculate_format_compliance(self, data: Any, expected_format: Dict[str, Any]) -> float:
        """Calculate format compliance score."""
        if isinstance(data, list):
            compliant_items = sum(
                1 for item in data 
                if self._item_matches_format(item, expected_format)
            )
            return compliant_items / len(data) if data else 1.0
        else:
            return 1.0 if self._item_matches_format(data, expected_format) else 0.0
    
    def _item_matches_format(self, item: Any, format_spec: Dict[str, Any]) -> bool:
        """Check if item matches format specification."""
        item_type = format_spec.get("type")
        
        if item_type and not isinstance(item, eval(item_type)):
            return False
        
        if isinstance(item, str):
            pattern = format_spec.get("pattern")
            if pattern and not re.match(pattern, item):
                return False
        
        return True
    
    async def _calculate_quality_score(self, data: Any, 
                                     evidence_collector: Optional[EvidenceCollector]) -> None:
        """Calculate overall data quality score."""
        scores = {
            "completeness": self._calculate_completeness(data),
            "consistency": self._calculate_consistency(data),
            "uniqueness": self._calculate_uniqueness(data)
        }
        
        # Weight the scores
        weights = {"completeness": 0.4, "consistency": 0.3, "uniqueness": 0.3}
        overall_score = sum(scores[metric] * weights[metric] for metric in scores)
        
        # Collect quality score evidence
        if evidence_collector:
            await self.collect_evidence(
                evidence_collector,
                "data_quality_score",
                {
                    "overall_score": overall_score,
                    "individual_scores": scores,
                    "weights": weights,
                    "thresholds": self.quality_thresholds,
                    "timestamp": datetime.now().isoformat()
                },
                "data_quality_score.json"
            )
        
        # Add quality score to validation results
        if overall_score >= 0.8:
            self.add_info(
                f"Overall data quality score: {overall_score:.2%}",
                "quality_score",
                {"score": overall_score, "breakdown": scores}
            )
        elif overall_score >= 0.6:
            self.add_warning(
                f"Data quality score needs improvement: {overall_score:.2%}",
                "quality_score",
                {"score": overall_score, "breakdown": scores},
                "Focus on improving low-scoring quality dimensions"
            )
        else:
            self.add_error(
                f"Data quality score unacceptable: {overall_score:.2%}",
                "quality_score",
                {"score": overall_score, "breakdown": scores},
                "Significant data quality issues require immediate attention"
            )
    
    def get_validation_rules(self) -> List[str]:
        """Get list of validation rules this validator implements."""
        return [
            "data_completeness",
            "data_accuracy", 
            "data_consistency",
            "data_validity",
            "data_uniqueness",
            "format_compliance",
            "quality_score"
        ]
