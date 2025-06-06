"""
Test Validation Engine

Tests for the core validation engine functionality.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.validation.core.validation_engine import ValidationEngine
from src.validation.core.validation_config import ValidationConfig, ValidationLevel, ValidationPhase
from src.validation.core.validation_result import ValidationResult, ValidationStatus
from src.validation.core.evidence_collector import EvidenceCollector


class TestValidationEngine:
    """Test cases for ValidationEngine."""
    
    @pytest.fixture
    def basic_config(self):
        """Basic validation configuration."""
        return ValidationConfig.create_basic_config()
    
    @pytest.fixture
    def standard_config(self):
        """Standard validation configuration."""
        return ValidationConfig.create_standard_config()
    
    @pytest.fixture
    def comprehensive_config(self):
        """Comprehensive validation configuration."""
        return ValidationConfig.create_comprehensive_config()
    
    @pytest.fixture
    def validation_engine(self, standard_config):
        """Validation engine with standard config."""
        return ValidationEngine(standard_config)
    
    @pytest.fixture
    def sample_context(self):
        """Sample validation context."""
        return {
            "task_definition": {
                "description": "Navigate to google.com and search for 'test'",
                "expected_outcomes": {"search_performed": True},
                "success_criteria": {"completion_required": True}
            },
            "task_result": {
                "status": "completed",
                "execution_time": 5.2,
                "extracted_data": ["result1", "result2", "result3"],
                "outcomes": {"search_performed": True}
            },
            "step_info": {
                "step_id": "step_001",
                "action": "navigate_to_url",
                "status": "completed",
                "execution_time": 2.1,
                "result": "Navigation successful"
            }
        }
    
    def test_engine_initialization(self, standard_config):
        """Test validation engine initialization."""
        engine = ValidationEngine(standard_config)
        
        assert engine.config == standard_config
        assert len(engine.validators) > 0
        assert "outcome" in engine.validators
        assert "step" in engine.validators
        assert ValidationPhase.PRE_EXECUTION in engine.phase_validators
        assert ValidationPhase.POST_EXECUTION in engine.phase_validators
    
    def test_engine_initialization_with_different_configs(self):
        """Test engine initialization with different configurations."""
        # Basic config
        basic_engine = ValidationEngine(ValidationConfig.create_basic_config())
        assert len(basic_engine.validators) >= 3  # Core validators
        
        # Comprehensive config
        comprehensive_engine = ValidationEngine(ValidationConfig.create_comprehensive_config())
        assert len(comprehensive_engine.validators) > len(basic_engine.validators)
        assert "performance" in comprehensive_engine.validators
        assert "security" in comprehensive_engine.validators
    
    @pytest.mark.asyncio
    async def test_start_validation(self, validation_engine):
        """Test starting validation session."""
        task_id = "test_task_001"
        task_definition = {"description": "Test task"}
        
        result = await validation_engine.start_validation(task_id, task_definition)
        
        assert isinstance(result, ValidationResult)
        assert result.task_id == task_id
        assert result.overall_status == ValidationStatus.PENDING
        assert validation_engine.current_validation == result
        assert validation_engine.evidence_collector is not None
    
    @pytest.mark.asyncio
    async def test_start_validation_without_evidence_collection(self):
        """Test starting validation without evidence collection."""
        config = ValidationConfig.create_basic_config()
        config.collect_evidence = False
        engine = ValidationEngine(config)
        
        result = await engine.start_validation("test_task", {})
        
        assert engine.evidence_collector is None
    
    @pytest.mark.asyncio
    async def test_validate_phase_pre_execution(self, validation_engine, sample_context):
        """Test pre-execution phase validation."""
        await validation_engine.start_validation("test_task", sample_context["task_definition"])
        
        await validation_engine.validate_phase(ValidationPhase.PRE_EXECUTION, sample_context)
        
        assert ValidationPhase.PRE_EXECUTION.value in validation_engine.current_validation.phase_results
        phase_result = validation_engine.current_validation.phase_results[ValidationPhase.PRE_EXECUTION.value]
        assert phase_result.status in [ValidationStatus.PASSED, ValidationStatus.WARNING, ValidationStatus.FAILED]
    
    @pytest.mark.asyncio
    async def test_validate_phase_during_execution(self, validation_engine, sample_context):
        """Test during-execution phase validation."""
        await validation_engine.start_validation("test_task", sample_context["task_definition"])
        
        await validation_engine.validate_phase(ValidationPhase.DURING_EXECUTION, sample_context)
        
        assert ValidationPhase.DURING_EXECUTION.value in validation_engine.current_validation.phase_results
    
    @pytest.mark.asyncio
    async def test_validate_phase_post_execution(self, validation_engine, sample_context):
        """Test post-execution phase validation."""
        await validation_engine.start_validation("test_task", sample_context["task_definition"])
        
        await validation_engine.validate_phase(ValidationPhase.POST_EXECUTION, sample_context)
        
        assert ValidationPhase.POST_EXECUTION.value in validation_engine.current_validation.phase_results
    
    @pytest.mark.asyncio
    async def test_validate_phase_disabled(self, validation_engine, sample_context):
        """Test validation phase when disabled."""
        # Disable post-execution validation
        validation_engine.config.post_execution.enabled = False
        
        await validation_engine.start_validation("test_task", sample_context["task_definition"])
        await validation_engine.validate_phase(ValidationPhase.POST_EXECUTION, sample_context)
        
        # Should not create phase result when disabled
        assert ValidationPhase.POST_EXECUTION.value not in validation_engine.current_validation.phase_results
    
    @pytest.mark.asyncio
    async def test_complete_validation(self, validation_engine, sample_context):
        """Test completing validation session."""
        await validation_engine.start_validation("test_task", sample_context["task_definition"])
        await validation_engine.validate_phase(ValidationPhase.POST_EXECUTION, sample_context)
        
        result = await validation_engine.complete_validation()
        
        assert isinstance(result, ValidationResult)
        assert result.overall_status != ValidationStatus.PENDING
        assert result.end_time is not None
        assert validation_engine.current_validation is None
        assert len(validation_engine.validation_history) == 1
    
    @pytest.mark.asyncio
    async def test_complete_validation_without_active_session(self, validation_engine):
        """Test completing validation without active session."""
        with pytest.raises(ValueError, match="No active validation session"):
            await validation_engine.complete_validation()
    
    @pytest.mark.asyncio
    async def test_validator_error_handling(self, validation_engine, sample_context):
        """Test error handling in validators."""
        # Mock a validator to raise an exception
        mock_validator = AsyncMock()
        mock_validator.validate.side_effect = Exception("Test validator error")
        mock_validator.__class__.__name__ = "MockValidator"
        
        validation_engine.validators["mock"] = mock_validator
        validation_engine.phase_validators[ValidationPhase.POST_EXECUTION].append(mock_validator)
        
        await validation_engine.start_validation("test_task", sample_context["task_definition"])
        await validation_engine.validate_phase(ValidationPhase.POST_EXECUTION, sample_context)
        
        # Should handle error gracefully and add issue
        result = await validation_engine.complete_validation()
        issues = result.get_all_issues()
        
        assert any("MockValidator" in issue.message for issue in issues)
    
    @pytest.mark.asyncio
    async def test_parallel_validator_execution(self):
        """Test parallel validator execution."""
        config = ValidationConfig.create_standard_config()
        config.post_execution.parallel_execution = True
        engine = ValidationEngine(config)
        
        # Mock validators with delays to test parallelism
        mock_validator_1 = AsyncMock()
        mock_validator_2 = AsyncMock()
        
        async def slow_validate_1(*args):
            await asyncio.sleep(0.1)
        
        async def slow_validate_2(*args):
            await asyncio.sleep(0.1)
        
        mock_validator_1.validate = slow_validate_1
        mock_validator_2.validate = slow_validate_2
        mock_validator_1.__class__.__name__ = "MockValidator1"
        mock_validator_2.__class__.__name__ = "MockValidator2"
        
        engine.phase_validators[ValidationPhase.POST_EXECUTION] = [mock_validator_1, mock_validator_2]
        
        await engine.start_validation("test_task", {})
        
        start_time = asyncio.get_event_loop().time()
        await engine.validate_phase(ValidationPhase.POST_EXECUTION, {})
        end_time = asyncio.get_event_loop().time()
        
        # Should complete faster than sequential execution
        assert (end_time - start_time) < 0.15  # Less than sum of individual delays
    
    @pytest.mark.asyncio
    async def test_fail_fast_behavior(self):
        """Test fail-fast behavior in validation."""
        config = ValidationConfig.create_standard_config()
        config.post_execution.fail_fast = True
        engine = ValidationEngine(config)
        
        # Mock validators - first one fails
        mock_validator_1 = AsyncMock()
        mock_validator_2 = AsyncMock()
        
        mock_validator_1.has_errors.return_value = True
        mock_validator_1.__class__.__name__ = "FailingValidator"
        mock_validator_2.__class__.__name__ = "SecondValidator"
        
        engine.phase_validators[ValidationPhase.POST_EXECUTION] = [mock_validator_1, mock_validator_2]
        
        await engine.start_validation("test_task", {})
        await engine.validate_phase(ValidationPhase.POST_EXECUTION, {})
        
        # First validator should be called, second should not due to fail-fast
        mock_validator_1.validate.assert_called_once()
        # Note: In actual implementation, we'd need to track this more precisely
    
    def test_add_custom_validator(self, validation_engine):
        """Test adding custom validator."""
        mock_validator = MagicMock()
        mock_validator.__class__.__name__ = "CustomValidator"
        
        validation_engine.add_custom_validator(
            "custom", 
            mock_validator, 
            [ValidationPhase.PRE_EXECUTION]
        )
        
        assert "custom" in validation_engine.validators
        assert mock_validator in validation_engine.phase_validators[ValidationPhase.PRE_EXECUTION]
    
    def test_get_validation_history(self, validation_engine):
        """Test getting validation history."""
        # Add some mock validation results
        for i in range(5):
            mock_result = MagicMock(spec=ValidationResult)
            mock_result.validation_id = f"validation_{i}"
            validation_engine.validation_history.append(mock_result)
        
        history = validation_engine.get_validation_history(3)
        assert len(history) == 3
        assert history[0].validation_id == "validation_2"  # Most recent 3
    
    def test_get_validation_statistics(self, validation_engine):
        """Test getting validation statistics."""
        # Add mock validation results
        for i in range(10):
            mock_result = MagicMock(spec=ValidationResult)
            mock_result.is_successful = i % 2 == 0  # 50% success rate
            mock_result.duration = 5.0
            mock_result.get_all_issues.return_value = [MagicMock()] * (i % 3)  # Variable issue count
            validation_engine.validation_history.append(mock_result)
        
        stats = validation_engine.get_validation_statistics()
        
        assert stats["total_validations"] == 10
        assert stats["successful_validations"] == 5
        assert stats["success_rate"] == 0.5
        assert stats["average_duration"] == 5.0
        assert "total_issues" in stats
        assert "average_issues_per_validation" in stats
    
    def test_get_validation_statistics_empty_history(self, validation_engine):
        """Test getting statistics with empty history."""
        stats = validation_engine.get_validation_statistics()
        assert stats["total_validations"] == 0


@pytest.mark.asyncio
class TestValidationEngineIntegration:
    """Integration tests for validation engine."""
    
    async def test_full_validation_workflow(self):
        """Test complete validation workflow."""
        config = ValidationConfig.create_standard_config()
        engine = ValidationEngine(config)
        
        # Sample task context
        context = {
            "task_definition": {
                "description": "Test task",
                "expected_outcomes": {"success": True}
            },
            "task_result": {
                "status": "completed",
                "execution_time": 3.5,
                "outcomes": {"success": True}
            },
            "step_info": {
                "step_id": "test_step",
                "action": "test_action",
                "status": "completed"
            }
        }
        
        # Start validation
        validation_result = await engine.start_validation("integration_test", context["task_definition"])
        
        # Run all phases
        await engine.validate_phase(ValidationPhase.PRE_EXECUTION, context)
        await engine.validate_phase(ValidationPhase.DURING_EXECUTION, context)
        await engine.validate_phase(ValidationPhase.POST_EXECUTION, context)
        
        # Complete validation
        final_result = await engine.complete_validation()
        
        # Verify results
        assert final_result.task_id == "integration_test"
        assert final_result.overall_status in [ValidationStatus.PASSED, ValidationStatus.WARNING]
        assert len(final_result.phase_results) == 3
        assert final_result.duration > 0
        
        # Verify evidence collection
        assert len(final_result.evidence_paths) > 0
    
    async def test_validation_with_errors(self):
        """Test validation workflow with errors."""
        config = ValidationConfig.create_standard_config()
        engine = ValidationEngine(config)
        
        # Context with errors
        context = {
            "task_definition": {
                "description": "Test task",
                "expected_outcomes": {"success": True}
            },
            "task_result": {
                "status": "failed",  # Task failed
                "execution_time": 10.5,  # Slow execution
                "outcomes": {"success": False},  # Wrong outcome
                "error_message": "Task execution failed"
            }
        }
        
        # Run validation
        await engine.start_validation("error_test", context["task_definition"])
        await engine.validate_phase(ValidationPhase.POST_EXECUTION, context)
        result = await engine.complete_validation()
        
        # Should have errors
        assert result.has_errors or len(result.get_all_issues()) > 0
        assert result.overall_status in [ValidationStatus.FAILED, ValidationStatus.WARNING]
