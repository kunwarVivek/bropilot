"""
Unit Tests for Test Case Management

Tests the test case management components including models, managers, and repositories.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from src.test_management.models import (
    TestCase, TestSuite, TestStep, TestResult, TestExecution,
    TestCaseStatus, TestPriority, TestType, ExecutionStatus
)
from src.test_management.managers import (
    TestCaseManager, TestSuiteManager, TestExecutionManager
)


class TestTestCaseModel:
    """Test TestCase model functionality."""
    
    def test_test_case_creation(self):
        """Test test case creation with default values."""
        test_case = TestCase(
            name="Sample Test",
            description="Sample test description",
            test_type=TestType.FUNCTIONAL,
            priority=TestPriority.HIGH
        )
        
        assert test_case.name == "Sample Test"
        assert test_case.description == "Sample test description"
        assert test_case.test_type == TestType.FUNCTIONAL
        assert test_case.priority == TestPriority.HIGH
        assert test_case.status == TestCaseStatus.DRAFT
        assert test_case.version == 1
        assert len(test_case.steps) == 0
    
    def test_test_step_management(self):
        """Test adding and removing test steps."""
        test_case = TestCase(name="Step Test", description="Test for steps")
        
        # Add steps
        step1 = TestStep(
            description="First step",
            action="Navigate to homepage",
            expected_result="Homepage loads successfully"
        )
        
        step2 = TestStep(
            description="Second step", 
            action="Click login button",
            expected_result="Login form appears"
        )
        
        test_case.add_step(step1)
        test_case.add_step(step2)
        
        assert len(test_case.steps) == 2
        assert test_case.steps[0].step_number == 1
        assert test_case.steps[1].step_number == 2
        
        # Remove step
        removed = test_case.remove_step(step1.id)
        assert removed is True
        assert len(test_case.steps) == 1
        assert test_case.steps[0].step_number == 1  # Renumbered
        assert test_case.steps[0].id == step2.id
    
    def test_test_case_serialization(self):
        """Test test case to_dict serialization."""
        test_case = TestCase(
            name="Serialization Test",
            description="Test serialization",
            test_type=TestType.REGRESSION,
            priority=TestPriority.MEDIUM,
            tags=["serialization", "test"],
            target_url="https://example.com"
        )
        
        step = TestStep(
            description="Test step",
            action="Perform action",
            expected_result="Expected result"
        )
        test_case.add_step(step)
        
        data = test_case.to_dict()
        
        assert data["name"] == "Serialization Test"
        assert data["test_type"] == "regression"
        assert data["priority"] == "medium"
        assert data["tags"] == ["serialization", "test"]
        assert data["target_url"] == "https://example.com"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["description"] == "Test step"


class TestTestSuiteModel:
    """Test TestSuite model functionality."""
    
    def test_test_suite_creation(self):
        """Test test suite creation."""
        test_suite = TestSuite(
            name="Regression Suite",
            description="Regression test suite",
            test_case_ids=["tc1", "tc2", "tc3"],
            parallel_execution=True,
            max_parallel_workers=3
        )
        
        assert test_suite.name == "Regression Suite"
        assert len(test_suite.test_case_ids) == 3
        assert test_suite.execution_order == ["tc1", "tc2", "tc3"]
        assert test_suite.parallel_execution is True
        assert test_suite.max_parallel_workers == 3
    
    def test_test_case_management_in_suite(self):
        """Test adding and removing test cases from suite."""
        test_suite = TestSuite(name="Management Test", description="Test management")
        
        # Add test cases
        test_suite.add_test_case("tc1")
        test_suite.add_test_case("tc2")
        test_suite.add_test_case("tc3", position=1)  # Insert at position 1
        
        assert len(test_suite.test_case_ids) == 3
        assert "tc1" in test_suite.test_case_ids
        assert "tc2" in test_suite.test_case_ids
        assert "tc3" in test_suite.test_case_ids
        assert test_suite.execution_order[1] == "tc3"  # Inserted at position 1
        
        # Remove test case
        removed = test_suite.remove_test_case("tc2")
        assert removed is True
        assert len(test_suite.test_case_ids) == 2
        assert "tc2" not in test_suite.test_case_ids
        assert "tc2" not in test_suite.execution_order
    
    def test_test_case_reordering(self):
        """Test reordering test cases in suite."""
        test_suite = TestSuite(
            name="Reorder Test",
            test_case_ids=["tc1", "tc2", "tc3"],
            execution_order=["tc1", "tc2", "tc3"]
        )
        
        # Reorder test cases
        new_order = ["tc3", "tc1", "tc2"]
        success = test_suite.reorder_test_cases(new_order)
        
        assert success is True
        assert test_suite.execution_order == new_order
        
        # Try invalid reorder (missing test case)
        invalid_order = ["tc1", "tc4"]  # tc4 not in suite
        success = test_suite.reorder_test_cases(invalid_order)
        assert success is False


class TestTestExecutionModel:
    """Test TestExecution model functionality."""
    
    def test_test_execution_creation(self):
        """Test test execution creation."""
        execution = TestExecution(
            name="Test Execution",
            test_case_ids=["tc1", "tc2"],
            environment="staging"
        )
        
        assert execution.name == "Test Execution"
        assert len(execution.test_case_ids) == 2
        assert execution.environment == "staging"
        assert execution.status == ExecutionStatus.PENDING
        assert execution.total_tests == 0
    
    def test_test_result_management(self):
        """Test adding test results and statistics calculation."""
        execution = TestExecution(name="Result Test")
        
        # Add test results
        result1 = TestResult(
            test_case_id="tc1",
            status=ExecutionStatus.PASSED,
            duration=5.2
        )
        
        result2 = TestResult(
            test_case_id="tc2", 
            status=ExecutionStatus.FAILED,
            duration=3.1,
            error_message="Test failed"
        )
        
        result3 = TestResult(
            test_case_id="tc3",
            status=ExecutionStatus.SKIPPED
        )
        
        execution.add_result(result1)
        execution.add_result(result2)
        execution.add_result(result3)
        
        # Check statistics
        assert execution.total_tests == 3
        assert execution.passed_tests == 1
        assert execution.failed_tests == 1
        assert execution.skipped_tests == 1
        assert execution.get_success_rate() == 1/3  # 1 passed out of 3 total


class TestTestCaseManager:
    """Test TestCaseManager functionality."""
    
    @pytest.fixture
    def mock_repository(self):
        """Mock test case repository."""
        repo = AsyncMock()
        return repo
    
    @pytest.fixture
    def test_case_manager(self, mock_repository):
        """Create test case manager with mock repository."""
        return TestCaseManager(mock_repository)
    
    @pytest.mark.asyncio
    async def test_create_test_case(self, test_case_manager, mock_repository):
        """Test creating a test case."""
        mock_repository.save.return_value = None
        
        test_case = await test_case_manager.create_test_case(
            name="Manager Test",
            description="Test case created by manager",
            test_type=TestType.FUNCTIONAL,
            priority=TestPriority.HIGH
        )
        
        assert test_case.name == "Manager Test"
        assert test_case.test_type == TestType.FUNCTIONAL
        assert test_case.priority == TestPriority.HIGH
        mock_repository.save.assert_called_once_with(test_case)
    
    @pytest.mark.asyncio
    async def test_create_from_natural_language(self, test_case_manager, mock_repository):
        """Test creating test case from natural language."""
        mock_llm = AsyncMock()
        mock_repository.save.return_value = None
        
        # Mock the generator
        with patch.object(test_case_manager.generator, 'generate_from_description') as mock_generate:
            mock_test_case = TestCase(
                name="Generated Test",
                description="Generated from natural language"
            )
            mock_generate.return_value = mock_test_case
            
            test_case = await test_case_manager.create_from_natural_language(
                description="Test login functionality",
                llm_provider=mock_llm
            )
            
            assert test_case.name == "Generated Test"
            mock_generate.assert_called_once_with(
                "Test login functionality", mock_llm
            )
            mock_repository.save.assert_called_once_with(mock_test_case)
    
    @pytest.mark.asyncio
    async def test_get_test_case(self, test_case_manager, mock_repository):
        """Test getting a test case by ID."""
        mock_test_case = TestCase(name="Retrieved Test")
        mock_repository.get_by_id.return_value = mock_test_case
        
        result = await test_case_manager.get_test_case("test_id")
        
        assert result == mock_test_case
        mock_repository.get_by_id.assert_called_once_with("test_id")
    
    @pytest.mark.asyncio
    async def test_update_test_case(self, test_case_manager, mock_repository):
        """Test updating a test case."""
        test_case = TestCase(name="Update Test", version=1)
        original_updated_at = test_case.updated_at
        mock_repository.save.return_value = None
        
        updated_case = await test_case_manager.update_test_case(test_case)
        
        assert updated_case.version == 2
        assert updated_case.updated_at > original_updated_at
        mock_repository.save.assert_called_once_with(test_case)
    
    @pytest.mark.asyncio
    async def test_search_test_cases(self, test_case_manager, mock_repository):
        """Test searching test cases."""
        mock_results = [
            TestCase(name="Search Result 1"),
            TestCase(name="Search Result 2")
        ]
        mock_repository.search.return_value = mock_results
        
        results = await test_case_manager.search_test_cases(
            query="search",
            test_type=TestType.FUNCTIONAL,
            tags=["tag1", "tag2"]
        )
        
        assert len(results) == 2
        assert results[0].name == "Search Result 1"
        mock_repository.search.assert_called_once_with(
            query="search",
            test_type=TestType.FUNCTIONAL,
            priority=None,
            status=None,
            tags=["tag1", "tag2"],
            limit=100,
            offset=0
        )
    
    @pytest.mark.asyncio
    async def test_clone_test_case(self, test_case_manager, mock_repository):
        """Test cloning a test case."""
        original_case = TestCase(
            name="Original Test",
            description="Original description",
            test_type=TestType.FUNCTIONAL,
            tags=["tag1", "tag2"]
        )
        
        mock_repository.get_by_id.return_value = original_case
        mock_repository.save.return_value = None
        
        cloned_case = await test_case_manager.clone_test_case(
            "original_id", "Cloned Test"
        )
        
        assert cloned_case.name == "Cloned Test"
        assert cloned_case.description == "Original description"
        assert cloned_case.test_type == TestType.FUNCTIONAL
        assert cloned_case.tags == ["tag1", "tag2"]
        assert cloned_case.id != original_case.id
        
        mock_repository.get_by_id.assert_called_once_with("original_id")
        mock_repository.save.assert_called_once_with(cloned_case)


class TestTestSuiteManager:
    """Test TestSuiteManager functionality."""
    
    @pytest.fixture
    def mock_repositories(self):
        """Mock repositories."""
        suite_repo = AsyncMock()
        case_repo = AsyncMock()
        return suite_repo, case_repo
    
    @pytest.fixture
    def test_suite_manager(self, mock_repositories):
        """Create test suite manager with mock repositories."""
        suite_repo, case_repo = mock_repositories
        return TestSuiteManager(suite_repo, case_repo)
    
    @pytest.mark.asyncio
    async def test_create_test_suite(self, test_suite_manager, mock_repositories):
        """Test creating a test suite."""
        suite_repo, case_repo = mock_repositories
        suite_repo.save.return_value = None
        
        test_suite = await test_suite_manager.create_test_suite(
            name="Suite Test",
            description="Test suite creation",
            test_case_ids=["tc1", "tc2"],
            parallel_execution=True
        )
        
        assert test_suite.name == "Suite Test"
        assert len(test_suite.test_case_ids) == 2
        assert test_suite.parallel_execution is True
        suite_repo.save.assert_called_once_with(test_suite)
    
    @pytest.mark.asyncio
    async def test_get_test_suite_with_cases(self, test_suite_manager, mock_repositories):
        """Test getting test suite with populated test cases."""
        suite_repo, case_repo = mock_repositories
        
        # Mock suite
        mock_suite = TestSuite(
            name="Suite with Cases",
            test_case_ids=["tc1", "tc2"],
            execution_order=["tc1", "tc2"]
        )
        suite_repo.get_by_id.return_value = mock_suite
        
        # Mock test cases
        mock_case1 = TestCase(name="Test Case 1")
        mock_case2 = TestCase(name="Test Case 2")
        case_repo.get_by_id.side_effect = [mock_case1, mock_case2]
        
        result = await test_suite_manager.get_test_suite_with_cases("suite_id")
        
        assert result is not None
        assert result["suite"] == mock_suite
        assert len(result["test_cases"]) == 2
        assert result["test_cases"][0].name == "Test Case 1"
        assert result["test_cases"][1].name == "Test Case 2"
    
    @pytest.mark.asyncio
    async def test_add_test_cases_to_suite(self, test_suite_manager, mock_repositories):
        """Test adding test cases to a suite."""
        suite_repo, case_repo = mock_repositories
        
        # Mock suite
        mock_suite = TestSuite(name="Add Cases Test")
        suite_repo.get_by_id.return_value = mock_suite
        suite_repo.save.return_value = None
        
        # Mock test cases exist
        case_repo.get_by_id.return_value = TestCase(name="Existing Case")
        
        success = await test_suite_manager.add_test_cases_to_suite(
            "suite_id", ["tc1", "tc2"]
        )
        
        assert success is True
        assert len(mock_suite.test_case_ids) == 2
        assert "tc1" in mock_suite.test_case_ids
        assert "tc2" in mock_suite.test_case_ids
        suite_repo.save.assert_called_once_with(mock_suite)


class TestTestExecutionManager:
    """Test TestExecutionManager functionality."""
    
    @pytest.fixture
    def mock_repositories(self):
        """Mock repositories."""
        execution_repo = AsyncMock()
        case_repo = AsyncMock()
        suite_repo = AsyncMock()
        return execution_repo, case_repo, suite_repo
    
    @pytest.fixture
    def test_execution_manager(self, mock_repositories):
        """Create test execution manager with mock repositories."""
        execution_repo, case_repo, suite_repo = mock_repositories
        return TestExecutionManager(execution_repo, case_repo, suite_repo)
    
    @pytest.mark.asyncio
    async def test_execute_test_case(self, test_execution_manager, mock_repositories):
        """Test executing a single test case."""
        execution_repo, case_repo, suite_repo = mock_repositories
        
        # Mock test case
        mock_test_case = TestCase(
            name="Execution Test",
            description="Test for execution",
            target_url="https://example.com"
        )
        case_repo.get_by_id.return_value = mock_test_case
        execution_repo.save.return_value = None
        
        # Mock LLM provider
        mock_llm = AsyncMock()
        
        # Mock task runner
        with patch('src.test_management.managers.run_task') as mock_run_task:
            mock_run_task.return_value = "Task completed successfully"
            
            execution = await test_execution_manager.execute_test_case(
                test_case_id="tc1",
                llm_provider=mock_llm,
                environment="test"
            )
            
            assert execution is not None
            assert "tc1" in execution.test_case_ids
            assert execution.environment == "test"
            assert len(execution.test_results) == 1
            
            # Verify task runner was called
            mock_run_task.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_test_suite_sequential(self, test_execution_manager, mock_repositories):
        """Test executing a test suite sequentially."""
        execution_repo, case_repo, suite_repo = mock_repositories
        
        # Mock test suite
        mock_suite = TestSuite(
            name="Sequential Suite",
            test_case_ids=["tc1", "tc2"],
            execution_order=["tc1", "tc2"],
            parallel_execution=False
        )
        suite_repo.get_by_id.return_value = mock_suite
        
        # Mock test cases
        mock_case1 = TestCase(name="Test Case 1")
        mock_case2 = TestCase(name="Test Case 2")
        case_repo.get_by_id.side_effect = [mock_case1, mock_case2]
        
        execution_repo.save.return_value = None
        
        # Mock LLM provider
        mock_llm = AsyncMock()
        
        # Mock task runner
        with patch('src.test_management.managers.run_task') as mock_run_task:
            mock_run_task.return_value = "Task completed"
            
            execution = await test_execution_manager.execute_test_suite(
                test_suite_id="suite1",
                llm_provider=mock_llm,
                environment="test"
            )
            
            assert execution is not None
            assert execution.test_suite_id == "suite1"
            assert len(execution.test_results) == 2
            
            # Verify sequential execution (run_task called twice)
            assert mock_run_task.call_count == 2
