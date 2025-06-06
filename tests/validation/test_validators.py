"""
Test Validators

Tests for individual validator implementations.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.validation.core.validation_config import ValidationConfig
from src.validation.core.validation_result import ValidationSeverity
from src.validation.core.evidence_collector import EvidenceCollector
from src.validation.validators.outcome_validator import OutcomeValidator
from src.validation.validators.data_quality_validator import DataQualityValidator
from src.validation.validators.step_validator import StepValidator
from src.validation.validators.checkpoint_validator import CheckpointValidator
from src.validation.validators.performance_validator import PerformanceValidator
from src.validation.validators.security_validator import SecurityValidator
from src.validation.validators.llm_validator import LLMValidator


class TestOutcomeValidator:
    """Test cases for OutcomeValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create outcome validator."""
        config = ValidationConfig.create_standard_config()
        return OutcomeValidator(config)
    
    @pytest.fixture
    def evidence_collector(self):
        """Mock evidence collector."""
        return AsyncMock(spec=EvidenceCollector)
    
    @pytest.mark.asyncio
    async def test_validate_successful_completion(self, validator, evidence_collector):
        """Test validation of successful task completion."""
        context = {
            "task_result": {
                "status": "completed",
                "execution_time": 5.2,
                "outcomes": {"search_performed": True}
            },
            "task_definition": {
                "expected_outcomes": {"search_performed": True},
                "success_criteria": {"completion_required": True}
            }
        }
        
        await validator.validate(context, evidence_collector)
        
        assert not validator.has_errors()
        assert any("completed successfully" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_validate_failed_completion(self, validator, evidence_collector):
        """Test validation of failed task completion."""
        context = {
            "task_result": {
                "status": "failed",
                "execution_time": 5.2
            },
            "task_definition": {
                "success_criteria": {"completion_required": True}
            }
        }
        
        await validator.validate(context, evidence_collector)
        
        assert validator.has_errors()
        assert any("did not complete successfully" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_validate_outcome_mismatch(self, validator, evidence_collector):
        """Test validation of outcome mismatch."""
        context = {
            "task_result": {
                "status": "completed",
                "outcomes": {"search_performed": False}
            },
            "task_definition": {
                "expected_outcomes": {"search_performed": True},
                "success_criteria": {"completion_required": True}
            }
        }
        
        await validator.validate(context, evidence_collector)
        
        assert validator.has_errors()
        assert any("does not match expected value" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_validate_execution_time_exceeded(self, validator, evidence_collector):
        """Test validation of execution time limits."""
        context = {
            "task_result": {
                "status": "completed",
                "execution_time": 35.0  # Exceeds limit
            },
            "task_definition": {
                "success_criteria": {
                    "completion_required": True,
                    "max_execution_time": 30.0
                }
            }
        }
        
        await validator.validate(context, evidence_collector)
        
        assert validator.has_warnings()
        assert any("execution time exceeded limit" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_string_comparison_methods(self, validator):
        """Test different string comparison methods."""
        # Exact match
        result = validator._compare_strings("test", "test")
        assert result["matches"] is True
        assert result["comparison_method"] == "exact"
        
        # Case insensitive match
        result = validator._compare_strings("Test", "test")
        assert result["matches"] is True
        assert result["comparison_method"] == "case_insensitive"
        
        # Substring match
        result = validator._compare_strings("test", "testing")
        assert result["matches"] is True
        assert result["comparison_method"] == "substring"
        
        # No match
        result = validator._compare_strings("test", "different")
        assert result["matches"] is False
    
    @pytest.mark.asyncio
    async def test_numeric_comparison_with_tolerance(self, validator):
        """Test numeric comparison with tolerance."""
        # Exact match
        result = validator._compare_numbers(10.0, 10.0)
        assert result["matches"] is True
        
        # Within tolerance
        result = validator._compare_numbers(10.0, 10.005)
        assert result["matches"] is True
        
        # Outside tolerance
        result = validator._compare_numbers(10.0, 11.0)
        assert result["matches"] is False


class TestDataQualityValidator:
    """Test cases for DataQualityValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create data quality validator."""
        config = ValidationConfig.create_standard_config()
        return DataQualityValidator(config)
    
    @pytest.mark.asyncio
    async def test_validate_data_completeness(self, validator):
        """Test data completeness validation."""
        context = {
            "task_result": {
                "extracted_data": ["item1", "item2", "", None, "item5"]
            }
        }
        
        await validator.validate(context)
        
        # Should detect incomplete data (empty string and None)
        completeness_score = validator._calculate_completeness(context["task_result"]["extracted_data"])
        assert completeness_score == 0.6  # 3 out of 5 items complete
    
    @pytest.mark.asyncio
    async def test_validate_data_consistency(self, validator):
        """Test data consistency validation."""
        # Consistent data
        consistent_data = ["item1", "item2", "item3"]
        consistency_score = validator._calculate_consistency(consistent_data)
        assert consistency_score == 1.0
        
        # Mixed types (inconsistent)
        inconsistent_data = ["string", 123, {"key": "value"}]
        consistency_score = validator._calculate_consistency(inconsistent_data)
        assert consistency_score < 1.0
    
    @pytest.mark.asyncio
    async def test_validate_data_uniqueness(self, validator):
        """Test data uniqueness validation."""
        # Unique data
        unique_data = ["item1", "item2", "item3"]
        uniqueness_score = validator._calculate_uniqueness(unique_data)
        assert uniqueness_score == 1.0
        
        # Duplicate data
        duplicate_data = ["item1", "item2", "item1", "item3"]
        uniqueness_score = validator._calculate_uniqueness(duplicate_data)
        assert uniqueness_score == 0.75  # 3 unique out of 4 total
    
    @pytest.mark.asyncio
    async def test_format_validation(self, validator):
        """Test format validation."""
        # Valid email
        assert validator._validate_format("test@example.com", "email")
        
        # Invalid email
        assert not validator._validate_format("invalid-email", "email")
        
        # Valid URL
        assert validator._validate_format("https://example.com", "url")
        
        # Invalid URL
        assert not validator._validate_format("not-a-url", "url")


class TestStepValidator:
    """Test cases for StepValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create step validator."""
        config = ValidationConfig.create_standard_config()
        return StepValidator(config)
    
    @pytest.mark.asyncio
    async def test_validate_step_structure(self, validator):
        """Test step structure validation."""
        # Valid step
        valid_step = {
            "step_id": "step_001",
            "action": "navigate_to_url",
            "status": "completed",
            "execution_time": 2.5
        }
        
        context = {"step_info": valid_step}
        await validator.validate(context)
        
        assert not validator.has_errors()
        
        # Invalid step (missing required fields)
        invalid_step = {
            "step_id": "step_002"
            # Missing action and status
        }
        
        validator.reset()
        context = {"step_info": invalid_step}
        await validator.validate(context)
        
        assert validator.has_errors()
        assert any("missing required fields" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_validate_step_timing(self, validator):
        """Test step timing validation."""
        step_info = {
            "step_id": "step_001",
            "action": "test_action",
            "status": "completed",
            "start_time": "2024-01-01T10:00:00Z",
            "end_time": "2024-01-01T10:00:05Z",
            "execution_time": 5.0
        }
        
        context = {"step_info": step_info}
        await validator.validate(context)
        
        # Should validate timing consistency
        assert not validator.has_errors()
    
    @pytest.mark.asyncio
    async def test_validate_step_dependencies(self, validator):
        """Test step dependency validation."""
        # Add completed step to history
        completed_step = {
            "step_id": "step_001",
            "action": "prerequisite",
            "status": "completed"
        }
        validator._record_step(completed_step)
        
        # Test step with satisfied dependencies
        dependent_step = {
            "step_id": "step_002",
            "action": "dependent_action",
            "status": "completed",
            "dependencies": ["step_001"]
        }
        
        context = {"step_info": dependent_step}
        await validator.validate(context)
        
        assert not validator.has_errors()
        assert any("dependencies satisfied" in issue.message for issue in validator.issues)
        
        # Test step with unsatisfied dependencies
        validator.reset()
        validator.step_history.clear()
        
        context = {"step_info": dependent_step}
        await validator.validate(context)
        
        assert validator.has_errors()
        assert any("unmet dependencies" in issue.message for issue in validator.issues)


class TestCheckpointValidator:
    """Test cases for CheckpointValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create checkpoint validator."""
        config = ValidationConfig.create_standard_config()
        return CheckpointValidator(config)
    
    @pytest.mark.asyncio
    async def test_create_checkpoint(self, validator):
        """Test checkpoint creation."""
        context = {
            "checkpoint_action": "create",
            "checkpoint_id": "test_checkpoint",
            "system_state": {"key": "value"},
            "task_state": {"progress": 50}
        }
        
        await validator.validate(context)
        
        assert not validator.has_errors()
        assert "test_checkpoint" in validator.checkpoints
        assert any("Checkpoint created" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_validate_checkpoint_integrity(self, validator):
        """Test checkpoint integrity validation."""
        # Create a checkpoint first
        checkpoint_data = {"test": "data"}
        checkpoint = {
            "id": "test_checkpoint",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": checkpoint_data,
            "hash": validator._calculate_checkpoint_hash(checkpoint_data)
        }
        
        validator.checkpoints["test_checkpoint"] = checkpoint
        
        # Validate integrity
        await validator._validate_checkpoint_integrity(checkpoint, None)
        
        assert not validator.has_errors()
        assert any("integrity verified" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_checkpoint_age_validation(self, validator):
        """Test checkpoint age validation."""
        # Old checkpoint
        old_checkpoint = {
            "id": "old_checkpoint",
            "timestamp": "2020-01-01T00:00:00Z",  # Very old
            "data": {}
        }
        
        await validator._validate_checkpoint_age(old_checkpoint, None)
        
        assert validator.has_warnings() or validator.has_errors()
        assert any("old" in issue.message.lower() for issue in validator.issues)


class TestPerformanceValidator:
    """Test cases for PerformanceValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create performance validator."""
        config = ValidationConfig.create_standard_config()
        return PerformanceValidator(config)
    
    @pytest.mark.asyncio
    async def test_validate_execution_performance(self, validator):
        """Test execution performance validation."""
        context = {
            "task_result": {
                "execution_time": 25.0,  # Within limits
                "steps": ["step1", "step2"],
                "errors": []
            }
        }
        
        # Mock system metrics
        with patch('psutil.cpu_percent', return_value=50.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 60.0
            mock_memory.return_value.total = 8 * 1024**3
            mock_memory.return_value.available = 3 * 1024**3
            mock_memory.return_value.used = 5 * 1024**3
            
            await validator.validate(context)
        
        # Should pass performance checks
        assert not validator.has_errors()
    
    @pytest.mark.asyncio
    async def test_validate_high_resource_usage(self, validator):
        """Test validation with high resource usage."""
        context = {
            "task_result": {
                "execution_time": 5.0,
                "steps": ["step1"],
                "errors": []
            }
        }
        
        # Mock high resource usage
        with patch('psutil.cpu_percent', return_value=95.0), \
             patch('psutil.virtual_memory') as mock_memory:
            
            mock_memory.return_value.percent = 95.0
            mock_memory.return_value.total = 8 * 1024**3
            mock_memory.return_value.available = 0.4 * 1024**3
            mock_memory.return_value.used = 7.6 * 1024**3
            
            await validator.validate(context)
        
        # Should detect high resource usage
        assert validator.has_warnings() or validator.has_errors()
        assert any("high" in issue.message.lower() for issue in validator.issues)


class TestSecurityValidator:
    """Test cases for SecurityValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create security validator."""
        config = ValidationConfig.create_standard_config()
        config.security_checks = True
        return SecurityValidator(config)
    
    @pytest.mark.asyncio
    async def test_validate_safe_urls(self, validator):
        """Test validation of safe URLs."""
        context = {
            "task_definition": {"url": "https://example.com"},
            "browser_state": {"url": "https://example.com"},
            "task_result": {"extracted_data": []}
        }
        
        await validator.validate(context)
        
        # Should pass security checks for safe URLs
        assert not validator.has_errors()
    
    @pytest.mark.asyncio
    async def test_validate_unsafe_urls(self, validator):
        """Test validation of unsafe URLs."""
        context = {
            "task_definition": {"url": "http://malware.com"},  # HTTP + dangerous domain
            "task_result": {"extracted_data": []}
        }
        
        await validator.validate(context)
        
        # Should detect security issues
        assert validator.has_warnings() or validator.has_errors()
    
    @pytest.mark.asyncio
    async def test_detect_sensitive_data(self, validator):
        """Test detection of sensitive data."""
        sensitive_data = [
            "My credit card is 4532-1234-5678-9012",
            "SSN: 123-45-6789",
            "Email: user@example.com"
        ]
        
        findings = validator._scan_for_sensitive_data(sensitive_data)
        
        assert len(findings) >= 3  # Should detect credit card, SSN, and email
        assert any(finding["type"] == "credit_card" for finding in findings)
        assert any(finding["type"] == "ssn" for finding in findings)
        assert any(finding["type"] == "email" for finding in findings)
    
    @pytest.mark.asyncio
    async def test_detect_injection_patterns(self, validator):
        """Test detection of injection patterns."""
        # SQL injection patterns
        assert validator._has_injection_patterns("'; DROP TABLE users; --")
        assert validator._has_injection_patterns("1' OR '1'='1")
        
        # XSS patterns
        assert validator._has_xss_patterns("<script>alert('xss')</script>")
        assert validator._has_xss_patterns("javascript:alert('xss')")
        
        # Safe inputs
        assert not validator._has_injection_patterns("normal search query")
        assert not validator._has_xss_patterns("normal text content")


class TestLLMValidator:
    """Test cases for LLMValidator."""
    
    @pytest.fixture
    def validator(self):
        """Create LLM validator."""
        config = ValidationConfig.create_standard_config()
        config.enable_llm_validation = True
        return LLMValidator(config)
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Mock LLM provider."""
        mock_provider = AsyncMock()
        mock_provider.invoke.return_value = json.dumps({
            "understanding_score": 0.9,
            "main_objective_understood": True,
            "requirements_captured": ["navigate", "search"],
            "missing_requirements": [],
            "misinterpretations": [],
            "completeness_score": 0.95,
            "overall_assessment": "Good understanding"
        })
        return mock_provider
    
    @pytest.mark.asyncio
    async def test_validate_task_understanding(self, validator, mock_llm_provider):
        """Test LLM task understanding validation."""
        context = {
            "llm_provider": mock_llm_provider,
            "task_definition": {
                "description": "Navigate to google.com and search for 'test'"
            },
            "llm_interpretation": "I will navigate to Google and perform a search for 'test'"
        }
        
        await validator.validate(context)
        
        assert not validator.has_errors()
        assert any("Good task understanding" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_validate_without_llm_provider(self, validator):
        """Test validation without LLM provider."""
        context = {
            "task_definition": {"description": "Test task"}
        }
        
        await validator.validate(context)
        
        assert validator.has_warnings()
        assert any("No LLM provider available" in issue.message for issue in validator.issues)
    
    @pytest.mark.asyncio
    async def test_parse_llm_response(self, validator):
        """Test parsing LLM responses."""
        # Valid JSON response
        valid_response = '{"score": 0.9, "status": "good"}'
        parsed = validator._parse_llm_response(valid_response)
        assert parsed == {"score": 0.9, "status": "good"}
        
        # JSON embedded in text
        embedded_response = 'Here is the analysis: {"score": 0.8} and some more text'
        parsed = validator._parse_llm_response(embedded_response)
        assert parsed == {"score": 0.8}
        
        # Invalid JSON
        invalid_response = 'This is not JSON'
        parsed = validator._parse_llm_response(invalid_response)
        assert parsed is None
        assert validator.has_warnings()


@pytest.mark.integration
class TestValidatorIntegration:
    """Integration tests for validators."""
    
    @pytest.mark.asyncio
    async def test_multiple_validators_workflow(self):
        """Test workflow with multiple validators."""
        config = ValidationConfig.create_comprehensive_config()
        
        # Create validators
        outcome_validator = OutcomeValidator(config)
        data_validator = DataQualityValidator(config)
        step_validator = StepValidator(config)
        
        # Sample context
        context = {
            "task_definition": {
                "description": "Test task",
                "expected_outcomes": {"success": True}
            },
            "task_result": {
                "status": "completed",
                "execution_time": 5.0,
                "extracted_data": ["item1", "item2", "item3"],
                "outcomes": {"success": True}
            },
            "step_info": {
                "step_id": "test_step",
                "action": "test_action",
                "status": "completed",
                "execution_time": 2.0
            }
        }
        
        # Run all validators
        await outcome_validator.validate(context)
        await data_validator.validate(context)
        await step_validator.validate(context)
        
        # Collect all issues
        all_issues = (outcome_validator.issues + 
                     data_validator.issues + 
                     step_validator.issues)
        
        # Should have mostly positive results
        error_count = sum(1 for issue in all_issues 
                         if issue.severity in [ValidationSeverity.ERROR, ValidationSeverity.CRITICAL])
        
        assert error_count == 0  # No errors expected for valid data
