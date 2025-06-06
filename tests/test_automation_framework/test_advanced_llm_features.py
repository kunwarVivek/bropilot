"""
Tests for Advanced LLM Test Features

Tests the advanced LLM-powered features:
- Test case auto-generation from requirements
- Test maintenance and updates when UI changes
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timezone

from src.test_automation_framework import create_test_automation_framework
from src.test_management.models import TestCase, TestType, TestPriority, TestCaseStatus
from src.test_management.llm_features import RequirementsToTestGenerator, TestMaintenanceEngine


class TestRequirementsToTestGeneration:
    """Test requirements-to-test generation functionality."""
    
    @pytest_asyncio.fixture
    async def framework(self):
        """Create test framework instance."""
        framework = await create_test_automation_framework(
            workspace_path="test_workspace_llm",
            environment="test"
        )
        
        # Mock LLM provider
        mock_llm = AsyncMock()
        framework.llm_provider = mock_llm
        
        yield framework
        
        # Cleanup
        await framework.cleanup()
    
    @pytest.fixture
    def sample_requirements(self):
        """Sample requirements document."""
        return """
        User Management System Requirements:
        
        1. User Registration
        - Users can register with email and password
        - Email must be unique
        - Password must be at least 8 characters
        
        2. User Login
        - Users can login with valid credentials
        - Account locks after 3 failed attempts
        - Session expires after 30 minutes of inactivity
        """
    
    @pytest.fixture
    def mock_llm_responses(self):
        """Mock LLM responses for requirements analysis."""
        return [
            # Features extraction
            """
            [
                {
                    "feature_name": "User Registration",
                    "description": "User registration functionality",
                    "acceptance_criteria": ["User can register", "Email validation"],
                    "priority": "high",
                    "test_types": ["functional"],
                    "dependencies": [],
                    "user_roles": ["guest"],
                    "business_rules": ["Unique email", "Password length"],
                    "edge_cases": ["Duplicate email", "Weak password"],
                    "estimated_test_cases": 4
                }
            ]
            """,
            # Scenarios for User Registration
            """
            [
                {
                    "scenario_name": "Valid User Registration",
                    "test_type": "positive",
                    "feature_name": "User Registration",
                    "preconditions": ["Registration page accessible"],
                    "test_steps": ["Navigate to registration", "Enter details", "Submit"],
                    "expected_results": ["Account created", "Confirmation shown"],
                    "test_data": {"email": "test@example.com", "password": "password123"},
                    "priority": "high",
                    "risk_level": "medium"
                }
            ]
            """,
            # Test case generation
            """
            {
                "name": "User Registration - Valid Registration",
                "description": "Test valid user registration process",
                "preconditions": ["Registration page is accessible"],
                "steps": [
                    {
                        "step_number": 1,
                        "description": "Navigate to registration",
                        "action": "Open registration page",
                        "expected_result": "Page loads successfully",
                        "validation_rules": ["Page title correct"],
                        "timeout": 30
                    }
                ],
                "postconditions": ["User account created"],
                "test_data": {"email": "test@example.com"}
            }
            """
        ]
    
    @pytest.mark.asyncio
    async def test_generate_test_cases_from_requirements(
        self,
        framework,
        sample_requirements,
        mock_llm_responses
    ):
        """Test generating test cases from requirements document."""
        # Setup mock responses
        import itertools
        response_cycle = itertools.cycle(mock_llm_responses)
        framework.llm_provider.invoke.side_effect = lambda prompt: next(response_cycle)
        
        # Generate test cases
        test_cases = await framework.generate_test_cases_from_requirements(
            requirements_document=sample_requirements,
            test_coverage_level="standard"
        )
        
        # Assertions
        assert len(test_cases) > 0
        assert all(isinstance(tc, TestCase) for tc in test_cases)
        assert any("User Registration" in tc.name for tc in test_cases)
        
        # Check test case properties
        test_case = test_cases[0]
        assert test_case.test_type == TestType.FUNCTIONAL
        assert test_case.priority in [TestPriority.HIGH, TestPriority.CRITICAL]
        assert len(test_case.steps) > 0
        assert test_case.created_by == "llm_generator"
    
    @pytest.mark.asyncio
    async def test_requirements_generator_feature_extraction(self):
        """Test feature extraction from requirements."""
        generator = RequirementsToTestGenerator()
        mock_llm = AsyncMock()
        
        # Mock LLM response
        mock_llm.invoke.return_value = """
        [
            {
                "feature_name": "Login System",
                "description": "User authentication",
                "acceptance_criteria": ["Valid login", "Invalid login handling"],
                "priority": "high",
                "test_types": ["functional", "security"],
                "dependencies": [],
                "user_roles": ["user"],
                "business_rules": ["Session timeout"],
                "edge_cases": ["Concurrent logins"],
                "estimated_test_cases": 5
            }
        ]
        """
        
        requirements = "Users can login with username and password"
        features = await generator._extract_testable_features(requirements, mock_llm)
        
        assert len(features) == 1
        assert features[0]["feature_name"] == "Login System"
        assert features[0]["priority"] == "high"
        assert "functional" in features[0]["test_types"]
    
    @pytest.mark.asyncio
    async def test_requirements_generator_scenario_generation(self):
        """Test scenario generation for features."""
        generator = RequirementsToTestGenerator()
        mock_llm = AsyncMock()

        # Mock LLM response
        mock_llm.invoke.return_value = """
        [
            {
                "scenario_name": "Successful Login",
                "test_type": "positive",
                "feature_name": "Login",
                "preconditions": ["User account exists"],
                "test_steps": ["Enter credentials", "Click login"],
                "expected_results": ["User logged in"],
                "test_data": {"username": "testuser"},
                "priority": "high",
                "risk_level": "low"
            }
        ]
        """

        feature = {
            "feature_name": "Login",
            "description": "User login functionality",
            "acceptance_criteria": ["Valid login works"],
            "business_rules": [],
            "edge_cases": []
        }

        scenarios = await generator._generate_scenarios_for_feature(
            feature, mock_llm, "standard"
        )

        assert len(scenarios) == 1
        assert scenarios[0]["scenario_name"] == "Successful Login"
        assert scenarios[0]["test_type"] == "positive"


class TestTestMaintenance:
    """Test test maintenance functionality."""
    
    @pytest_asyncio.fixture
    async def framework(self):
        """Create test framework instance."""
        framework = await create_test_automation_framework(
            workspace_path="test_workspace_maintenance",
            environment="test"
        )
        
        # Mock LLM provider
        mock_llm = AsyncMock()
        framework.llm_provider = mock_llm
        
        yield framework
        
        # Cleanup
        await framework.cleanup()
    
    @pytest.fixture
    def sample_test_case(self):
        """Sample test case for maintenance testing."""
        return TestCase(
            name="Login Test",
            description="Test user login functionality",
            test_type=TestType.FUNCTIONAL,
            priority=TestPriority.HIGH,
            status=TestCaseStatus.ACTIVE,
            target_url="https://example.com/login",
            tags=["login", "authentication"]
        )
    
    @pytest.fixture
    def ui_changes_description(self):
        """Sample UI changes description."""
        return """
        Login Page Changes:
        - Email field ID changed from 'email' to 'user-email'
        - Password field class changed to 'pwd-input'
        - Login button text changed from 'Login' to 'Sign In'
        """
    
    @pytest.mark.asyncio
    async def test_analyze_ui_changes_impact(
        self,
        framework,
        sample_test_case,
        ui_changes_description
    ):
        """Test UI changes impact analysis."""
        # Save test case first
        await framework.test_case_manager.repository.save(sample_test_case)
        
        # Mock LLM response
        framework.llm_provider.invoke.return_value = """
        {
            "overall_impact": "medium",
            "summary": "Login page changes affect authentication tests",
            "test_case_impacts": [
                {
                    "test_case_id": "test_id",
                    "test_case_name": "Login Test",
                    "impact_level": "medium",
                    "affected_elements": ["email_field", "password_field"],
                    "required_updates": ["Update selectors"],
                    "failure_risk": "medium",
                    "recommended_actions": ["Update element locators"],
                    "estimated_effort": "1 hour"
                }
            ],
            "global_recommendations": ["Update page objects"]
        }
        """
        
        # Analyze impact
        impact_analysis = await framework.analyze_ui_changes_impact(
            ui_changes_description=ui_changes_description,
            affected_test_case_ids=[sample_test_case.id]
        )
        
        # Assertions
        assert impact_analysis["overall_impact"] == "medium"
        assert len(impact_analysis["test_case_impacts"]) == 1
        assert impact_analysis["test_case_impacts"][0]["test_case_name"] == "Login Test"
        assert len(impact_analysis["global_recommendations"]) > 0
    
    @pytest.mark.asyncio
    async def test_update_test_case_for_changes(
        self,
        framework,
        sample_test_case,
        ui_changes_description
    ):
        """Test updating test case for UI changes."""
        # Save test case first
        await framework.test_case_manager.repository.save(sample_test_case)
        
        # Mock LLM response
        framework.llm_provider.invoke.return_value = """
        {
            "updated_name": "Login Test (Updated)",
            "updated_description": "Updated login test for new UI",
            "updated_steps": [
                {
                    "step_number": 1,
                    "description": "Navigate to login page",
                    "action": "Open login page with new design",
                    "expected_result": "Page loads with new layout",
                    "validation_rules": ["New design elements visible"],
                    "timeout": 30
                }
            ],
            "new_preconditions": ["New UI is deployed"],
            "new_postconditions": [],
            "updated_test_data": {"email_field_id": "user-email"},
            "change_summary": "Updated for new UI elements",
            "confidence_level": "high"
        }
        """
        
        # Update test case
        updated_test_case = await framework.update_test_case_for_changes(
            test_case_id=sample_test_case.id,
            change_description=ui_changes_description,
            update_strategy="smart"
        )
        
        # Assertions
        assert updated_test_case.name == "Login Test (Updated)"
        assert updated_test_case.version == sample_test_case.version + 1
        assert updated_test_case.updated_by == "llm_maintenance_engine"
        assert "updated_for_changes" in updated_test_case.tags
        assert len(updated_test_case.steps) > 0
    
    @pytest.mark.asyncio
    async def test_bulk_update_test_cases(
        self,
        framework,
        ui_changes_description
    ):
        """Test bulk updating multiple test cases."""
        # Create multiple test cases
        test_cases = []
        for i in range(3):
            test_case = TestCase(
                name=f"Test Case {i+1}",
                description=f"Test case {i+1} description",
                test_type=TestType.FUNCTIONAL,
                priority=TestPriority.MEDIUM
            )
            await framework.test_case_manager.repository.save(test_case)
            test_cases.append(test_case)
        
        # Mock LLM response (will cycle)
        framework.llm_provider.invoke.return_value = """
        {
            "updated_name": "Updated Test Case",
            "updated_description": "Updated description",
            "updated_steps": [],
            "new_preconditions": [],
            "new_postconditions": [],
            "updated_test_data": {},
            "change_summary": "Bulk update applied",
            "confidence_level": "medium"
        }
        """
        
        # Bulk update
        test_case_ids = [tc.id for tc in test_cases]
        updated_cases = await framework.bulk_update_test_cases_for_changes(
            test_case_ids=test_case_ids,
            change_description=ui_changes_description,
            update_strategy="smart"
        )
        
        # Assertions
        assert len(updated_cases) == len(test_cases)
        for updated_case in updated_cases:
            assert updated_case.version == 2  # Original was 1
            assert updated_case.updated_by == "llm_maintenance_engine"
    
    @pytest.mark.asyncio
    async def test_test_maintenance_engine_impact_analysis(self):
        """Test TestMaintenanceEngine impact analysis."""
        engine = TestMaintenanceEngine()
        mock_llm = AsyncMock()
        
        # Mock LLM response
        mock_llm.invoke.return_value = """
        {
            "overall_impact": "high",
            "summary": "Significant changes detected",
            "test_case_impacts": [],
            "global_recommendations": ["Review all tests"]
        }
        """
        
        test_cases = [TestCase(name="Test", description="Test case")]
        ui_changes = "Major UI redesign"
        
        impact = await engine.analyze_ui_changes_impact(
            ui_changes_description=ui_changes,
            affected_test_cases=test_cases,
            llm_provider=mock_llm
        )
        
        assert impact["overall_impact"] == "high"
        assert "summary" in impact
        assert "test_case_impacts" in impact
        assert "global_recommendations" in impact


class TestAdvancedLLMIntegration:
    """Integration tests for advanced LLM features."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_requirements_to_maintenance(self):
        """Test complete flow from requirements to maintenance."""
        # This would test the complete workflow:
        # 1. Generate tests from requirements
        # 2. Simulate UI changes
        # 3. Analyze impact
        # 4. Update affected tests
        
        framework = await create_test_automation_framework(
            workspace_path="test_e2e_llm",
            environment="test"
        )
        
        try:
            # Mock LLM provider
            mock_llm = AsyncMock()
            framework.llm_provider = mock_llm
            
            # Mock responses for the complete flow
            responses = [
                # Requirements analysis
                '''[{
                    "feature_name": "Login",
                    "description": "Login feature",
                    "acceptance_criteria": ["User can login"],
                    "priority": "high",
                    "test_types": ["functional"],
                    "dependencies": [],
                    "user_roles": ["user"],
                    "business_rules": [],
                    "edge_cases": [],
                    "estimated_test_cases": 3
                }]''',
                # Scenario generation
                '''[{
                    "scenario_name": "Valid Login",
                    "test_type": "positive",
                    "feature_name": "Login",
                    "preconditions": [],
                    "test_steps": ["Login"],
                    "expected_results": ["Success"],
                    "test_data": {},
                    "priority": "high",
                    "risk_level": "low"
                }]''',
                # Test case generation
                '''{"name": "Login Test", "description": "Test login", "steps": []}''',
                # Impact analysis
                '''{"overall_impact": "medium", "test_case_impacts": []}''',
                # Test case update
                '''{"updated_name": "Updated Login Test", "updated_steps": []}'''
            ]
            
            import itertools
            response_cycle = itertools.cycle(responses)
            mock_llm.invoke.side_effect = lambda prompt: next(response_cycle)
            
            # Step 1: Generate from requirements
            requirements = "Users can login with email and password"
            test_cases = await framework.generate_test_cases_from_requirements(
                requirements_document=requirements,
                test_coverage_level="basic"
            )
            
            assert len(test_cases) > 0
            
            # Step 2: Analyze UI changes impact
            ui_changes = "Login button changed"
            impact = await framework.analyze_ui_changes_impact(
                ui_changes_description=ui_changes,
                affected_test_case_ids=[test_cases[0].id]
            )
            
            assert "overall_impact" in impact
            
            # Step 3: Update test case
            updated_case = await framework.update_test_case_for_changes(
                test_case_id=test_cases[0].id,
                change_description=ui_changes
            )
            
            assert updated_case.version > test_cases[0].version
            
        finally:
            await framework.cleanup()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
